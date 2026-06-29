---
title: Benchmarking
---

# Region & LA comparisons

>Compare SEND attendance|absence|inclusion measures against No SEN baseline  
>Choose metric and region to see how selected SEND group, eg `EHC plan` or `SEN support` with those recorded as `No SEN`

N.b - Work here very much in flex/dev/alpha. I'm trialing ideas around the existing data, but also investigating the underlying data towards this. Take all with pinch of salt for now. 

Core calc is:

`SEND gap = selected SEND group value - No SEN value`

Gap units depend on selected metric. For attendance and absence percentage fields, gap is **%-point difference**, not count of days. For attendance reason fields, benchmark charts use derived **sessions per 1,000 possible sessions** rate, instead of raw session count. Assumes school day uses 2 attendance sessions(am/pm).

## Derived attendance reason rate

to make LA comparisons fairer on attendance reason fields benchmark charts use:

`reason sessions per 1,000 possible sessions = reason sessions / possible sessions * 1,000`

raw DfE session counts still used in the explorer page(see page tab above); but larger LAs may naturally have larger raw counts so believe it makes sense to adjust pre benchmarking. 


<div class="benchmark-controls benchmark-controls-global">
  <label>
    Metric
    <select id="story-metric">
      <option value="">Select metric</option>
    </select>
  </label>

  <label>
    Period
    <select id="story-period">
      <option value="">All periods</option>
    </select>
  </label>

  <label>
    Phase
    <select id="story-phase">
      <option value="">All phases</option>
    </select>
  </label>

  <label>
    SEND group
    <select id="story-send">
      <option value="EHC plan">EHC plan</option>
      <option value="SEN support">SEN support</option>
    </select>
  </label>

  <label>
  Breakdown type
    <select id="story-send-detail">
      <option value="">SEN provision|primary need</option>
    </select>
  </label>
</div>

<div id="benchmark-status" class="benchmark-status benchmark-status--loading">
  Loading benchmark manifest...
</div>

<div class="benchmark-card">
  <h2>Regional SEND gap to No SEN</h2>
  <p>
    gap calculated as selected SEND group val minus No SEN value for same LA,
    period, phase and metric. unit depends on selected metric: attendance and absence %s are
    shown as %-point gaps, attendance reason fields are session-count gaps, and suspension/exclusion
    rates are rate-point gaps per 100(child).
  </p>
  <div class="chart-loading-wrap" style="height: 360px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="region-gap-chart"></canvas>
  </div>
</div>

<!-- <div class="benchmark-controls benchmark-controls-region">
  <label>
    Region for LA charts and table
    <select id="story-region">
      <option value="">All regions</option>
    </select>
  </label>
</div> -->

<!-- add highlight on region name as otherwise not obvious enough once selected -->
<div class="benchmark-controls benchmark-controls-region">
  <label>
    Region for LA charts and table
    <select id="story-region">
      <option value="">All regions</option>
    </select>
    <span id="region-selected-chip" class="selected-region-chip region-selected-chip-inline" hidden></span>
  </label>
</div>

<div class="benchmark-card">
  <h2 id="la-gap-heading">LA SEND gap within selected region: all regions</h2>
  <p>
    LA difference from own No SEN baseline for selected SEND group
  </p>
  <div class="chart-loading-wrap" style="height: 520px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="la-gap-chart"></canvas>
  </div>
</div>

<!-- apply all 3 EHC/Provision & No SEN to chart -->
<div class="benchmark-card">
  <div class="benchmark-card-header">
    <div>
      <h2>LA comparison across No SEN, SEN support and EHC plan</h2>
      <p id="provision-comparison-subtitle">
        Compare No SEN, SEN support and EHC plan data across LAs
          Shown ordering driven by the above 'SEND group' filter.
      </p>
      <p class="comparison-note">
      Markers show selected metric value for
      No SEN, SEN support and EHC plan children, aligned to period, phase,
      breakdown and region filters currently set(above).
    </p>
      <!-- <p class="comparison-note comparison-note-muted">
      Gap ordering calculated as selected SEND group value minus No SEN value.
      For absence, suspensions and exclusions, positive gaps (usually) indicate higher
      rates than No SEN. For attendance, negative gaps usually indicate lower
      attendance than No SEN.
    </p> -->
    </div>
  </div>

  <div id="provision-comparison-chart" class="comparison-chart"></div>
</div>

<div class="benchmark-card">
  <h2 id="la-baseline-heading">Local authority SEND value vs No SEN value: all regions</h2>
  <p>
    LA in region compare selected SEND group value with No SEN val
  </p>
  <div class="chart-loading-wrap" style="height: 520px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="la-baseline-chart"></canvas>
  </div>
</div>

<div class="benchmark-card">
  <h2 id="largest-gaps-heading">Largest gaps: all regions</h2>
  <div id="story-table"></div>
</div>

<div class="benchmark-card">
  <h2>SEN primary need comparison</h2>
  <p>
    Compare LA values for selected SEN primary need.  
    This section does not use No SEN gap as primary-need categories are different breakdown from SEN provision. To see SEND characteristic data breakdown here, the above filters must be set to bring through the related data, e.g.:
    Metric: Absence %
    Region for LA charts and table: East Midlands, or any named region (i.e. not 'All Regions')
    Period: latest / default
    Phase: Total or otherwise any available phase
  </p>

  <div class="benchmark-controls benchmark-controls-need">
    <label>
      SEN type / primary need
      <select id="need-category">
        <option value="">Select SEN type</option>
      </select>
    </label>
  </div>

  <div class="chart-loading-wrap" style="height: 520px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="need-la-chart"></canvas>
  </div>

  <div id="need-table"></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
(async function () {
  // DOM references
  const status = document.getElementById("benchmark-status");

  const metricFilter = document.getElementById("story-metric");
  const periodFilter = document.getElementById("story-period");
  const phaseFilter = document.getElementById("story-phase");
  const sendFilter = document.getElementById("story-send");
  const sendDetailFilter = document.getElementById("story-send-detail");
  const regionFilter = document.getElementById("story-region");
  const needCategoryFilter = document.getElementById("need-category");

  const table = document.getElementById("story-table");
  const needTable = document.getElementById("need-table");

  const regionGapCanvas = document.getElementById("region-gap-chart");
  const laGapCanvas = document.getElementById("la-gap-chart");
  const laBaselineCanvas = document.getElementById("la-baseline-chart");
  const needLaCanvas = document.getElementById("need-la-chart");

  const laGapHeading = document.getElementById("la-gap-heading");
  const laBaselineHeading = document.getElementById("la-baseline-heading");
  const largestGapsHeading = document.getElementById("largest-gaps-heading");

  const controlPanels = [...document.querySelectorAll(".benchmark-controls")];
  const chartWraps = [...document.querySelectorAll(".chart-loading-wrap")];

  // towards highlight on selected region above charts (bit clearer)
  const regionSelectedChip = document.getElementById("region-selected-chip");
  const regionControls = document.querySelector(".benchmark-controls-region");

  // Page state
  let renderToken = 0;
  let benchmarkManifest = null;

  let metricRows = [];
  let primaryNeedRows = [];

  const metricCache = new Map();
  const primaryNeedCache = new Map();

  let regionGapChart = null;
  let laGapChart = null;
  let laBaselineChart = null;
  let needLaChart = null;

  const preferredMetrics = [
    "attendance_perc",
    "overall_absence_perc",
    "authorised_absence_perc",
    "unauthorised_absence_perc",
    "auth_part_time_perc",
    "reason_c2_authorised_temp_reduced_timetable_per_1000_sessions",
    "reason_b_aea_education_off_site_per_1000_sessions",
    "reason_k_aea_education_arranged_by_la_per_1000_sessions",
    "sess_overall_percent",
    "sess_unauthorised_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "susp_rate",
    "one_plus_susp_rate",
    "perm_excl_rate"
  ];

  // Basic UI helpers
  function setControlsDisabled(disabled) {
    for (const el of [regionFilter, metricFilter, periodFilter, phaseFilter, sendFilter, sendDetailFilter, needCategoryFilter]) {
      if (el) el.disabled = disabled;
    }

    for (const panel of controlPanels) {
      panel.classList.toggle("is-loading", disabled);
    }
  }

  function setVisualLoading(isLoading, message = "Updating charts...") {
    for (const wrap of chartWraps) {
      wrap.classList.toggle("is-loading", isLoading);
      const mask = wrap.querySelector(".chart-loading-mask");
      if (mask) mask.textContent = message;
    }

    if (table) table.classList.toggle("is-loading", isLoading);
    if (needTable) needTable.classList.toggle("is-loading", isLoading);
  }

  function setStatus(message, isError = false, isLoading = false) {
    status.innerHTML = message;
    status.classList.remove("benchmark-status--loading", "benchmark-status--error", "benchmark-status--ok");

    if (isError) {
      status.classList.add("benchmark-status--error");
      return;
    }

    if (isLoading) {
      status.classList.add("benchmark-status--loading");
      return;
    }

    status.classList.add("benchmark-status--ok");
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
    if (value === null || value === undefined || value === "") return "";
    const num = Number(value);

    if (!Number.isNaN(num) && Number.isFinite(num)) {
      return num.toLocaleString(undefined, { maximumFractionDigits: digits });
    }

    return value;
  }

  function uniqueValues(rows, field) {
    return [...new Set(
      rows
        .map(r => r[field])
        .filter(v => v !== null && v !== undefined && v !== "")
    )].sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
  }

  function clearSelect(selectEl, label) {
    selectEl.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    selectEl.appendChild(option);
  }

  function addOptions(selectEl, values) {
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      selectEl.appendChild(option);
    }
  }

  function destroyChart(chart) {
    if (chart) chart.destroy();
  }

  function clearCharts() {
    for (const chart of [regionGapChart, laGapChart, laBaselineChart, needLaChart]) {
      destroyChart(chart);
    }

    regionGapChart = null;
    laGapChart = null;
    laBaselineChart = null;
    needLaChart = null;
  }

  // Manifest helpers
  function provisionMetricInfo(metric) {
    return benchmarkManifest?.provision_gap_files?.[metric] ||
      benchmarkManifest?.la_metric_files?.[metric] ||
      null;
  }

  function primaryNeedMetricInfo(metric) {
    return benchmarkManifest?.primary_need_files?.[metric] || null;
  }

  function metricMeta(metric) {
    return (benchmarkManifest?.metrics || []).find(m => m.column === metric) || {};
  }

  function metricLabel(metric) {
    const meta =
      provisionMetricInfo(metric) ||
      primaryNeedMetricInfo(metric) ||
      benchmarkManifest?.la_metric_files?.[metric];

    if (meta && meta.metric_label) {
      return meta.metric_label;
    }

    return metricMeta(metric).label || metric;
  }

  function metricDirection(metric) {
    return metricMeta(metric).direction || "neutral";
  }

  function metricType(metric) {
    return metricMeta(metric).metric_type || "value";
  }

  function metricUnit(metric) {
    const type = metricType(metric);

    if (type === "percent") return "% points";
    if (type === "rate") return "rate points per 100 pupils";
    if (type === "rate_per_1000_sessions") return "sessions per 1,000 possible sessions";

    if (type === "count") {
      if (metric.includes("reason_")) return "sessions";
      if (metric === "number_of_pupils") return "pupils";
      if (metric.includes("enrolments")) return "enrolments";
      return "count";
    }

    return "value";
  }

  function metricValueLabel(metric) {
    const label = metricLabel(metric);
    const type = metricType(metric);

    if (type === "rate") return `${label} per 100 pupils`;
    if (type === "count") return `${label}, ${metricUnit(metric)}`;

    return label;
  }

  function metricSortForConcern(metric) {
    const direction = metricDirection(metric);

    if (direction === "higher") {
      return "ascending";
    }

    if (direction === "lower") {
      return "descending";
    }

    return "absolute";
  }

  function gapAxisLabel(metric) {
    return `SEND minus No SEN(Gap), ${metricUnit(metric)}`;
  }

  function sendValueLabel(metric) {
    return `${sendFilter.value || "SEND"} ${metricValueLabel(metric)}`;
  }

  function noSenValueLabel(metric) {
    return `No SEN ${metricValueLabel(metric)}`;
  }

  function gapTableLabel(metric) {
    return `Gap, ${metricUnit(metric)}`;
  }

  function normaliseSendCategory(value) {
    const text = String(value ?? "").trim().toLowerCase();

    if (!text) return "";

    if (
      text === "ehc plan" ||
      text.includes("statement or ehc") ||
      text.includes("statement/ehc") ||
      text.includes("statement of sen") ||
      text.includes("education health and care") ||
      text.includes("education, health and care")
    ) {
      return "EHC plan";
    }

    if (text === "sen support" || text.includes("sen support")) {
      return "SEN support";
    }

    if (
      text === "no sen" ||
      text.includes("no identified sen") ||
      text.includes("without sen")
    ) {
      return "No SEN";
    }

    return String(value ?? "");
  }

  // Fetch helpers
  async function fetchRecords(fileRef) {
    const url = new URL("../" + fileRef, document.baseURI);
    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Could not load ${url.href}: HTTP ${res.status}`);
    }

    const data = await res.json();
    return Array.isArray(data.records) ? data.records : [];
  }

  function storyFileRefs(info) {
    if (!info) return [];

    if (info.file) {
      return [info.file];
    }

    if (info.regions) {
      return Object.values(info.regions)
        .map(r => r.file)
        .filter(Boolean);
    }

    return [];
  }

  async function loadMetricRows(metric) {
    if (!metric) {
      metricRows = [];
      return;
    }

    const cacheKey = `provision:${metric}`;

    if (metricCache.has(cacheKey)) {
      metricRows = metricCache.get(cacheKey);
      return;
    }

    const metricInfo = provisionMetricInfo(metric);

    if (!metricInfo) {
      throw new Error(`No provision benchmark file listed for ${metric}`);
    }

    const files = storyFileRefs(metricInfo);

    if (!files.length) {
      throw new Error(`No provision benchmark story files listed for ${metric}`);
    }

    setStatus(`Loading <code>${escapeHtml(metricInfo.metric_label || metric)}</code> benchmark rows...`, false, true);

    const chunks = await Promise.all(files.map(fetchRecords));
    const rows = chunks.flat();

    metricCache.set(cacheKey, rows);
    metricRows = rows;
  }

  async function loadPrimaryNeedRows(metric) {
    primaryNeedRows = [];

    if (!metric || !regionFilter.value) {
      return;
    }

    const info = primaryNeedMetricInfo(metric);

    if (!info || !info.regions) {
      return;
    }

    const regionInfo = info.regions[regionFilter.value];

    if (!regionInfo || !regionInfo.file) {
      return;
    }

    const cacheKey = `primary:${metric}:${regionFilter.value}`;

    if (primaryNeedCache.has(cacheKey)) {
      primaryNeedRows = primaryNeedCache.get(cacheKey);
      return;
    }

    const rows = await fetchRecords(regionInfo.file);

    primaryNeedCache.set(cacheKey, rows);
    primaryNeedRows = rows;
  }

  // Region and filter helpers
  function regionOptionsFromRows(rows) {
    const byCode = new Map();

    for (const row of rows) {
      const code = row.region_code || row.region_name || row.region_label;

      if (!code) continue;

      if (!byCode.has(code)) {
        byCode.set(code, row.region_name || row.region_label || code);
      }
    }

    return [...byCode.entries()]
      .sort((a, b) => String(a[1]).localeCompare(String(b[1])));
  }

  function selectedRegionLabel() {
    const value = regionFilter.value;

    if (!value) {
      return "all regions";
    }

    const selected = [...regionFilter.options].find(o => o.value === value);
    return selected ? selected.textContent : value;
  }

  function updateRegionHeadings() {
    // must run after region dropdown update from scheduleRender()
    // must also run after refreshProvisionFilters() in render()

    const regionLabel = selectedRegionLabel();
    const hasRegion = Boolean(regionFilter.value);

    const regionMarkup = hasRegion
      ? `<span class="selected-region-chip">${escapeHtml(regionLabel)}</span>`
      : escapeHtml(regionLabel);

    if (laGapHeading) {
      laGapHeading.innerHTML = `LA SEND gap within selected region: ${regionMarkup}`;
    }

    if (laBaselineHeading) {
      laBaselineHeading.innerHTML = `Local authority SEND value vs No SEN value: ${regionMarkup}`;
    }

    if (largestGapsHeading) {
      largestGapsHeading.innerHTML = `Largest gaps: ${regionMarkup}`;
    }

    if (regionControls) {
      regionControls.classList.toggle("has-region-selected", hasRegion);
    }

    if (regionSelectedChip) {
      regionSelectedChip.hidden = !hasRegion;
      regionSelectedChip.textContent = hasRegion ? regionLabel : "";
    }
  }

  function filterRowsToSelectedRegion(rows) {
    const region = regionFilter.value;

    if (!region) {
      return rows;
    }

    return rows.filter(r =>
      r.region_code === region ||
      r.region_name === region ||
      r.region_label === region
    );
  }

  function latestPeriodValue(rows) {
    const values = uniqueValues(rows, "time_period");

    if (!values.length) {
      return "";
    }

    return values
      .map(v => String(v))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .at(-1);
  }

  function preferredPhaseValue(rows) {
    const values = uniqueValues(rows, "education_phase");

    const preferred = [
      "Total",
      "State-funded total",
      "All",
      "All schools",
      "State-funded primary",
      "Primary",
      "State-funded secondary",
      "Secondary",
      "Special"
    ];

    return preferred.find(v => values.includes(v)) || values[0] || "";
  }

  function ensureSingleChartSliceSelected() {
    if (!periodFilter.value) {
      const latest = latestPeriodValue(metricRows);
      if (latest && [...periodFilter.options].some(o => o.value === latest)) {
        periodFilter.value = latest;
      }
    }

    if (!phaseFilter.value) {
      const phase = preferredPhaseValue(metricRows);
      if (phase && [...phaseFilter.options].some(o => o.value === phase)) {
        phaseFilter.value = phase;
      }
    }
  }

  function refreshProvisionFilters() {
    const previousRegion = regionFilter.value;
    const previousPeriod = periodFilter.value;
    const previousPhase = phaseFilter.value;
    const previousSendDetail = sendDetailFilter ? sendDetailFilter.value : "";

    clearSelect(regionFilter, "All regions");
    clearSelect(periodFilter, "All periods");
    clearSelect(phaseFilter, "All phases");

    for (const [code, label] of regionOptionsFromRows(metricRows)) {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = label;
      regionFilter.appendChild(option);
    }

    addOptions(periodFilter, uniqueValues(metricRows, "time_period"));
    addOptions(phaseFilter, uniqueValues(metricRows, "education_phase"));

    if (sendDetailFilter) {
      clearSelect(sendDetailFilter, "All SEND breakdowns");
      addOptions(sendDetailFilter, uniqueValues(metricRows, "send_detail_display"));

      if ([...sendDetailFilter.options].some(o => o.value === previousSendDetail)) {
        sendDetailFilter.value = previousSendDetail;
      }
    }

    if ([...regionFilter.options].some(o => o.value === previousRegion)) {
      regionFilter.value = previousRegion;
    }

    if ([...periodFilter.options].some(o => o.value === previousPeriod)) {
      periodFilter.value = previousPeriod;
    }

    if ([...phaseFilter.options].some(o => o.value === previousPhase)) {
      phaseFilter.value = previousPhase;
    }
  }

  function refreshPrimaryNeedFilter() {
    const previousNeed = needCategoryFilter ? needCategoryFilter.value : "";

    if (!needCategoryFilter) {
      return;
    }

    clearSelect(needCategoryFilter, "Select SEN type");

    const values = uniqueValues(primaryNeedRows, "sen_type_label");
    addOptions(needCategoryFilter, values);

    if ([...needCategoryFilter.options].some(o => o.value === previousNeed)) {
      needCategoryFilter.value = previousNeed;
    } else if (values.length) {
      needCategoryFilter.value = values[0];
    }
  }

  // Provision gap calculations
  function baseFilterRows(rows) {
    let filtered = rows;

    const period = periodFilter.value;
    const phase = phaseFilter.value;
    const sendDetail = sendDetailFilter ? sendDetailFilter.value : "";

    if (sendDetail) {
      filtered = filtered.filter(r => r.send_detail_display === sendDetail);
    }

    if (period) {
      filtered = filtered.filter(r => String(r.time_period) === String(period));
    }

    if (phase) {
      filtered = filtered.filter(r => r.education_phase === phase);
    }

    filtered = filtered.filter(r => {
      const category = normaliseSendCategory(r.send_category);
      return (
        category === "No SEN" ||
        category === "SEN support" ||
        category === "EHC plan"
      );
    });

    return filtered;
  }

  function makePairKey(row, level) {
    const parts = [
      row.time_period || "",
      row.time_identifier || "",
      row.academic_year || "",
      row.education_phase || "",
      row.phase_type_grouping || "",
      row.metric || ""
    ];

    if (level === "la") {
      parts.push(row.new_la_code || row.la_name || "");
    }

    if (level === "region") {
      parts.push(row.region_code || row.region_name || "");
    }

    return parts.join("||");
  }

  function computeGapRows(level) {
    const selectedSend = sendFilter.value || "EHC plan";
    const filtered = baseFilterRows(metricRows);
    const pairs = new Map();

    for (const row of filtered) {
      const key = makePairKey(row, level);

      if (!pairs.has(key)) {
        pairs.set(key, {
          key,
          time_period: row.time_period,
          time_identifier: row.time_identifier,
          academic_year: row.academic_year,
          education_phase: row.education_phase,
          metric: row.metric,
          metric_label: row.metric_label,
          region_code: row.region_code,
          region_name: row.region_name,
          region_label: row.region_label,
          new_la_code: row.new_la_code,
          la_name: row.la_name,
          selected_send: selectedSend,
          send_value: null,
          no_sen_value: null
        });
      }

      const item = pairs.get(key);
      const category = normaliseSendCategory(row.send_category);

      if (category === selectedSend) {
        item.send_value = Number(row.value);
      }

      if (category === "No SEN") {
        item.no_sen_value = Number(row.value);
      }
    }

    return [...pairs.values()]
      .filter(r =>
        r.send_value !== null &&
        r.no_sen_value !== null &&
        Number.isFinite(r.send_value) &&
        Number.isFinite(r.no_sen_value)
      )
      .map(r => ({
        ...r,
        gap_to_no_sen: r.send_value - r.no_sen_value
      }));
  }

  function aggregateRegionGapsFromLa() {
    const laGaps = computeGapRows("la");
    const byRegion = new Map();

    for (const row of laGaps) {
      const key = row.region_code || row.region_name || row.region_label || "Unknown region";

      if (!byRegion.has(key)) {
        byRegion.set(key, {
          region_code: row.region_code,
          region_name: row.region_name,
          region_label: row.region_label,
          selected_send: row.selected_send,
          send_sum: 0,
          no_sen_sum: 0,
          gap_sum: 0,
          la_names: new Set(),
          count: 0
        });
      }

      const item = byRegion.get(key);

      item.send_sum += row.send_value;
      item.no_sen_sum += row.no_sen_value;
      item.gap_sum += row.gap_to_no_sen;

      if (row.la_name) {
        item.la_names.add(row.la_name);
      }

      item.count += 1;
    }

    return [...byRegion.values()]
      .filter(r => r.count > 0)
      .map(r => ({
        ...r,
        la_count: r.la_names.size,
        send_value: r.send_sum / r.count,
        no_sen_value: r.no_sen_sum / r.count,
        gap_to_no_sen: r.gap_sum / r.count
      }));
  }

  // Build one chart row per LA after filters.
  // This keeps repeated source/period/phase slices from appearing as duplicate LA labels.
  function aggregateLaGaps() {
    let rows = computeGapRows("la");
    rows = filterRowsToSelectedRegion(rows);

    const byLa = new Map();

    for (const row of rows) {
      const key = row.new_la_code || row.la_name || "Unknown LA";

      if (!byLa.has(key)) {
        byLa.set(key, {
          new_la_code: row.new_la_code,
          la_name: row.la_name,
          region_code: row.region_code,
          region_name: row.region_name,
          region_label: row.region_label,
          selected_send: row.selected_send,
          send_sum: 0,
          no_sen_sum: 0,
          gap_sum: 0,
          count: 0
        });
      }

      const item = byLa.get(key);
      item.send_sum += row.send_value;
      item.no_sen_sum += row.no_sen_value;
      item.gap_sum += row.gap_to_no_sen;
      item.count += 1;
    }

    return [...byLa.values()]
      .filter(r => r.count > 0)
      .map(r => ({
        ...r,
        send_value: r.send_sum / r.count,
        no_sen_value: r.no_sen_sum / r.count,
        gap_to_no_sen: r.gap_sum / r.count
      }));
  }

  function sortByConcern(rows, metric) {
    const mode = metricSortForConcern(metric);

    return [...rows].sort((a, b) => {
      if (mode === "ascending") {
        return Number(a.gap_to_no_sen) - Number(b.gap_to_no_sen);
      }

      if (mode === "descending") {
        return Number(b.gap_to_no_sen) - Number(a.gap_to_no_sen);
      }

      return Math.abs(Number(b.gap_to_no_sen)) - Math.abs(Number(a.gap_to_no_sen));
    });
  }

  function sortValueByConcern(rows, metric) {
    const mode = metricSortForConcern(metric);

    return [...rows].sort((a, b) => {
      if (mode === "ascending") {
        return Number(a.value) - Number(b.value);
      }

      return Number(b.value) - Number(a.value);
    });
  }

  // Primary need calculations
  function primaryNeedBaseRows() {
    let rows = primaryNeedRows;

    const period = periodFilter.value;
    const phase = phaseFilter.value;
    const selectedNeed = needCategoryFilter ? needCategoryFilter.value : "";

    if (period) {
      rows = rows.filter(r => String(r.time_period) === String(period));
    }

    if (phase) {
      rows = rows.filter(r => r.education_phase === phase);
    }

    if (selectedNeed) {
      rows = rows.filter(r => r.sen_type_label === selectedNeed);
    }

    return rows;
  }

  function aggregatePrimaryNeedLaValues() {
    const rows = primaryNeedBaseRows();
    const byLa = new Map();

    for (const row of rows) {
      const key = row.new_la_code || row.la_name || "Unknown LA";
      const value = Number(row.value);

      if (!Number.isFinite(value)) {
        continue;
      }

      if (!byLa.has(key)) {
        byLa.set(key, {
          new_la_code: row.new_la_code,
          la_name: row.la_name,
          region_code: row.region_code,
          region_name: row.region_name,
          region_label: row.region_label,
          sen_type_label: row.sen_type_label,
          value_sum: 0,
          count: 0
        });
      }

      const item = byLa.get(key);
      item.value_sum += value;
      item.count += 1;
    }

    return [...byLa.values()]
      .filter(r => r.count > 0)
      .map(r => ({
        ...r,
        value: r.value_sum / r.count
      }));
  }

  // Chart renderers
  function renderRegionGapChart() {
    const metric = metricFilter.value;
    const rows = sortByConcern(aggregateRegionGapsFromLa(), metric);

    destroyChart(regionGapChart);

    if (!rows.length) {
      regionGapCanvas.style.display = "none";
      return [];
    }

    regionGapCanvas.style.display = "block";

    regionGapChart = new Chart(regionGapCanvas, {
      type: "bar",
      data: {
        labels: rows.map(r => r.region_name),
        datasets: [{
          label: gapAxisLabel(metric),
          data: rows.map(r => Number(r.gap_to_no_sen.toFixed(3)))
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: currentSliceLabel() },
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: context => {
                const row = rows[context.dataIndex];
                return [
                  `${gapAxisLabel(metric)}: ${formatValue(context.raw)}`,
                  `SEND value: ${formatValue(row.send_value)}`,
                  `No SEN value: ${formatValue(row.no_sen_value)}`,
                  `LA comparisons: ${row.la_count || row.count || ""}`
                ];
              }
            }
          }
        },
        scales: {
          y: { ticks: { autoSkip: false } },
          x: { title: { display: true, text: gapAxisLabel(metric) } }
        }
      }
    });

    return rows;
  }

  function renderLaGapChart() {
    const metric = metricFilter.value;
    let rows = sortByConcern(aggregateLaGaps(), metric).slice(0, 40);

    destroyChart(laGapChart);

    if (!rows.length) {
      laGapCanvas.style.display = "none";
      return [];
    }

    laGapCanvas.style.display = "block";

    laGapChart = new Chart(laGapCanvas, {
      type: "bar",
      data: {
        labels: rows.map(r => r.la_name),
        datasets: [{
          label: gapAxisLabel(metric),
          data: rows.map(r => Number(r.gap_to_no_sen.toFixed(3)))
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: `${currentSliceLabel()} | ${selectedRegionLabel()}` },
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: context => {
                const row = rows[context.dataIndex];
                return [
                  `${gapAxisLabel(metric)}: ${formatValue(context.raw)}`,
                  `SEND value: ${formatValue(row.send_value)}`,
                  `No SEN value: ${formatValue(row.no_sen_value)}`,
                  `Source slices averaged: ${row.count || ""}`
                ];
              }
            }
          }
        },
        scales: {
          y: { ticks: { autoSkip: false } },
          x: { title: { display: true, text: gapAxisLabel(metric) } }
        }
      }
    });

    return rows;
  }

  function renderLaBaselineChart() {
    const metric = metricFilter.value;
    let rows = sortByConcern(aggregateLaGaps(), metric).slice(0, 25);

    destroyChart(laBaselineChart);

    if (!rows.length) {
      laBaselineCanvas.style.display = "none";
      return [];
    }

    laBaselineCanvas.style.display = "block";

    laBaselineChart = new Chart(laBaselineCanvas, {
      type: "bar",
      data: {
        labels: rows.map(r => r.la_name),
        datasets: [
          {
            label: sendValueLabel(metric),
            data: rows.map(r => Number(r.send_value.toFixed(3)))
          },
          {
            label: noSenValueLabel(metric),
            data: rows.map(r => Number(r.no_sen_value.toFixed(3)))
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: `${currentSliceLabel()} | ${selectedRegionLabel()}` },
          legend: { display: true }
        },
        scales: {
          y: { ticks: { autoSkip: false } },
          x: { title: { display: true, text: metricValueLabel(metric) } }
        }
      }
    });

    return rows;
  }

  function renderPrimaryNeedLaChart() {
    const metric = metricFilter.value;
    const selectedNeed = needCategoryFilter ? needCategoryFilter.value : "";

    destroyChart(needLaChart);

    if (!regionFilter.value) {
      if (needLaCanvas) needLaCanvas.style.display = "none";
      if (needTable) {
        needTable.innerHTML = "<p>Select a region to load SEN primary need comparison rows.</p>";
      }
      return [];
    }

    if (!selectedNeed) {
      if (needLaCanvas) needLaCanvas.style.display = "none";
      if (needTable) {
        needTable.innerHTML = "<p>Select a SEN type / primary need to show this comparison.</p>";
      }
      return [];
    }

    let rows = sortValueByConcern(aggregatePrimaryNeedLaValues(), metric).slice(0, 40);

    if (!rows.length) {
      needLaCanvas.style.display = "none";
      if (needTable) {
        needTable.innerHTML = "<p>No rows match the selected SEN type, metric, period, phase and region.</p>";
      }
      return [];
    }

    needLaCanvas.style.display = "block";

    needLaChart = new Chart(needLaCanvas, {
      type: "bar",
      data: {
        labels: rows.map(r => r.la_name),
        datasets: [{
          label: `${selectedNeed} ${metricValueLabel(metric)}`,
          data: rows.map(r => Number(r.value.toFixed(3)))
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: `${metricValueLabel(metric)} | ${selectedNeed} | ${selectedRegionLabel()}`
          },
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: context => {
                const row = rows[context.dataIndex];
                return [
                  `${metricValueLabel(metric)}: ${formatValue(context.raw)}`,
                  `Source slices averaged: ${row.count || ""}`
                ];
              }
            }
          }
        },
        scales: {
          y: { ticks: { autoSkip: false } },
          x: { title: { display: true, text: metricValueLabel(metric) } }
        }
      }
    });

    return rows;
  }







  // Table renderers
  function renderTable(rows) {
    const metric = metricFilter.value;
    const shown = rows.slice(0, 25);

    if (!shown.length) {
      table.innerHTML = "<p>No SEND vs No SEN comparison rows match current filters</p>";
      return;
    }

    const columns = [
      "region_name",
      "la_name",
      "selected_send",
      "send_value",
      "no_sen_value",
      "gap_to_no_sen"
    ];

    const labels = {
      region_name: "Region",
      la_name: "LA",
      selected_send: "SEND group",
      send_value: sendValueLabel(metric),
      no_sen_value: noSenValueLabel(metric),
      gap_to_no_sen: gapTableLabel(metric)
    };

    const header = columns.map(c => `<th>${escapeHtml(labels[c] || c)}</th>`).join("");

    const body = shown.map(row => {
      const cells = columns.map(c => {
        const value = ["send_value", "no_sen_value", "gap_to_no_sen"].includes(c)
          ? formatValue(row[c], 3)
          : row[c];

        return `<td>${escapeHtml(value)}</td>`;
      }).join("");

      return `<tr>${cells}</tr>`;
    }).join("");

    table.innerHTML = `
      <p>
        Showing ${shown.length} largest benchmark gaps for
        <strong>${escapeHtml(sendFilter.value)}</strong>,
        metric <strong>${escapeHtml(metricLabel(metric))}</strong>,
        region <strong>${escapeHtml(selectedRegionLabel())}</strong>.
      </p>
      <div style="overflow:auto; max-height:60vh;">
        <table>
          <thead><tr>${header}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  function renderPrimaryNeedTable(rows) {
    if (!needTable) {
      return;
    }

    const metric = metricFilter.value;
    const selectedNeed = needCategoryFilter ? needCategoryFilter.value : "";

    if (!regionFilter.value) {
      needTable.innerHTML = "<p>Select a region to load SEN primary need rows.</p>";
      return;
    }

    if (!selectedNeed) {
      needTable.innerHTML = "<p>Select a SEN type / primary need to show LA values.</p>";
      return;
    }

    const shown = rows.slice(0, 25);

    if (!shown.length) {
      needTable.innerHTML = "<p>No SEN primary need rows match the current filters.</p>";
      return;
    }

    const columns = ["region_name", "la_name", "sen_type_label", "value", "count"];

    const labels = {
      region_name: "Region",
      la_name: "LA",
      sen_type_label: "SEN type",
      value: metricValueLabel(metric),
      count: "Source slices averaged"
    };

    const header = columns.map(c => `<th>${escapeHtml(labels[c] || c)}</th>`).join("");

    const body = shown.map(row => {
      const cells = columns.map(c => {
        const value = c === "value" ? formatValue(row[c], 3) : row[c];
        return `<td>${escapeHtml(value)}</td>`;
      }).join("");

      return `<tr>${cells}</tr>`;
    }).join("");

    needTable.innerHTML = `
      <p>
        Showing ${shown.length} LA values for
        <strong>${escapeHtml(selectedNeed)}</strong>,
        metric <strong>${escapeHtml(metricLabel(metric))}</strong>,
        region <strong>${escapeHtml(selectedRegionLabel())}</strong>.
      </p>
      <div style="overflow:auto; max-height:50vh;">
        <table>
          <thead><tr>${header}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }



//////////


  const provisionComparisonChart = document.getElementById("provision-comparison-chart");
  const provisionComparisonSubtitle = document.getElementById("provision-comparison-subtitle");

  function normaliseProvisionGroup(value) {
    const text = String(value || "").trim().toLowerCase();

    if (
      text === "ehc plan" ||
      text.includes("statement or ehc") ||
      text.includes("statement/ehc") ||
      text.includes("education health and care") ||
      text.includes("education, health and care")
    ) {
      return "EHC plan";
    }

    if (text === "sen support" || text.includes("sen support")) {
      return "SEN support";
    }

    if (
      text === "no sen" ||
      text.includes("no identified sen") ||
      text.includes("without sen")
    ) {
      return "No SEN";
    }

    return String(value || "").trim();
  }

  function currentSendGroupForOrdering() {
    return normaliseProvisionGroup(sendFilter?.value || "EHC plan");
  }


  function currentProvisionComparisonOrder() {
    const selectedGroup = currentSendGroupForOrdering();

    if (selectedGroup === "SEN support") {
      return {
        key: "sen_support_gap",
        label: "SEN support gap to No SEN"
      };
    }

    if (selectedGroup === "No SEN") {
      return {
        key: "no_sen_value",
        label: "No SEN value"
      };
    }

    return {
      key: "ehc_gap",
      label: "EHC plan gap to No SEN"
    };
  }

  // 
  function provisionComparisonSourceRows() {
    let rows = baseFilterRows(metricRows);
    rows = filterRowsToSelectedRegion(rows);
    return rows;
  }

  function buildProvisionComparisonRows(rows) {
    const grouped = new Map();

    for (const row of rows) {
      const group = normaliseProvisionGroup(row.send_category);

      if (!["No SEN", "SEN support", "EHC plan"].includes(group)) {
        continue;
      }

      const laCode = row.new_la_code || row.la_name;

      if (!laCode) {
        continue;
      }

      const key = [
        laCode,
        row.la_name || "",
        row.region_code || "",
        row.time_period || "",
        row.time_identifier || "",
        row.academic_year || "",
        row.education_phase || "",
        row.phase_type_grouping || "",
        row.metric || ""
      ].join("||");

      if (!grouped.has(key)) {
        grouped.set(key, {
          new_la_code: row.new_la_code,
          la_name: row.la_name || laCode,
          region_code: row.region_code,
          region_name: row.region_name,
          time_period: row.time_period,
          time_identifier: row.time_identifier,
          academic_year: row.academic_year,
          education_phase: row.education_phase,
          phase_type_grouping: row.phase_type_grouping,
          metric: row.metric,
          metric_label: row.metric_label || row.metric,
          no_sen_value: null,
          sen_support_value: null,
          ehc_plan_value: null
        });
      }

      const item = grouped.get(key);
      const value = Number(row.value);

      if (!Number.isFinite(value)) {
        continue;
      }

      if (group === "No SEN") {
        item.no_sen_value = value;
      }

      if (group === "SEN support") {
        item.sen_support_value = value;
      }

      if (group === "EHC plan") {
        item.ehc_plan_value = value;
      }
    }

    return [...grouped.values()]
      .map(row => ({
        ...row,
        sen_support_gap: (
          Number.isFinite(row.sen_support_value) && Number.isFinite(row.no_sen_value)
            ? row.sen_support_value - row.no_sen_value
            : null
        ),
        ehc_gap: (
          Number.isFinite(row.ehc_plan_value) && Number.isFinite(row.no_sen_value)
            ? row.ehc_plan_value - row.no_sen_value
            : null
        )
      }))
      .filter(row =>
        Number.isFinite(row.no_sen_value) ||
        Number.isFinite(row.sen_support_value) ||
        Number.isFinite(row.ehc_plan_value)
      );
  }

  function sortProvisionComparisonRows(rows, orderKey) {
    return rows.slice().sort((a, b) => {
      const av = Number(a[orderKey]);
      const bv = Number(b[orderKey]);

      if (!Number.isFinite(av) && !Number.isFinite(bv)) return 0;
      if (!Number.isFinite(av)) return 1;
      if (!Number.isFinite(bv)) return -1;

      return bv - av;
    });
  }

  function renderProvisionComparisonChart() {
    if (!provisionComparisonChart) {
      return;
    }

    const order = currentProvisionComparisonOrder();

    const sourceRows = provisionComparisonSourceRows();
    const comparisonRows = sortProvisionComparisonRows(
      buildProvisionComparisonRows(sourceRows),
      order.key
    ).slice(0, 30);


    if (provisionComparisonSubtitle) {
      provisionComparisonSubtitle.innerHTML = `
        Compare No SEN, SEN support and EHC plan values for each LA.
        Ordered by <strong>${escapeHtml(order.label)}</strong>, from the 'SEND group' filter(above)
      `;
    }


    if (!comparisonRows.length) {
      provisionComparisonChart.innerHTML = `
        <div class="empty-state">
          No comparison rows are available for the current metric and filters.
        </div>
      `;
      return;
    }

    const values = [];

    for (const row of comparisonRows) {
      for (const key of ["no_sen_value", "sen_support_value", "ehc_plan_value"]) {
        const value = Number(row[key]);
        if (Number.isFinite(value)) {
          values.push(value);
        }
      }
    }

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue || 1;

    const width = 980;
    const left = 210;
    const right = 30;
    const top = 82;
    const rowHeight = 26;
    const height = top + comparisonRows.length * rowHeight + 45;
    const plotWidth = width - left - right;

    function x(value) {
      if (!Number.isFinite(Number(value))) {
        return null;
      }

      return left + ((Number(value) - minValue) / range) * plotWidth;
    }

    function y(index) {
      return top + index * rowHeight;
    }

    // show if data vals are % or rate to make it clearer in chart
    function fmt(value) {
      if (!Number.isFinite(Number(value))) {
        return "";
      }

      const formatted = Number(value).toLocaleString(undefined, {
        maximumFractionDigits: 2
      });

      if (metricType(metricFilter.value) === "percent") {
        return `${formatted}%`;
      }

      return formatted;
    }


    const rowsSvg = comparisonRows.map((row, index) => {
      const yPos = y(index);
      const noSenX = x(row.no_sen_value);
      const senSupportX = x(row.sen_support_value);
      const ehcX = x(row.ehc_plan_value);

      const lineXs = [noSenX, senSupportX, ehcX].filter(v => v !== null);
      const minX = lineXs.length ? Math.min(...lineXs) : null;
      const maxX = lineXs.length ? Math.max(...lineXs) : null;

      return `
        <g>
          <text class="la-label" x="0" y="${yPos + 4}">
            ${escapeHtml(row.la_name)}
          </text>

          ${
            lineXs.length > 1
              ? `<line class="comparison-line" x1="${minX}" x2="${maxX}" y1="${yPos}" y2="${yPos}" />`
              : ""
          }

          ${
            noSenX !== null
              ? `<circle class="dot-no-sen" cx="${noSenX}" cy="${yPos}" r="4">
                  <title>${escapeHtml(row.la_name)} No SEN: ${fmt(row.no_sen_value)}</title>
                </circle>`
              : ""
          }

          ${
            senSupportX !== null
              ? `<circle class="dot-sen-support" cx="${senSupportX}" cy="${yPos}" r="4">
                  <title>${escapeHtml(row.la_name)} SEN support: ${fmt(row.sen_support_value)}. Gap to No SEN: ${fmt(row.sen_support_gap)}</title>
                </circle>`
              : ""
          }

          ${
            ehcX !== null
              ? `<circle class="dot-ehc-plan" cx="${ehcX}" cy="${yPos}" r="4">
                  <title>${escapeHtml(row.la_name)} EHC plan: ${fmt(row.ehc_plan_value)}. Gap to No SEN: ${fmt(row.ehc_gap)}</title>
                </circle>`
              : ""
          }
        </g>
      `;
    }).join("");

  const valueScaleLabel = metricValueLabel(metricFilter.value);

  provisionComparisonChart.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img">
      <text class="series-label dot-no-sen" x="${left}" y="18">● No SEN</text>
      <text class="series-label dot-sen-support" x="${left + 95}" y="18">● SEN support</text>
      <text class="series-label dot-ehc-plan" x="${left + 225}" y="18">● EHC plan</text>

      <text class="axis-label" x="${left}" y="44">
        Value scale: ${escapeHtml(valueScaleLabel)}
      </text>

      <text class="axis-label" x="${left}" y="64">${fmt(minValue)}</text>
      <text class="axis-label" x="${width - right - 70}" y="64">${fmt(maxValue)}</text>

      <line x1="${left}" x2="${width - right}" y1="70" y2="70" stroke="#ccc" />

      ${rowsSvg}
    </svg>
  `;
  }


//////////

  function currentSliceLabel() {
    const parts = [];

    if (metricFilter.value) parts.push(metricLabel(metricFilter.value));
    if (sendFilter.value) parts.push(sendFilter.value);
    if (periodFilter.value) parts.push(`period ${periodFilter.value}`);
    if (phaseFilter.value) parts.push(phaseFilter.value);

    return parts.join(" | ");
  }

  async function render() {
    const thisRender = ++renderToken;

    try {
      const metric = metricFilter.value;

      if (!metric) {
        clearCharts();
        table.innerHTML = "<p>Select metric to load benchmark story</p>";
        setStatus("Select metric to load benchmark story");
        return;
      }

      setVisualLoading(true, "Loading selected benchmark...");
      setControlsDisabled(true);

      await loadMetricRows(metric);

      if (thisRender !== renderToken) return;

      refreshProvisionFilters();
      ensureSingleChartSliceSelected();
      updateRegionHeadings();

      await loadPrimaryNeedRows(metric);

      if (thisRender !== renderToken) return;

    refreshPrimaryNeedFilter();

    const regionGapRows = renderRegionGapChart() || [];
    const laGapRows = renderLaGapChart() || [];

    renderProvisionComparisonChart();
    renderLaBaselineChart();
    renderTable(laGapRows);

    const primaryNeedChartRows = renderPrimaryNeedLaChart() || [];
    renderPrimaryNeedTable(primaryNeedChartRows);

    setStatus(
      `Loaded ${metricRows.length.toLocaleString()} provision rows for ` +
      `<strong>${escapeHtml(metricLabel(metric))}</strong>.` +
      (primaryNeedRows.length ? ` Loaded ${primaryNeedRows.length.toLocaleString()} primary need rows for ${escapeHtml(selectedRegionLabel())}.` : "")
    );
    } catch (err) {
      console.error(err);
      clearCharts();
      setStatus(`<strong>Could not render benchmark story.</strong><br>${escapeHtml(err.message || err)}`, true);
    } finally {
      if (thisRender === renderToken) {
        setVisualLoading(false);
        setControlsDisabled(false);
      }
    }
  }

  try {
    setControlsDisabled(true);
    setVisualLoading(true, "Loading benchmark manifest...");
    setStatus("Loading benchmark manifest...", false, true);

    const benchmarkBaseUrl = new URL("../data/benchmarks/", document.baseURI);
    const manifestRes = await fetch(new URL("benchmark_manifest.json", benchmarkBaseUrl), { cache: "no-store" });

    if (!manifestRes.ok) {
      throw new Error(`Could not load benchmark manifest: HTTP ${manifestRes.status}`);
    }

    benchmarkManifest = await manifestRes.json();
    window.LA_SEND_BENCHMARK_MANIFEST = benchmarkManifest;

    clearSelect(metricFilter, "Select metric");

    const availableMetrics =
      benchmarkManifest.provision_gap_files ||
      benchmarkManifest.la_metric_files ||
      {};

    const metricRowsForSelect = preferredMetrics
      .filter(metric => availableMetrics[metric])
      .map(metric => ({
        metric,
        label: availableMetrics[metric].metric_label || metricLabel(metric)
      }));

    for (const row of metricRowsForSelect) {
      const option = document.createElement("option");
      option.value = row.metric;
      option.textContent = row.label;
      metricFilter.appendChild(option);
    }

    if ([...metricFilter.options].some(o => o.value === "attendance_perc")) {
      metricFilter.value = "attendance_perc";
    } else if (metricFilter.options.length > 1) {
      metricFilter.selectedIndex = 1;
    }

    // ket user know the updated data being pulled/set up
    function scheduleRender(event) {
      if (event && event.target === metricFilter) {
        periodFilter.value = "";
        phaseFilter.value = "";
        if (sendDetailFilter) sendDetailFilter.value = "";
        if (needCategoryFilter) needCategoryFilter.value = "";
      }

      updateRegionHeadings();
      setVisualLoading(true, "Updating charts...");
      render();
    }

    metricFilter.addEventListener("change", scheduleRender);
    regionFilter.addEventListener("change", scheduleRender);
    periodFilter.addEventListener("change", scheduleRender);
    phaseFilter.addEventListener("change", scheduleRender);
    sendFilter.addEventListener("change", scheduleRender);
    if (sendDetailFilter) sendDetailFilter.addEventListener("change", scheduleRender);
    if (needCategoryFilter) needCategoryFilter.addEventListener("change", scheduleRender);

    await render();

  } catch (err) {
    console.error(err);
    clearCharts();
    setVisualLoading(false);
    setControlsDisabled(false);
    setStatus(`<strong>Could not load benchmark story page</strong><br>${escapeHtml(err.message || err)}`, true);
  }
})();
</script>
