from typing import Literal, Optional

from pydantic import BaseModel, Field


EventType = Literal["mascal", "fpcon", "hub_degraded", "hub_offline", "inventory_loss", "operational_state_change"]
Severity = Literal["low", "medium", "high"]
HubRouteScope = Literal["primary", "primary_secondary", "all"]


class ForecastRequest(BaseModel):
    selected_node_id: str = Field(..., examples=["theater"])
    event_type: Optional[EventType] = Field(default=None)
    severity: Severity = Field(default="medium")
    duration_days: int = Field(default=14, ge=1, le=180)
    forecast_horizon_days: int = Field(default=90, ge=1, le=365)
    hub_route_scope: HubRouteScope = Field(default="primary")
    target_operational_state: Optional[str] = None
    events: list["ScenarioEvent"] = Field(default_factory=list)


class ScenarioEvent(BaseModel):
    node_id: str
    event_type: EventType
    severity: Severity = Field(default="medium")
    duration_days: int = Field(default=14, ge=1, le=180)
    target_operational_state: Optional[str] = None


class DemandProfileUpdate(BaseModel):
    active_supported_population: int = Field(ge=0)
    daily_encounter_rate: float = Field(ge=0, le=1)
    phlebotomy_probability: float = Field(ge=0, le=1)
    specimens_per_phlebotomy: float = Field(ge=0)
    operational_state: str
    waste_factor: float = Field(ge=1, le=5)


class NodeUpdate(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    population: int = Field(ge=0)
    stock_days: int = Field(ge=0, le=365)


class GlobalStockPostureUpdate(BaseModel):
    stock_days: int = Field(ge=0, le=365)
    hub_route_scope: HubRouteScope = Field(default="primary")


class InventoryBalanceUpdate(BaseModel):
    item_id: str
    quantity_on_hand: float = Field(ge=0)


class NodeInventoryUpdate(BaseModel):
    balances: list[InventoryBalanceUpdate]
