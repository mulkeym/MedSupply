# Medical Resupply Predictor Architecture Overview

## Architectural Direction

The proof of concept uses a web UI backed by a Python API. The browser renders the map and scenario controls, while the backend owns data storage, burn-rate assumptions, and impact calculations.

This keeps end-user computers simple: users need only a browser. Future data collection, database changes, scheduled ingestion, and model improvements can happen on the server side without changing client machines.

## Current Components

```text
Browser GUI
  - Google Maps regional supply-chain map
  - Node selection
  - Data tab node directory independent from operations selection
  - Global stock-posture scenario controls
  - Node detail controls
  - Burn-rate profile controls
  - Node-level material inventory controls
  - Event simulation controls
  - Impact and risk tables

FastAPI Backend
  - Serves the GUI
  - Exposes network and forecast APIs
  - Stores synthetic data in SQLite
  - Calculates burn rates and scenario impacts

SQLite Database
  - Items
  - Nodes
  - Routes
  - Operational states
  - Node demand profiles
  - Inventory balances
```

## API Surface

```text
GET  /
GET  /api/health
GET  /api/network
PUT  /api/scenario/stock-posture
GET  /api/map-config
GET  /api/items
GET  /api/nodes
PUT  /api/nodes/{node_id}
GET  /api/routes
GET  /api/operational-states
GET  /api/demand-profiles
GET  /api/inventory
GET  /api/nodes/{node_id}/inventory
PUT  /api/nodes/{node_id}/demand-profile
PUT  /api/nodes/{node_id}/inventory
POST /api/forecast/run
```

## Demand Model Decision

Burn rate is modeled per node, not globally. Each node has a demand profile that describes the population and medical workload generating consumption.

Core formula:

```text
daily demand =
active supported population
* workload driver
* item usage rate
* operational state multiplier
* event multiplier
* waste factor
```

The workload driver depends on the item demand basis:

```text
phlebotomy_event =
population * daily encounter rate * phlebotomy probability

specimen =
population * daily encounter rate * phlebotomy probability * specimens per phlebotomy

patient_encounter =
population * daily encounter rate

personnel_day =
population
```

This avoids forcing every supply item into a single "per draw" model.

## Node Demand Profile

Each node stores:

```text
node_id
active_supported_population
daily_encounter_rate
phlebotomy_probability
specimens_per_phlebotomy
operational_state
waste_factor
```

This separates assigned population from active demand. A node may be assigned 4,000 personnel but only have a subset actively generating medical consumption.

## Operational States

Operational states are stored as data rather than hard-coded logic.

Initial states:

| State | Demand Multiplier | Route Latency Multiplier |
|---|---:|---:|
| Reduced Manning / Standby | 0.35 | 1.00 |
| Garrison / Steady State | 1.00 | 1.00 |
| Training / Exercise | 1.50 | 1.00 |
| Deployment Prep / Mobilization | 1.75 | 1.05 |
| Forward Deployed | 1.75 | 1.15 |
| Active Operations | 2.00 | 1.20 |
| Combat Operations | 3.00 | 1.35 |

Terminology is intentionally understandable rather than overly doctrinal. It can be renamed later to match the target organization.

## Event Model

Events are scenario overlays. They may affect demand, supply routes, or inventory. The forecast API accepts an event queue so multiple node events can be compounded in the same run.

Current events:

| Event | Demand Effect | Supply Effect |
|---|---:|---|
| MASCAL | Acute spike, then sustained surge | None yet, priority recommendation only |
| FPCON restriction | Modest demand increase | Route latency increase |
| Hub degradation | No direct demand increase | Outbound route delay and reliability reduction |
| Hub offline | No direct demand increase | Primary outbound routes blocked |
| Inventory loss | No direct demand increase | Inventory reduced at selected node |

Operational state describes ongoing node posture. Events describe temporary disruption or surge.

Queued events are combined as follows:

- Demand events multiply together when they affect the same node on the same forecast day.
- Inventory-loss events reduce starting inventory for affected nodes.
- Hub degradation events stack route latency and reliability penalties on affected outbound routes.
- Hub offline events override affected primary outbound routes to blocked.
- FPCON events can delay affected downstream routes while also increasing demand.

The GUI keeps the queue visible in the right panel. A planner selects a node, configures an event, adds it to the queue, then runs the combined scenario.

## Inventory Policy

The current POC starts from a green steady-state baseline. Synthetic nodes are initialized with a 180-day stock posture so planners can begin with a healthy network, apply an event, and then inspect the forecasted degradation.

Inventory is stored as explicit node-and-item balances. The Data tab lets a planner select any node, view on-hand quantities by item, compare them against modeled daily burn, and update those balances. Forecasts use the stored inventory as the starting point before applying event effects and route reachability.

The Data tab uses its own selected node state. Selecting a node for data maintenance does not change the Operations map selection or the event target. The current editable node record fields are name, type, assigned personnel, target stock days, latitude, and longitude.

A global stock-posture control supports quick scenario setup. Setting all sites to 7, 30, 60, or 180 days updates both node `stock_days` and the explicit item inventory balances derived from each node's current burn-rate profile. Hub balances are sized from aggregate demand for the hub plus all primary downstream nodes it supports. This keeps the forecast behavior aligned with the visible scenario setting.

Forecast burn uses the same supported-demand view. A theater hub evaluates demand for the theater hub, regional hubs, MTFs, and forward units beneath it on primary routes. A regional hub evaluates itself and its primary downstream MTF and spoke nodes. Leaf nodes evaluate only their own demand.

The global stock-posture control also has a hub coverage option:

- Primary paths only: hub inventory covers nodes reachable through primary routes.
- Primary + secondary paths: hub inventory covers nodes reachable through primary or secondary routes.
- Primary + secondary + tertiary paths: hub inventory covers nodes reachable through all modeled route priorities.

This setting sizes inventory. The forecast burn rate still uses the current supported-demand view and route event effects; extra secondary or tertiary stock acts as contingency depth.

The forecast uses net drawdown rather than gross depletion. In steady state, baseline replenishment offsets baseline demand when a node remains supply-reachable, so a 30-day posture remains green during a no-event forecast. Inventory is consumed when demand exceeds baseline replenishment, when inventory is lost, or when routes disconnect the node from replenishment.

Path latency is included as a replenishment delay. The backend compares each node's current shortest reachable path from the strategic supplier to its normal primary-route path. Added latency creates a temporary replenishment gap, so affected nodes burn local posture for the extra days before baseline replenishment resumes. Blocked paths remove replenishment until an alternate reachable path exists.

The inventory calculation uses a simple days-of-supply model:

```text
initial inventory = baseline daily demand * stock_days * item skew
reorder point = baseline daily demand * 21
critical level = baseline daily demand * 7
```

Events are scenario overlays, not permanent changes. The GUI has a Clear Queue action that reruns the forecast with no events and returns the map to the steady-state baseline.

Supply-line disruptions are now included in the inventory posture. The backend computes route reachability after queued events are applied. If a node cannot be reached through any non-blocked primary, secondary, or tertiary route, it falls back to a smaller organic stock posture by echelon:

| Node Type | Organic Stock Days |
|---|---:|
| Theater hub | 120 |
| Regional hub | 60 |
| MTF | 45 |
| Forward unit | 21 |
| Battalion aid | 14 |

This lets secondary and tertiary routes preserve supply where they remain reachable, while disconnected spokes show risk even if the steady-state baseline is green.

This should later evolve into reorder quantities, shelf-life constraints, lot tracking, and item substitution rules.

## Data Storage Decision

SQLite is used for the POC because it is simple and local. The schema is intentionally close to a future Postgres model:

```text
items
nodes
routes
operational_states
node_demand_profiles
inventory_balances
```

Nodes include approximate public city/base-area latitude/longitude for regional map placement. They are intentionally not exact facility coordinates and should be replaced with authorized location data before operational use.

Google Maps is configured by setting:

```text
MEDSUPPLY_GOOGLE_MAPS_API_KEY
```

If the key is absent, the map area shows a setup message.

Recommended production direction:

```text
Postgres
PostGIS if real map coordinates and geospatial overlays are needed
scheduled ingestion jobs for external supply and encounter data
audit tables for scenario runs and user changes
```

## Future Work

High-value next steps:

- Add CSV import/export for items, nodes, routes, inventory, and demand profiles.
- Store forecast runs and scenario results for comparison.
- Add route capacity and partial fulfillment logic.
- Add item substitution rules.
- Add shelf-life and expiration-aware inventory.
- Add user roles and audit history.
- Replace synthetic data with authoritative logistics and medical workload feeds.
