
I'll come back to this, but some notes re per-session conv on benchmarking visuals

## Derived attendance reason rate

Core calc is:

`SEND gap = selected SEND group value - No SEN value`

Gap units depend on selected metric. For attendance and absence percentage fields, gap is **%-point difference**, not count of days. For attendance reason fields, benchmark charts use derived **sessions per 1,000 possible sessions** rate, instead of raw session count. Assumes school day uses 2 attendance sessions(am/pm).

## Derived attendance reason rate

to make LA comparisons fairer on attendance reason fields benchmark charts use:

`reason sessions per 1,000 possible sessions = reason sessions / possible sessions * 1,000`

Gap units depend on selected metric. For attendance and absence percentage fields, gap is **%-point difference**, not count of days. For attendance reason fields, benchmark charts use derived **sessions per 1,000 possible sessions** rate, instead of raw session count. Assumes school day uses 2 attendance sessions(am/pm).


## Overview of data sources

| metric  | data source fields | source file / url |
|---|---|---|
| Attendance % | `attendance_perc`, `overall_absence_perc`, `authorised_absence_perc`, `unauthorised_absence_perc`, `auth_part_time_perc` | source file(s) `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for context `attendance_current_ytd_2025_26_week20_processed.csv.gz`. <br><br>Autumn SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/c4f3e40d-a038-464c-9740-062a2a1a420e/csv`<br>Spring SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/d8b4d97d-0c39-4d96-91e3-6714a7d47342/csv` |
| Absence characteristics % | `sess_overall_percent`, `sess_authorised_percent`, `sess_unauthorised_percent`, `enrolments_pa_10_exact_percent`, `enrolments_pa_50_exact_percent` | Source file: `absence_characteristics_2024_25_autumn_spring_processed.csv.gz`. <br><br>DfE CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/a5f750db-286a-4d63-a31b-d2a5c1d6d7e0/csv` |
| Attendance reason rates, derived for benchmarking | `reason_c2_authorised_temp_reduced_timetable_per_1000_sessions`, `reason_b_aea_education_off_site_per_1000_sessions`, `reason_k_aea_education_arranged_by_la_per_1000_sessions` | Derived from attendance source files, especially `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for context `attendance_current_ytd_2025_26_week20_processed.csv.gz`. <br><br>Uses DfE fields such as `possible_sessions` + raw reason session count fields |
| Attendance reason raw counts | `reason_c2_authorised_temp_reduced_timetable`, `reason_b_aea_education_off_site`, `reason_k_aea_education_arranged_by_la` | Source file(s): `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for context `attendance_current_ytd_2025_26_week20_processed.csv.gz`. <br><br>Autumn SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/c4f3e40d-a038-464c-9740-062a2a1a420e/csv`<br>Spring SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/d8b4d97d-0c39-4d96-91e3-6714a7d47342/csv` |
| Suspension and exclusion rates | `susp_rate`, `one_+_susp_rate`, `perm_excl_rate` | Source file(s): `exclusions_characteristics_2024_25_spring_term_processed.csv.gz`. <br><br>DfE CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/ed60fee6-bdab-414b-82d9-337f914575de/csv` |
| SEN profile counts | `number_of_pupils` | Source file(s): `sen_profile_year_group_need_2024_25_processed.csv.gz`. Confirm exact DfE URL from `docs/data/la_send_manifest.json` or `data/processed/source_manifest.csv`, as depends on configured SEN profile source. |


## Overview of dat asources full

| Metric family | Data source fields | DfE source group | Source file / URL | SEND value / No SEN value means | Gap means | Interpretation note |
|---|---|---|---|---|---|---|
| Attendance % | `attendance_perc`, `overall_absence_perc`, `authorised_absence_perc`, `unauthorised_absence_perc`, `auth_part_time_perc` | DfE: Pupil school attendance, attendance by SEN / attendance context datasets | source file(s) `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for context `attendance_current_ytd_2025_26_week20_processed.csv.gz`.<br><br>Autumn SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/c4f3e40d-a038-464c-9740-062a2a1a420e/csv`<br>Spring SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/d8b4d97d-0c39-4d96-91e3-6714a7d47342/csv` | % of poss sessions | %-point difference | For `attendance_perc`: For absence measures: -ve SEND gap means selected SEND group < No SEN in absenses &  +ve SEND gap means selected SEND group > No SEN in absences |
| Absence characteristics % | `sess_overall_percent`, `sess_authorised_percent`, `sess_unauthorised_percent`, `enrolments_pa_10_exact_percent`, `enrolments_pa_50_exact_percent` | DfE: Pupil absence in schools in England, pupil characteristics datasets | Source file: `absence_characteristics_2024_25_autumn_spring_processed.csv.gz`.<br><br>DfE CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/a5f750db-286a-4d63-a31b-d2a5c1d6d7e0/csv` | % of sessions, depending on field | %-point difference | Persistent absence == missing >10%  sessions. Severe absence == missing >50% sessions |
| Attendance reason rates, derived for benchmarking | `reason_c2_authorised_temp_reduced_timetable_per_1000_sessions`, `reason_b_aea_education_off_site_per_1000_sessions`, `reason_k_aea_education_arranged_by_la_per_1000_sessions` | Derived from DfE: Pupil attendance in schools, attendance reason fields | Derived from the attendance source files, especially `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for current context `attendance_current_ytd_2025_26_week20_processed.csv.gz`.<br><br>Uses DfE fields such as `possible_sessions` + raw reason session count fields. | Number of reason sessions per 1,000 possible sessions | Rate difference, sessions per 1,000 possible sessions | derived benchmark fields. preferred for LA-vs-LA comparison as they adjust for size of attendance denominator |
| Attendance reason raw counts | `reason_c2_authorised_temp_reduced_timetable`, `reason_b_aea_education_off_site`, `reason_k_aea_education_arranged_by_la` | DfE: Pupil attendance in schools, attendance reason fields | source file(s): `attendance_sen_2025_26_autumn_term_processed.csv.gz`, `attendance_sen_2025_26_spring_term_processed.csv.gz`, for context `attendance_current_ytd_2025_26_week20_processed.csv.gz`.<br><br>Autumn SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/c4f3e40d-a038-464c-9740-062a2a1a420e/csv`<br>Spring SEN CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/d8b4d97d-0c39-4d96-91e3-6714a7d47342/csv` | Number of attendance sessions recorded with that reason | Session-count difference | session counts, not days and not rates. Larger LAs may have larger counts, so raw counts are less fair for benchmarking unless converted to rate |
| Suspension and exclusion rates | `susp_rate`, `one_+_susp_rate`, `perm_excl_rate` | DfE: Suspensions and permanent exclusions in England, pupil characteristics datasets | source file(s): `exclusions_characteristics_2024_25_spring_term_processed.csv.gz`.<br><br>DfE CSV: `https://explore-education-statistics.service.gov.uk/data-catalogue/data-set/ed60fee6-bdab-414b-82d9-337f914575de/csv` | Rate per 100 pupils | Rate-point diff per 100 pupils | DfEsuspension rate == suspensions/pupils*100. also permanent exclusion rate |
| SEN profile counts | `number_of_pupils` | DfE: SEN in England / SEN profile-style datasets | source file(s): `sen_profile_year_group_need_2024_25_processed.csv.gz`. DfE url in `docs/data/la_send_manifest.json` or `data/processed/source_manifest.csv`, as depends on SEN profile source | Pupil count | Pupil-count difference | context for cohort size but not ideal as siloed SEND-vs-No-SEN gap story |


