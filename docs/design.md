# Medical Resupply Predictor POC Design

## Purpose

This proof of concept predicts phlebotomy-support supply risk across a notional USINDOPACOM-style medical logistics network. It is intended for planning demonstrations with simulated, unclassified data.

The first user workflow is:

1. View a hub-and-spoke medical supply chain map.
2. Start from a green steady-state baseline.
3. Select a node such as a logistics hub, MTF, or forward medical unit.
4. Add one or more events such as MASCAL, FPCON restriction, hub degradation, or hub offline to the queue.
5. Run a compound forecast.
6. See downstream stockout risk, affected routes, alternate supply options, and recommended actions.
7. Clear the queue to return to steady state.

## Scope

The POC focuses on consumables that support phlebotomy:

- Nitrile gloves
- Blood collection tubes
- Butterfly needle sets
- Alcohol prep pads
- Gauze pads
- Tourniquets
- Specimen bags
- Barcode labels

The current implementation uses a browser frontend backed by a Python FastAPI service. The backend owns the simulated data, SQLite persistence, and forecast calculations so future data collection can be added without changing end-user computers.

## Key Questions

The POC should answer:

- Which nodes fall below reorder point?
- Which nodes stock out during the forecast horizon?
- Which item causes the first mission risk?
- How do MASCAL or FPCON events affect demand?
- How does hub or route disruption affect resupply latency?
- Which secondary or tertiary route should be activated?
- What minimum supply levels should be targeted?

## Regional Network Model

The system models the supply chain as a directed graph.

### Node Types

- Strategic supplier
- DLA / prime vendor source
- Theater medical logistics hub
- Regional medical logistics hub
- MTF
- Forward medical unit
- Battalion aid station

Each node has:

- Name
- Type
- Supported population
- Active supported population
- Operational state
- Daily encounter rate
- Phlebotomy probability
- Current inventory by item
- Primary, secondary, and tertiary upstream supply options

### Route Types

Routes include:

- Source node
- Destination node
- Priority: primary, secondary, or tertiary
- Delivery latency in days
- Reliability score
- Status: normal, delayed, blocked, or alternate active

## Demand Model

Demand is rule based for transparency and is driven by per-node burn-rate profiles.

```text
Daily item demand =
active supported population
* workload driver
* item usage per draw
* operational state multiplier
* event demand multiplier
* waste factor
```

The workload driver depends on item demand basis. Phlebotomy supplies use phlebotomy events, specimen bags and labels use specimen volume, and future items can use patient encounters or personnel-days.

Default values:

- Daily encounter rate: 0.018
- Phlebotomy rate: 0.38
- Waste factor: 1.08
- Steady-state inventory posture: 180 days of baseline supply in the synthetic dataset

OPTEMPO multipliers:

| Mode | Multiplier |
|---|---:|
| Garrison | 1.0 |
| Training | 1.5 |
| Deployment prep | 1.75 |
| Active engagement | 2.0 |

Event multipliers:

| Event | Demand Effect | Supply Effect |
|---|---:|---|
| MASCAL | 5.0x first 3 days, 2.0x remainder | Priority resupply recommended |
| FPCON restriction | 1.25x | Route latency +50 percent |
| Hub degradation | 1.0x | Outbound route latency +100 percent, reliability reduction |
| Hub offline | 1.0x | Primary outbound routes blocked |
| Inventory loss | 1.0x | Inventory reduced at selected node |

## Inventory Policy

The POC uses three thresholds:

```text
target stock = 30 days of baseline demand
reorder point = 21 days of baseline demand
critical level = 7 days of baseline demand
```

For hubs, baseline demand is the aggregate demand of the hub plus all primary downstream nodes it supports. For leaf nodes, baseline demand is local node demand. This means a 30-day theater hub posture should cover 30 days of the primary downstream theater supply tree, not just the hub's assigned personnel.

The global stock posture tool can size hub inventory using primary routes only, primary plus secondary routes, or all primary/secondary/tertiary routes. This lets planners compare lean hub posture against a contingency posture that carries enough stock to support alternate-route responsibilities.

Forecasting uses net drawdown:

```text
net drawdown = event-adjusted demand - reachable baseline replenishment
```

In a no-event steady state, net drawdown is zero for reachable nodes. Scenario events create risk by increasing demand, reducing inventory, or disrupting replenishment.

Route latency affects replenishment timing. The model compares current path latency to normal primary path latency; the difference is treated as a temporary replenishment gap. During the gap, the node burns its local posture even if the route is still technically reachable.

Forecast status:

- Healthy: greater than reorder point
- Watch: less than reorder point
- At risk: forecasted below critical level
- Stockout: forecasted to reach zero

## Prediction Outputs

The app produces:

- Node risk status
- Days until first stockout
- First affected item
- Impacted downstream nodes
- Route status changes
- Alternate route recommendations
- Item-level days of supply

## Quality Metrics

When real or exercise data becomes available, track:

- Demand forecast mean absolute error
- Lead-time forecast error
- Stockout prediction precision
- Stockout prediction recall
- False-positive shortage rate
- False-negative shortage rate
- Days-of-supply error
- Recommendation success rate

For the synthetic POC, quality checks focus on whether scenario changes produce directionally correct outputs.

## Datasets Required For Production

- Inventory by node and item
- Item catalog and unit of issue
- Supported population by medical node
- Patient encounter volume
- Phlebotomy procedure frequency
- Requisition history
- Fulfillment lead times
- Transportation route latency
- Route reliability and capacity
- Event history for MASCAL, FPCON, training, and exercises
- Substitute item rules
- Shelf-life and storage constraints

## UI Design

The primary interface is a graph map.

- Node color shows worst projected supply status.
- Route style shows primary, secondary, or tertiary line.
- Route color shows normal, delayed, blocked, or alternate active.
- Selecting a node opens inventory, upstream options, and scenario controls.
- Running a scenario updates the map and impact panel.

Views:

- Operations tab with regional supply map, topology map, event queue, and forecast results
- Data tab with its own node directory, global stock-posture scenarios, node detail editing, burn-rate assumption editing, and material inventory controls
- Selected node panel
- Scenario controls
- Impact summary
- Item risk table
- Route impact table

## Implementation Notes

The first API-backed version uses:

- `backend/app/main.py`
- `backend/app/services/forecast.py`
- `backend/app/data/simulated.py`
- `backend/app/database.py`
- `backend/med_supply.db`
- `index.html`
- `src/styles.css`
- `src/app.js`

Future versions should store data in Postgres, add scheduled ingestion, and support CSV import/export.
