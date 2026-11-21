/* EcoTrack dashboard: plain JavaScript, no build step. */

const state = {
  refreshTimer: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* response is not JSON */
    }
    throw new Error(detail);
  }

  return response.json();
}

function setStatus(online) {
  const status = $("status");
  status.classList.toggle("online", online);
  status.classList.toggle("offline", !online);
  $("status-text").textContent = online ? "live" : "offline";
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  const diffSeconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (diffSeconds < 60) return `${Math.max(diffSeconds, 0)}s ago`;
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
  return date.toLocaleDateString();
}

function formatValue(value, unit) {
  const rounded = Math.round(value * 100) / 100;
  return unit ? `${rounded} ${unit}` : String(rounded);
}

function renderReadings(readings) {
  const body = $("readings");
  body.replaceChildren();

  if (readings.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "empty";
    cell.textContent = "No readings yet — add the first one.";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }

  for (const reading of readings) {
    const row = document.createElement("tr");

    const device = document.createElement("td");
    device.textContent = reading.device_id;

    const metric = document.createElement("td");
    metric.textContent = reading.metric;

    const value = document.createElement("td");
    value.className = "num";
    value.textContent = formatValue(reading.value, reading.unit);

    const recorded = document.createElement("td");
    recorded.textContent = formatDate(reading.recorded_at);
    recorded.title = reading.recorded_at;

    row.append(device, metric, value, recorded);
    body.appendChild(row);
  }
}

function renderStats(stats) {
  $("total").textContent = stats.total_readings;
  $("devices").textContent = stats.devices;
  $("latest").textContent = formatDate(stats.latest_reading_at);

  const container = $("metrics");
  container.replaceChildren();

  if (stats.metrics.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No data yet.";
    container.appendChild(empty);
    return;
  }

  const maxAverage = Math.max(...stats.metrics.map((item) => Math.abs(item.average)), 1);

  for (const item of stats.metrics) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const name = document.createElement("span");
    name.className = "bar-name";
    name.textContent = item.metric;

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max((Math.abs(item.average) / maxAverage) * 100, 2)}%`;
    track.appendChild(fill);

    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = `avg ${Math.round(item.average * 100) / 100} · n=${item.count}`;
    value.title = `min ${item.minimum}, max ${item.maximum}`;

    row.append(name, track, value);
    container.appendChild(row);
  }
}

async function refresh() {
  try {
    const [stats, readings] = await Promise.all([
      api("/api/stats"),
      api("/api/readings?limit=12"),
    ]);
    renderStats(stats);
    renderReadings(readings);
    setStatus(true);
  } catch (error) {
    setStatus(false);
    console.error("Failed to refresh dashboard:", error);
  }
}

async function submitReading(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type='submit']");
  const message = $("form-message");

  const payload = {
    device_id: form.device_id.value.trim(),
    metric: form.metric.value,
    value: Number(form.value.value),
  };

  message.className = "form-message";
  message.textContent = "Sending…";
  button.disabled = true;

  try {
    await api("/api/readings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    message.classList.add("ok");
    message.textContent = `Reading from ${payload.device_id} stored.`;
    await refresh();
  } catch (error) {
    message.classList.add("error");
    message.textContent = `Error: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function init() {
  $("reading-form").addEventListener("submit", submitReading);
  $("refresh").addEventListener("click", refresh);
  refresh();
  state.refreshTimer = window.setInterval(refresh, 10000);
}

document.addEventListener("DOMContentLoaded", init);
