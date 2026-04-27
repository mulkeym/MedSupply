from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from backend.app.data.simulated import DEMAND_PROFILES, ITEMS, NODES, OPERATIONAL_STATES, ROUTES

DATABASE_PATH = Path(os.getenv("MEDSUPPLY_DATABASE", "backend/med_supply.db"))
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


def connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    with connection() as conn:
        conn.executescript(
            """
            create table if not exists items (
                id text primary key,
                name text not null,
                unit text not null,
                usage_per_draw real not null,
                usage_rate real,
                demand_basis text,
                criticality text not null
            );

            create table if not exists nodes (
                id text primary key,
                name text not null,
                type text not null,
                x integer not null,
                y integer not null,
                latitude real,
                longitude real,
                population integer not null,
                optempo text not null,
                stock_days integer not null
            );

            create table if not exists routes (
                id text primary key,
                source_node_id text not null,
                destination_node_id text not null,
                priority text not null,
                days integer not null,
                reliability real not null
            );

            create table if not exists operational_states (
                id text primary key,
                label text not null,
                demand_multiplier real not null,
                route_latency_multiplier real not null,
                description text not null
            );

            create table if not exists node_demand_profiles (
                node_id text primary key,
                active_supported_population integer not null,
                daily_encounter_rate real not null,
                phlebotomy_probability real not null,
                specimens_per_phlebotomy real not null,
                operational_state text not null,
                waste_factor real not null
            );

            create table if not exists inventory_balances (
                node_id text not null,
                item_id text not null,
                quantity_on_hand real not null,
                primary key (node_id, item_id)
            );
            """
        )
        _ensure_column(conn, "items", "usage_rate", "real")
        _ensure_column(conn, "items", "demand_basis", "text")
        _ensure_column(conn, "nodes", "latitude", "real")
        _ensure_column(conn, "nodes", "longitude", "real")
        if conn.execute("select count(*) from items").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into items (id, name, unit, usage_per_draw, usage_rate, demand_basis, criticality)
                values (:id, :name, :unit, :usage_per_draw, :usage_rate, :demand_basis, :criticality)
                """,
                ITEMS,
            )
        else:
            for item in ITEMS:
                conn.execute(
                    """
                    update items
                    set usage_rate = coalesce(usage_rate, :usage_rate),
                        demand_basis = coalesce(demand_basis, :demand_basis)
                    where id = :id
                    """,
                    item,
                )
        if conn.execute("select count(*) from nodes").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into nodes (id, name, type, x, y, latitude, longitude, population, optempo, stock_days)
                values (:id, :name, :type, :x, :y, :latitude, :longitude, :population, :optempo, :stock_days)
                """,
                NODES,
            )
        else:
            for node in NODES:
                conn.execute(
                    """
                    update nodes
                    set latitude = coalesce(latitude, :latitude),
                        longitude = coalesce(longitude, :longitude),
                        stock_days = max(stock_days, :stock_days)
                    where id = :id
                    """,
                    node,
                )
        if conn.execute("select count(*) from routes").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into routes (id, source_node_id, destination_node_id, priority, days, reliability)
                values (:id, :from, :to, :priority, :days, :reliability)
                """,
                ROUTES,
            )
        if conn.execute("select count(*) from operational_states").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into operational_states (id, label, demand_multiplier, route_latency_multiplier, description)
                values (:id, :label, :demand_multiplier, :route_latency_multiplier, :description)
                """,
                OPERATIONAL_STATES,
            )
        if conn.execute("select count(*) from node_demand_profiles").fetchone()[0] == 0:
            conn.executemany(
                """
                insert into node_demand_profiles (
                    node_id,
                    active_supported_population,
                    daily_encounter_rate,
                    phlebotomy_probability,
                    specimens_per_phlebotomy,
                    operational_state,
                    waste_factor
                )
                values (
                    :node_id,
                    :active_supported_population,
                    :daily_encounter_rate,
                    :phlebotomy_probability,
                    :specimens_per_phlebotomy,
                    :operational_state,
                    :waste_factor
                )
                """,
                DEMAND_PROFILES,
            )
        if conn.execute("select count(*) from inventory_balances").fetchone()[0] == 0:
            _seed_inventory_balances(conn)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    columns = {row["name"] for row in conn.execute(f"pragma table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"alter table {table} add column {column} {column_type}")


def get_items() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "select id, name, unit, usage_per_draw, usage_rate, demand_basis, criticality from items order by id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_nodes() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "select id, name, type, x, y, latitude, longitude, population, optempo, stock_days from nodes order by rowid"
        ).fetchall()
        return [dict(row) for row in rows]


def get_node(node_id: str) -> dict | None:
    return next((node for node in get_nodes() if node["id"] == node_id), None)


def update_node(node_id: str, node: dict) -> dict:
    with connection() as conn:
        cursor = conn.execute(
            """
            update nodes
            set name = :name,
                type = :type,
                latitude = :latitude,
                longitude = :longitude,
                population = :population,
                stock_days = :stock_days
            where id = :node_id
            """,
            {"node_id": node_id, **node},
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Unknown node: {node_id}")
    updated = get_node(node_id)
    if updated is None:
        raise ValueError(f"Unknown node: {node_id}")
    return updated


ROUTE_SCOPE_PRIORITIES = {
    "primary": {"primary"},
    "primary_secondary": {"primary", "secondary"},
    "all": {"primary", "secondary", "tertiary"},
}


def apply_global_stock_posture(stock_days: int, hub_route_scope: str = "primary") -> dict:
    states = {state["id"]: state for state in get_operational_states()}
    profiles = {profile["node_id"]: profile for profile in get_demand_profiles()}
    items = get_items()
    nodes = get_nodes()
    routes = get_routes()
    route_priorities = ROUTE_SCOPE_PRIORITIES.get(hub_route_scope, ROUTE_SCOPE_PRIORITIES["primary"])
    inventory_rows = []

    for node in nodes:
        for item in items:
            baseline = max(1, _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, route_priorities))
            inventory_rows.append(
                {
                    "node_id": node["id"],
                    "item_id": item["id"],
                    "quantity_on_hand": round(baseline * stock_days * ITEM_SKEW[item["id"]]),
                }
            )

    with connection() as conn:
        conn.execute("update nodes set stock_days = ?", (stock_days,))
        conn.executemany(
            """
            insert into inventory_balances (node_id, item_id, quantity_on_hand)
            values (:node_id, :item_id, :quantity_on_hand)
            on conflict(node_id, item_id) do update set
                quantity_on_hand = excluded.quantity_on_hand
            """,
            inventory_rows,
        )

    return {
        "stock_days": stock_days,
        "hub_route_scope": hub_route_scope,
        "nodes_updated": len(nodes),
        "balances_updated": len(inventory_rows),
    }


def get_routes() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            select
                id,
                source_node_id as 'from',
                destination_node_id as 'to',
                priority,
                days,
                reliability
            from routes
            order by rowid
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_operational_states() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            select id, label, demand_multiplier, route_latency_multiplier, description
            from operational_states
            order by demand_multiplier, id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_demand_profiles() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            select
                p.node_id,
                p.active_supported_population,
                p.daily_encounter_rate,
                p.phlebotomy_probability,
                p.specimens_per_phlebotomy,
                p.operational_state,
                p.waste_factor,
                s.label as operational_state_label,
                s.demand_multiplier as operational_state_multiplier,
                s.route_latency_multiplier as route_latency_multiplier
            from node_demand_profiles p
            join operational_states s on s.id = p.operational_state
            order by p.rowid
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_demand_profile(node_id: str) -> dict | None:
    return next((profile for profile in get_demand_profiles() if profile["node_id"] == node_id), None)


def update_demand_profile(node_id: str, profile: dict) -> dict:
    with connection() as conn:
        if conn.execute("select count(*) from operational_states where id = ?", (profile["operational_state"],)).fetchone()[0] == 0:
            raise ValueError(f"Unknown operational state: {profile['operational_state']}")
        cursor = conn.execute(
            """
            update node_demand_profiles
            set active_supported_population = :active_supported_population,
                daily_encounter_rate = :daily_encounter_rate,
                phlebotomy_probability = :phlebotomy_probability,
                specimens_per_phlebotomy = :specimens_per_phlebotomy,
                operational_state = :operational_state,
                waste_factor = :waste_factor
            where node_id = :node_id
            """,
            {"node_id": node_id, **profile},
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Unknown node demand profile: {node_id}")
    updated = get_demand_profile(node_id)
    if updated is None:
        raise ValueError(f"Unknown node demand profile: {node_id}")
    return updated


def get_inventory_balances() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            select
                i.node_id,
                i.item_id,
                item.name as item_name,
                item.unit,
                item.criticality,
                i.quantity_on_hand
            from inventory_balances i
            join items item on item.id = i.item_id
            order by i.node_id, item.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_node_inventory(node_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            select
                i.node_id,
                i.item_id,
                item.name as item_name,
                item.unit,
                item.criticality,
                i.quantity_on_hand
            from inventory_balances i
            join items item on item.id = i.item_id
            where i.node_id = ?
            order by item.name
            """,
            (node_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_node_inventory(node_id: str, balances: list[dict]) -> list[dict]:
    with connection() as conn:
        if conn.execute("select count(*) from nodes where id = ?", (node_id,)).fetchone()[0] == 0:
            raise ValueError(f"Unknown node: {node_id}")
        valid_items = {row["id"] for row in conn.execute("select id from items").fetchall()}
        for balance in balances:
            if balance["item_id"] not in valid_items:
                raise ValueError(f"Unknown item: {balance['item_id']}")
            conn.execute(
                """
                insert into inventory_balances (node_id, item_id, quantity_on_hand)
                values (:node_id, :item_id, :quantity_on_hand)
                on conflict(node_id, item_id) do update set
                    quantity_on_hand = excluded.quantity_on_hand
                """,
                {"node_id": node_id, **balance},
            )
    return get_node_inventory(node_id)


def _seed_inventory_balances(conn: sqlite3.Connection) -> None:
    states = {state["id"]: state for state in OPERATIONAL_STATES}
    profiles = {profile["node_id"]: profile for profile in DEMAND_PROFILES}
    rows = []
    for node in NODES:
        for item in ITEMS:
            baseline = max(1, _supported_daily_demand(node["id"], NODES, ROUTES, profiles, states, item))
            rows.append(
                {
                    "node_id": node["id"],
                    "item_id": item["id"],
                    "quantity_on_hand": round(baseline * node["stock_days"] * ITEM_SKEW[item["id"]]),
                }
            )
    conn.executemany(
        """
        insert into inventory_balances (node_id, item_id, quantity_on_hand)
        values (:node_id, :item_id, :quantity_on_hand)
        """,
        rows,
    )


def _seed_daily_demand(profile: dict, state: dict, item: dict) -> float:
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
    return base * state["demand_multiplier"] * profile["waste_factor"]


def _supported_daily_demand(
    node_id: str,
    nodes: list[dict],
    routes: list[dict],
    profiles: dict[str, dict],
    states: dict[str, dict],
    item: dict,
    route_priorities: set[str] | None = None,
) -> float:
    downstream_ids = _downstream_ids(node_id, routes, route_priorities or {"primary"})
    return sum(
        _seed_daily_demand(profiles[downstream_id], states[profiles[downstream_id]["operational_state"]], item)
        for downstream_id in downstream_ids
        if downstream_id in profiles and any(node["id"] == downstream_id for node in nodes)
    )


def _downstream_ids(node_id: str, routes: list[dict], route_priorities: set[str]) -> set[str]:
    children_by_node: dict[str, list[str]] = {}
    for route in routes:
        if route["priority"] not in route_priorities:
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
