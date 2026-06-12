---
title: Benchmarking
---

# Region & LA comparisons

>Compare SEND attendance|absence|inclusion measures against No SEN baseline  
>Choose metric and region to see how selected SEND group, eg `EHC plan` or `SEN support` with those recorded as `No SEN`


Core calc is:

`SEND gap = selected SEND group value - No SEN value`

Gap units depend on selected metric. For attendance and absence percentage fields, gap is **%-point difference**, not count of days. For attendance reason fields, benchmark charts use derived **sessions per 1,000 possible sessions** rate, instead of raw session count. Assumes school day uses 2 attendance sessions(am/pm).

## Derived attendance reason rate

to make LA comparisons fairer on attendance reason fields benchmark charts use:

`reason sessions per 1,000 possible sessions = reason sessions / possible sessions * 1,000`

raw DfE session counts still used in the explorer page(see page tab above); but larger LAs may naturally have larger raw counts so believe it makes sense to adjust pre benchmarking. 

<div class="benchmark-controls">
  <label>
    Region
    <select id="story-region">
      <option value="">All regions</option>
    </select>
  </label>

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
  SEND breakdown
    <select id="story-send-detail">
      <option value="">All SEND breakdowns</option>
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

<div class="benchmark-card">
  <h2>LA SEND gap within selected region</h2>
  <p>
    LA difference from own No SEN baseline for selected SEND group
  </p>
  <div class="chart-loading-wrap" style="height: 520px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="la-gap-chart"></canvas>
  </div>


<div class="benchmark-card">
  <h2>Local authority SEND value vs No SEN value</h2>
  <p>
    LA in region compare selected SEND group value with No SEN val
  </p>
  <div class="chart-loading-wrap" style="height: 520px;">
    <div class="chart-loading-mask">Updating chart...</div>
    <canvas id="la-baseline-chart"></canvas>
  </div>


<div class="benchmark-card">
  <h2>Largest gaps</h2>
  <div id="story-table"></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
(async function () {
  const status = document.getElementById("benchmark-status");

  const regionFilter = document.getElementById("story-region");
  const metricFilter = document.getElementById("story-metric");
  const periodFilter = document.getElementById("story-period");
  const phaseFilter = document.getElementById("story-phase");
  const sendFilter = document.getElementById("story-send");

  const table = document.getElementById("story-table");

  const regionGapCanvas = document.getElementById("region-gap-chart");
  const laGapCanvas = document.getElementById("la-gap-chart");
  const laBaselineCanvas = document.getElementById("la-baseline-chart");

  const controlPanel = document.querySelector(".benchmark-controls");
  const chartWraps = [...document.querySelectorAll(".chart-loading-wrap")];

  const sendDetailFilter = document.getElementById("story-send-detail");

  let renderToken = 0;

  let benchmarkManifest = null;
  let metricRows = [];
  let metricCache = new Map();

  let regionGapChart = null;
  let laGapChart = null;
  let laBaselineChart = null;

  const preferredMetrics = [
    "attendance_perc",
    "overall_absence_perc",
    "authorised_absence_perc",
    "unauthorised_absence_perc",
    "auth_part_time_perc",
    "reason_c2_authorised_temp_reduced_timetable_per_1000_sessions",
    "reason_b_aea_education_off_site_per_1000_sessions",
    "reason_k_aea_education_arranged_by_la_per_1000_sessions",
    // "reason_c2_authorised_temp_reduced_timetable",
    // "reason_b_aea_education_off_site",
    // "reason_k_aea_education_arranged_by_la",
    "sess_overall_percent",
    "sess_unauthorised_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "susp_rate",
    "one_plus_susp_rate",
    "perm_excl_rate"
  ];


  function setControlsDisabled(disabled) {
    for (const el of [regionFilter, metricFilter, periodFilter, phaseFilter, sendFilter, sendDetailFilter]) {
      if (el) el.disabled = disabled;
    }
    if (controlPanel) {
      controlPanel.classList.toggle("is-loading", disabled);
    }
  }

  function setVisualLoading(isLoading, message = "Updating charts...") {
    for (const wrap of chartWraps) {
      wrap.classList.toggle("is-loading", isLoading);

      const mask = wrap.querySelector(".chart-loading-mask");
      if (mask) {
        mask.textContent = message;
      }
    }

    if (table) {
      table.classList.toggle("is-loading", isLoading);
    }
  }

  function clearCharts() {
    if (regionGapChart) {
      regionGapChart.destroy();
      regionGapChart = null;
    }

    if (laGapChart) {
      laGapChart.destroy();
      laGapChart = null;
    }

    if (laBaselineChart) {
      laBaselineChart.destroy();
      laBaselineChart = null;
    }
  }

  function setStatus(message, isError = false, isLoading = false) {
    status.innerHTML = message;

    status.classList.remove(
      "benchmark-status--loading",
      "benchmark-status--error",
      "benchmark-status--ok"
    );

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
    )].sort((a, b) => String(a).localeCompare(String(b)));
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

  function metricLabel(metric) {
    const meta = benchmarkManifest?.la_metric_files?.[metric];

    if (meta && meta.metric_label) {
      return meta.metric_label;
    }

    const fallback = (benchmarkManifest?.metrics || []).find(m => m.column === metric);
    return fallback?.label || metric;
  }

  function metricDirection(metric) {
    const meta = (benchmarkManifest?.metrics || []).find(m => m.column === metric);
    return meta?.direction || "neutral";
  }

  function metricSortForConcern(metric) {
    const direction = metricDirection(metric);

    if (direction === "higher") {
      // attendance- worse gaps are more -ve
      return "ascending";
    }

    if (direction === "lower") {
      // absence / suspension / exclusion- worse gaps are more +ve
      return "descending";
    }

    return "absolute";
  }


  function metricMeta(metric) {
    return (benchmarkManifest?.metrics || []).find(m => m.column === metric) || {};
  }

  function metricType(metric) {
    return metricMeta(metric).metric_type || "value";
  }

  function metricUnit(metric) {
    const type = metricType(metric);

    if (type === "percent") {
      return "% points";
    }

    if (type === "rate") {
      return "rate points per 100 pupils";
    }

    if (type === "rate_per_1000_sessions") {
      return "sessions per 1,000 possible sessions";
    }

    if (type === "count") {
      if (metric.includes("reason_")) {
        return "sessions";
      }

      if (metric === "number_of_pupils") {
        return "pupils";
      }

      if (metric.includes("enrolments")) {
        return "enrolments";
      }

      return "count";
    }

    return "value";
  }

  function metricValueLabel(metric) {
    const label = metricLabel(metric);
    const unit = metricUnit(metric);
    const type = metricType(metric);

    if (type === "percent") {
      return `${label}`;
    }

    if (type === "rate") {
      return `${label} per 100 pupils`;
    }

    if (type === "rate_per_1000_sessions") {
      return `${label}`;
    }

    if (type === "count") {
      return `${label}, ${unit}`;
    }

    return label;
  }

  function gapAxisLabel(metric) {
    const unit = metricUnit(metric);
    return `SEND minus No SEN(Gap), ${unit}`;
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


  function gapLabel(metric) {
    const label = metricLabel(metric);
    return `${label}, SEND minus No SEN`;
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

  async function loadMetricRows(metric) {
    if (!metric) {
      metricRows = [];
      return;
    }

    if (metricCache.has(metric)) {
      metricRows = metricCache.get(metric);
      return;
    }

    const metricInfo = benchmarkManifest?.la_metric_files?.[metric];

    if (!metricInfo || !metricInfo.file) {
      throw new Error(`No LA metric file listed for ${metric}`);
    }

    const url = new URL("../" + metricInfo.file, document.baseURI);

    setStatus(`Loading <code>${escapeHtml(metricInfo.metric_label || metric)}</code> benchmark rows...`, false, true);

    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Could not load ${url.href}: HTTP ${res.status}`);
    }

    const data = await res.json();
    const rows = Array.isArray(data.records) ? data.records : [];

    metricCache.set(metric, rows);
    metricRows = rows;
  }

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

    // first story deliberately SEND attendance/absence focused
    // Keep rows where No SEN baseline can exist
    filtered = filtered.filter(r =>
      r.send_category === "No SEN" ||
      r.send_category === "SEN support" ||
      r.send_category === "EHC plan"
    );

    return filtered;
  }

  function makePairKey(row, level) {
    const parts = [
      row.source_key || "",
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
          source_key: row.source_key,
          source_role: row.source_role,
          source_domain: row.source_domain,
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

      if (row.send_category === selectedSend) {
        item.send_value = Number(row.value);
      }

      if (row.send_category === "No SEN") {
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
          metric: row.metric,
          metric_label: row.metric_label,
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

  function destroyChart(chart) {
    if (chart) {
      chart.destroy();
    }
  }

  function renderRegionGapChart() {
    const metric = metricFilter.value;
    const rows = sortByConcern(aggregateRegionGapsFromLa(), metric);

    destroyChart(regionGapChart);

    if (!rows.length) {
      regionGapCanvas.style.display = "none";
      return null;
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
          title: {
            display: true,
            text: currentSliceLabel()
          },
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
          y: {
            ticks: {
              autoSkip: false
            }
          },
          x: {
            title: {
              display: true,
              text: gapAxisLabel(metric)
            }
          }
        }
      }
    });

    return rows;
  }

  function renderLaGapChart() {
    const metric = metricFilter.value;
    const region = regionFilter.value;

    let rows = computeGapRows("la");

    if (region) {
      rows = rows.filter(r => r.region_name === region || r.region_code === region || r.region_label === region);
    }

    rows = sortByConcern(rows, metric).slice(0, 40);

    destroyChart(laGapChart);

    if (!rows.length) {
      laGapCanvas.style.display = "none";
      return null;
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
          title: {
            display: true,
            text: currentSliceLabel()
          },
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: context => `${context.dataset.label}: ${formatValue(context.raw)}`
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: gapAxisLabel(metric)
            }
          }
        }
      }
    });

    return rows;
  }

  function renderLaBaselineChart() {
    const metric = metricFilter.value;
    const region = regionFilter.value;

    let rows = computeGapRows("la");

    if (region) {
      rows = rows.filter(r => r.region_name === region || r.region_code === region || r.region_label === region);
    }

    rows = sortByConcern(rows, metric).slice(0, 25);

    destroyChart(laBaselineChart);

    if (!rows.length) {
      laBaselineCanvas.style.display = "none";
      return null;
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
          title: {
            display: true,
            text: currentSliceLabel()
          },
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: context => `${context.dataset.label}: ${formatValue(context.raw)}`
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: metricValueLabel(metric)
            }
          }
        }
      }
    });

    return rows;
  }

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
      "time_period",
      "education_phase",
      "selected_send",
      "send_value",
      "no_sen_value",
      "gap_to_no_sen"
    ];

    const labels = {
      region_name: "Region",
      la_name: "LA",
      time_period: "Period",
      education_phase: "Phase",
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
        metric <strong>${escapeHtml(metricLabel(metric))}</strong>.
      </p>
      <div style="overflow:auto; max-height:60vh;">
        <table>
          <thead><tr>${header}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  function currentSliceLabel() {
    const parts = [];

    if (metricFilter.value) {
      parts.push(metricLabel(metricFilter.value));
    }

    if (sendFilter.value) {
      parts.push(sendFilter.value);
    }

    if (periodFilter.value) {
      parts.push(`period ${periodFilter.value}`);
    }

    if (phaseFilter.value) {
      parts.push(phaseFilter.value);
    }

    return parts.join(" | ");
  }

  function refreshFiltersFromMetricRows() {
    const previousRegion = regionFilter.value;
    const previousPeriod = periodFilter.value;
    const previousPhase = phaseFilter.value;
    const previousSendDetail = sendDetailFilter ? sendDetailFilter.value : "";

    if (sendDetailFilter) {
      clearSelect(sendDetailFilter, "All SEND breakdowns");
      addOptions(sendDetailFilter, uniqueValues(metricRows, "send_detail_display"));

      if ([...sendDetailFilter.options].some(o => o.value === previousSendDetail)) {
        sendDetailFilter.value = previousSendDetail;
      }
    }
    clearSelect(regionFilter, "All regions");
    clearSelect(periodFilter, "All periods");
    clearSelect(phaseFilter, "All phases");

    addOptions(regionFilter, uniqueValues(metricRows, "region_name"));
    addOptions(periodFilter, uniqueValues(metricRows, "time_period"));
    addOptions(phaseFilter, uniqueValues(metricRows, "education_phase"));

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

      // If another render started while this one was loading, abandon this result.
      if (thisRender !== renderToken) {
        return;
      }

      refreshFiltersFromMetricRows();
      ensureSingleChartSliceSelected();

      if (thisRender !== renderToken) {
        return;
      }

      const laGapRows = renderLaGapChart() || [];
      renderRegionGapChart();
      renderLaBaselineChart();
      renderTable(laGapRows);

      setStatus(
        `Loaded ${metricRows.length.toLocaleString()} rows for ` +
        `<strong>${escapeHtml(metricLabel(metric))}</strong>.`
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

    const availableMetrics = benchmarkManifest.la_metric_files || {};
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
    }

    // ket user know the updated data being pulled/set up
    function scheduleRender() {
      setVisualLoading(true, "Updating charts...");
      render();
    }

    metricFilter.addEventListener("change", scheduleRender);
    regionFilter.addEventListener("change", scheduleRender);
    periodFilter.addEventListener("change", scheduleRender);
    phaseFilter.addEventListener("change", scheduleRender);
    sendFilter.addEventListener("change", scheduleRender);

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