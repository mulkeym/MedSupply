const API_BASE = window.MEDSUPPLY_API_BASE || "";

let items = [];
let nodes = [];
let routes = [];
let operationalStates = [];
let inventoryBalances = [];
let mapConfig = null;
let selectedNodeId = "theater";
let dataSelectedNodeId = "theater";
let forecast = null;
let eventQueue = [];
let googleMapInstance = null;
let googleMapsLoadPromise = null;
let geoMarkers = [];
let geoLines = [];
let geoInfoWindow = null;
let geoLabels = [];

const map = document.getElementById("networkMap");
const geoMapShell = document.getElementById("geoMapShell");
const googleMapElement = document.getElementById("googleMap");
const mapSetupMessage = document.getElementById("mapSetupMessage");
const selectedNodeName = document.getElementById("selectedNodeName");
const selectedNodeMeta = document.getElementById("selectedNodeMeta");
const selectedNodeStats = document.getElementById("selectedNodeStats");
const dataNodeName = document.getElementById("dataNodeName");
const dataNodeMeta = document.getElementById("dataNodeMeta");
const dataNodeList = document.getElementById("dataNodeList");
const dataNodeStats = document.getElementById("dataNodeStats");
const nodeNameInput = document.getElementById("nodeNameInput");
const nodeTypeInput = document.getElementById("nodeTypeInput");
const nodePopulationInput = document.getElementById("nodePopulationInput");
const nodeStockDaysInput = document.getElementById("nodeStockDaysInput");
const nodeLatitudeInput = document.getElementById("nodeLatitudeInput");
const nodeLongitudeInput = document.getElementById("nodeLongitudeInput");
const globalStockPosture = document.getElementById("globalStockPosture");
const hubRouteScope = document.getElementById("hubRouteScope");
const impactSummary = document.getElementById("impactSummary");
const itemRiskTable = document.getElementById("itemRiskTable");
const routeImpactTable = document.getElementById("routeImpactTable");
const inventoryEditorTable = document.getElementById("inventoryEditorTable");
const activeEventBanner = document.getElementById("activeEventBanner");
const eventQueuePanel = document.getElementById("eventQueue");
const queueCount = document.getElementById("queueCount");
const eventType = document.getElementById("eventType");
const eventTypeDescription = document.getElementById("eventTypeDescription");
const eventStateTargetGroup = document.getElementById("eventStateTargetGroup");
const eventOperationalState = document.getElementById("eventOperationalState");
const eventOperationalStateDescription = document.getElementById("eventOperationalStateDescription");
const severity = document.getElementById("severity");
const severityDescription = document.getElementById("severityDescription");
const activePopulation = document.getElementById("activePopulation");
const operationalState = document.getElementById("operationalState");
const stateImpactPreview = document.getElementById("stateImpactPreview");
const stateEventDuration = document.getElementById("stateEventDuration");
const queueStateEventButton = document.getElementById("queueStateEventButton");
const encounterRate = document.getElementById("encounterRate");
const phlebotomyRate = document.getElementById("phlebotomyRate");
const specimensPerDraw = document.getElementById("specimensPerDraw");
const wasteFactor = document.getElementById("wasteFactor");

document.getElementById("runButton").addEventListener("click", runCurrentSimulation);
document.getElementById("resetButton").addEventListener("click", resetForecast);
document.getElementById("clearEventButton").addEventListener("click", resetForecast);
document.getElementById("addEventButton").addEventListener("click", addEventToQueue);
eventType.addEventListener("change", renderEventSimulationControls);
eventOperationalState.addEventListener("change", renderEventSimulationControls);
severity.addEventListener("change", renderSeverityDescription);
document.getElementById("applyGlobalStockButton").addEventListener("click", applyGlobalStockPosture);
document.querySelectorAll("button[data-stock-days]").forEach((button) => {
  button.addEventListener("click", () => {
    globalStockPosture.value = button.dataset.stockDays;
    applyGlobalStockPosture();
  });
});
document.getElementById("saveNodeButton").addEventListener("click", saveNodeDetails);
document.getElementById("saveProfileButton").addEventListener("click", saveDemandProfile);
document.getElementById("saveInventoryButton").addEventListener("click", saveNodeInventory);
queueStateEventButton.addEventListener("click", queueOperationalStateEvent);
document.getElementById("operationsTabButton").addEventListener("click", () => setActiveTab("operations"));
document.getElementById("dataTabButton").addEventListener("click", () => setActiveTab("data"));
operationalState.addEventListener("change", renderStateImpactPreview);

async function init() {
  showLoading("Loading network and baseline forecast.");
  try {
    const [networkResponse, forecastResponse, mapConfigResponse] = await Promise.all([
      fetch(`${API_BASE}/api/network`),
      fetch(`${API_BASE}/api/forecast/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_node_id: selectedNodeId,
          event_type: null,
          events: [],
          hub_route_scope: hubRouteScope.value,
          forecast_horizon_days: Number(document.getElementById("horizon").value)
        })
      }),
      fetch(`${API_BASE}/api/map-config`)
    ]);

    if (!networkResponse.ok || !forecastResponse.ok || !mapConfigResponse.ok) {
      throw new Error("API request failed");
    }

    const network = await networkResponse.json();
    items = network.items;
    nodes = network.nodes;
    routes = network.routes;
    operationalStates = network.operational_states;
    inventoryBalances = network.inventory;
    forecast = await forecastResponse.json();
    mapConfig = await mapConfigResponse.json();
    renderOperationalStateOptions();
    renderEventSimulationControls();
    renderSeverityDescription();
    renderAll();
  } catch (error) {
    showApiError(error);
  }
}

async function applyGlobalStockPosture() {
  showLoading("Applying global stock posture.");
  try {
    const response = await fetch(`${API_BASE}/api/scenario/stock-posture`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stock_days: Number(globalStockPosture.value),
        hub_route_scope: hubRouteScope.value
      })
    });

    if (!response.ok) {
      throw new Error(`Global stock posture update failed with HTTP ${response.status}`);
    }

    const network = await response.json();
    items = network.items;
    nodes = network.nodes;
    routes = network.routes;
    operationalStates = network.operational_states;
    inventoryBalances = network.inventory;
    await requestForecast({ events: eventQueue });
  } catch (error) {
    showApiError(error);
  }
}

async function saveNodeDetails() {
  showLoading("Saving node details.");
  try {
    const response = await fetch(`${API_BASE}/api/nodes/${dataSelectedNodeId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nodeNameInput.value.trim(),
        type: nodeTypeInput.value.trim(),
        population: Number(nodePopulationInput.value),
        stock_days: Number(nodeStockDaysInput.value),
        latitude: nodeLatitudeInput.value === "" ? null : Number(nodeLatitudeInput.value),
        longitude: nodeLongitudeInput.value === "" ? null : Number(nodeLongitudeInput.value)
      })
    });

    if (!response.ok) {
      throw new Error(`Node update failed with HTTP ${response.status}`);
    }

    const updated = await response.json();
    nodes = nodes.map((node) => node.id === dataSelectedNodeId ? updated : node);
    await requestForecast({ events: eventQueue });
  } catch (error) {
    showApiError(error);
  }
}

async function saveDemandProfile() {
  showLoading("Saving burn rate assumptions.");
  try {
    const response = await fetch(`${API_BASE}/api/nodes/${dataSelectedNodeId}/demand-profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        active_supported_population: Number(activePopulation.value),
        daily_encounter_rate: Number(encounterRate.value),
        phlebotomy_probability: Number(phlebotomyRate.value),
        specimens_per_phlebotomy: Number(specimensPerDraw.value),
        operational_state: operationalState.value,
        waste_factor: Number(wasteFactor.value)
      })
    });

    if (!response.ok) {
      throw new Error(`Demand profile update failed with HTTP ${response.status}`);
    }

    await requestForecast({
      events: eventQueue
    });
  } catch (error) {
    showApiError(error);
  }
}

async function saveNodeInventory() {
  showLoading("Saving material inventory.");
  try {
    const balances = [...document.querySelectorAll("input[data-inventory-item]")]
      .map((input) => ({
        item_id: input.dataset.inventoryItem,
        quantity_on_hand: Number(input.value)
      }));

    const response = await fetch(`${API_BASE}/api/nodes/${dataSelectedNodeId}/inventory`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ balances })
    });

    if (!response.ok) {
      throw new Error(`Inventory update failed with HTTP ${response.status}`);
    }

    const updated = await response.json();
    inventoryBalances = [
      ...inventoryBalances.filter((balance) => balance.node_id !== dataSelectedNodeId),
      ...updated
    ];
    await requestForecast({ events: eventQueue });
  } catch (error) {
    showApiError(error);
  }
}

async function resetForecast() {
  showLoading("Clearing active event and returning to steady state.");
  eventQueue = [];
  await requestForecast({ events: [] });
}

async function runCurrentSimulation() {
  await requestForecast({ events: eventQueue });
}

function addEventToQueue() {
  const queuedEvent = {
    id: window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    node_id: selectedNodeId,
    event_type: document.getElementById("eventType").value,
    severity: document.getElementById("severity").value,
    duration_days: Number(document.getElementById("duration").value)
  };
  if (queuedEvent.event_type === "operational_state_change") {
    queuedEvent.target_operational_state = eventOperationalState.value;
  }
  eventQueue.push(queuedEvent);
  renderEventQueue();
  renderActiveEventBanner();
}

function queueOperationalStateEvent() {
  eventQueue.push({
    id: window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    node_id: dataSelectedNodeId,
    event_type: "operational_state_change",
    target_operational_state: operationalState.value,
    severity: "medium",
    duration_days: Number(stateEventDuration.value)
  });
  renderEventQueue();
  renderActiveEventBanner();
}

function removeQueuedEvent(id) {
  eventQueue = eventQueue.filter((event) => event.id !== id);
  renderEventQueue();
  renderActiveEventBanner();
}

async function requestForecast({ events = eventQueue }) {
  showLoading("Running forecast.");
  try {
    const response = await fetch(`${API_BASE}/api/forecast/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_node_id: selectedNodeId,
        event_type: null,
        events: events.map(({ id, ...event }) => event),
        hub_route_scope: hubRouteScope.value,
        forecast_horizon_days: Number(document.getElementById("horizon").value)
      })
    });

    if (!response.ok) {
      throw new Error(`Forecast request failed with HTTP ${response.status}`);
    }

    forecast = await response.json();
    renderAll();
  } catch (error) {
    showApiError(error);
  }
}

function renderAll() {
  renderMap();
  renderGeoOverlay();
  renderSelectedNode();
  renderEventSimulationControls();
  renderDataNodeList();
  renderDataNodeHeader();
  renderNodeDetailControls();
  renderDemandProfileControls();
  renderStateImpactPreview();
  renderInventoryEditor();
  renderActiveEventBanner();
  renderEventQueue();
  renderSummary();
  renderItemRiskTable();
  renderRouteImpactTable();
  renderMetrics();
}

function setActiveTab(tab) {
  const operationsActive = tab === "operations";
  document.getElementById("operationsTabButton").classList.toggle("active", operationsActive);
  document.getElementById("dataTabButton").classList.toggle("active", !operationsActive);
  document.getElementById("operationsTab").classList.toggle("active", operationsActive);
  document.getElementById("dataTab").classList.toggle("active", !operationsActive);
}

function renderActiveEventBanner() {
  const clearButton = document.getElementById("clearEventButton");
  if (!eventQueue.length) {
    activeEventBanner.classList.remove("active");
    activeEventBanner.innerHTML = `<strong>Steady state baseline</strong>No active event is applied. Nodes should remain green unless burn-rate assumptions are changed.`;
    clearButton.disabled = true;
    return;
  }

  activeEventBanner.classList.add("active");
  activeEventBanner.innerHTML = `<strong>Queued scenario</strong>${eventQueue.length} event${eventQueue.length === 1 ? "" : "s"} ready to run or already applied.`;
  clearButton.disabled = false;
}

function renderEventQueue() {
  queueCount.textContent = `${eventQueue.length} queued`;
  if (!eventQueue.length) {
    eventQueuePanel.innerHTML = `<div class="queue-item"><strong>No queued events</strong><span>Select a node and add an event to build a compound scenario.</span></div>`;
    return;
  }

  eventQueuePanel.innerHTML = eventQueue
    .map((event) => `
      <div class="queue-item">
        <strong>${describeQueuedEvent(event)}</strong>
        <span>${eventDetailSummary(event)}</span>
        <button type="button" data-event-id="${event.id}">Remove</button>
      </div>
    `)
    .join("");

  eventQueuePanel.querySelectorAll("button[data-event-id]").forEach((button) => {
    button.addEventListener("click", () => removeQueuedEvent(button.dataset.eventId));
  });
}

function renderOperationalStateOptions() {
  const options = operationalStates
    .map((state) => `<option value="${state.id}">${state.label} (${state.demand_multiplier}x)</option>`)
    .join("");
  operationalState.innerHTML = options;
  eventOperationalState.innerHTML = options;
}

function renderEventSimulationControls() {
  renderEventTypeDescription();
  const stateEventSelected = eventType.value === "operational_state_change";
  eventStateTargetGroup.classList.toggle("visible", stateEventSelected);
  severity.disabled = stateEventSelected;
  if (stateEventSelected) {
    severity.value = "medium";
    const node = forecastNodeById(selectedNodeId);
    const currentStateId = node?.demand_profile?.operational_state;
    if (!eventOperationalState.value || eventOperationalState.value === currentStateId) {
      const alternateState = operationalStates.find((state) => state.id !== currentStateId);
      eventOperationalState.value = alternateState?.id || currentStateId || operationalStates[0]?.id || "";
    }
    const selectedState = operationalStates.find((state) => state.id === eventOperationalState.value);
    eventOperationalStateDescription.textContent = selectedState
      ? `${selectedState.description} Route latency uses ${selectedState.route_latency_multiplier}x for outbound paths from the selected node.`
      : "";
  } else {
    eventOperationalStateDescription.textContent = "";
  }
}

function renderEventTypeDescription() {
  const descriptions = {
    mascal: "Mass-casualty surge: increases phlebotomy-related demand at the selected node and downstream supported nodes for the event duration.",
    fpcon: "Force-protection restriction: adds moderate demand pressure and slows affected downstream routes to represent access controls and movement friction.",
    hub_degraded: "Hub degradation: keeps the hub online but delays outbound routes and reduces route reliability.",
    hub_offline: "Hub offline: marks the selected hub offline and blocks its outbound routes, forcing supported nodes onto available alternates if stocked and reachable.",
    inventory_loss: "Inventory loss: immediately reduces on-hand stock at the selected node and affected downstream nodes without changing route availability.",
    operational_state_change: "Operational state change: applies a temporary state shift to the selected node, changing burn rate and route latency during the event window."
  };
  eventTypeDescription.textContent = descriptions[eventType.value] || "";
}

function renderSeverityDescription() {
  const descriptions = {
    low: "Low: limited disruption. Demand, latency, reliability, or inventory effects are mild and usually preserve planning margin.",
    medium: "Medium: planning baseline for a meaningful disruption. Effects are large enough to expose weak stock posture or fragile routes.",
    high: "High: severe disruption. Demand surge, route delay, reliability loss, or inventory loss is amplified and should stress the network."
  };
  severityDescription.textContent = descriptions[severity.value] || "";
}

function renderMap() {
  map.innerHTML = "";
  const routeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const nodeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  map.appendChild(routeLayer);
  map.appendChild(nodeLayer);

  forecast.routes.forEach((route) => {
    const from = nodeById(route.from);
    const to = nodeById(route.to);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const curve = Math.abs(from.x - to.x) > 160 ? 38 : 0;
    const midY = (from.y + to.y) / 2 - curve;
    path.setAttribute("d", `M ${from.x} ${from.y + 28} C ${from.x} ${midY}, ${to.x} ${midY}, ${to.x} ${to.y - 28}`);
    path.setAttribute("class", `route ${route.priority} ${route.status}`);
    routeLayer.appendChild(path);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", (from.x + to.x) / 2);
    label.setAttribute("y", (from.y + to.y) / 2 - curve - 6);
    label.setAttribute("class", "route-label");
    label.textContent = `${route.current_days}d`;
    routeLayer.appendChild(label);
  });

  forecast.nodes.forEach((node) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", `node-group ${node.id === selectedNodeId ? "selected" : ""}`);
    group.setAttribute("tabindex", "0");
    group.addEventListener("click", () => {
      selectedNodeId = node.id;
      renderAll();
    });

    const shape = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    shape.setAttribute("x", node.x - 58);
    shape.setAttribute("y", node.y - 30);
    shape.setAttribute("width", 116);
    shape.setAttribute("height", 60);
    shape.setAttribute("rx", node.type.includes("hub") || node.type === "Supplier" ? 8 : 4);
    shape.setAttribute("class", "node-shape");
    shape.setAttribute("fill", statusColor(node.status));
    group.appendChild(shape);

    const daysBadge = document.createElementNS("http://www.w3.org/2000/svg", "text");
    daysBadge.setAttribute("x", node.x);
    daysBadge.setAttribute("y", node.y - 8);
    daysBadge.setAttribute("class", "node-days");
    daysBadge.textContent = node.first_stockout ? `${node.first_stockout}d` : node.status === "healthy" ? "OK" : "Watch";
    group.appendChild(daysBadge);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", node.x);
    label.setAttribute("y", node.y + 50);
    label.setAttribute("class", "node-label");
    label.textContent = node.name;
    group.appendChild(label);

    const type = document.createElementNS("http://www.w3.org/2000/svg", "text");
    type.setAttribute("x", node.x);
    type.setAttribute("y", node.y + 66);
    type.setAttribute("class", "node-type");
    type.textContent = node.type;
    group.appendChild(type);

    nodeLayer.appendChild(group);
  });
}

async function renderGeoOverlay() {
  if (!forecast || !mapConfig) return;
  if (!mapConfig.enabled) {
    mapSetupMessage.textContent = "Google Maps is not configured. Set MEDSUPPLY_GOOGLE_MAPS_API_KEY in the backend environment and restart the API to enable the regional map overlay.";
    mapSetupMessage.classList.add("visible");
    return;
  }

  try {
    await loadGoogleMaps();
  } catch (error) {
    mapSetupMessage.textContent = `Google Maps failed to load: ${error.message}`;
    mapSetupMessage.classList.add("visible");
    return;
  }

  mapSetupMessage.classList.remove("visible");
  if (!googleMapInstance) {
    googleMapInstance = new google.maps.Map(googleMapElement, {
      center: mapConfig.center,
      zoom: mapConfig.zoom,
      mapTypeId: "terrain",
      streetViewControl: false,
      fullscreenControl: true,
      mapTypeControl: true
    });
    geoInfoWindow = new google.maps.InfoWindow();
  }

  clearGeoOverlay();
  renderGeoRoutes();
  renderGeoNodes();
}

function loadGoogleMaps() {
  if (window.google && window.google.maps) return Promise.resolve();
  if (googleMapsLoadPromise) return googleMapsLoadPromise;

  googleMapsLoadPromise = new Promise((resolve, reject) => {
    const callbackName = "initMedSupplyGoogleMap";
    window[callbackName] = () => {
      delete window[callbackName];
      resolve();
    };

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(mapConfig.api_key)}&callback=${callbackName}`;
    script.async = true;
    script.defer = true;
    script.onerror = () => reject(new Error("script request failed"));
    document.head.appendChild(script);
  });

  return googleMapsLoadPromise;
}

function clearGeoOverlay() {
  geoMarkers.forEach((marker) => marker.setMap(null));
  geoLines.forEach((line) => line.setMap(null));
  geoLabels.forEach((label) => label.setMap(null));
  geoMarkers = [];
  geoLines = [];
  geoLabels = [];
}

function renderGeoRoutes() {
  forecast.routes.forEach((route) => {
    const from = nodeById(route.from);
    const to = nodeById(route.to);
    if (!hasGeoPoint(from) || !hasGeoPoint(to)) return;

    const line = new google.maps.Polyline({
      path: [
        { lat: from.latitude, lng: from.longitude },
        { lat: to.latitude, lng: to.longitude }
      ],
      geodesic: true,
      strokeColor: routeColor(route),
      strokeOpacity: route.priority === "primary" ? 0.86 : 0,
      strokeWeight: route.priority === "primary" ? 3 : 2,
      icons: geoRoutePattern(route),
      map: googleMapInstance
    });

    line.addListener("click", () => {
      geoInfoWindow.setContent(`
        <strong>${from.name} -> ${to.name}</strong><br>
        Route: ${route.priority}<br>
        Status: ${route.status}<br>
        Latency: ${route.current_days} days<br>
        Reliability: ${Math.round(route.reliability * 100)}%
      `);
      geoInfoWindow.setPosition(geoMidpoint(from, to));
      geoInfoWindow.open(googleMapInstance);
    });

    geoLines.push(line);
    geoLabels.push(createGeoRouteLabel(route, from, to));
  });
}

function geoRoutePattern(route) {
  if (route.priority === "primary") return [];
  if (route.priority === "tertiary") {
    return [
      {
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: routeColor(route),
          fillOpacity: 0.8,
          scale: 2.3,
          strokeColor: routeColor(route),
          strokeOpacity: 0.8,
          strokeWeight: 1
        },
        offset: "0",
        repeat: "14px"
      }
    ];
  }
  return [
    {
      icon: {
        path: "M 0,-1 0,1",
        strokeColor: routeColor(route),
        strokeOpacity: 0.82,
        strokeWeight: 2.5,
        scale: 3
      },
      offset: "0",
      repeat: "18px"
    }
  ];
}

function renderGeoNodes() {
  forecast.nodes.forEach((node) => {
    if (!hasGeoPoint(node)) return;
    const marker = new google.maps.Marker({
      position: { lat: node.latitude, lng: node.longitude },
      map: googleMapInstance,
      title: node.name,
      icon: markerIcon(node)
    });

    marker.addListener("click", () => {
      selectedNodeId = node.id;
      geoInfoWindow.setContent(`
        <strong>${node.name}</strong><br>
        ${node.type}<br>
        Status: ${labelForStatus(node.status)}<br>
        Daily burn: ${node.daily_burn_rate.toLocaleString()} units<br>
        First stockout: ${node.first_stockout ? `${node.first_stockout} days` : "None in horizon"}
      `);
      geoInfoWindow.open(googleMapInstance, marker);
      renderAll();
    });

    geoMarkers.push(marker);
    geoLabels.push(createGeoLabel(node));
  });
}

function createGeoLabel(node) {
  const label = new google.maps.OverlayView();
  const element = document.createElement("div");
  element.className = `geo-node-label ${node.id === selectedNodeId ? "selected" : ""}`;
  element.textContent = node.additional_path_latency_days > 0
    ? `${node.name} +${node.additional_path_latency_days}d`
    : node.name;

  label.onAdd = function onAdd() {
    this.getPanes().overlayMouseTarget.appendChild(element);
    element.addEventListener("click", () => {
      selectedNodeId = node.id;
      renderAll();
    });
  };

  label.draw = function draw() {
    const point = this.getProjection().fromLatLngToDivPixel(
      new google.maps.LatLng(node.latitude, node.longitude)
    );
    if (!point) return;
    element.style.left = `${point.x}px`;
    element.style.top = `${point.y + 22}px`;
  };

  label.onRemove = function onRemove() {
    element.remove();
  };

  label.setMap(googleMapInstance);
  return label;
}

function createGeoRouteLabel(route, from, to) {
  const label = new google.maps.OverlayView();
  const element = document.createElement("div");
  element.className = `geo-route-label ${route.status}`;
  element.textContent = `${route.current_days}d`;
  const position = geoMidpoint(from, to);

  label.onAdd = function onAdd() {
    this.getPanes().overlayLayer.appendChild(element);
  };

  label.draw = function draw() {
    const point = this.getProjection().fromLatLngToDivPixel(
      new google.maps.LatLng(position.lat, position.lng)
    );
    if (!point) return;
    element.style.left = `${point.x}px`;
    element.style.top = `${point.y}px`;
  };

  label.onRemove = function onRemove() {
    element.remove();
  };

  label.setMap(googleMapInstance);
  return label;
}

function geoMidpoint(from, to) {
  let fromLng = from.longitude;
  let toLng = to.longitude;
  if (Math.abs(fromLng - toLng) > 180) {
    if (fromLng < 0) fromLng += 360;
    if (toLng < 0) toLng += 360;
  }
  const lng = normalizeLongitude((fromLng + toLng) / 2);
  return {
    lat: (from.latitude + to.latitude) / 2,
    lng
  };
}

function normalizeLongitude(lng) {
  if (lng > 180) return lng - 360;
  if (lng < -180) return lng + 360;
  return lng;
}

function markerIcon(node) {
  const size = node.id === selectedNodeId ? 44 : 36;
  const stroke = node.id === selectedNodeId ? "#111827" : "#ffffff";
  return {
    url: typedMarkerSvg(node, size, stroke),
    scaledSize: new google.maps.Size(size, size),
    anchor: new google.maps.Point(size / 2, size / 2)
  };
}

function typedMarkerSvg(node, size, stroke) {
  const fill = statusColor(node.status);
  const glyph = nodeGlyph(node.type);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 44 44">
      <circle cx="22" cy="22" r="18" fill="${fill}" stroke="${stroke}" stroke-width="3"/>
      ${glyph}
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function nodeGlyph(type) {
  if (type === "MTF") {
    return `<rect x="13" y="19" width="18" height="12" rx="2" fill="#fff"/><rect x="19" y="13" width="6" height="18" rx="1" fill="#fff"/>`;
  }
  if (type.includes("hub") || type === "Prime vendor") {
    return `<path d="M12 20h20v12H12z" fill="#fff"/><path d="M10 20l12-8 12 8z" fill="#fff"/><path d="M17 24h10v8H17z" fill="${statusColor("healthy")}" opacity=".55"/>`;
  }
  if (type === "Supplier") {
    return `<path d="M11 30h22v-9l-6 3v-5l-6 3v-6H11z" fill="#fff"/><rect x="15" y="25" width="3" height="3" fill="${statusColor("healthy")}" opacity=".55"/><rect x="22" y="25" width="3" height="3" fill="${statusColor("healthy")}" opacity=".55"/>`;
  }
  if (type === "Battalion aid") {
    return `<rect x="12" y="18" width="20" height="14" rx="2" fill="#fff"/><path d="M22 14v16M14 22h16" stroke="${statusColor("healthy")}" stroke-width="4" stroke-linecap="round" opacity=".65"/>`;
  }
  return `<path d="M15 31V13h13l-2 5 2 5H15" fill="#fff"/><path d="M15 31h-3" stroke="#fff" stroke-width="3" stroke-linecap="round"/>`;
}

function renderSelectedNode() {
  const node = forecastNodeById(selectedNodeId);
  selectedNodeName.textContent = node.name;
  selectedNodeMeta.textContent = `${node.type} | ${node.population.toLocaleString()} assigned personnel`;

  selectedNodeStats.innerHTML = "";
  const stats = [
    ["Status", labelForStatus(node.status)],
    ["First stockout", node.first_stockout ? `${node.first_stockout} days` : "None in horizon"],
    ["First risk", node.first_critical ? `${node.first_critical} days` : "None in horizon"],
    ["Daily burn", `${node.daily_burn_rate.toLocaleString()} units`],
    ["Supply line", node.supply_reachable ? "Reachable" : "Disconnected"],
    ["Path latency", `${node.path_latency_days ?? "--"} days`],
    ["Added latency", `${node.additional_path_latency_days ?? 0} days`],
    ["Stock posture", `${node.effective_stock_days} days`],
    ["Riskiest item", node.riskiest_item],
    ["Operational state", node.demand_profile.operational_state_label]
  ];
  stats.forEach(([label, value]) => {
    const div = document.createElement("div");
    div.className = "stat-card";
    div.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
    selectedNodeStats.appendChild(div);
  });
}

function renderDataNodeList() {
  dataNodeList.innerHTML = forecast.nodes
    .map((node) => `
      <button class="data-node-button ${node.id === dataSelectedNodeId ? "active" : ""}" type="button" data-node-id="${node.id}">
        <span>
          <strong>${node.name}</strong>
          <small>${node.type} | ${node.population.toLocaleString()} personnel</small>
        </span>
        <span class="pill ${node.status}">${labelForStatus(node.status)}</span>
      </button>
    `)
    .join("");

  dataNodeList.querySelectorAll("button[data-node-id]").forEach((button) => {
    button.addEventListener("click", () => {
      dataSelectedNodeId = button.dataset.nodeId;
      renderDataNodeList();
      renderDataNodeHeader();
      renderNodeDetailControls();
      renderDemandProfileControls();
      renderInventoryEditor();
    });
  });
}

function renderDataNodeHeader() {
  const node = forecastNodeById(dataSelectedNodeId);
  dataNodeName.textContent = node.name;
  dataNodeMeta.textContent = `${node.type} | ${node.population.toLocaleString()} assigned personnel | ${node.demand_profile.operational_state_label}`;
  dataNodeStats.innerHTML = `
    <div class="stat-card"><strong>${labelForStatus(node.status)}</strong><span>Forecast status</span></div>
    <div class="stat-card"><strong>${node.daily_burn_rate.toLocaleString()}</strong><span>Daily burn units</span></div>
    <div class="stat-card"><strong>${node.supply_reachable ? "Reachable" : "Disconnected"}</strong><span>Supply line</span></div>
    <div class="stat-card"><strong>${node.additional_path_latency_days ?? 0} days</strong><span>Added latency</span></div>
    <div class="stat-card"><strong>${node.effective_stock_days} days</strong><span>Stock posture</span></div>
  `;
}

function renderNodeDetailControls() {
  const node = nodeById(dataSelectedNodeId);
  nodeNameInput.value = node.name;
  nodeTypeInput.value = node.type;
  nodePopulationInput.value = node.population;
  nodeStockDaysInput.value = node.stock_days;
  nodeLatitudeInput.value = node.latitude ?? "";
  nodeLongitudeInput.value = node.longitude ?? "";
}

function renderDemandProfileControls() {
  const profile = forecastNodeById(dataSelectedNodeId).demand_profile;
  activePopulation.value = profile.active_supported_population;
  operationalState.value = profile.operational_state;
  encounterRate.value = profile.daily_encounter_rate;
  phlebotomyRate.value = profile.phlebotomy_probability;
  specimensPerDraw.value = profile.specimens_per_phlebotomy;
  wasteFactor.value = profile.waste_factor;
}

function renderStateImpactPreview() {
  const node = forecastNodeById(dataSelectedNodeId);
  const profile = node.demand_profile;
  const currentState = operationalStates.find((state) => state.id === profile.operational_state);
  const selectedState = operationalStates.find((state) => state.id === operationalState.value) || currentState;
  const currentMultiplier = currentState?.demand_multiplier || 1;
  const selectedMultiplier = selectedState?.demand_multiplier || 1;
  const latencyCurrent = currentState?.route_latency_multiplier || 1;
  const latencySelected = selectedState?.route_latency_multiplier || 1;
  const burnChange = ((selectedMultiplier / currentMultiplier) - 1) * 100;
  const projectedDailyBurn = node.daily_burn_rate * (selectedMultiplier / currentMultiplier);
  const projectedPopulation = Number(activePopulation.value || profile.active_supported_population);

  stateImpactPreview.innerHTML = `
    <div class="impact-card">
      <strong>State impact preview</strong>
      <p>Compare the current operational state to the selected state.</p>
      <div class="state-impact-grid">
        <div><span>Current</span><strong>${currentState?.label || profile.operational_state_label}</strong></div>
        <div><span>Selected</span><strong>${selectedState?.label || operationalState.value}</strong></div>
        <div><span>Daily burn</span><strong>${projectedDailyBurn.toLocaleString()}</strong></div>
        <div><span>Change</span><strong>${burnChange >= 0 ? "+" : ""}${burnChange.toFixed(1)}%</strong></div>
        <div><span>Route latency</span><strong>${latencyCurrent.toFixed(2)}x → ${latencySelected.toFixed(2)}x</strong></div>
        <div><span>Supported population</span><strong>${projectedPopulation.toLocaleString()}</strong></div>
      </div>
    </div>
  `;
  queueStateEventButton.disabled = !selectedState || selectedState.id === profile.operational_state;
}

function renderInventoryEditor() {
  const forecastNode = forecastNodeById(dataSelectedNodeId);
  const forecastByItem = Object.fromEntries(forecastNode.item_results.map((item) => [item.item_id, item]));
  const balances = inventoryBalances
    .filter((balance) => balance.node_id === dataSelectedNodeId)
    .sort((a, b) => a.item_name.localeCompare(b.item_name));

  inventoryEditorTable.innerHTML = `
    <table>
      <thead>
        <tr><th>Item</th><th>Unit</th><th>On hand</th><th>Daily burn</th><th>Days</th></tr>
      </thead>
      <tbody>
        ${balances.map((balance) => {
          const item = forecastByItem[balance.item_id];
          const days = item && item.daily_burn_rate > 0 ? Math.floor(Number(balance.quantity_on_hand) / item.daily_burn_rate) : "--";
          return `
            <tr>
              <td>${balance.item_name}</td>
              <td>${balance.unit}</td>
              <td>
                <input
                  class="inventory-input"
                  data-inventory-item="${balance.item_id}"
                  type="number"
                  min="0"
                  step="1"
                  value="${Math.round(balance.quantity_on_hand)}"
                >
              </td>
              <td>${item ? item.daily_burn_rate.toLocaleString() : "--"}</td>
              <td>${days}</td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

function renderSummary() {
  const atRisk = forecast.nodes
    .filter((node) => ["risk", "stockout", "watch", "offline"].includes(node.status))
    .sort((a, b) => (a.first_stockout ?? a.first_critical ?? 999) - (b.first_stockout ?? b.first_critical ?? 999))
    .slice(0, 6);

  impactSummary.innerHTML = `
    <div class="impact-card">
      <strong>${forecast.events && forecast.events.length ? `${forecast.events.length} queued event${forecast.events.length === 1 ? "" : "s"} applied.` : "Baseline forecast with no active event."}</strong>
      <p>Forecast horizon: ${forecast.horizon} days. Node colors show the worst projected phlebotomy supply condition.</p>
    </div>
  `;

  if (!atRisk.length) {
    impactSummary.innerHTML += `<div class="impact-card healthy"><strong>No projected shortages</strong><p>All nodes remain above risk thresholds during the forecast horizon.</p></div>`;
    return;
  }

  atRisk.forEach((node) => {
    const recommendation = forecast.recommendations.find((entry) => entry.node_id === node.id);
    const hasStockout = node.first_stockout !== null && node.first_stockout !== undefined;
    const hasCritical = node.first_critical !== null && node.first_critical !== undefined;
    const message = hasStockout
      ? `${node.riskiest_item} stockout projected in ${node.first_stockout} days.`
      : hasCritical
        ? `${node.riskiest_item} falls below threshold in ${node.first_critical} days.`
        : `${node.riskiest_item} requires attention.`;
    impactSummary.innerHTML += `
      <div class="impact-card ${node.status}">
        <strong>${node.name}</strong>
        <p>${message} Recommended action: ${recommendation ? recommendation.action : "continue monitoring supply posture"}.</p>
      </div>
    `;
  });
}

function renderItemRiskTable() {
  const node = forecastNodeById(selectedNodeId);
  const rows = node.item_results
    .map((item) => {
      const hasStockout = item.stockout_day !== null && item.stockout_day !== undefined;
      const hasCritical = item.critical_day !== null && item.critical_day !== undefined;
      const status = hasStockout
        ? "stockout"
        : hasCritical
          ? "risk"
          : item.net_burn_rate > 0 && item.balance <= item.reorder_point
            ? "watch"
            : "healthy";
      const daysToStockout = hasStockout
        ? `${item.stockout_day}d`
        : item.net_burn_rate === 0
          ? "No drawdown"
          : `>${forecast.horizon}d`;
      return `
        <tr>
          <td>${item.item_name}</td>
          <td><span class="pill ${status}">${labelForStatus(status)}</span></td>
          <td>${item.balance.toLocaleString()}</td>
          <td>${item.daily_burn_rate.toLocaleString()}</td>
          <td>${item.net_burn_rate.toLocaleString()}</td>
          <td>${daysToStockout}</td>
          <td>${hasCritical ? `${item.critical_day}d` : "--"}</td>
        </tr>
      `;
    })
    .join("");

  itemRiskTable.innerHTML = `
    <table>
      <thead>
        <tr><th>Item</th><th>Status</th><th>Projected balance</th><th>Daily burn</th><th>Net drawdown</th><th>Days to stockout</th><th>Critical</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderRouteImpactTable() {
  const rows = forecast.routes
    .filter((route) => route.from === selectedNodeId || route.to === selectedNodeId || route.status !== "normal")
    .map((route) => `
      <tr>
        <td>${nodeById(route.from).name} -> ${nodeById(route.to).name}</td>
        <td>${route.priority}</td>
        <td><span class="pill ${route.status}">${route.status}</span></td>
        <td>${route.current_days}d</td>
        <td>${Math.round(route.reliability * 100)}%</td>
      </tr>
    `)
    .join("");

  routeImpactTable.innerHTML = `
    <table>
      <thead>
        <tr><th>Route</th><th>Type</th><th>Status</th><th>Latency</th><th>Reliability</th></tr>
      </thead>
      <tbody>${rows || `<tr><td colspan="5">No direct or event-impacted routes.</td></tr>`}</tbody>
    </table>
  `;
}

function renderMetrics() {
  document.getElementById("metricNodesAtRisk").textContent = forecast.metrics.nodes_at_risk;
  document.getElementById("metricEarliestStockout").textContent = forecast.metrics.earliest_stockout ? `${forecast.metrics.earliest_stockout}d` : "--";
  document.getElementById("metricRoutesImpacted").textContent = forecast.metrics.routes_impacted;
}

function describeEvent(event) {
  const node = nodeById(event.node_id);
  if (event.type === "operational_state_change") {
    const state = operationalStates.find((entry) => entry.id === event.target_operational_state);
    return `${eventName(event.type)} at ${node.name} to ${state ? state.label : event.target_operational_state} for ${event.duration} days.`;
  }
  return `${eventName(event.type)} at ${node.name} for ${event.duration} days.`;
}

function eventName(type) {
  const eventNames = {
    mascal: "MASCAL demand surge",
    fpcon: "FPCON restriction",
    hub_degraded: "Hub degradation",
    hub_offline: "Hub offline",
    inventory_loss: "Inventory loss",
    operational_state_change: "Operational state change"
  };
  return eventNames[type] || type;
}

function describeQueuedEvent(event) {
  const node = nodeById(event.node_id);
  if (event.event_type === "operational_state_change") {
    const state = operationalStates.find((entry) => entry.id === event.target_operational_state);
    return `${eventName(event.event_type)} at ${node.name} -> ${state ? state.label : event.target_operational_state}`;
  }
  return `${eventName(event.event_type)} at ${node.name}`;
}

function eventDetailSummary(event) {
  if (event.event_type === "operational_state_change") {
    return `${event.duration_days} days | applies to node only`;
  }
  return `${event.severity} severity | ${event.duration_days} days`;
}

function showLoading(message) {
  impactSummary.innerHTML = `<div class="impact-card"><strong>${message}</strong><p>Waiting for backend API response.</p></div>`;
}

function showApiError(error) {
  impactSummary.innerHTML = `
    <div class="impact-card stockout">
      <strong>Backend API unavailable</strong>
      <p>${error.message}. Start the FastAPI server, then refresh this page.</p>
    </div>
  `;
}

function nodeById(id) {
  return nodes.find((node) => node.id === id) || forecastNodeById(id);
}

function hasGeoPoint(node) {
  return Number.isFinite(node.latitude) && Number.isFinite(node.longitude);
}

function routeColor(route) {
  if (route.status === "blocked") return "#c0392b";
  if (route.status === "delayed") return "#c7921c";
  if (route.status === "alternate") return "#2563eb";
  if (route.priority === "secondary") return "#d49a17";
  if (route.priority === "tertiary") return "#2563eb";
  return "#1769aa";
}

function forecastNodeById(id) {
  return forecast.nodes.find((node) => node.id === id);
}

function statusColor(status) {
  return {
    healthy: "#26845d",
    watch: "#c7921c",
    risk: "#d4662f",
    stockout: "#c0392b",
    offline: "#6b7280"
  }[status] || "#6b7280";
}

function labelForStatus(status) {
  return {
    healthy: "Healthy",
    watch: "Watch",
    risk: "At risk",
    stockout: "Stockout",
    offline: "Offline"
  }[status] || status;
}

init();
