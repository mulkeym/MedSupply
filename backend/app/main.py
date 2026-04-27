from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.database import (
    apply_global_stock_posture,
    get_demand_profiles,
    get_inventory_balances,
    get_items,
    get_node_inventory,
    get_nodes,
    get_operational_states,
    get_routes,
    initialize_database,
    update_demand_profile,
    update_node,
    update_node_inventory,
)
from backend.app.schemas import (
    DemandProfileUpdate,
    ForecastRequest,
    GlobalStockPostureUpdate,
    NodeInventoryUpdate,
    NodeUpdate,
)
from backend.app.services.forecast import network_payload, run_forecast

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Medical Resupply Predictor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/src", StaticFiles(directory=PROJECT_ROOT / "src"), name="frontend-src")


@app.get("/")
def gui() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/network")
def network() -> dict:
    return network_payload()


@app.put("/api/scenario/stock-posture")
def put_global_stock_posture(stock_posture: GlobalStockPostureUpdate) -> dict:
    apply_global_stock_posture(stock_posture.stock_days, stock_posture.hub_route_scope)
    return network_payload()


@app.get("/api/map-config")
def map_config() -> dict:
    api_key = os.getenv("MEDSUPPLY_GOOGLE_MAPS_API_KEY", "")
    return {
        "provider": "google",
        "enabled": bool(api_key),
        "api_key": api_key,
        "center": {"lat": 8.0, "lng": 137.0},
        "zoom": 4,
    }


@app.get("/api/items")
def items() -> list[dict]:
    return get_items()


@app.get("/api/nodes")
def nodes() -> list[dict]:
    return get_nodes()


@app.put("/api/nodes/{node_id}")
def put_node(node_id: str, node_update: NodeUpdate) -> dict:
    try:
        return update_node(node_id, node_update.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/routes")
def routes() -> list[dict]:
    return get_routes()


@app.get("/api/operational-states")
def operational_states() -> list[dict]:
    return get_operational_states()


@app.get("/api/demand-profiles")
def demand_profiles() -> list[dict]:
    return get_demand_profiles()


@app.get("/api/inventory")
def inventory() -> list[dict]:
    return get_inventory_balances()


@app.get("/api/nodes/{node_id}/inventory")
def node_inventory(node_id: str) -> list[dict]:
    return get_node_inventory(node_id)


@app.put("/api/nodes/{node_id}/inventory")
def put_node_inventory(node_id: str, inventory_update: NodeInventoryUpdate) -> list[dict]:
    try:
        return update_node_inventory(
            node_id,
            [balance.model_dump() for balance in inventory_update.balances],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/nodes/{node_id}/demand-profile")
def demand_profile(node_id: str, profile: DemandProfileUpdate) -> dict:
    try:
        return update_demand_profile(node_id, profile.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/forecast/run")
def forecast(request: ForecastRequest) -> dict:
    return run_forecast(request)
