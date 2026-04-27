from __future__ import annotations

from copy import deepcopy
from math import ceil

from backend.app.database import (
    get_demand_profiles,
    get_inventory_balances,
    get_items,
    get_nodes,
    get_operational_states,
    get_routes,
)
from backend.app.schemas import ForecastRequest

SEVERITY = {
    "low": {
        "mascal_peak": 3,
        "mascal_sustain": 1.5,
        "fpcon_demand": 1.1,
        "fpcon_latency": 1.25,
        "latency_multiplier": 1.5,
        "reliability_penalty": 0.12,
        "inventory_retained": 0.75,
    },
    "medium": {
        "mascal_peak": 5,
        "mascal_sustain": 2,
        "fpcon_demand": 1.25,
        "fpcon_latency": 1.5,
        "latency_multiplier": 2,
        "reliability_penalty": 0.25,
        "inventory_retained": 0.5,
    },
    "high": {
        "mascal_peak": 8,
        "mascal_sustain": 3,
        "fpcon_demand": 1.45,
        "fpcon_latency": 2,
        "latency_multiplier": 3,
        "reliability_penalty": 0.4,
        "inventory_retained": 0.25,
    },
}

ITEM_SKEW = {
    "gloves": 1,
    "tubes": 0.9,
    "butterfly": 0.72,
    "alcohol": 1.05,
    "gauze": 1.1,
    "tourniquet": 0.8,
    "bags": 0.88,
    "labels": 1.15,
}

LOCAL_STOCK_DAYS = {
    "Supplier": 180,
    "Prime vendor": 180,
    "Theater hub": 120,
    "Regional hub": 60,
    "MTF": 45,
    "Forward unit": 21,
    "Battalion aid": 14,
}

ROUTE_SCOPE_PRIORITIES = {
    "primary": {"primary"},
    "primary_secondary": {"primary", "secondary"},
    "all": {"primary", "secondary", "tertiary"},
}


def network_payload() -> dict:
    return {
        "items": get_items(),
        "nodes": get_nodes(),
        "routes": get_routes(),
        "operational_states": get_operational_states(),
        "demand_profiles": get_demand_profiles(),
        "inventory": get_inventory_balances(),
    }


def run_forecast(request: ForecastRequest) -> dict:
    items = get_items()
    nodes = get_nodes()
    routes = get_routes()
    profiles = {profile["node_id"]: profile for profile in get_demand_profiles()}
    states = {state["id"]: state for state in get_operational_states()}
    inventory = {
        (balance["node_id"], balance["item_id"]): balance["quantity_on_hand"]
        for balance in get_inventory_balances()
    }
    events = _events_from_request(request)
    route_priorities = ROUTE_SCOPE_PRIORITIES[request.hub_route_scope]
    route_results = [_forecast_route(route, routes, profiles, states, events) for route in routes]
    physically_reachable_nodes = _reachable_nodes(route_results)
    replenishment_nodes = _reachable_nodes(route_results, route_priorities)
    path_latencies = _path_latencies(routes, route_results, profiles, route_priorities)
    node_results = [
        _forecast_node(
            node,
            nodes,
            routes,
            profiles,
            states,
            items,
            inventory,
            events,
            route_results,
            physically_reachable_nodes,
            replenishment_nodes,
            path_latencies,
            request.forecast_horizon_days,
        )
        for node in nodes
    ]

    return {
        "event": events[0] if len(events) == 1 else None,
        "events": events,
        "horizon": request.forecast_horizon_days,
        "nodes": node_results,
        "routes": route_results,
        "metrics": _metrics(node_results, route_results),
        "recommendations": _recommendations(node_results, route_results),
    }


def _events_from_request(request: ForecastRequest) -> list[dict]:
    if request.events:
        return [
            _build_event(
                node_id=event.node_id,
                event_type=event.event_type,
                severity=event.severity,
                duration_days=event.duration_days,
                target_operational_state=event.target_operational_state,
            )
            for event in request.events
        ]
    if request.event_type is None:
        return []
    return [
        _build_event(
            node_id=request.selected_node_id,
            event_type=request.event_type,
            severity=request.severity,
            duration_days=request.duration_days,
            target_operational_state=request.target_operational_state,
        )
    ]

def _build_event(
    node_id: str,
    event_type: str,
    severity: str,
    duration_days: int,
    target_operational_state: str | None = None,
) -> dict:
    return {
        "node_id": node_id,
        "type": event_type,
        "duration": duration_days,
        "severity": SEVERITY[severity],
        "severity_name": severity,
        "target_operational_state": target_operational_state,
    }


def _forecast_node(
    node: dict,
    nodes: list[dict],
    routes: list[dict],
    profiles: dict[str, dict],
    states: dict[str, dict],
    items: list[dict],
    inventory: dict[tuple[str, str], float],
    events: list[dict],
    route_results: list[dict],
    physically_reachable_nodes: set[str],
    replenishment_nodes: set[str],
    path_latencies: dict[str, dict],
    horizon: int,
) -> dict:
    item_results = []
    profile = profiles[node["id"]]
    is_offline = _is_node_offline(node["id"], events)
    effective_stock_days = _effective_stock_days(node, events, route_results, replenishment_nodes)
    latency = path_latencies.get(node["id"], {"additional_days": 0, "current_days": None, "baseline_days": None})
    for item in items:
        baseline_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, None, 1)
        balance = _adjusted_inventory(node, item, inventory, events, effective_stock_days, baseline_demand)
        reorder_point = baseline_demand * 21
        critical_level = baseline_demand * 7
        stockout_day = None
        critical_day = None
        total_net_burn = 0

        if is_offline:
            stockout_day = 0
            critical_day = 0
        else:
            for day in range(1, horizon + 1):
                event_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, events, day)
                replenishment = baseline_demand if node["id"] in replenishment_nodes and day > latency["additional_days"] else 0
                net_burn = max(0, event_demand - replenishment)
                total_net_burn += net_burn
                balance -= net_burn
                if net_burn > 0 and critical_day is None and balance <= critical_level:
                    critical_day = day
                if net_burn > 0 and stockout_day is None and balance <= 0:
                    stockout_day = day
                    break

        event_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, events, min(horizon, 1))
        net_daily_burn = max(
            0,
            event_demand - (baseline_demand if node["id"] in replenishment_nodes and latency["additional_days"] == 0 else 0),
        )
        remaining_days = None if net_daily_burn == 0 else max(0, balance / max(1, net_daily_burn))
        item_results.append(
            {
                "item_id": item["id"],
                "item_name": item["name"],
                "balance": max(0, round(balance)),
                "reorder_point": round(reorder_point),
                "critical_level": round(critical_level),
                "stockout_day": stockout_day,
                "critical_day": critical_day,
                "remaining_days": None if remaining_days is None else round(remaining_days),
                "daily_burn_rate": round(event_demand, 2),
                "baseline_replenishment_rate": round(baseline_demand, 2) if node["id"] in replenishment_nodes and not is_offline else 0,
                "net_burn_rate": round(baseline_demand, 2) if is_offline else round(net_daily_burn, 2),
                "total_net_burn": round(total_net_burn, 2),
                "demand_basis": item["demand_basis"],
            }
        )

    first_stockout = _min_defined([item["stockout_day"] for item in item_results])
    first_critical = _min_defined([item["critical_day"] for item in item_results])
    riskiest = sorted(
        item_results,
        key=lambda item: item["stockout_day"] if item["stockout_day"] is not None else item["critical_day"] if item["critical_day"] is not None else 999,
    )[0]
    result = deepcopy(node)
    result["item_results"] = item_results
    result["demand_profile"] = profile
    result["daily_burn_rate"] = round(sum(item["daily_burn_rate"] for item in item_results), 2)
    result["offline"] = is_offline
    result["supply_reachable"] = node["id"] in physically_reachable_nodes
    result["replenishment_supported"] = node["id"] in replenishment_nodes and not is_offline
    result["effective_stock_days"] = effective_stock_days
    result["path_latency_days"] = latency["current_days"]
    result["baseline_path_latency_days"] = latency["baseline_days"]
    result["additional_path_latency_days"] = latency["additional_days"]
    result["first_stockout"] = first_stockout
    result["first_critical"] = first_critical
    result["riskiest_item"] = riskiest["item_name"]
    result["status"] = "offline" if is_offline else _status_for_node(first_stockout, first_critical, item_results, horizon)
    return result


def _forecast_route(
    route: dict,
    routes: list[dict],
    profiles: dict[str, dict],
    states: dict[str, dict],
    events: list[dict],
) -> dict:
    result = deepcopy(route)
    result["status"] = "normal"
    effective_state = _effective_operational_state(profiles[route["from"]], states, events, route["from"], 1)
    result["current_days"] = ceil(route["days"] * effective_state["route_latency_multiplier"])
    result["reliability"] = route["reliability"]

    if not events:
        return result

    alternate_destinations = set()
    for event in events:
        affected_outbound = route["from"] == event["node_id"] or route["to"] in _downstream_of(event["node_id"], routes)
        disrupted_primary_destinations = [
            candidate["to"]
            for candidate in routes
            if candidate["from"] == event["node_id"] and candidate["priority"] == "primary"
        ]
        alternate_destinations.update(disrupted_primary_destinations)

        if event["type"] == "hub_offline" and route["from"] == event["node_id"]:
            result["status"] = "blocked"
            result["reliability"] = 0
        elif event["type"] == "hub_degraded" and route["from"] == event["node_id"] and result["status"] != "blocked":
            result["status"] = "delayed"
            result["current_days"] = ceil(result["current_days"] * event["severity"]["latency_multiplier"])
            result["reliability"] = max(0.15, result["reliability"] - event["severity"]["reliability_penalty"])
        elif event["type"] == "fpcon" and affected_outbound and result["status"] != "blocked":
            result["status"] = "delayed"
            result["current_days"] = ceil(result["current_days"] * event["severity"]["fpcon_latency"])
            result["reliability"] = max(0.25, result["reliability"] - 0.18)

    if route["priority"] != "primary" and route["to"] in alternate_destinations and result["status"] == "normal":
        result["status"] = "alternate"

    return result


def _daily_demand(
    node: dict,
    profile: dict,
    item: dict,
    events: list[dict] | None,
    day: int,
    states: dict[str, dict],
) -> float:
    effective_state = _effective_operational_state(profile, states, events or [], node["id"], day)
    active_population = profile["active_supported_population"]
    encounter_rate = profile["daily_encounter_rate"]
    phlebotomy_probability = profile["phlebotomy_probability"]
    usage_rate = item["usage_rate"] if item["usage_rate"] is not None else item["usage_per_draw"]
    basis = item["demand_basis"] or "phlebotomy_event"

    if basis == "patient_encounter":
        base = active_population * encounter_rate * usage_rate
    elif basis == "personnel_day":
        base = active_population * usage_rate
    elif basis == "specimen":
        base = active_population * encounter_rate * phlebotomy_probability * profile["specimens_per_phlebotomy"] * usage_rate
    else:
        base = active_population * encounter_rate * phlebotomy_probability * usage_rate

    base *= effective_state["demand_multiplier"] * profile["waste_factor"]
    return base * _event_demand_multiplier(events or [], node["id"], day)


def _effective_operational_state(
    profile: dict,
    states: dict[str, dict],
    events: list[dict],
    node_id: str,
    day: int,
) -> dict:
    state_id = profile["operational_state"]
    for event in events:
        if event["type"] != "operational_state_change":
            continue
        if event["node_id"] != node_id:
            continue
        if day > event["duration"]:
            continue
        target_state = event.get("target_operational_state")
        if target_state in states:
            state_id = target_state
    return states.get(state_id, states[profile["operational_state"]])


def _supported_daily_demand(
    node_id: str,
    nodes: list[dict],
    routes: list[dict],
    profiles: dict[str, dict],
    states: dict[str, dict],
    item: dict,
    events: list[dict] | None,
    day: int,
) -> float:
    nodes_by_id = {node["id"]: node for node in nodes}
    return sum(
        _daily_demand(nodes_by_id[downstream_id], profiles[downstream_id], item, events, day, states)
        for downstream_id in _primary_downstream_ids(node_id, routes)
        if downstream_id in nodes_by_id and downstream_id in profiles
    )


def _primary_downstream_ids(node_id: str, routes: list[dict]) -> set[str]:
    children_by_node: dict[str, list[str]] = {}
    for route in routes:
        if route["priority"] != "primary":
            continue
        children_by_node.setdefault(route["from"], []).append(route["to"])

    downstream = {node_id}
    stack = list(children_by_node.get(node_id, []))
    while stack:
        child_id = stack.pop()
        if child_id in downstream:
            continue
        downstream.add(child_id)
        stack.extend(children_by_node.get(child_id, []))
    return downstream


def _event_demand_multiplier(events: list[dict], node_id: str, day: int) -> float:
    multiplier = 1
    for event in events:
        if not _is_event_node_affected(event, node_id) or day > event["duration"]:
            continue
        if event["type"] == "mascal":
            multiplier *= event["severity"]["mascal_peak"] if day <= 3 else event["severity"]["mascal_sustain"]
        elif event["type"] == "fpcon":
            multiplier *= event["severity"]["fpcon_demand"]
    return multiplier


def _node_inventory(node: dict, item: dict, baseline_demand: float) -> int:
    baseline = max(1, baseline_demand)
    return round(baseline * node["stock_days"] * ITEM_SKEW[item["id"]])


def _adjusted_inventory(
    node: dict,
    item: dict,
    inventory: dict[tuple[str, str], float],
    events: list[dict],
    effective_stock_days: int,
    baseline_demand: float,
) -> float:
    baseline = max(1, baseline_demand)
    stored_inventory = inventory.get((node["id"], item["id"]), _node_inventory(node, item, baseline_demand))
    effective_inventory = round(baseline * effective_stock_days * ITEM_SKEW[item["id"]])
    quantity = stored_inventory if effective_stock_days >= node["stock_days"] else min(stored_inventory, effective_inventory)
    for event in events:
        if event["type"] == "inventory_loss" and _is_event_node_affected(event, node["id"]):
            quantity *= event["severity"]["inventory_retained"]
    return quantity


def _effective_stock_days(node: dict, events: list[dict], route_results: list[dict], reachable_nodes: set[str]) -> int:
    if any(event["type"] == "hub_offline" and event["node_id"] == node["id"] for event in events):
        return 0
    if node["population"] == 0:
        return node["stock_days"]
    if node["id"] in reachable_nodes:
        return node["stock_days"]
    return min(node["stock_days"], LOCAL_STOCK_DAYS.get(node["type"], 21))


def _reachable_nodes(route_results: list[dict], route_priorities: set[str] | None = None) -> set[str]:
    roots = {"supplier"}
    reachable = set(roots)
    changed = True
    while changed:
        changed = False
        for route in route_results:
            if route["status"] == "blocked":
                continue
            if route_priorities is not None and route["priority"] not in route_priorities:
                continue
            if route["from"] in reachable and route["to"] not in reachable:
                reachable.add(route["to"])
                changed = True
    return reachable


def _path_latencies(
    routes: list[dict],
    route_results: list[dict],
    profiles: dict[str, dict],
    route_priorities: set[str],
) -> dict[str, dict]:
    baseline = _shortest_path_days(
        [
            {
                "from": route["from"],
                "to": route["to"],
                "current_days": ceil(route["days"] * profiles[route["from"]]["route_latency_multiplier"]),
                "status": "normal",
            }
            for route in routes
            if route["priority"] == "primary"
        ]
    )
    current = _shortest_path_days([
        route
        for route in route_results
        if route["status"] != "blocked" and route["priority"] in route_priorities
    ])
    node_ids = set(baseline) | set(current)
    return {
        node_id: {
            "baseline_days": baseline.get(node_id),
            "current_days": current.get(node_id),
            "additional_days": max(0, (current.get(node_id) or 0) - (baseline.get(node_id) or 0))
            if node_id in current and node_id in baseline
            else 0,
        }
        for node_id in node_ids
    }


def _shortest_path_days(routes: list[dict]) -> dict[str, int]:
    distances = {"supplier": 0}
    changed = True
    while changed:
        changed = False
        for route in routes:
            if route["from"] not in distances:
                continue
            candidate = distances[route["from"]] + route["current_days"]
            if route["to"] not in distances or candidate < distances[route["to"]]:
                distances[route["to"]] = candidate
                changed = True
    return distances


def _is_event_node_affected(event: dict, node_id: str) -> bool:
    if node_id == event["node_id"]:
        return True
    if event["type"] in {"mascal", "fpcon"}:
        return node_id in _downstream_of(event["node_id"], get_routes())
    return False


def _is_node_offline(node_id: str, events: list[dict]) -> bool:
    return any(event["type"] == "hub_offline" and event["node_id"] == node_id for event in events)


def _downstream_of(node_id: str, routes: list[dict]) -> list[str]:
    seen = set()
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        for route in routes:
            if route["from"] == current and route["priority"] == "primary" and route["to"] not in seen:
                seen.add(route["to"])
                queue.append(route["to"])
    return list(seen)


def _status_for_node(first_stockout: int | None, first_critical: int | None, item_results: list[dict], horizon: int) -> str:
    if first_stockout is not None and first_stockout <= horizon:
        return "stockout"
    if first_critical is not None and first_critical <= horizon:
        return "risk"
    if any(item["net_burn_rate"] > 0 and item["balance"] <= item["reorder_point"] for item in item_results):
        return "watch"
    return "healthy"


def _metrics(node_results: list[dict], route_results: list[dict]) -> dict:
    earliest_stockout = _min_defined([node["first_stockout"] for node in node_results])
    return {
        "nodes_at_risk": len([node for node in node_results if node["status"] in {"watch", "risk", "stockout", "offline"}]),
        "earliest_stockout": earliest_stockout,
        "routes_impacted": len([route for route in route_results if route["status"] != "normal"]),
    }


def _recommendations(node_results: list[dict], route_results: list[dict]) -> list[dict]:
    recommendations = []
    for node in node_results:
        if node["status"] not in {"risk", "stockout", "offline"}:
            continue
        inbound = [
            route
            for route in route_results
            if route["to"] == node["id"] and route["priority"] != "primary" and route["status"] != "blocked"
        ]
        if node["status"] == "offline":
            action = "Restore node operations or shift supported demand to alternate hubs"
        elif inbound:
            best = sorted(inbound, key=lambda route: route["current_days"])[0]
            action = f"Activate {best['priority']} route from {_node_name(best['from'])}"
        elif not node.get("supply_reachable", True):
            action = "No viable upstream route; push emergency package or restore a supply line"
        elif node["type"] in {"Forward unit", "Battalion aid"}:
            action = "Push a 72-hour emergency phlebotomy package"
        else:
            action = "Increase reorder priority and stage additional safety stock"
        recommendations.append(
            {
                "node_id": node["id"],
                "node_name": node["name"],
                "action": action,
                "status": node["status"],
                "first_stockout": node["first_stockout"],
                "riskiest_item": node["riskiest_item"],
            }
        )
    return recommendations


def _node_name(node_id: str) -> str:
    return next(node["name"] for node in get_nodes() if node["id"] == node_id)


def _min_defined(values: list[int | None]) -> int | None:
    defined = [value for value in values if value is not None]
    return min(defined) if defined else None
