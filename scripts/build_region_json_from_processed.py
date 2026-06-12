# python scripts/build_region_json_from_processed.py "data/processed/*processed.csv"
# python scripts/build_region_json_from_processed.py "data/processed/*processed.csv" "data/processed/*processed.csv.gz"
# Dont include: data/processed/la_send_measure_long.csv.gz

# important. 
# Dont run without explicit file type arg, might double count otherwise! 
# either against .csv, or .csv.gz 
# python scripts/build_region_json_from_processed.py "data/processed/*processed.csv.gz"
# python scripts/build_benchmark_json.py

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import math

from collections import defaultdict
from pathlib import Path
import glob

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.json"
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"
REGIONS_DIR = DOCS_DATA_DIR / "regions"
TMP_DIR = DOCS_DATA_DIR / "_regions_tmp"


DISPLAY_COLUMNS = [
    # Filter and display fields
    "region_code",
    "region_name",
    "region_label",
    "new_la_code",
    "la_name",
    "time_period",
    "time_identifier",
    "academic_year",

    # Source metadata
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

    # Education / SEND grouping
    "education_phase",
    "phase_type_grouping",
    "send_category",
    "send_detail_display",

    # Attendance by SEN / current attendance reason counts
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
    "num_schools",
    "reason_c2_authorised_temp_reduced_timetable",
    "reason_b_aea_education_off_site",
    "reason_k_aea_education_arranged_by_la",

    # Absence by characteristics
    "absence_terms",
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

    # Suspensions and exclusions
    "headcount",
    "suspension",
    "susp_rate",
    "one_plus_susp",
    "one_plus_susp_rate",
    "perm_excl",
    "perm_excl_rate",

    # SEN profile
    "number_of_pupils",
]

def logical_processed_key(path: Path) -> str:
    """
    Return a stable logical key for a processed source file.

    Examples:
      absence_characteristics_2024_25_processed.csv
      absence_characteristics_2024_25_processed.csv.gz

    both become:
      absence_characteristics_2024_25_processed
    """
    name = path.name

    if name.endswith(".csv.gz"):
        return name[:-7]  # remove .csv.gz

    if name.endswith(".csv"):
        return name[:-4]  # remove .csv

    return path.stem


def resolve_processed_inputs(patterns: list[str]) -> list[Path]:
    """
    Expand input globs and de-duplicate .csv / .csv.gz variants.

    Preference:
      1. .csv.gz
      2. .csv

    This prevents accidental double-counting when using a broad glob such as:
      data/processed/*processed.csv*
    """
    candidates: list[Path] = []

    for pattern in patterns:
        matches = [Path(p) for p in glob.glob(pattern)]

        if not matches:
            print(f"WARNING: no files matched input pattern: {pattern}")

        candidates.extend(matches)

    candidates = sorted({p for p in candidates if p.exists()})

    grouped: dict[str, list[Path]] = defaultdict(list)

    for path in candidates:
        grouped[logical_processed_key(path)].append(path)

    selected: list[Path] = []

    for key, paths in sorted(grouped.items()):
        gz_paths = [p for p in paths if p.name.endswith(".csv.gz")]
        csv_paths = [p for p in paths if p.name.endswith(".csv")]

        if gz_paths:
            chosen = sorted(gz_paths)[0]
        elif csv_paths:
            chosen = sorted(csv_paths)[0]
        else:
            chosen = sorted(paths)[0]

        skipped = [p for p in paths if p != chosen]

        if skipped:
            print(f"WARNING: duplicate processed source variants for {key}")
            print(f"  using:   {chosen}")
            for p in skipped:
                print(f"  skipped: {p}")

        selected.append(chosen)

    print(f"Resolved processed input files: {len(selected)} selected from {len(candidates)} candidates")

    return selected


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
            # Avoid feeding generated preview files back into the split build.
            if path.name == "la_send_measure_long.csv" or path.name == "la_send_measure_long.csv.gz":
                print(f"Skipping combined long file: {path}")
                continue
            found.append(path)
        else:
            print(f"WARNING: file not found, skipped: {path}")

    return sorted(set(found))


def load_source_registry(path: Path = CONFIG_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        print(f"WARNING: source registry not found: {path}")
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        sources = data.get("sources", data)
    else:
        sources = data

    registry: dict[str, dict[str, Any]] = {}

    if isinstance(sources, dict):
        iterable = []
        for key, value in sources.items():
            if isinstance(value, dict):
                iterable.append({"key": key, **value})
    else:
        iterable = sources

    for item in iterable:
        if not isinstance(item, dict):
            continue

        key = item.get("key") or item.get("source_key") or item.get("id") or item.get("name")

        if not key:
            continue

        registry[str(key)] = {
            "source_key": str(key),
            "source_domain": item.get("domain") or item.get("source_domain"),
            "source_title": item.get("title") or item.get("source_title") or str(key),
            "source_url": item.get("page_url") or item.get("source_url") or item.get("url"),
            "source_csv_url": item.get("url") or item.get("source_csv_url"),
            "source_role": item.get("source_role") or item.get("domain") or item.get("source_domain"),
            "cadence": item.get("cadence"),
            "freshness_tier": item.get("freshness_tier"),
            "send_disaggregated": item.get("send_disaggregated"),
            "current_context": item.get("current_context"),
            "notes": item.get("notes") or item.get("description"),
        }

    return registry


def safe_region_file_name(region_code: str, region_name: str) -> str:
    value = region_code or region_name or "unknown_region"
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_")
    return f"{value or 'unknown_region'}.json"


def first_non_empty(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    out = pd.Series([""] * len(df), index=df.index, dtype="object")

    for col in columns:
        if col not in df.columns:
            continue

        values = df[col].fillna("").astype(str).str.strip()
        out = out.mask(out.eq("") & values.ne(""), values)

    return out


def json_safe_value(value: Any) -> Any:
    """
    Convert pandas/numpy missing values and non-finite numbers to JSON-safe nulls
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    return value


def records_to_jsonable(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.to_dict(orient="records")

    out = []

    for row in records:
        clean_row = {
            str(key): json_safe_value(value)
            for key, value in row.items()
        }
        out.append(clean_row)

    return out


def round_numeric_columns(df: pd.DataFrame, decimals: int = 3) -> pd.DataFrame:
    out = df.copy()

    protected = {
        "time_period",
        "academic_year",
        "new_la_code",
        "old_la_code",
    }

    for col in out.columns:
        if col in protected:
            continue

        numeric = pd.to_numeric(out[col], errors="coerce")
        non_empty = out[col].notna().sum()

        if non_empty and numeric.notna().sum() / non_empty >= 0.9:
            out[col] = numeric.round(decimals)

    return out


def _is_blank_series(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().eq("")


def enrich_source_metadata(df: pd.DataFrame, registry: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """
    Fill source metadata from config/sources.json where processed files dont
    already contain those fields
    """
    out = df.copy()

    if "source_key" not in out.columns:
        return out

    metadata_cols = [
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

    for col in metadata_cols:
        if col not in out.columns:
            out[col] = None

    for key, meta in registry.items():
        mask = out["source_key"].astype(str).eq(str(key))

        if not mask.any():
            continue

        for col in metadata_cols:
            value = meta.get(col)

            if value is None:
                continue

            blank = _is_blank_series(out[col])
            out.loc[mask & blank, col] = value

    # fallbacks useful for older processed files
    if "source_role" in out.columns and "source_domain" in out.columns:
        blank = _is_blank_series(out["source_role"])
        out.loc[blank, "source_role"] = out.loc[blank, "source_domain"]

    if "send_disaggregated" in out.columns and "source_domain" in out.columns:
        blank = _is_blank_series(out["send_disaggregated"])
        out.loc[blank, "send_disaggregated"] = out.loc[blank, "source_domain"].isin(
            [
                "attendance_sen",
                "absence_characteristics",
                "exclusions_characteristics",
                "sen_profile",
            ]
        )

    if "current_context" in out.columns and "source_domain" in out.columns:
        blank = _is_blank_series(out["current_context"])
        out.loc[blank, "current_context"] = out.loc[blank, "source_domain"].isin(
            [
                "attendance_current_daily",
                "attendance_current_weekly",
                "attendance_current_ytd",
                "persistent_absence_current",
            ]
        )

    return out


def normalise_chunk(df: pd.DataFrame, registry: dict[str, dict[str, Any]]) -> pd.DataFrame:
    out = df.copy()

    if "geographic_level" in out.columns:
        geo = out["geographic_level"].fillna("").astype(str).str.lower()
        out = out[geo.str.contains("local authority", regex=False)].copy()

    if out.empty:
        return out

    if "region_name" not in out.columns:
        out["region_name"] = ""
    if "region_code" not in out.columns:
        out["region_code"] = ""

    region_name = out["region_name"].fillna("").astype(str).str.strip()
    region_code = out["region_code"].fillna("").astype(str).str.strip()

    out["region_label"] = [
        f"{name} ({code})" if name and code else name or code
        for name, code in zip(region_name, region_code)
    ]

    out["send_category"] = first_non_empty(
        out,
        [
            "sen",
            "breakdown",
            "characteristic",
            "sen_status",
            "sen_primary_need",
        ],
    )

    out["send_detail_display"] = first_non_empty(
        out,
        [
            "breakdown_topic",
            "characteristic_group",
            "sen_primary_need",
            "send_detail",
        ],
    )

    out = enrich_source_metadata(out, registry)

    for col in ["send_disaggregated", "current_context"]:
        if col in out.columns:
            out[col] = out[col].map(normalise_bool_like)

    keep = [col for col in DISPLAY_COLUMNS if col in out.columns]
    out = out[keep].copy()

    out = round_numeric_columns(out, decimals=3)

    return out


def append_region_records(
    df: pd.DataFrame,
    tmp_files: dict[str, Path],
    region_meta: dict[str, dict[str, Any]],
    source_domains: set[str],
    source_keys: set[str],
    source_roles: set[str],
    cadences: set[str],
    freshness_tiers: set[str],
) -> None:
    if df.empty:
        return

    if "region_code" in df.columns:
        region_codes = df["region_code"].fillna("").astype(str)
    else:
        region_codes = pd.Series([""] * len(df), index=df.index)

    if "region_name" in df.columns:
        region_names = df["region_name"].fillna("").astype(str)
    else:
        region_names = pd.Series([""] * len(df), index=df.index)

# region_code should exist, but keep fallback for older data
    if "region_label" in df.columns:
        region_labels = df["region_label"].fillna("").astype(str)
    else:
        region_labels = region_names

    grouping = pd.DataFrame(
        {
            "_region_code": region_codes,
            "_region_name": region_names,
            "_region_label": region_labels,
        },
        index=df.index,
    )

    for (region_code, region_name, region_label), idx in grouping.groupby(
        ["_region_code", "_region_name", "_region_label"],
        dropna=False,
    ).groups.items():
        code = str(region_code or "").strip()
        name = str(region_name or "").strip()
        label = str(region_label or "").strip()

        if not code and not name:
            code = "unknown_region"
            name = "Unknown region"
            label = "Unknown region"

        file_name = safe_region_file_name(code, name)
        tmp_path = tmp_files.setdefault(file_name, TMP_DIR / f"{file_name}.ndjson")

        region_meta.setdefault(
            file_name,
            {
                "region_code": code,
                "region_name": name,
                "region_label": label,
                "file": f"regions/{file_name}",
                "record_count": 0,
            },
        )

        part = df.loc[list(idx)].copy()
        records = records_to_jsonable(part)

        with tmp_path.open("a", encoding="utf-8") as f:
            for row in records:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

        region_meta[file_name]["record_count"] += len(records)

        if "source_domain" in part.columns:
            source_domains.update(
                str(v) for v in part["source_domain"].dropna().unique() if str(v).strip()
            )

        if "source_key" in part.columns:
            source_keys.update(
                str(v) for v in part["source_key"].dropna().unique() if str(v).strip()
            )
        if "source_role" in part.columns:
            source_roles.update(
                str(v) for v in part["source_role"].dropna().unique() if str(v).strip()
            )

        if "cadence" in part.columns:
            cadences.update(
                str(v) for v in part["cadence"].dropna().unique() if str(v).strip()
            )

        if "freshness_tier" in part.columns:
            freshness_tiers.update(
                str(v) for v in part["freshness_tier"].dropna().unique() if str(v).strip()
            )

def finalise_region_files(
    tmp_files: dict[str, Path],
    region_meta: dict[str, dict[str, Any]],
    pretty: bool,
) -> None:
    REGIONS_DIR.mkdir(parents=True, exist_ok=True)

    for file_name, tmp_path in sorted(tmp_files.items()):
        records = []

        with tmp_path.open("r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))

        records.sort(
            key=lambda r: (
                str(r.get("new_la_code") or ""),
                str(r.get("time_period") or ""),
                str(r.get("source_domain") or ""),
                str(r.get("education_phase") or ""),
                str(r.get("send_category") or ""),
            )
        )

        payload = {
            **region_meta[file_name],
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "records": records,
        }

        out_path = REGIONS_DIR / file_name

        with out_path.open("w", encoding="utf-8") as f:
            if pretty:
                json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
            else:
                json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

        print(f"Saved {out_path.relative_to(PROJECT_ROOT)} ({len(records):,} records)")


def normalise_bool_like(value: Any) -> Any:
    if value is None:
        return None

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    if text in {"", "nan", "none", "null"}:
        return None

    return value

def build_region_json(
    input_paths: list[Path],
    chunksize: int,
    pretty: bool,
) -> None:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if REGIONS_DIR.exists():
        shutil.rmtree(REGIONS_DIR)
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)

    REGIONS_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    registry = load_source_registry()

    tmp_files: dict[str, Path] = {}
    region_meta: dict[str, dict[str, Any]] = {}

    source_domains: set[str] = set()
    source_keys: set[str] = set()
    source_roles: set[str] = set()
    cadences: set[str] = set()
    freshness_tiers: set[str] = set()
    input_files = []
    total_rows = 0
    total_kept = 0

    for path in input_paths:
        print(f"Processing {path}")
        input_files.append(str(path))

        for chunk in pd.read_csv(path, chunksize=chunksize, compression="infer", low_memory=False):
            total_rows += len(chunk)
            norm = normalise_chunk(chunk, registry)
            total_kept += len(norm)

            append_region_records(
                norm,
                tmp_files=tmp_files,
                region_meta=region_meta,
                source_domains=source_domains,
                source_keys=source_keys,
                source_roles=source_roles,
                cadences=cadences,
                freshness_tiers=freshness_tiers,
            )

    finalise_region_files(tmp_files, region_meta, pretty=pretty)

    manifest = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "title": "LA SEND regional data manifest",
        "description": (
            "Manifest for region-split LA SEND attendance, absence, suspensions and exclusions preview data."
        ),
        "input_files": input_files,
        "input_row_count": total_rows,
        "kept_local_authority_row_count": total_kept,
        "region_count": len(region_meta),
        "regions": sorted(
            region_meta.values(),
            key=lambda r: (r.get("region_name") or "", r.get("region_code") or ""),
        ),
        "source_domains": sorted(source_domains),
        "source_keys": sorted(source_keys),
        "source_roles": sorted(source_roles),
        "cadences": sorted(cadences),
        "freshness_tiers": sorted(freshness_tiers),
        "source_registry": registry,
    }

    manifest_path = DOCS_DATA_DIR / "la_send_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)
        else:
            json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    shutil.rmtree(TMP_DIR)

    print(f"Saved {manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"Input rows: {total_rows:,}")
    print(f"Kept local authority rows: {total_kept:,}")
    print(f"Regions: {len(region_meta):,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build region-split JSON files from source-specific processed CSV files"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Processed CSV/CSV.GZ input glob(s) eg data/processed/*processed.csv*",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Rows per chunk while reading CSV files",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write indented JSON. Default writes minified JSON",
    )

    args = parser.parse_args()

    # input_paths = expand_input_paths(args.inputs)
    input_paths = resolve_processed_inputs(args.inputs)

    if not input_paths:
        raise SystemExit("No input files found.")

    build_region_json(
        input_paths=input_paths,
        chunksize=args.chunksize,
        pretty=args.pretty,
    )


if __name__ == "__main__":
    main()