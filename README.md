# Medical Resupply Predictor POC

This is a proof of concept for simulating phlebotomy-support medical supply risk across a notional theater logistics network.

The frontend is a browser-based map interface. The backend is a Python FastAPI service that owns the simulated data and forecast calculations.

## Run The Prototype

Install backend dependencies:

```bash
cd backend
python3 -m pip install -r requirements.txt
```

Start the API from the repository root:

```bash
python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the GUI in a browser:

```text
http://127.0.0.1:8000/
```

The frontend calls:

```text
http://127.0.0.1:8000
```

## Google Map Configuration

The main GUI uses the regional Google Map view. Start the API with a Google Maps JavaScript API key:

```bash
MEDSUPPLY_GOOGLE_MAPS_API_KEY="your-key" python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The map uses approximate public city/base-area coordinates for INDOPACOM planning context. They are intentionally not exact facility coordinates and are not authoritative logistics data.

## What It Demonstrates

- Tabbed workflow separating operations from data entry
- A Google Maps regional logistics map with typed node markers and supply-line edges
- Simulated phlebotomy supply catalog and inventory
- Data tab node directory independent from the Operations map selection
- Editable core node details, burn-rate assumptions, and node-level inventory
- Editable node-level material inventory by item
- Global scenario control for setting all sites to common stock postures
- Configurable hub stock posture based on primary, secondary, or tertiary downstream coverage
- SQLite-backed synthetic data storage
- Python API-based impact calculation
- Node selection for hubs, MTFs, forward units, and aid stations
- Scenario events:
  - MASCAL demand surge
  - FPCON restriction
  - Hub degradation
  - Hub offline
  - Inventory loss
- Compound event queue for multi-node scenarios
- Forecast horizon selection
- Node risk coloring
- Route latency and alternate-route impact
- Item-level stockout and critical-level projections

## Key Files

- `docs/design.md`: product and model design document
- `docs/architecture-overview.md`: backend, data model, and burn-rate architecture decisions
- `backend/app/main.py`: FastAPI application and API routes
- `backend/app/services/forecast.py`: forecast and route-impact engine
- `backend/app/data/simulated.py`: synthetic phlebotomy supply chain dataset
- `backend/app/database.py`: SQLite setup and data access
- `backend/med_supply.db`: generated local SQLite database after first API startup
- `index.html`: static app shell
- `src/styles.css`: dashboard and map styling
- `src/app.js`: frontend API client and map rendering

## API Endpoints

```text
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
PUT  /api/nodes/{node_id}/inventory
PUT  /api/nodes/{node_id}/demand-profile
POST /api/forecast/run
```

## Suggested Demo Flow

1. Open `http://127.0.0.1:8000/`.
2. Use the `Operations` tab to select `Pacific Theater Medical Hub`.
3. Choose `Hub degradation`, `Medium`, `14 days`.
4. Add it to the event queue.
5. Select another node and add a second event if desired.
6. Run the queued scenario.
7. Review node colors, route statuses, the impact summary, and item risk table.
8. Use the `Data` tab node directory to review or edit node details, burn-rate assumptions, and material inventory without changing the Operations map selection.
9. Use the global stock posture control to compare one-week, 30-day, 60-day, and 180-day network postures.
9. Select an MTF or forward unit and compare projected stockouts.
10. Use `Clear Queue` to return the map to the green steady-state baseline.
