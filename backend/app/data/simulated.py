ITEMS = [
    {"id": "gloves", "name": "Nitrile gloves", "unit": "pairs", "usage_per_draw": 2, "usage_rate": 2, "demand_basis": "phlebotomy_event", "criticality": "high"},
    {"id": "tubes", "name": "Blood collection tubes", "unit": "tubes", "usage_per_draw": 1.4, "usage_rate": 1.4, "demand_basis": "phlebotomy_event", "criticality": "high"},
    {"id": "butterfly", "name": "Butterfly needle sets", "unit": "sets", "usage_per_draw": 0.35, "usage_rate": 0.35, "demand_basis": "phlebotomy_event", "criticality": "high"},
    {"id": "alcohol", "name": "Alcohol prep pads", "unit": "pads", "usage_per_draw": 2, "usage_rate": 2, "demand_basis": "phlebotomy_event", "criticality": "medium"},
    {"id": "gauze", "name": "Gauze pads", "unit": "pads", "usage_per_draw": 1, "usage_rate": 1, "demand_basis": "phlebotomy_event", "criticality": "medium"},
    {"id": "tourniquet", "name": "Tourniquets", "unit": "each", "usage_per_draw": 0.08, "usage_rate": 0.08, "demand_basis": "phlebotomy_event", "criticality": "medium"},
    {"id": "bags", "name": "Specimen bags", "unit": "bags", "usage_per_draw": 0.35, "usage_rate": 0.35, "demand_basis": "specimen", "criticality": "medium"},
    {"id": "labels", "name": "Barcode labels", "unit": "labels", "usage_per_draw": 1.2, "usage_rate": 1.2, "demand_basis": "specimen", "criticality": "low"},
]

OPTEMPO = {
    "standby": 0.35,
    "garrison": 1,
    "training": 1.5,
    "mobilization": 1.75,
    "forward_deployed": 1.75,
    "deployment": 1.75,
    "active_operations": 2,
    "active": 2,
    "combat_operations": 3,
}

OPERATIONAL_STATES = [
    {"id": "standby", "label": "Reduced Manning / Standby", "demand_multiplier": 0.35, "route_latency_multiplier": 1.0, "description": "Minimal staffing and low routine patient flow."},
    {"id": "garrison", "label": "Garrison / Steady State", "demand_multiplier": 1.0, "route_latency_multiplier": 1.0, "description": "Baseline home-station medical demand."},
    {"id": "training", "label": "Training / Exercise", "demand_multiplier": 1.5, "route_latency_multiplier": 1.0, "description": "Higher routine injuries, readiness checks, and exercise tempo."},
    {"id": "mobilization", "label": "Deployment Prep / Mobilization", "demand_multiplier": 1.75, "route_latency_multiplier": 1.05, "description": "Pre-deployment screening and readiness processing."},
    {"id": "forward_deployed", "label": "Forward Deployed", "demand_multiplier": 1.75, "route_latency_multiplier": 1.15, "description": "Forward posture with increased medical workload and logistics friction."},
    {"id": "active_operations", "label": "Active Operations", "demand_multiplier": 2.0, "route_latency_multiplier": 1.2, "description": "Sustained operational workload above steady state."},
    {"id": "combat_operations", "label": "Combat Operations", "demand_multiplier": 3.0, "route_latency_multiplier": 1.35, "description": "High operational medical workload and degraded logistics reliability."},
]

NODES = [
    {"id": "supplier", "name": "Strategic Supplier", "type": "Supplier", "x": 590, "y": 55, "latitude": 32.7157, "longitude": -117.1611, "population": 0, "optempo": "garrison", "stock_days": 180},
    {"id": "dla", "name": "DLA Prime Vendor", "type": "Prime vendor", "x": 590, "y": 150, "latitude": 21.3187, "longitude": -157.9225, "population": 0, "optempo": "garrison", "stock_days": 180},
    {"id": "theater", "name": "Pacific Theater Medical Hub", "type": "Theater hub", "x": 590, "y": 255, "latitude": 13.4443, "longitude": 144.7937, "population": 4000, "optempo": "garrison", "stock_days": 180},
    {"id": "northHub", "name": "Regional Hub North", "type": "Regional hub", "x": 260, "y": 380, "latitude": 26.3344, "longitude": 127.8056, "population": 2200, "optempo": "training", "stock_days": 180},
    {"id": "centralHub", "name": "Regional Hub Central", "type": "Regional hub", "x": 590, "y": 390, "latitude": 14.8229, "longitude": 120.2827, "population": 2600, "optempo": "deployment", "stock_days": 180},
    {"id": "southHub", "name": "Regional Hub South", "type": "Regional hub", "x": 920, "y": 380, "latitude": -12.4258, "longitude": 130.8875, "population": 1800, "optempo": "garrison", "stock_days": 180},
    {"id": "mtfA", "name": "MTF Alpha", "type": "MTF", "x": 180, "y": 520, "latitude": 35.2836, "longitude": 139.6672, "population": 1400, "optempo": "training", "stock_days": 180},
    {"id": "mtfB", "name": "MTF Bravo", "type": "MTF", "x": 480, "y": 535, "latitude": 15.1850, "longitude": 120.5590, "population": 1600, "optempo": "deployment", "stock_days": 180},
    {"id": "mtfC", "name": "MTF Charlie", "type": "MTF", "x": 760, "y": 535, "latitude": -14.5211, "longitude": 132.3781, "population": 1300, "optempo": "garrison", "stock_days": 180},
    {"id": "fmuA", "name": "Forward Unit Red", "type": "Forward unit", "x": 95, "y": 650, "latitude": 34.1460, "longitude": 132.2350, "population": 650, "optempo": "training", "stock_days": 180},
    {"id": "basA", "name": "BAS Silver", "type": "Battalion aid", "x": 265, "y": 650, "latitude": 33.1595, "longitude": 129.7237, "population": 520, "optempo": "active", "stock_days": 180},
    {"id": "fmuB", "name": "Forward Unit Blue", "type": "Forward unit", "x": 480, "y": 660, "latitude": 10.3157, "longitude": 123.8854, "population": 740, "optempo": "deployment", "stock_days": 180},
    {"id": "basB", "name": "BAS Gold", "type": "Battalion aid", "x": 760, "y": 660, "latitude": 1.3521, "longitude": 103.8198, "population": 480, "optempo": "garrison", "stock_days": 180},
    {"id": "fmuC", "name": "Forward Unit Green", "type": "Forward unit", "x": 1010, "y": 650, "latitude": -19.2589, "longitude": 146.8169, "population": 610, "optempo": "training", "stock_days": 180},
]

ROUTES = [
    {"id": "r1", "from": "supplier", "to": "dla", "priority": "primary", "days": 14, "reliability": 0.93},
    {"id": "r2", "from": "dla", "to": "theater", "priority": "primary", "days": 10, "reliability": 0.9},
    {"id": "r3", "from": "theater", "to": "northHub", "priority": "primary", "days": 5, "reliability": 0.86},
    {"id": "r4", "from": "theater", "to": "centralHub", "priority": "primary", "days": 4, "reliability": 0.88},
    {"id": "r5", "from": "theater", "to": "southHub", "priority": "primary", "days": 6, "reliability": 0.84},
    {"id": "r6", "from": "northHub", "to": "mtfA", "priority": "primary", "days": 2, "reliability": 0.9},
    {"id": "r7", "from": "centralHub", "to": "mtfB", "priority": "primary", "days": 2, "reliability": 0.88},
    {"id": "r8", "from": "southHub", "to": "mtfC", "priority": "primary", "days": 3, "reliability": 0.83},
    {"id": "r9", "from": "mtfA", "to": "fmuA", "priority": "primary", "days": 1, "reliability": 0.82},
    {"id": "r10", "from": "mtfA", "to": "basA", "priority": "primary", "days": 1, "reliability": 0.8},
    {"id": "r11", "from": "mtfB", "to": "fmuB", "priority": "primary", "days": 1, "reliability": 0.8},
    {"id": "r12", "from": "mtfC", "to": "basB", "priority": "primary", "days": 1, "reliability": 0.82},
    {"id": "r13", "from": "mtfC", "to": "fmuC", "priority": "primary", "days": 2, "reliability": 0.78},
    {"id": "r14", "from": "theater", "to": "mtfB", "priority": "secondary", "days": 6, "reliability": 0.76},
    {"id": "r15", "from": "centralHub", "to": "mtfA", "priority": "secondary", "days": 4, "reliability": 0.74},
    {"id": "r16", "from": "northHub", "to": "mtfB", "priority": "secondary", "days": 5, "reliability": 0.73},
    {"id": "r17", "from": "southHub", "to": "mtfB", "priority": "tertiary", "days": 7, "reliability": 0.68},
    {"id": "r18", "from": "centralHub", "to": "mtfC", "priority": "secondary", "days": 5, "reliability": 0.72},
    {"id": "r19", "from": "mtfB", "to": "basB", "priority": "secondary", "days": 2, "reliability": 0.7},
]

DEMAND_PROFILES = [
    {"node_id": "supplier", "active_supported_population": 0, "daily_encounter_rate": 0.0, "phlebotomy_probability": 0.0, "specimens_per_phlebotomy": 1.0, "operational_state": "garrison", "waste_factor": 1.0},
    {"node_id": "dla", "active_supported_population": 0, "daily_encounter_rate": 0.0, "phlebotomy_probability": 0.0, "specimens_per_phlebotomy": 1.0, "operational_state": "garrison", "waste_factor": 1.0},
    {"node_id": "theater", "active_supported_population": 4000, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.38, "specimens_per_phlebotomy": 1.2, "operational_state": "garrison", "waste_factor": 1.08},
    {"node_id": "northHub", "active_supported_population": 2200, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.38, "specimens_per_phlebotomy": 1.2, "operational_state": "training", "waste_factor": 1.08},
    {"node_id": "centralHub", "active_supported_population": 2600, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.38, "specimens_per_phlebotomy": 1.2, "operational_state": "mobilization", "waste_factor": 1.08},
    {"node_id": "southHub", "active_supported_population": 1800, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.38, "specimens_per_phlebotomy": 1.2, "operational_state": "garrison", "waste_factor": 1.08},
    {"node_id": "mtfA", "active_supported_population": 1400, "daily_encounter_rate": 0.02, "phlebotomy_probability": 0.4, "specimens_per_phlebotomy": 1.25, "operational_state": "training", "waste_factor": 1.1},
    {"node_id": "mtfB", "active_supported_population": 1600, "daily_encounter_rate": 0.021, "phlebotomy_probability": 0.42, "specimens_per_phlebotomy": 1.25, "operational_state": "mobilization", "waste_factor": 1.1},
    {"node_id": "mtfC", "active_supported_population": 1300, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.36, "specimens_per_phlebotomy": 1.2, "operational_state": "garrison", "waste_factor": 1.08},
    {"node_id": "fmuA", "active_supported_population": 650, "daily_encounter_rate": 0.024, "phlebotomy_probability": 0.35, "specimens_per_phlebotomy": 1.1, "operational_state": "training", "waste_factor": 1.12},
    {"node_id": "basA", "active_supported_population": 520, "daily_encounter_rate": 0.028, "phlebotomy_probability": 0.32, "specimens_per_phlebotomy": 1.1, "operational_state": "active_operations", "waste_factor": 1.12},
    {"node_id": "fmuB", "active_supported_population": 740, "daily_encounter_rate": 0.026, "phlebotomy_probability": 0.36, "specimens_per_phlebotomy": 1.15, "operational_state": "forward_deployed", "waste_factor": 1.12},
    {"node_id": "basB", "active_supported_population": 480, "daily_encounter_rate": 0.018, "phlebotomy_probability": 0.3, "specimens_per_phlebotomy": 1.1, "operational_state": "garrison", "waste_factor": 1.1},
    {"node_id": "fmuC", "active_supported_population": 610, "daily_encounter_rate": 0.023, "phlebotomy_probability": 0.34, "specimens_per_phlebotomy": 1.1, "operational_state": "training", "waste_factor": 1.12},
]
