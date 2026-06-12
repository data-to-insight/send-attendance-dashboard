---
title: " "
hide:
  # - title
  - navigation
  - toc
---

<style>
  .md-grid {
    max-width: none;
  }

  .md-main__inner {
    margin: 0;
  }

  .md-content {
    max-width: none;
  }

  .md-content__inner {
    margin: 0;
    max-width: none;
    padding-left: 1.2rem;
    padding-right: 1.2rem;
  }
</style>


Data from generated regional JSON files under `docs/data/regions/`, loaded via `docs/data/la_send_manifest.json`.
<p>
  Combines LA level breakdowns for attendance, absence, suspensions and exclusions by SEND-related characteristic 
</p>

<div id="send-load-status" style="padding:.6rem .8rem; border:1px solid #ddd; margin:.5rem 0 1rem 0;">
  Loading LA SEND preview data...
</div>


<input id="send-search" type="search" placeholder="Search LA, source, SEN group, measure..." style="width:100%; padding:.6rem; margin:.5rem 0 1rem 0;">

<div id="send-summary"></div>

<div style="display:flex; gap:.5rem; flex-wrap:wrap; margin:1rem 0;">
  <select id="send-region-filter">
    <option value="">All regions</option>
  </select>

  <select id="send-la-filter">
    <option value="">All local authorities</option>
  </select>

  <select id="send-source-filter">
    <option value="">All sources</option>
  </select>

    <select id="send-group-filter">
    <option value="">All SEND groups</option>
    </select>
</div>

<div id="send-table"></div>

<script>
(async function () {
  const statusBox = document.getElementById("send-load-status");
  const summary = document.getElementById("send-summary");
  const search = document.getElementById("send-search");
  const regionFilter = document.getElementById("send-region-filter");
  const laFilter = document.getElementById("send-la-filter");
  const sourceFilter = document.getElementById("send-source-filter");
  const sendGroupFilter = document.getElementById("send-group-filter");
  const table = document.getElementById("send-table");

  let manifest = null;
  let records = [];
  const regionCache = new Map();

  const DATA_BASE_URL = new URL("../data/", document.baseURI);

  function setStatus(message, isError = false) {
    if (!statusBox) return;
    statusBox.innerHTML = message;
    statusBox.style.borderColor = isError ? "#b00020" : "#ddd";
    statusBox.style.background = isError ? "#fff4f4" : "#fafafa";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatValue(value, column = "") {
    if (value === null || value === undefined || value === "") {
      return "";
    }

    const textColumns = new Set([
      "time_period",
      "academic_year",
      "new_la_code",
      "old_la_code",
      "region_code"
    ]);

    if (textColumns.has(column)) {
      return String(value);
    }

    const num = Number(value);

    if (!Number.isNaN(num) && Number.isFinite(num)) {
      return num.toLocaleString(undefined, {
        maximumFractionDigits: 3
      });
    }

    return value;
  }

  function uniqueValues(rows, field) {
    return [...new Set(rows.map(r => r[field]).filter(Boolean))]
      .sort((a, b) => String(a).localeCompare(String(b)));
  }

  function clearSelect(selectEl, label) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = label;
    selectEl.appendChild(option);
  }

  function addOptions(selectEl, values) {
    if (!selectEl) return;

    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      selectEl.appendChild(option);
    }
  }

  function laLabel(row) {
    const name = row.la_name || "";
    const code = row.new_la_code || "";
    return code ? `${name} (${code})` : name;
  }

  function rowText(row) {
    return Object.values(row).join(" ").toLowerCase();
  }

  function columnLabel(column) {
    const labels = {
      region_name: "Region",
      la_name: "LA",
      time_period: "Period",
      time_identifier: "Type",
      source_url: "Source",
      education_phase: "Phase",
      send_category: "SEND",
      send_detail_display: "Detail",
      // VG requested
      reason_c2_authorised_temp_reduced_timetable: "C2 temp timetable",
      reason_b_aea_education_off_site: "B off-site edu",
      reason_k_aea_education_arranged_by_la: "K LA arranged",

      attendance_perc: "Attend %",
      overall_attendance: "Attend",
      overall_absence_perc: "Abs %",
      authorised_absence_perc: "Auth %",
      unauthorised_absence_perc: "Unauth %",
      appointments_perc: "Appt %",
      illness_perc: "Ill %",
      auth_excluded_perc: "Excl %",
      auth_part_time_perc: "PTT %",
      possible_sessions: "Poss",
      present_sessions: "Pres",

      enrolments: "Enrol",
      sess_possible: "Poss",
      sess_overall_percent: "Abs %",
      sess_authorised_percent: "Auth %",
      sess_unauthorised_percent: "Unauth %",
      enrolments_pa_10_exact_percent: "PA 10%+",
      enrolments_pa_50_exact_percent: "SA 50%+",
      sess_auth_illness_rate: "Ill rate",
      sess_auth_appointments_rate: "Appt rate",
      sess_auth_excluded_rate: "Excl rate",
      sess_auth_temp_reduced_timetable_rate: "RTT rate",

      susp_rate: "Susp rate",
      one_plus_susp_rate: "1+ susp",
      perm_excl_rate: "Perm excl",

      number_of_pupils: "Pupils"
    };

    return labels[column] || column;
  }

  function sourceCards(manifest) {
    const registry = manifest.source_registry || {};
    const keys = manifest.source_keys || [];

    if (!keys.length) {
      return "<p>No source keys found in the manifest.</p>";
    }

    return keys.map(key => {
      const meta = registry[key] || {};
      const title = meta.source_title || key;
      const url = meta.source_url || "";
      const domain = meta.source_domain || "";

      const link = url
        ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>`
        : escapeHtml(title);

      return `
        <div class="send-source-card">
          <div><strong>${link}</strong></div>
          <div><code>${escapeHtml(key)}</code></div>
          <div>${escapeHtml(domain)}</div>
        </div>
      `;
    }).join("");
  }

  function populateLaFilter(rows) {
    clearSelect(laFilter, "All local authorities");

    const laOptions = [...new Map(
      rows
        .filter(r => r.new_la_code || r.la_name)
        .map(r => [r.new_la_code || r.la_name, laLabel(r)])
    ).entries()]
    .sort((a, b) => a[1].localeCompare(b[1]));

    for (const [value, label] of laOptions) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      laFilter.appendChild(option);
    }
  }

  function refreshFilters(rows) {
    populateLaFilter(rows);

    clearSelect(sourceFilter, "All sources");
    addOptions(sourceFilter, uniqueValues(rows, "source_domain"));

    clearSelect(sendGroupFilter, "All SEND groups");
    addOptions(sendGroupFilter, uniqueValues(rows, "send_category"));
  }

  async function loadRegion(regionFile) {
    if (!regionFile) {
      records = [];
      refreshFilters(records);
      table.innerHTML = "<p>Select a region to load data.</p>";
      return;
    }

    if (regionCache.has(regionFile)) {
      records = regionCache.get(regionFile);
      refreshFilters(records);
      render();
      return;
    }

    const url = new URL(regionFile, DATA_BASE_URL);

    setStatus(`Loading region data from <code>${escapeHtml(url.href)}</code>...`);

    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Fetch failed: HTTP ${res.status} ${res.statusText} for ${url.href}`);
    }

    const data = await res.json();
    records = Array.isArray(data.records) ? data.records : [];

    regionCache.set(regionFile, records);

    refreshFilters(records);

    setStatus(
      `Loaded ${records.length.toLocaleString()} records for ${escapeHtml(data.region_label || data.region_name || regionFile)}.`
    );

    render();
  }

  function render() {
    const q = search.value.trim().toLowerCase();
    const la = laFilter.value;
    const source = sourceFilter.value;
    const sendGroup = sendGroupFilter.value;

    let filtered = records;

    if (la) {
      filtered = filtered.filter(r => (r.new_la_code || r.la_name) === la);
    }

    if (source) {
      filtered = filtered.filter(r => r.source_domain === source);
    }

    if (sendGroup) {
      filtered = filtered.filter(r => r.send_category === sendGroup);
    }

    if (q) {
      filtered = filtered.filter(r => rowText(r).includes(q));
    }

    const shown = filtered.slice(0, 250);

    const baseColumns = [
      "region_name",
      "la_name",
      "time_period",
      "time_identifier",
      "source_url",
      "education_phase",
      "send_category",
      "send_detail_display"
    ];

    const preferredMeasures = [
      "attendance_perc",
      "overall_attendance",
      "overall_absence_perc",
      "authorised_absence_perc",
      "unauthorised_absence_perc",
      "appointments_perc",
      "illness_perc",
      "auth_excluded_perc",
      "auth_part_time_perc",
      "possible_sessions",
      "present_sessions",
      // VG request
      "reason_c2_authorised_temp_reduced_timetable",
      "reason_b_aea_education_off_site",
      "reason_k_aea_education_arranged_by_la",

      "enrolments",
      "sess_possible",
      "sess_overall_percent",
      "sess_authorised_percent",
      "sess_unauthorised_percent",
      "enrolments_pa_10_exact_percent",
      "enrolments_pa_50_exact_percent",
      "sess_auth_illness_rate",
      "sess_auth_appointments_rate",
      "sess_auth_excluded_rate",
      "sess_auth_temp_reduced_timetable_rate",

      "susp_rate",
      "one_plus_susp_rate",
      "perm_excl_rate",

      "number_of_pupils"
    ];

    const availableColumns = new Set(filtered.flatMap(r => Object.keys(r)));

    // //replace/d with below to force width fit for too-wide data table
    // const columns = [
    //   ...baseColumns.filter(c => availableColumns.has(c)),
    //   ...preferredMeasures.filter(c => availableColumns.has(c))
    // ];
    // table fit to width repalcement/tmp block START
    const candidateColumns = [
      ...baseColumns.filter(c => availableColumns.has(c)),
      ...preferredMeasures.filter(c => availableColumns.has(c))
    ];

    function hasVisibleValue(rows, column) {
      return rows.some(row => {
        const value = row[column];
        return value !== null
          && value !== undefined
          && value !== ""
          && value !== "nan"
          && value !== "NaN";
      });
    }

    const alwaysShowColumns = new Set([
      "region_name",
      "la_name",
      "time_period",
      "time_identifier",
      "source_url",
      "education_phase",
      "send_category",
      "send_detail_display"
    ]);

    const columns = candidateColumns.filter(c =>
      alwaysShowColumns.has(c) || hasVisibleValue(filtered, c)
    );
    // table fit to width repalcement/tmp block end


    const header = columns.map(c => `<th>${escapeHtml(columnLabel(c))}</th>`).join("");

    const body = shown.map(row => {
      const cells = columns.map(c => {
        if (c === "source_url" && row[c]) {
          return `<td><a href="${escapeHtml(row[c])}" target="_blank" rel="noopener noreferrer">source</a></td>`;
        }

        return `<td>${escapeHtml(formatValue(row[c], c))}</td>`;
      }).join("");

      return `<tr>${cells}</tr>`;
    }).join("");

    table.innerHTML = `
      <p>Showing ${shown.length} of ${filtered.length} matching records. Showing ${columns.length} populated columns.</p>
      <div id="send-table-wrap">
        <table>
          <thead><tr>${header}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  try {
    const manifestUrl = new URL("la_send_manifest.json", DATA_BASE_URL);

    setStatus(`Loading manifest from <code>${escapeHtml(manifestUrl.href)}</code>...`);

    const res = await fetch(manifestUrl, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Fetch failed: HTTP ${res.status} ${res.statusText} for ${manifestUrl.href}`);
    }

    manifest = await res.json();

    window.LA_SEND_MANIFEST = manifest;

    clearSelect(regionFilter, "Select region");

    for (const region of manifest.regions || []) {
      const option = document.createElement("option");
      option.value = region.file;
      option.textContent = `${region.region_label || region.region_name} (${Number(region.record_count || 0).toLocaleString()} records)`;
      regionFilter.appendChild(option);
    }

    clearSelect(laFilter, "All local authorities");
    clearSelect(sourceFilter, "All sources");
    clearSelect(sendGroupFilter, "All SEND groups");

    summary.innerHTML = `
      <p><strong>Generated:</strong> ${escapeHtml(manifest.generated_at || "")}</p>
      <p><strong>Regions:</strong> ${Number(manifest.region_count || 0).toLocaleString()}</p>
      <p><strong>Local authority rows:</strong> ${Number(manifest.kept_local_authority_row_count || 0).toLocaleString()}</p>

      <details>
        <summary>Source files</summary>
        ${sourceCards(manifest)}
      </details>
    `;

    setStatus("Manifest loaded. Select region to load table data");

    regionFilter.addEventListener("change", async () => {
      try {
        await loadRegion(regionFilter.value);
      } catch (err) {
        console.error(err);
        setStatus(`<strong>Could not load region.</strong><br>${escapeHtml(err.message || err)}`, true);
      }
    });

    search.addEventListener("input", render);
    laFilter.addEventListener("change", render);
    sourceFilter.addEventListener("change", render);
    sendGroupFilter.addEventListener("change", render);

    table.innerHTML = "<p>Select region to load data</p>";

  } catch (err) {
    console.error(err);

    setStatus(
      `
        <strong>Could not load LA SEND manifest</strong><br>
        ${escapeHtml(err.message || err)}<br><br>
        Check file exists:<br>
        <code>docs/data/la_send_manifest.json</code>
      `,
      true
    );
  }
})();
</script>