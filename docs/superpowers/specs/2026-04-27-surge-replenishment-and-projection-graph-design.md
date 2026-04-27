# Surge Replenishment Model & Inventory Projection Graph

## Problem

Two gaps in the current forecast engine:

1. **Surge replenishment ignores path latency.** When a demand surge event occurs, replenishment stays at baseline level forever. The excess demand above baseline permanently burns local stock because surge replenishment never arrives. This is too pessimistic for long forecasts and fails to differentiate between nodes close to supply vs far away.

2. **No visual inventory projection.** Planners can see stockout day and current balance in the item risk table, but cannot see how inventory evolves over time. A graph showing projected balances across the forecast horizon would make risk trajectories immediately visible.

## Design

### 1. Surge Replenishment Model

**File:** `backend/app/services/forecast.py`, function `_forecast_node`

Current replenishment logic (line 207):
```python
replenishment = baseline_demand if reachable and day > additional_days else 0
```

New replenishment logic:
```python
full_path_latency = latency["current_days"] or 0
if node not reachable:
    replenishment = 0
elif day <= full_path_latency:
    # Surge request is in transit. Only baseline pipeline flows.
    replenishment = baseline_demand
else:
    # Surge supplies have arrived. Replenishment matches actual demand.
    replenishment = event_demand
```

Behavior:
- **Days 1 through `current_days` (full path latency):** Replenishment = baseline demand. Excess demand above baseline burns local stock. The surge resupply request is in transit through the supply chain.
- **Days after `current_days`:** Replenishment = event demand (capped at actual demand). Surge supplies have arrived. Net burn drops to zero for reachable nodes.
- **Unreachable nodes:** Replenishment = 0 throughout. No change from current behavior.
- **Route disruption:** Uses `current_days` (degraded/alternate path latency), not `baseline_days`. A degraded route means longer wait for surge supplies.

Impact: nodes close to supply (short path latency) recover quickly. Distant nodes at the end of long supply chains burn more stock before surge help arrives.

The `additional_days` concept is no longer needed for the replenishment calculation. It was previously used to delay baseline replenishment during route disruption, but the new model subsumes this: `current_days` already incorporates route degradation.

### 2. Daily Balance Timeseries (API Change)

**File:** `backend/app/services/forecast.py`, function `_forecast_node`

The day-by-day simulation loop already computes `balance` at each step. Currently this value is discarded after the loop. Change: capture it into a list.

Add to each item result:
```python
"daily_balances": [round(balance_at_day_1), round(balance_at_day_2), ...]
```

This is a list of length `horizon` (one entry per forecast day). Values represent projected on-hand quantity after that day's net burn.

No other API fields change. All existing response fields remain.

### 3. Inventory Projection Chart (Frontend)

**Files:** `index.html`, `src/app.js`, `src/styles.css`

**Library:** Chart.js via CDN (`<script>` tag in `index.html`). Lightweight, no build step, works with the existing static frontend.

**Chart placement:** New `<canvas>` element below the item risk table in the Operations tab right panel.

**Chart spec:**
- Type: line chart
- X-axis: forecast day (1 to horizon)
- Y-axis: projected balance (units)
- Lines: one per supply item (8 lines), each a distinct color
- Reference lines: horizontal dashed lines for reorder point and critical level of the riskiest item
- Legend: item names, matching line colors
- Responsive: fits the right panel width

**Updates when:**
- A new forecast runs (scenario or baseline)
- A different node is selected on the Operations map
- Queue is cleared (returns to baseline)

**Rendering function:** New `renderProjectionChart()` called alongside the existing `renderItemRiskTable()`. Uses the `daily_balances` array from the selected node's item results.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/forecast.py` | Update replenishment logic in `_forecast_node`; capture `daily_balances` per item |
| `index.html` | Add Chart.js CDN script tag; add `<canvas>` element for chart |
| `src/app.js` | Add `renderProjectionChart()` function; call it on forecast/node selection |
| `src/styles.css` | Style the chart container |

## Out of Scope

- Graduated ramp-up of surge replenishment (potential future enhancement)
- Per-item chart view (start with all items on one chart; float riskiest to top later)
- Upstream node surge capacity limits
- Chart interactivity beyond Chart.js defaults (tooltips are built in)
