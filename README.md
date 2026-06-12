# DfE SEND attendance, absence, suspensions and exclusions

LA level data from DfE Explore Education Stats endpoints

focus:

- attendance by SEN
- absence by pupil characteristics, filtered to SEND related
- suspensions and permanent exclusions by pupil characteristic, filtered to SEND related
- SEN profile and primary need context

## Shape notes

DfE sources dont all share one (easier) "SEND outcome" granularity

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

Outputs to:

```text
data/raw/
data/processed/
```


## Source files

Source list in:

```text
config/sources.json
```

Current sources:

| Source key | Domain | Notes |
|---|---|---|
| `attendance_sen_2024_25_academic_year` | `attendance_sen` | Full 2024/25 academic year attendance by SEN |
| `attendance_sen_2025_26_autumn_term` | `attendance_sen` | Autumn 2025/26 attendance by SEN |
| `attendance_sen_2025_26_spring_term` | `attendance_sen` | Spring 2025/26 attendance by SEN |
| `absence_characteristics_2024_25` | `absence_characteristics` | absence by characteristics, filtered to SEND rows |
| `exclusions_characteristics_2024_25_spring` | `exclusions_characteristics` | suspensions and permanent exclusions by characteristics, filtered to SEND rows |
| `sen_profile_year_group_need_2024_25` | `sen_profile` | SEN denominator and primary need profile |

## Add new EES files

If/when DfE publishes newer SEN attendance feed, add new object in `config/sources.json` e.g.:

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

Keep older source keys, so can reproduce historic outputs
