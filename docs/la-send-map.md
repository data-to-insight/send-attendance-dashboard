---
title: LA SEND map
hide:
  - toc
---

# LA SEND map

<link
  rel="stylesheet"
  href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>
<link
  rel="stylesheet"
  href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>

<style>
  .md-grid {
    max-width: initial;
  }

  .la-send-map-page {
    width: 100%;
  }

  /* Main vertical layout: filters, status, map */
  .la-send-map-layout,
  .la-send-map-stack {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
    width: 100%;
  }

  /* Filters above map (not yet functional!) */
  .benchmark-controls.la-send-map-controls-top,
  .la-send-map-controls,
  .la-send-map-controls-top {
    order: 1;
    position: static;
    z-index: 20;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: end;
    width: 100%;
    margin-bottom: 0;
  }

  .benchmark-controls.la-send-map-controls-top label,
  .la-send-map-controls label,
  .la-send-map-controls-top label {
    min-width: 220px;
    flex: 1 1 220px;
  }

  /* Status sits btwn filters and map */
  #map-status {
    order: 2;
  }

  /* Map panel for compatibility*/
  .la-send-map-panel {
    order: 3;
    width: 100%;
    min-width: 0;
  }

  /* Main Leaflet map container */
  #la-send-map {
    order: 3;
    width: 100%;
    height: 75vh;
    min-height: 640px;
    border: 1px solid var(--md-default-fg-color--lightest);
    border-radius: 0.5rem;
    position: relative;
    z-index: 1;
  }

  #la-send-map .leaflet-container,
  .leaflet-container {
    width: 100%;
    height: 100%;
  }

  /* Leaflet popup / tooltip sizing */
  #la-send-map .leaflet-popup-content {
    font-size: 0.72rem;
    line-height: 1.25;
    margin: 0.55rem 0.7rem;
    max-width: 220px;
  }

  #la-send-map .leaflet-popup-content strong {
    font-size: 0.78rem;
  }

  #la-send-map .leaflet-popup-content br {
    line-height: 1.1;
  }

  #la-send-map .leaflet-popup-content-wrapper {
    border-radius: 0.45rem;
  }

  #la-send-map .leaflet-tooltip {
    font-size: 0.7rem;
    line-height: 1.2;
    padding: 0.25rem 0.4rem;
  }

  /* Leaflet attribution text */
  #la-send-map .leaflet-control-attribution {
    font-size: 0.5rem;
    line-height: 1.1;
    padding: 1px 4px;
  }

  #la-send-map .leaflet-control-attribution a {
    font-size: inherit;
  }

  @media (max-width: 900px) {
    .benchmark-controls.la-send-map-controls-top,
    .la-send-map-controls,
    .la-send-map-controls-top {
      display: flex;
      flex-direction: column;
      align-items: stretch;
    }

    .benchmark-controls.la-send-map-controls-top label,
    .la-send-map-controls label,
    .la-send-map-controls-top label {
      min-width: 0;
      width: 100%;
      flex: 1 1 auto;
    }

    #la-send-map {
      height: 70vh;
      min-height: 520px;
    }
  }
</style>
<div class="la-send-map-layout">

  <div class="benchmark-controls la-send-map-controls-top">
    <label>
      Metric
      <select id="map-metric">
        <option value="">Loading metrics...</option>
      </select>
    </label>

    <label>
      Region
      <select id="map-region">
        <option value="all_regions">All regions</option>
      </select>
    </label>

    <label>
      SEND group
      <select id="map-send">
        <option value="EHC plan">EHC plan</option>
        <option value="SEN support">SEN support</option>
      </select>
    </label>
  </div>

  <div id="map-status" class="benchmark-status benchmark-status--loading">
    Loading map...
  </div>

  <div id="la-send-map"></div>

</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<script>
(async function () {
  const status = document.getElementById("map-status");
  const metricSelect = document.getElementById("map-metric");
  const regionSelect = document.getElementById("map-region");
  const sendSelect = document.getElementById("map-send");

  let map = null;
  let boundaryLayer = null;
  let boundaries = null;
  let manifest = null;
  let valueRows = [];
  let valueByLa = new Map();

  function setStatus(message, isError = false) {
    status.innerHTML = message;
    status.classList.toggle("benchmark-status--error", isError);
    status.classList.toggle("benchmark-status--ok", !isError);
    status.classList.remove("benchmark-status--loading");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatValue(value, digits = 2) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "";
    return n.toLocaleString(undefined, { maximumFractionDigits: digits });
  }

  async function fetchJson(fileRef) {
    const url = new URL("../" + fileRef, document.baseURI);
    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Could not load ${url.href}: HTTP ${res.status}`);
    }

    return await res.json();
  }

  function metricInfo(metric) {
    return manifest.metric_files?.[metric] || null;
  }

  function selectedRegionFileInfo(metric) {
    const info = metricInfo(metric);

    if (!info) {
      return null;
    }

    const region = regionSelect.value || "all_regions";

    if (region === "all_regions") {
      return info.all_regions;
    }

    return info.regions?.[region] || null;
  }

  function getFeatureLaCode(feature) {
    return feature.properties?.new_la_code;
  }

  function getFeatureLaName(feature) {
    return feature.properties?.la_name || feature.properties?.new_la_code || "Unknown LA";
  }

  function selectedSendGroup() {
    return sendSelect.value || "EHC plan";
  }

  function buildValueIndex() {
    const sendGroup = selectedSendGroup();

    valueByLa = new Map();

    for (const row of valueRows) {
      if (row.send_group !== sendGroup) {
        continue;
      }

      const code = row.new_la_code;

      if (!code) {
        continue;
      }

      // If multiple period/phase rows keep latest-ish one by simple order.
      // Later can add explicit period/phase controls to map
      valueByLa.set(code, row);
    }
  }

  function colourForGap(value, direction) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
      return "#d9d9d9";
    }

    const v = Number(value);

    // For attendance, negative gap usually concern signal
    if (direction === "higher") {
      if (v <= -10) return "#7f0000";
      if (v <= -5) return "#b30000";
      if (v <= -2) return "#d7301f";
      if (v < 0) return "#fc8d59";
      if (v === 0) return "#f7f7f7";
      if (v <= 2) return "#c7e9c0";
      return "#41ab5d";
    }

    // For absence, suspensions, exclusions, positive gap usually concern
    if (v >= 10) return "#7f0000";
    if (v >= 5) return "#b30000";
    if (v >= 2) return "#d7301f";
    if (v > 0) return "#fc8d59";
    if (v === 0) return "#f7f7f7";
    if (v >= -2) return "#c7e9c0";
    return "#41ab5d";
  }

  function styleFeature(feature) {
    const metric = metricSelect.value;
    const info = metricInfo(metric);
    const direction = info?.direction || "neutral";
    const code = getFeatureLaCode(feature);
    const row = valueByLa.get(code);

    return {
      fillColor: colourForGap(row?.gap_to_no_sen, direction),
      weight: row ? 1 : 0.5,
      opacity: 1,
      color: row ? "#555" : "#aaa",
      fillOpacity: row ? 0.78 : 0.25
    };
  }

  function onEachFeature(feature, layer) {
    const code = getFeatureLaCode(feature);
    const name = getFeatureLaName(feature);
    const row = valueByLa.get(code);

    let html = `<strong>${escapeHtml(name)}</strong>`;

    if (row) {
      html += `
        <br>Region: ${escapeHtml(row.region_name || "")}
        <br>SEND group: ${escapeHtml(row.send_group || "")}
        <br>SEND value: ${formatValue(row.send_value, 2)}
        <br>No SEN value: ${formatValue(row.no_sen_value, 2)}
        <br>Gap to No SEN: <strong>${formatValue(row.gap_to_no_sen, 2)}</strong>
        <br>Period: ${escapeHtml(row.time_period || "")}
        <br>Phase: ${escapeHtml(row.education_phase || "")}
      `;
    } else {
      html += `<br>No value for current selection`;
    }

    layer.bindPopup(html);
  }

  function renderMapLayer() {
    if (!map || !boundaries) {
      return;
    }

    if (boundaryLayer) {
      boundaryLayer.remove();
      boundaryLayer = null;
    }

    buildValueIndex();

    boundaryLayer = L.geoJson(boundaries, {
      style: styleFeature,
      onEachFeature: onEachFeature
    }).addTo(map);

    if (boundaryLayer.getBounds().isValid()) {
      map.fitBounds(boundaryLayer.getBounds(), { padding: [12, 12] });
    }
  }

  async function loadValuesAndRender() {
    const metric = metricSelect.value;

    if (!metric) {
      return;
    }

    const fileInfo = selectedRegionFileInfo(metric);

    if (!fileInfo || !fileInfo.file) {
      throw new Error(`No map value file for metric ${metric} and region ${regionSelect.value || "all_regions"}`);
    }

    setStatus(`Loading ${escapeHtml(fileInfo.region_label || "map values")}...`);

    const payload = await fetchJson(fileInfo.file);
    valueRows = Array.isArray(payload.records) ? payload.records : [];

    renderMapLayer();

    setStatus(
      `Loaded ${valueRows.length.toLocaleString()} map rows for ` +
      `<strong>${escapeHtml(metricInfo(metric)?.metric_label || metric)}</strong>, ` +
      `<strong>${escapeHtml(fileInfo.region_label || "All regions")}</strong>.`
    );
  }

  try {
    setStatus("Loading map manifest...");

    manifest = await fetchJson("data/maps/la_send_map_manifest.json");

    if (!manifest.boundary_file) {
      throw new Error("Map manifest is missing boundary_file");
    }

    metricSelect.innerHTML = "";

    for (const item of manifest.metrics || []) {
      const option = document.createElement("option");
      option.value = item.metric;
      option.textContent = item.metric_label || item.metric;
      metricSelect.appendChild(option);
    }

    if (manifest.default_metric && [...metricSelect.options].some(o => o.value === manifest.default_metric)) {
      metricSelect.value = manifest.default_metric;
    }

    const defaultMetricInfo = metricInfo(metricSelect.value);

    regionSelect.innerHTML = "";
    const allOption = document.createElement("option");
    allOption.value = "all_regions";
    allOption.textContent = "All regions";
    regionSelect.appendChild(allOption);

    for (const [regionCode, info] of Object.entries(defaultMetricInfo?.regions || {})) {
      const option = document.createElement("option");
      option.value = regionCode;
      option.textContent = info.region_label || regionCode;
      regionSelect.appendChild(option);
    }

    setStatus("Loading LA boundaries...");
    boundaries = await fetchJson(manifest.boundary_file);

    if (!boundaries.features || !boundaries.features.length) {
      throw new Error("Boundary GeoJSON has no features");
    }

    map = L.map("la-send-map", {
      scrollWheelZoom: true,
      attributionControl: true
    }).setView([52.8, -1.5], 6);

    map.attributionControl.setPrefix("");

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 11,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    metricSelect.addEventListener("change", async function () {
      const info = metricInfo(metricSelect.value);

      regionSelect.innerHTML = "";
      const allOption = document.createElement("option");
      allOption.value = "all_regions";
      allOption.textContent = "All regions";
      regionSelect.appendChild(allOption);

      for (const [regionCode, regionInfo] of Object.entries(info?.regions || {})) {
        const option = document.createElement("option");
        option.value = regionCode;
        option.textContent = regionInfo.region_label || regionCode;
        regionSelect.appendChild(option);
      }

      await loadValuesAndRender();
    });

    regionSelect.addEventListener("change", loadValuesAndRender);
    sendSelect.addEventListener("change", function () {
      renderMapLayer();
    });

    await loadValuesAndRender();

  } catch (err) {
    console.error(err);
    setStatus(`<strong>Could not load map.</strong><br>${escapeHtml(err.message || err)}`, true);
  }
})();
</script>