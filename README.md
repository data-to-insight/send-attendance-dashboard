# DfE SEND attendance, absence, suspensions and exclusions starter

This is a small starter repo for building local authority level England datasets from DfE Explore Education Statistics CSV endpoints.

It focuses on:

- attendance by SEN
- absence by pupil characteristics, filtered to SEND related rows
- suspensions and permanent exclusions by pupil characteristic, filtered to SEND related rows
- SEN profile and primary need context

## Why this shape

The DfE sources do not all share one tidy "SEND outcome" grain. The safer pattern is to keep source-specific processed tables, then create a long measure table with shared join fields.

Main join spine:

```text
new_la_code
time_period
time_identifier
education_phase or phase_type_grouping
sen, breakdown, characteristic, sen_status, sen_primary_need
```

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell users may prefer: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/build_dfe_send_attendance_exclusions.py --refresh
```

Outputs are written to:

```text
data/raw/
data/processed/
```

The most useful combined file is:

```text
data/processed/la_send_measure_long.csv
```

## Source files

The source list is in:

```text
config/sources.json
```

Current starter sources:

| Source key | Domain | Notes |
|---|---|---|
| `attendance_sen_2024_25_academic_year` | `attendance_sen` | Full 2024/25 academic year attendance by SEN |
| `attendance_sen_2025_26_autumn_term` | `attendance_sen` | Autumn 2025/26 attendance by SEN |
| `attendance_sen_2025_26_spring_term` | `attendance_sen` | Spring 2025/26 attendance by SEN |
| `absence_characteristics_2024_25` | `absence_characteristics` | Accredited absence by characteristics, filtered to SEND rows |
| `exclusions_characteristics_2024_25_spring` | `exclusions_characteristics` | Accredited suspensions and permanent exclusions by characteristics, filtered to SEND rows |
| `sen_profile_year_group_need_2024_25` | `sen_profile` | SEN denominator and primary need profile |

## Suggested use

Use the source-specific tables for exact publication-aligned analysis.

Use `la_send_measure_long.csv` for exploratory charting, local authority dashboards and cross-source joins.

For example, to compare LA level SEND attendance and suspension rates:

1. Filter `source_domain = attendance_sen`, `measure_name = attendance_perc`
2. Filter `source_domain = exclusions_characteristics`, `measure_name = susp_rate`
3. Join on `new_la_code`, compatible `time_period` or reporting window, `education_phase`, and SEND grouping
4. Treat `time_period` carefully, because attendance may be annual or termly while exclusions are termly

## Adding newer EES files

When DfE publishes a newer SEN attendance feed, add a new object in `config/sources.json` using:

```json
{
  "key": "attendance_sen_2026_27_autumn_term",
  "domain": "attendance_sen",
  "title": "Example",
  "publication": "Pupil attendance in schools",
  "release": "Autumn term 2026/27",
  "url": "https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/<dataset-id>/csv",
  "page_url": "https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/<dataset-id>",
  "grain_hint": "new_la_code, time_period, time_identifier, education_phase, sen",
  "why": "Termly attendance by SEN"
}
```

Keep older source keys rather than overwriting them, so historic outputs remain reproducible.
