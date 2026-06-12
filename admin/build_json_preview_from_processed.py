from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.json"
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"


PROFILE_COLUMNS = [
    "source_key",
    "source_domain",
    "source_title",
    "time_period",
    "time_identifier",
    "academic_year",
    "geographic_level",
    "region_code",
    "region_name",
    "new_la_code",
    "old_la_code",
    "la_name",
    "education_phase",
    "phase_type_grouping",
    "sen",
    "send_group",
    "send_detail",
    "breakdown_topic",
    "breakdown",
    "characteristic_group",
    "characteristic",
    "sen_status",
    "sen_primary_need",
    "measure_name",
]

RECORD_COLUMNS = [
    "source_key",
    "source_domain",
    "source_title",
    "source_url",
    "time_period",
    "time_identifier",
    "academic_year",
    "geographic_level",
    "region_code",
    "region_name",
    "region_label",
    "new_la_code",
    "old_la_code",
    "la_name",
    "education_phase",
    "phase_type_grouping",
    "sen",
    "send_group",
    "send_detail",
    "breakdown_topic",
    "breakdown",
    "characteristic_group",
    "characteristic",
    "sen_status",
    "sen_primary_need",
    "measure_name",
    "measure_value",
]

WIDE_INDEX_COLUMNS = [
    "region_name",
    "region_label",
    "new_la_code",
    "la_name",
    "time_period",
    "time_identifier",
    "academic_year",
    "source_domain",
    "source_title",
    "source_url",
    "education_phase",
    "phase_type_grouping",
    "sen",
    "send_group",
    "send_detail",
    "sen_status",
    "sen_primary_need",
]

WIDE_PRIORITY_MEASURES = [
    # Attendance by SEN
    "attendance_perc",
    "overall_attendance",
    "overall_absence_perc",
    "authorised_absence_perc",
    "unauthorised_absence_perc",
    "illness_perc",
    "auth_excluded_perc",
    "pa_perc",
    "possible_sessions",
    "present_sessions",

    # Absence by characteristics
    "sess_overall_percent",
    "sess_authorised_percent",
    "sess_unauthorised_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "sess_possible",
    "enrolments",

    # Suspensions and exclusions
    "suspension",
    "susp_rate",
    "one_plus_susp",
    "one_plus_susp_rate",
    "perm_excl",
    "perm_excl_rate",

    # SEN profile / denominator
    "number_of_pupils",
]

DISPLAY_WIDE_COLUMNS = [
    # Utility/filter/debug fields, keep in json even if not shown in tbl
    "region_name",
    "region_label",
    "new_la_code",
    "la_name",
    "time_period",
    "time_identifier",
    "academic_year",
    "source_key",
    "source_domain",
    "source_title",
    "source_url",
    "education_phase",
    "phase_type_grouping",
    "send_category",
    "send_detail_display",

    # Attendance by SEN
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

    # Absence by characteristics
    "sess_overall_percent",
    "sess_authorised_percent",
    "sess_unauthorised_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "sess_possible",
    "enrolments",

    # Suspensions and exclusions
    "suspension",
    "susp_rate",
    "one_plus_susp",
    "one_plus_susp_rate",
    "perm_excl",
    "perm_excl_rate",

    # SEN profile / denominator
    "number_of_pupils",
]


def expand_input_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []

    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            paths.extend(Path(m) for m in matches)
        else:
            paths.append(Path(pattern))

    found = []
    for path in paths:
        if path.exists() and path.is_file():
            found.append(path)
        else:
            print(f"WARNING: file not found skipped: {path}")

    return sorted(set(found))


def normalise_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def records_to_jsonable(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.where(pd.notna(df), None)
    records = clean.to_dict(orient="records")

    return [
        {str(k): normalise_value(v) for k, v in row.items()}
        for row in records
    ]


def present_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def detect_key_column(df: pd.DataFrame) -> str | None:
    for col in ["source_key", "source_domain", "source_title"]:
        if col in df.columns:
            return col

    return None


def period_sort_value(df: pd.DataFrame) -> pd.Series:
    """
    Create simple sortable val from DfE time fields

    deliberately pragmatic rather than perfect. works well enough
    to id latest rows for lightweight preview
    """
    if "time_period" in df.columns:
        period_text = df["time_period"].fillna("").astype(str)
    elif "academic_year" in df.columns:
        period_text = df["academic_year"].fillna("").astype(str)
    else:
        period_text = pd.Series([""] * len(df), index=df.index)

    digits = period_text.str.replace(r"\D+", "", regex=True)
    numeric_part = pd.to_numeric(digits.str.slice(0, 6), errors="coerce").fillna(0)

    if "time_identifier" in df.columns:
        identifier = df["time_identifier"].fillna("").astype(str).str.lower()
    else:
        identifier = pd.Series([""] * len(df), index=df.index)

    term_rank = pd.Series([0] * len(df), index=df.index, dtype="int64")
    term_rank = term_rank.mask(identifier.str.contains("autumn", regex=False), 1)
    term_rank = term_rank.mask(identifier.str.contains("spring", regex=False), 2)
    term_rank = term_rank.mask(identifier.str.contains("summer", regex=False), 3)
    term_rank = term_rank.mask(identifier.str.contains("academic year", regex=False), 4)
    term_rank = term_rank.mask(identifier.str.contains("full year", regex=False), 4)

    week_match = identifier.str.extract(r"week\D*(\d+)", expand=False)
    week_rank = pd.to_numeric(week_match, errors="coerce").fillna(0)

    return (numeric_part * 1000) + (term_rank * 100) + week_rank


def update_counter(counter: Counter, series: pd.Series, top_per_chunk: int = 250) -> None:
    values = series.fillna("").astype(str).str.strip()
    values = values[values.ne("")]

    if values.empty:
        return

    counter.update(values.value_counts().head(top_per_chunk).to_dict())


def profile_file(path: Path, chunksize: int) -> tuple[dict[str, Any], dict[str, float], dict[str, dict[str, str]]]:
    print(f"Profiling: {path}")

    row_count = 0
    columns: list[str] = []
    counters: dict[str, Counter] = defaultdict(Counter)
    latest_period_by_key: dict[str, float] = {}
    la_region_lookup: dict[str, dict[str, str]] = {}

    measure_value_min: float | None = None
    measure_value_max: float | None = None

    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False, compression="infer"):
        if not columns:
            columns = list(chunk.columns)

        row_count += len(chunk)

        for col in present_columns(chunk, PROFILE_COLUMNS):
            update_counter(counters[col], chunk[col])

        # Build reusable LA to region lookup from any source that has it
        needed = {"new_la_code", "la_name", "region_code", "region_name"}
        if needed.issubset(set(chunk.columns)):
            geo_chunk = chunk[
                ["new_la_code", "la_name", "region_code", "region_name"]
            ].drop_duplicates()

            for row in geo_chunk.to_dict(orient="records"):
                la_code = str(row.get("new_la_code") or "").strip()
                la_name = str(row.get("la_name") or "").strip()
                region_code = str(row.get("region_code") or "").strip()
                region_name = str(row.get("region_name") or "").strip()

                if not la_code:
                    continue

                if not region_name or region_name.lower() in {"total", "nan", "none"}:
                    continue

                la_region_lookup.setdefault(
                    la_code,
                    {
                        "new_la_code": la_code,
                        "la_name": la_name,
                        "region_code": region_code,
                        "region_name": region_name,
                    },
                )

        if "measure_value" in chunk.columns:
            numeric = pd.to_numeric(chunk["measure_value"], errors="coerce")
            if numeric.notna().any():
                chunk_min = float(numeric.min())
                chunk_max = float(numeric.max())
                measure_value_min = chunk_min if measure_value_min is None else min(measure_value_min, chunk_min)
                measure_value_max = chunk_max if measure_value_max is None else max(measure_value_max, chunk_max)

        period_sort = period_sort_value(chunk)
        key_col = detect_key_column(chunk)

        if key_col:
            keys = chunk[key_col].fillna(path.stem).astype(str)
        else:
            keys = pd.Series([path.stem] * len(chunk), index=chunk.index)

        tmp = pd.DataFrame({"key": keys, "period_sort": period_sort})
        for key, max_sort in tmp.groupby("key")["period_sort"].max().items():
            current = latest_period_by_key.get(key)
            if current is None or max_sort > current:
                latest_period_by_key[key] = float(max_sort)

    profile = {
        "path": str(path),
        "file_name": path.name,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "row_count": int(row_count),
        "columns": columns,
        "measure_value_min": measure_value_min,
        "measure_value_max": measure_value_max,
        "top_values": {
            col: [
                {"value": value, "count": int(count)}
                for value, count in counter.most_common(50)
            ]
            for col, counter in counters.items()
        },
    }

    return profile, latest_period_by_key, la_region_lookup


def collect_latest_sample(
    path: Path,
    latest_period_by_key: dict[str, float],
    chunksize: int,
    max_records: int,
    local_authority_only: bool,
) -> list[dict[str, Any]]:
    print(f"Collecting latest sample: {path}")

    records: list[dict[str, Any]] = []
    remaining = max_records

    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False, compression="infer"):
        if remaining <= 0:
            break

        key_col = detect_key_column(chunk)

        if key_col:
            keys = chunk[key_col].fillna(path.stem).astype(str)
        else:
            keys = pd.Series([path.stem] * len(chunk), index=chunk.index)

        period_sort = period_sort_value(chunk)
        target_sort = keys.map(latest_period_by_key).fillna(-1)

        mask = period_sort.eq(target_sort)

        if local_authority_only and "geographic_level" in chunk.columns:
            geo = chunk["geographic_level"].fillna("").astype(str).str.lower()
            mask = mask & geo.str.contains("local authority", regex=False)

        sample = chunk.loc[mask].copy()

        if sample.empty:
            continue

        keep_cols = present_columns(sample, RECORD_COLUMNS)

        if not keep_cols:
            keep_cols = list(sample.columns[:25])

        sample = sample[keep_cols].head(remaining)
        records.extend(records_to_jsonable(sample))
        remaining = max_records - len(records)

    return records

def load_source_registry(path: Path = CONFIG_PATH) -> dict[str, dict[str, Any]]:
    """
    Load source metadata from config/sources.json

    Supports either:
      {"sources": [{...}, {...}]}

    or:
      [{...}, {...}]

    Expected source fields flexible but ideally:
      key, title, url, domain
    """
    if not path.exists():
        print(f"WARNING: source registry not found: {path}")
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        sources = data.get("sources", data)
    else:
        sources = data

    registry: dict[str, dict[str, Any]] = {}

    if isinstance(sources, dict):
        iterable = []
        for key, value in sources.items():
            if isinstance(value, dict):
                item = {"key": key, **value}
            else:
                item = {"key": key, "value": value}
            iterable.append(item)
    else:
        iterable = sources

    for item in iterable:
        if not isinstance(item, dict):
            continue

        key = (
            item.get("key")
            or item.get("source_key")
            or item.get("id")
            or item.get("name")
        )

        if not key:
            continue

        registry[str(key)] = {
            "source_key": str(key),
            "source_domain": item.get("domain") or item.get("source_domain"),
            "source_title": item.get("title") or item.get("source_title") or str(key),
            "source_url": item.get("url") or item.get("source_url"),
            "notes": item.get("notes") or item.get("description"),
        }

    return registry


def enrich_records_with_source_registry(
    records: list[dict[str, Any]],
    source_registry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Add source URL/title/domain to sample records where/if avail
    """
    for row in records:
        key = str(row.get("source_key") or "")
        meta = source_registry.get(key)

        if not meta:
            continue

        row.setdefault("source_title", meta.get("source_title"))
        row.setdefault("source_domain", meta.get("source_domain"))
        row.setdefault("source_url", meta.get("source_url"))

    return records


def sort_preview_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort browser-facing records by LA code then time period

    Keep sort stable and add fields to make page easier to scan
    """
    if not records:
        return records

    df = pd.DataFrame(records)

    for col in [
        "new_la_code",
        "time_period",
        "time_identifier",
        "source_domain",
        "source_key",
        "la_name",
        "measure_name",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["_period_sort"] = period_sort_value(df)

    df = df.sort_values(
        by=[
            "region_name",
            "new_la_code",
            "_period_sort",
            "time_period",
            "time_identifier",
            "source_domain",
            "source_key",
            "measure_name",
        ],
        kind="mergesort",
        na_position="last",
    )

    df = df.drop(columns=["_period_sort"], errors="ignore")
    df = df.where(pd.notna(df), None)

    return records_to_jsonable(df)

def merge_la_region_lookups(
    lookups: list[dict[str, dict[str, str]]],
) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}

    for lookup in lookups:
        for la_code, meta in lookup.items():
            if la_code not in merged:
                merged[la_code] = meta

    return merged


def enrich_records_with_region_lookup(
    records: list[dict[str, Any]],
    la_region_lookup: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """
    Ensure every LA sample record has region_code, region_name and region_label
    where can infer from another source row
    """
    for row in records:
        la_code = str(row.get("new_la_code") or "").strip()
        meta = la_region_lookup.get(la_code, {})

        if not row.get("region_code") and meta.get("region_code"):
            row["region_code"] = meta["region_code"]

        if not row.get("region_name") and meta.get("region_name"):
            row["region_name"] = meta["region_name"]

        region_name = str(row.get("region_name") or "").strip()
        region_code = str(row.get("region_code") or "").strip()

        if region_name and region_code:
            row["region_label"] = f"{region_name} ({region_code})"
        elif region_name:
            row["region_label"] = region_name
        elif region_code:
            row["region_label"] = region_code
        else:
            row["region_label"] = ""

    return records

def first_non_empty_column(df: pd.DataFrame, columns: list[str], output_col: str) -> pd.DataFrame:
    """
    Create one display col using first non-empty value from possible fields
    """
    result = pd.Series([""] * len(df), index=df.index, dtype="object")

    for col in columns:
        if col not in df.columns:
            continue

        values = df[col].fillna("").astype(str).str.strip()
        result = result.mask(result.eq("") & values.ne(""), values)

    df[output_col] = result

    return df

def round_numeric_values(df: pd.DataFrame, decimals: int = 3) -> pd.DataFrame:
    """
    Round numeric cols to reduce JSON file size(prev loads taking too long!) and improve display
    """
    out = df.copy()

    for col in out.columns:
        numeric = pd.to_numeric(out[col], errors="coerce")

        if numeric.notna().sum() == 0:
            continue

        # Only replace if most non-empty values numeric
        non_empty = out[col].notna().sum()
        if non_empty and numeric.notna().sum() / non_empty >= 0.9:
            out[col] = numeric.round(decimals)

    return out


def build_wide_records_from_long_records(
    records: list[dict[str, Any]],
    max_rows: int = 10_000,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Convert long display records into wide browser-eased tbl

    Input:
        LA + SEND group + measure_name + measure_value

    Output:
        LA + SEND group + attendance_perc + overall_absence_perc + susp_rate + etc

    Returns:
        wide_records, wide_measure_cols
    """
    if not records:
        return [], []

    df = pd.DataFrame(records)

    if "measure_name" not in df.columns or "measure_value" not in df.columns:
        return records[:max_rows], []

    df = first_non_empty_column(
        df,
        ["sen", "send_group", "sen_status", "breakdown", "characteristic"],
        "send_category",
    )

    df = first_non_empty_column(
        df,
        ["sen_primary_need", "send_detail", "breakdown_topic", "characteristic_group"],
        "send_detail_display",
    )

    index_cols = [
        col for col in WIDE_INDEX_COLUMNS
        if col in df.columns and col not in {"send_group", "send_detail"}
    ]

    for extra_col in ["send_category", "send_detail_display"]:
        if extra_col in df.columns and extra_col not in index_cols:
            index_cols.append(extra_col)

    df = df[df["measure_name"].notna()].copy()
    df["measure_name"] = df["measure_name"].astype(str).str.strip()
    df = df[df["measure_name"].ne("")]

    if df.empty:
        return [], []

    # fill null grouping fields before grouping/pivoting
    # otherwise rows with None in index cols (might be) dropped
    for col in index_cols:
        df[col] = df[col].fillna("").astype(str)

    df["measure_value"] = df["measure_value"].where(pd.notna(df["measure_value"]), None)

    grouped = (
        df.groupby(index_cols + ["measure_name"], dropna=False)["measure_value"]
        .first()
        .reset_index()
    )

    wide = grouped.pivot(
        index=index_cols,
        columns="measure_name",
        values="measure_value",
    ).reset_index()

    wide.columns = [str(col) for col in wide.columns]

    measure_cols = [col for col in wide.columns if col not in index_cols]

    priority_measure_cols = [
        col for col in WIDE_PRIORITY_MEASURES
        if col in measure_cols
    ]

    other_measure_cols = sorted(
        col for col in measure_cols
        if col not in priority_measure_cols
    )

    wide_measure_columns = priority_measure_cols + other_measure_cols

    wide = wide[index_cols + wide_measure_columns]

    if "new_la_code" not in wide.columns:
        wide["new_la_code"] = ""

    if "time_period" not in wide.columns:
        wide["time_period"] = ""

    wide["_period_sort"] = period_sort_value(wide)

    sort_cols = [
        col for col in [
            "region_name",
            "new_la_code",
            "_period_sort",
            "time_period",
            "time_identifier",
            "source_domain",
            "education_phase",
            "send_category",
            "send_detail_display",
        ]
        if col in wide.columns
    ]

    wide = wide.sort_values(
        by=sort_cols,
        kind="mergesort",
        na_position="last",
    )

    wide = wide.drop(columns=["_period_sort"], errors="ignore")

    if len(wide) > max_rows:
        wide = wide.head(max_rows)

    display_cols = [col for col in DISPLAY_WIDE_COLUMNS if col in wide.columns]
    extra_measure_cols = [
        col for col in wide_measure_columns
        if col in wide.columns and col not in display_cols
    ]

    # Keep display cols first, and keep any unexpected useful measure cols
    wide = wide[display_cols + extra_measure_cols]


    wide = wide.where(pd.notna(wide), None)
    wide = round_numeric_values(wide, decimals=3)

    return records_to_jsonable(wide), wide_measure_columns


def build_preview_json(
    input_paths: list[Path],
    output_path: Path,
    chunksize: int,
    max_records_per_file: int,
    local_authority_only: bool,
    pretty: bool,
    include_long_records: bool = False,
) -> None:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    profiles = []
    all_records = []
    la_region_lookups = []
    source_registry = load_source_registry()

    for path in input_paths:
        profile, latest_period_by_key, la_region_lookup = profile_file(path, chunksize=chunksize)
        profiles.append(profile)
        la_region_lookups.append(la_region_lookup)
        
        sample_records = collect_latest_sample(
            path=path,
            latest_period_by_key=latest_period_by_key,
            chunksize=chunksize,
            max_records=max_records_per_file,
            local_authority_only=local_authority_only,
        )

        for row in sample_records:
            row["_source_file"] = path.name

        all_records.extend(sample_records)

    combined_la_region_lookup = merge_la_region_lookups(la_region_lookups)


    all_records = enrich_records_with_source_registry(all_records, source_registry)
    all_records = enrich_records_with_region_lookup(all_records, combined_la_region_lookup)
    all_records = sort_preview_records(all_records)

    wide_records, wide_measure_columns = build_wide_records_from_long_records(
        all_records,
        max_rows=10_000,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "title": "LA SEND processed data preview",
        "description": (
            "Chunked preview generated from (local copy)processed CSV or CSV.GZ files "
            "lightweight browser-facing extract, not full dataset"
        ),
        "input_file_count": len(input_paths),
        "sample_record_count": len(all_records),
        "wide_record_count": len(wide_records),
        "wide_measure_columns": wide_measure_columns,
        "source_registry": source_registry,
        "la_region_lookup": combined_la_region_lookup,
        "profiles": profiles,
        "long_record_count": len(all_records),
        "records": all_records if include_long_records else [],
        "wide_records": wide_records,
    }
    with output_path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved: {output_path}")
    print(f"JSON size MB: {output_path.stat().st_size / 1024 / 1024:,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build MkDocs/GitHub Pages JSON preview from processed CSV files"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="1+ CSV/CSV.GZ files or glob patterns, e.g data/processed/*.csv.gz",
    )
    parser.add_argument(
        "--output",
        default=str(DOCS_DATA_DIR / "la_send_latest_summary.json"),
        help="Output JSON path",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Rows per chunk while reading large CSV files",
    )
    parser.add_argument(
        "--max-records-per-file",
        type=int,
        default=5_000,
        help="Maximum latest sample records to include per input file",
    )
    parser.add_argument(
        "--all-geographies",
        action="store_true",
        help="Incl all geographic levels. Default keeps local authority rows only where possible",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write indented JSON. Default writes smaller minified JSON",
    )
    parser.add_argument(
        "--include-long-records",
        action="store_true",
        help="Incl long records array in output JSON. Useful for debug but large",
    )


    args = parser.parse_args()

    input_paths = expand_input_paths(args.inputs)

    if not input_paths:
        raise SystemExit("No input files found.")

    build_preview_json(
        input_paths=input_paths,
        output_path=Path(args.output),
        chunksize=args.chunksize,
        max_records_per_file=args.max_records_per_file,
        local_authority_only=not args.all_geographies,
        pretty=args.pretty,
        include_long_records=args.include_long_records,
    )


if __name__ == "__main__":
    main()