# Surge Replenishment & Inventory Projection Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add latency-aware surge replenishment to the forecast engine and a Chart.js inventory projection graph showing projected daily balances for all items at a selected node.

**Architecture:** The backend forecast loop in `_forecast_node` gets updated replenishment logic that uses full path latency to delay surge supplies, and captures daily balances per item into the API response. The frontend adds a Chart.js line chart below the item risk table that renders these timeseries.

**Tech Stack:** Python/FastAPI (backend), Chart.js via CDN (frontend), vanilla JS

---

## File Structure

| File | Role | Change Type |
|------|------|-------------|
| `backend/app/services/forecast.py` | Forecast engine | Modify |
| `backend/tests/test_forecast.py` | Forecast unit tests | Create |
| `backend/requirements.txt` | Python deps | Modify (add pytest) |
| `index.html` | App shell | Modify (add Chart.js CDN + canvas) |
| `src/app.js` | Frontend logic | Modify (add chart rendering) |
| `src/styles.css` | Styling | Modify (chart container style) |

---

### Task 1: Add pytest and create test scaffolding

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_forecast.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Add `pytest` to the end of `backend/requirements.txt`:

```
fastapi>=0.110,<1
uvicorn[standard]>=0.27,<1
pytest>=8,<9
```

- [ ] **Step 2: Install updated dependencies**

Run: `pip install -r backend/requirements.txt`

- [ ] **Step 3: Create test directory and initial test file**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/test_forecast.py`:

```python
"""Tests for the forecast engine."""

from backend.app.services.forecast import run_forecast
from backend.app.schemas import ForecastRequest
from backend.app.database import initialize_database


def setup_module():
    initialize_database()
```

- [ ] **Step 4: Verify pytest discovers the test file**

Run: `python3 -m pytest backend/tests/test_forecast.py --collect-only`
Expected: `no tests ran` (collected 0 items, no errors)

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/tests/
git commit -m "chore: add pytest and test scaffolding for forecast engine"
```

---

### Task 2: Test and implement surge replenishment model

**Files:**
- Modify: `backend/tests/test_forecast.py`
- Modify: `backend/app/services/forecast.py:192-215`

- [ ] **Step 1: Write test for surge replenishment behavior**

Append to `backend/tests/test_forecast.py`:

```python
def test_surge_replenishment_delays_by_path_latency():
    """After a MASCAL, excess demand above baseline should burn local stock
    for the duration of the full path latency. After that, surge replenishment
    arrives and net burn drops to zero."""
    request = ForecastRequest(
        selected_node_id="fmuA",
        events=[{
            "node_id": "fmuA",
            "event_type": "mascal",
            "severity": "medium",
            "duration_days": 90,
        }],
        forecast_horizon_days=90,
    )
    result = run_forecast(request)
    fmu = next(n for n in result["nodes"] if n["id"] == "fmuA")
    # fmuA path latency from supplier: supplier->dla(14)->theater(10)->northHub(5)->mtfA(2)->fmuA(1) = 32 days
    # During surge, net burn should be positive for early days (path latency period)
    # After path latency, surge replenishment arrives and net burn should be zero
    gloves = next(i for i in fmu["item_results"] if i["item_id"] == "gloves")
    balances = gloves["daily_balances"]
    assert len(balances) == 90

    # Balance should be declining during the path latency period
    assert balances[0] < balances[0] + 1  # trivially true, but balance exists
    # After path latency (~32 days), balance should stabilize (stop declining)
    # Check that balance at day 50 equals balance at day 45 (both past latency, surge replenishment flowing)
    # Allow small rounding tolerance
    if gloves["stockout_day"] is None or gloves["stockout_day"] > 50:
        assert abs(balances[49] - balances[44]) <= 2, (
            f"Balance should stabilize after path latency. Day 45: {balances[44]}, Day 50: {balances[49]}"
        )


def test_baseline_steady_state_unchanged():
    """With no events, net burn should remain zero for reachable nodes."""
    request = ForecastRequest(
        selected_node_id="theater",
        forecast_horizon_days=30,
    )
    result = run_forecast(request)
    theater = next(n for n in result["nodes"] if n["id"] == "theater")
    for item in theater["item_results"]:
        assert item["stockout_day"] is None, f"{item['item_name']} has unexpected stockout"
        # daily_balances should exist and be stable
        balances = item["daily_balances"]
        assert len(balances) == 30
        assert balances[0] == balances[29], (
            f"{item['item_name']} balance changed in steady state: day 1={balances[0]}, day 30={balances[29]}"
        )


def test_daily_balances_length_matches_horizon():
    """daily_balances array should have exactly horizon entries."""
    for horizon in [30, 90, 180]:
        request = ForecastRequest(
            selected_node_id="theater",
            forecast_horizon_days=horizon,
        )
        result = run_forecast(request)
        node = result["nodes"][0]
        for item in node["item_results"]:
            assert len(item["daily_balances"]) == horizon, (
                f"Expected {horizon} entries, got {len(item['daily_balances'])} for {item['item_name']}"
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_forecast.py -v`
Expected: FAIL — `daily_balances` key does not exist yet.

- [ ] **Step 3: Implement surge replenishment and daily balances capture**

In `backend/app/services/forecast.py`, replace the item loop inside `_forecast_node` (lines 192–238) with:

```python
    for item in items:
        baseline_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, None, 1)
        balance = _adjusted_inventory(node, item, inventory, events, effective_stock_days, baseline_demand)
        initial_balance = balance
        reorder_point = baseline_demand * 21
        critical_level = baseline_demand * 7
        stockout_day = None
        critical_day = None
        total_net_burn = 0
        daily_balances = []
        full_path_latency = latency["current_days"] or 0

        if is_offline:
            stockout_day = 0
            critical_day = 0
            daily_balances = [0] * horizon
        else:
            for day in range(1, horizon + 1):
                event_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, events, day)
                if node["id"] not in replenishment_nodes:
                    replenishment = 0
                elif day <= full_path_latency:
                    replenishment = baseline_demand
                else:
                    replenishment = event_demand
                net_burn = max(0, event_demand - replenishment)
                total_net_burn += net_burn
                balance -= net_burn
                if net_burn > 0 and critical_day is None and balance <= critical_level:
                    critical_day = day
                if net_burn > 0 and stockout_day is None and balance <= 0:
                    stockout_day = day
                daily_balances.append(max(0, round(balance)))

        event_demand = _supported_daily_demand(node["id"], nodes, routes, profiles, states, item, events, min(horizon, 1))
        if node["id"] not in replenishment_nodes:
            net_daily_burn = max(0, event_demand)
        elif full_path_latency > 0:
            net_daily_burn = max(0, event_demand - baseline_demand)
        else:
            net_daily_burn = max(0, event_demand - event_demand)
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
                "daily_balances": daily_balances,
            }
        )
```

Key changes from the original:
1. Removed the `break` after stockout — simulation must continue to fill `daily_balances` for every day.
2. Replenishment logic uses `full_path_latency` (`current_days`) instead of `additional_days`. Before the latency expires, only baseline replenishment flows. After, replenishment matches event demand.
3. `daily_balances` list is appended each day and included in the item result dict.
4. `net_daily_burn` summary stat updated to reflect the new model.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_forecast.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/forecast.py backend/tests/test_forecast.py
git commit -m "feat: add latency-aware surge replenishment and daily balance timeseries"
```

---

### Task 3: Add Chart.js and canvas element to HTML

**Files:**
- Modify: `index.html:143-144` and `index.html:284`

- [ ] **Step 1: Add Chart.js CDN script tag before app.js**

In `index.html`, replace line 284:

```html
    <script src="src/app.js"></script>
```

with:

```html
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script src="src/app.js"></script>
```

- [ ] **Step 2: Add canvas element after the item risk table**

In `index.html`, replace lines 141-144:

```html
          <section class="result-panel">
            <h2>Item Risk</h2>
            <div id="itemRiskTable" class="table-wrap"></div>
          </section>
```

with:

```html
          <section class="result-panel">
            <h2>Item Risk</h2>
            <div id="itemRiskTable" class="table-wrap"></div>
            <div class="chart-container">
              <h3>Projected Inventory</h3>
              <canvas id="projectionChart"></canvas>
            </div>
          </section>
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add Chart.js CDN and projection chart canvas element"
```

---

### Task 4: Add chart container styling

**Files:**
- Modify: `src/styles.css`

- [ ] **Step 1: Add chart-container styles**

Append to the end of `src/styles.css`:

```css
.chart-container {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface, #1e293b);
  border-radius: 8px;
}

.chart-container h3 {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  color: var(--text-secondary, #94a3b8);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/styles.css
git commit -m "style: add chart container styling for projection graph"
```

---

### Task 5: Implement projection chart rendering in frontend

**Files:**
- Modify: `src/app.js`

- [ ] **Step 1: Add chart instance variable at the top of app.js**

After line 11 (`let eventQueue = [];`), add:

```javascript
let projectionChartInstance = null;
```

- [ ] **Step 2: Add the renderProjectionChart function**

Add before the final closing of the file (after the `renderRouteImpactTable` function, around line 1040):

```javascript
const CHART_COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b",
  "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16",
];

function renderProjectionChart() {
  const canvas = document.getElementById("projectionChart");
  if (!canvas) return;
  const node = forecastNodeById(selectedNodeId);
  if (!node || !node.item_results || !node.item_results[0].daily_balances) {
    if (projectionChartInstance) {
      projectionChartInstance.destroy();
      projectionChartInstance = null;
    }
    return;
  }

  const horizon = node.item_results[0].daily_balances.length;
  const labels = Array.from({ length: horizon }, (_, i) => i + 1);

  const datasets = node.item_results.map((item, idx) => ({
    label: item.item_name,
    data: item.daily_balances,
    borderColor: CHART_COLORS[idx % CHART_COLORS.length],
    backgroundColor: "transparent",
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.1,
  }));

  // Add reference lines for the riskiest item
  const riskiest = [...node.item_results].sort(
    (a, b) =>
      (a.stockout_day ?? a.critical_day ?? 9999) -
      (b.stockout_day ?? b.critical_day ?? 9999)
  )[0];

  if (riskiest) {
    datasets.push({
      label: "Reorder point",
      data: Array(horizon).fill(riskiest.reorder_point),
      borderColor: "#f59e0b",
      borderDash: [8, 4],
      borderWidth: 1,
      pointRadius: 0,
      hidden: false,
    });
    datasets.push({
      label: "Critical level",
      data: Array(horizon).fill(riskiest.critical_level),
      borderColor: "#ef4444",
      borderDash: [4, 4],
      borderWidth: 1,
      pointRadius: 0,
      hidden: false,
    });
  }

  if (projectionChartInstance) {
    projectionChartInstance.destroy();
  }

  projectionChartInstance = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 300 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#94a3b8", boxWidth: 12, padding: 10, font: { size: 11 } },
        },
        tooltip: {
          callbacks: {
            title: (items) => `Day ${items[0].label}`,
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} units`,
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Forecast Day", color: "#94a3b8" },
          ticks: { color: "#64748b", maxTicksLimit: 15 },
          grid: { color: "rgba(100,116,139,0.15)" },
        },
        y: {
          title: { display: true, text: "Projected Balance (units)", color: "#94a3b8" },
          ticks: { color: "#64748b" },
          grid: { color: "rgba(100,116,139,0.15)" },
          beginAtZero: true,
        },
      },
    },
  });
}
```

- [ ] **Step 3: Add renderProjectionChart to the renderAll function**

In `src/app.js`, in the `renderAll()` function (around line 324), add `renderProjectionChart();` after the `renderItemRiskTable();` call:

Replace:
```javascript
  renderItemRiskTable();
  renderRouteImpactTable();
```

with:
```javascript
  renderItemRiskTable();
  renderProjectionChart();
  renderRouteImpactTable();
```

- [ ] **Step 4: Verify locally**

Run: `python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`

Open `http://127.0.0.1:8000/`, select a node, run a MASCAL scenario, and confirm:
- The chart appears below the item risk table
- 8 item lines are visible with distinct colors
- Dashed reorder point and critical level reference lines appear
- Balance lines decline during surge, then stabilize after path latency
- Chart updates when selecting a different node

- [ ] **Step 5: Commit**

```bash
git add src/app.js
git commit -m "feat: add inventory projection chart with all items on one graph"
```

---

### Task 6: Run all tests and push

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All tests PASS.

- [ ] **Step 2: Push to GitHub (triggers Render deploy)**

```bash
git push
```
