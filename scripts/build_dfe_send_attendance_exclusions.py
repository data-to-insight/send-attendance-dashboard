#!/usr/bin/env python3
"""
Build starter local authority SEND attendance, absence, suspension and exclusion data pack

The script:
- read DfE Explore Education Statistics CSV endpoints from config/sources.json
- download each source to data/raw
- filter to local authority rows
- keep SEND related rows where relevant
- write source-specific processed CSVs
- write long-form combined measure table for easier joining and exploration

Example:
    python scripts/build_dfe_send_attendance_exclusions.py --refresh

Optional:
    python scripts/build_dfe_send_attendance_exclusions.py --only attendance_sen_2025_26_spring_term
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


SEND_TERMS = (
    "sen",
    "special educational need",
    "special education need",
    "ehc",
    "education, health and care",
    "statement",
    "school action",
    "support",
)

SOURCE_COLUMNS = [
    "source_key",
    "source_domain",
    "source_title",
    "source_url",
    "source_csv_url",
    "source_role",
    "cadence",
    "freshness_tier",
    "send_disaggregated",
    "current_context",
]

REASON_SESSION_COLS = [
    "reason_c2_authorised_temp_reduced_timetable",
    "reason_b_aea_education_off_site",
    "reason_k_aea_education_arranged_by_la",
]

@dataclass(frozen=True)
class Source:
    key: str
    domain: str
    title: str
    publication: str = ""
    release: str = ""
    url: str = ""
    page_url: str = ""
    grain_hint: str = ""
    why: str = ""

    # New source classification fields for MkDocs/UI layer
    cadence: str = ""
    freshness_tier: str = ""
    source_role: str = ""
    send_disaggregated: bool | None = None
    current_context: bool | None = None


def read_sources(path: Path = CONFIG_PATH) -> list[Source]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    allowed = {field.name for field in fields(Source)}

    sources = []
    for item in payload["sources"]:
        filtered = {key: value for key, value in item.items() if key in allowed}
        sources.append(Source(**filtered))

    return sources


def safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    cleaned = cleaned.strip("_").lower()
    return cleaned or "source"


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        pd.Index(df.columns)
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def is_local_authority(df: pd.DataFrame) -> pd.Series:
    if "geographic_level" not in df.columns:
        return pd.Series([True] * len(df), index=df.index)

    return (
        df["geographic_level"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("local authority")
    )


def contains_any(series: pd.Series, terms: Iterable[str]) -> pd.Series:
    text = series.fillna("").astype(str).str.lower()
    mask = pd.Series([False] * len(series), index=series.index)
    for term in terms:
        mask = mask | text.str.contains(term, regex=False)
    return mask


def select_present(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[c for c in columns if c in df.columns]].copy()



def with_source_columns(columns: list[str]) -> list[str]:
    return SOURCE_COLUMNS + columns

def add_source_columns(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    df = df.copy()

    source_values = {
        "source_key": source.key,
        "source_domain": source.domain,
        "source_title": source.title,
        "source_url": source.page_url or source.url,
        "source_csv_url": source.url,
        "source_role": source.source_role or source.domain,
        "cadence": source.cadence,
        "freshness_tier": source.freshness_tier,
        "send_disaggregated": source.send_disaggregated,
        "current_context": source.current_context,
    }

    # Assignment safer than insert as cant create dup col names
    for col, value in source_values.items():
        df[col] = value

    ordered = list(source_values.keys()) + [
        col for col in df.columns
        if col not in source_values
    ]

    return df[ordered].copy()


def download_source(source: Source, refresh: bool = False) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{safe_filename(source.key)}.csv"

    if raw_path.exists() and not refresh:
        print(f"Using cached raw file: {raw_path.relative_to(PROJECT_ROOT)}")
        return raw_path

    print(f"Downloading: {source.key}")
    df = pd.read_csv(source.url, low_memory=False)
    df = normalise_columns(df)
    df.to_csv(raw_path, index=False)
    print(f"Saved raw file: {raw_path.relative_to(PROJECT_ROOT)} ({len(df):,} rows)")
    return raw_path


def read_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    return normalise_columns(df)


def process_attendance_sen(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    """
    Attendance by SEN feeds already contain sen col, so keep all SEN vals:
    No SEN, SEN support and EHC plan. Keeping No SEN helps benchmarking
    """
    df = df[is_local_authority(df)].copy()

    keep_cols = with_source_columns([
        "source_key",
        "source_domain",
        "source_title",
        "source_url",
        "time_period",
        "time_identifier",
        "academic_year",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "new_la_code",
        "old_la_code",
        "la_name",
        "education_phase",
        "sen",
        "num_schools",
        "possible_sessions",
        "present_sessions",
        "approved_educational_activity",
        "overall_attendance",
        "overall_absence",
        "authorised_absence",
        "unauthorised_absence",
        "late_sessions",
        "reason_c2_authorised_temp_reduced_timetable",
        "reason_b_aea_education_off_site",
        "reason_k_aea_education_arranged_by_la",
        "attendance_perc",
        "overall_absence_perc",
        "authorised_absence_perc",
        "unauthorised_absence_perc",
        "illness_perc",
        "appointments_perc",
        "unauth_hol_perc",
        "unauth_oth_perc",
        "unauth_late_registers_closed_perc",
        "unauth_not_yet_perc",
        "auth_excluded_perc",
        "auth_part_time_perc",
        "pa_perc",
    ])

    out = add_source_columns(df, source)
    return select_present(out, keep_cols)

def process_attendance_current(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    """
    Current attendance context feeds from fortnightly attendance release

    useful for current LA-level context, but not SEND-disaggregated
    unless source itself contains SEN col


    keeps likely Week 20 fields where they exist 
    Missing fields harmless because select_present() drops absent cols

    """
    df = df[is_local_authority(df)].copy()

    keep_cols = with_source_columns([
        "time_period",
        "time_identifier",
        "academic_year",
        "attendance_date",
        "week_start_date",
        "week_commencing",
        "time_frame",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "new_la_code",
        "old_la_code",
        "la_name",
        "education_phase",
        "num_schools",
        "possible_sessions",
        "present_sessions",
        "approved_educational_activity",
        "overall_attendance",
        "overall_absence",
        "authorised_absence",
        "unauthorised_absence",
        "late_sessions",
        "attendance_perc",
        "overall_absence_perc",
        "authorised_absence_perc",
        "unauthorised_absence_perc",
        "illness_perc",
        "appointments_perc",
        "unauth_hol_perc",
        "unauth_oth_perc",
        "unauth_late_registers_closed_perc",
        "unauth_not_yet_perc",
        "auth_excluded_perc",
        "auth_part_time_perc",
        "pa_perc",
    ])

    out = add_source_columns(df, source)
    return select_present(out, keep_cols)


def process_absence_characteristics(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    df = df[is_local_authority(df)].copy()

    if "breakdown_topic" in df.columns:
        topic_mask = contains_any(df["breakdown_topic"], SEND_TERMS)
    else:
        topic_mask = pd.Series([False] * len(df), index=df.index)

    if "breakdown" in df.columns:
        detail_mask = contains_any(df["breakdown"], SEND_TERMS)
    else:
        detail_mask = pd.Series([False] * len(df), index=df.index)

    df = df[topic_mask | detail_mask].copy()

    keep_cols = with_source_columns([
        "source_key",
        "source_domain",
        "source_title",
        "source_url",
        "time_period",
        "time_identifier",
        "absence_terms",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "old_la_code",
        "new_la_code",
        "la_name",
        "education_phase",
        "breakdown_topic",
        "breakdown",
        "enrolments",
        "sess_possible",
        "sess_overall",
        "sess_authorised",
        "sess_unauthorised",
        "sess_overall_percent",
        "sess_authorised_percent",
        "sess_unauthorised_percent",
        "enrolments_pa_10_exact",
        "enrolments_pa_10_exact_percent",
        "enrolments_pa_50_exact",
        "enrolments_pa_50_exact_percent",
        "sess_auth_illness_rate",
        "sess_auth_appointments_rate",
        "sess_auth_excluded_rate",
        "sess_auth_temp_reduced_timetable_rate",
        "sess_unauth_holiday_rate",
        "sess_unauth_late_rate",
        "sess_unauth_other_rate",
        "sess_unauth_noyet_rate",
    ])

    out = add_source_columns(df, source)
    return select_present(out, keep_cols)


def process_exclusions_characteristics(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    df = df[is_local_authority(df)].copy()

    if "characteristic_group" in df.columns:
        group_mask = contains_any(df["characteristic_group"], SEND_TERMS)
    else:
        group_mask = pd.Series([False] * len(df), index=df.index)

    if "characteristic" in df.columns:
        detail_mask = contains_any(df["characteristic"], SEND_TERMS)
    else:
        detail_mask = pd.Series([False] * len(df), index=df.index)

    df = df[group_mask | detail_mask].copy()

    keep_cols = with_source_columns([
        "source_key",
        "source_domain",
        "source_title",
        "source_url",
        "time_identifier",
        "time_period",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "new_la_code",
        "old_la_code",
        "la_name",
        "education_phase",
        "characteristic_group",
        "characteristic",
        "headcount",
        "perm_excl",
        "perm_excl_rate",
        "suspension",
        "susp_rate",
        "one_plus_susp",
        "one_plus_susp_rate",
    ])

    out = add_source_columns(df, source)
    return select_present(out, keep_cols)


def process_sen_profile(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    df = df[is_local_authority(df)].copy()

    keep_cols = with_source_columns([
        "source_key",
        "source_domain",
        "source_title",
        "source_url",
        "time_period",
        "time_identifier",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "old_la_code",
        "new_la_code",
        "la_name",
        "phase_type_grouping",
        "sen_status",
        "sen_primary_need",
        "number_of_pupils",
        "nc_early_years",
        "nc_reception",
        "nc_year_1",
        "nc_year_2",
        "nc_year_3",
        "nc_year_4",
        "nc_year_5",
        "nc_year_6",
        "nc_year_7",
        "nc_year_8",
        "nc_year_9",
        "nc_year_10",
        "nc_year_11",
        "nc_year_12",
        "nc_year_13",
        "nc_year_14",
        "nc_not_followed",
    ])

    out = add_source_columns(df, source)
    return select_present(out, keep_cols)

def process_one(raw_path: Path, source: Source) -> pd.DataFrame:
    df = read_raw(raw_path)

    if source.domain == "attendance_sen":
        return process_attendance_sen(df, source)

    if source.domain in {
        "attendance_current_daily",
        "attendance_current_weekly",
        "attendance_current_ytd",
        "persistent_absence_current",
    }:
        return process_attendance_current(df, source)

    if source.domain == "absence_characteristics":
        return process_absence_characteristics(df, source)

    if source.domain == "exclusions_characteristics":
        return process_exclusions_characteristics(df, source)

    if source.domain == "sen_profile":
        return process_sen_profile(df, source)

    raise ValueError(f"Unknown source domain: {source.domain}")


def save_processed(df: pd.DataFrame, source: Source) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{safe_filename(source.key)}_processed.csv.gz"
    df.to_csv(out_path, index=False, compression="gzip")
    print(f"Saved processed file: {out_path.relative_to(PROJECT_ROOT)} ({len(df):,} rows)")
    return out_path

def melt_measures(df: pd.DataFrame, id_cols: list[str], measure_cols: list[str]) -> pd.DataFrame:
    df = df.copy()

    # Defensive fix, duplicate column names break pandas melt because df[col]
    # becomes a DataFrame instead of a Series.
    if df.columns.duplicated().any():
        duplicated = df.columns[df.columns.duplicated()].tolist()
        print(f"WARNING: dropping duplicated columns before melt: {duplicated}")
        df = df.loc[:, ~df.columns.duplicated()].copy()

    id_present = []
    seen = set()

    for col in id_cols:
        if col in df.columns and col not in seen:
            id_present.append(col)
            seen.add(col)

    measures_present = []
    for col in measure_cols:
        if col in df.columns and col not in seen:
            measures_present.append(col)

    if not measures_present:
        return pd.DataFrame()

    tidy = df.melt(
        id_vars=id_present,
        value_vars=measures_present,
        var_name="measure_name",
        value_name="measure_value",
    )


    # Keep suppressed vals such as z in source-specific outputs, but long
    # measure table intended for analysis, so coerce non-numeric values to null
    tidy["measure_value"] = pd.to_numeric(tidy["measure_value"], errors="coerce")
    tidy = tidy.dropna(subset=["measure_value"])

    return tidy




def to_long_measures(df: pd.DataFrame, source: Source) -> pd.DataFrame:
    base_ids = [
        "source_key",
        "source_domain",
        "source_title",
        "source_url",
        "source_csv_url",
        "source_role",
        "cadence",
        "freshness_tier",
        "send_disaggregated",
        "current_context",
        "time_period",
        "time_identifier",
        "academic_year",
        "geographic_level",
        "country_code",
        "country_name",
        "region_code",
        "region_name",
        "new_la_code",
        "old_la_code",
        "la_name",
        "education_phase",
        "phase_type_grouping",
        "sen",
        "breakdown_topic",
        "breakdown",
        "characteristic_group",
        "characteristic",
        "sen_status",
        "sen_primary_need",
    ]

    if source.domain in {
        "attendance_sen",
        "attendance_current_daily",
        "attendance_current_weekly",
        "attendance_current_ytd",
        "persistent_absence_current",
    }:
        measure_cols = [
            "num_schools",
            "possible_sessions",
            "present_sessions",
            "approved_educational_activity",
            "overall_attendance",
            "overall_absence",
            "authorised_absence",
            "unauthorised_absence",
            "late_sessions",
            "reason_c2_authorised_temp_reduced_timetable",
            "reason_b_aea_education_off_site",
            "reason_k_aea_education_arranged_by_la",
            "attendance_perc",
            "overall_absence_perc",
            "authorised_absence_perc",
            "unauthorised_absence_perc",
            "illness_perc",
            "appointments_perc",
            "auth_excluded_perc",
            "auth_part_time_perc",
            "pa_perc",
        ]
    elif source.domain == "absence_characteristics":
        measure_cols = [
            "enrolments",
            "sess_possible",
            "sess_overall",
            "sess_authorised",
            "sess_unauthorised",
            "sess_overall_percent",
            "sess_authorised_percent",
            "sess_unauthorised_percent",
            "enrolments_pa_10_exact",
            "enrolments_pa_10_exact_percent",
            "enrolments_pa_50_exact",
            "enrolments_pa_50_exact_percent",
            "sess_auth_illness_rate",
            "sess_auth_appointments_rate",
            "sess_auth_excluded_rate",
            "sess_auth_temp_reduced_timetable_rate",
        ]
    elif source.domain == "exclusions_characteristics":
        measure_cols = [
            "headcount",
            "perm_excl",
            "perm_excl_rate",
            "suspension",
            "susp_rate",
            "one_plus_susp",
            "one_plus_susp_rate",
        ]
    elif source.domain == "sen_profile":
        measure_cols = [
            "number_of_pupils",
            "nc_early_years",
            "nc_reception",
            "nc_year_1",
            "nc_year_2",
            "nc_year_3",
            "nc_year_4",
            "nc_year_5",
            "nc_year_6",
            "nc_year_7",
            "nc_year_8",
            "nc_year_9",
            "nc_year_10",
            "nc_year_11",
            "nc_year_12",
            "nc_year_13",
            "nc_year_14",
            "nc_not_followed",
        ]
    else:
        measure_cols = []

    tidy = melt_measures(df, base_ids, measure_cols)

    # Create a common SEND characteristic column to make joins easier to inspect.
    if tidy.empty:
        return tidy

    tidy["send_group"] = ""
    if "sen" in tidy.columns:
        tidy["send_group"] = tidy["send_group"].mask(tidy["send_group"].eq(""), tidy["sen"].fillna(""))
    if "breakdown" in tidy.columns:
        tidy["send_group"] = tidy["send_group"].mask(tidy["send_group"].eq(""), tidy["breakdown"].fillna(""))
    if "characteristic" in tidy.columns:
        tidy["send_group"] = tidy["send_group"].mask(tidy["send_group"].eq(""), tidy["characteristic"].fillna(""))
    if "sen_status" in tidy.columns:
        tidy["send_group"] = tidy["send_group"].mask(tidy["send_group"].eq(""), tidy["sen_status"].fillna(""))

    return tidy


def write_manifest(processed_frames: list[tuple[Source, pd.DataFrame]]) -> Path:
    rows = []

    for source, df in processed_frames:
        rows.append(
            {
                "source_key": source.key,
                "source_domain": source.domain,
                "title": source.title,
                "publication": source.publication,
                "release": source.release,
                "cadence": source.cadence,
                "freshness_tier": source.freshness_tier,
                "source_role": source.source_role,
                "send_disaggregated": source.send_disaggregated,
                "current_context": source.current_context,
                "rows_processed": len(df),
                "columns_processed": len(df.columns),
                "grain_hint": source.grain_hint,
                "source_page_url": source.page_url,
                "csv_url": source.url,
            }
        )

    manifest = pd.DataFrame(rows)
    out_path = PROCESSED_DIR / "source_manifest.csv"
    manifest.to_csv(out_path, index=False)
    print(f"Saved manifest: {out_path.relative_to(PROJECT_ROOT)}")
    return out_path


def build(args: argparse.Namespace) -> None:
    sources = read_sources()
    if args.only:
        requested = set(args.only)
        sources = [source for source in sources if source.key in requested]
        missing = requested - {source.key for source in sources}
        if missing:
            raise ValueError(f"Unknown source key(s): {', '.join(sorted(missing))}")

    processed_frames: list[tuple[Source, pd.DataFrame]] = []
    long_frames: list[pd.DataFrame] = []

    for source in sources:
        raw_path = download_source(source, refresh=args.refresh)
        processed = process_one(raw_path, source)
        save_processed(processed, source)
        processed_frames.append((source, processed))

        if args.write_long:
            long_df = to_long_measures(processed, source)
            if not long_df.empty:
                long_frames.append(long_df)

    write_manifest(processed_frames)

    if args.write_long and long_frames:
        all_long = pd.concat(long_frames, ignore_index=True, sort=False)
        long_path = PROCESSED_DIR / "la_send_measure_long.csv.gz"
        all_long.to_csv(long_path, index=False, compression="gzip")
        print(f"Saved long measure table: {long_path.relative_to(PROJECT_ROOT)} ({len(all_long):,} rows)")

    print("Done")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build LA SEND attendance, absence, suspension and exclusion starter data from DfE EES CSVs."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Redownload raw CSV files instead of using cached files.",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        help="Optional source key or keys to run. See config/sources.json.",
    )
    parser.add_argument(
        "--write-long",
        action="store_true",
        help="Write the combined long measure table. This can be very large.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    build(parse_args(sys.argv[1:]))
