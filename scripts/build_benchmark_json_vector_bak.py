#!/usr/bin/env python3
"""
Initial attempt at build benchmark json from region-split LA SEND data

Inputs:
    docs/data/la_send_manifest.json
    docs/data/regions/*.json

Outputs:
    docs/data/benchmarks/benchmark_manifest.json
    docs/data/benchmarks/region_benchmark_summary.json
    docs/data/benchmarks/la_by_metric/*.json

Purpose:
    Create small browser-friendly benchmark files for:
      - LA vs LA comparison
      - Region vs region comparison
      - LA vs region / national context

eg
    python scripts/build_benchmark_json.py

Optional:
    python scripts/build_benchmark_json.py --pretty
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import re
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"
REGIONS_DIR = DOCS_DATA_DIR / "regions"
MANIFEST_PATH = DOCS_DATA_DIR / "la_send_manifest.json"
BENCHMARK_DIR = DOCS_DATA_DIR / "benchmarks"
LA_BY_METRIC_DIR = BENCHMARK_DIR / "la_by_metric"

STORY_DIR = BENCHMARK_DIR / "story"
PRIMARY_NEED_BY_METRIC_REGION_DIR = STORY_DIR / "primary_need_by_metric_region"
PROVISION_GAP_BY_METRIC_DIR = STORY_DIR / "provision_gap_by_metric"



@dataclass(frozen=True)
class MetricSpec:
    column: str
    label: str
    direction: str = "lower"  # lower, higher, neutral
    metric_type: str = "value"  # percent, count, rate, value
    numerator: str | None = None
    denominator: str | None = None
    denominator_label: str | None = None




BROWSER_COLUMNS = [
    "source_domain",
    "source_role",
    "time_period",
    "time_identifier",
    "academic_year",
    "education_phase",
    "phase_type_grouping",
    "send_category",
    "send_detail_display",
    "sen_type_label",
    "region_code",
    "region_name",
    "region_label",
    "new_la_code",
    "la_name",
    "metric",
    "metric_label",
    "metric_type",
    "direction",
    "value",
    "numerator_sum",
    "denominator_sum",
    "denominator_label",
    "row_count",
]


CORE_DIMENSIONS = [
    "source_key",
    "source_domain",
    "source_role",
    "cadence",
    "freshness_tier",
    "send_disaggregated",
    "current_context",
    "time_period",
    "time_identifier",
    "academic_year",
    "education_phase",
    "phase_type_grouping",
    "send_category",
    "send_detail_display",
    "sen_type_label",
]


LA_COLUMNS = [
    "region_code",
    "region_name",
    "region_label",
    "new_la_code",
    "la_name",
]


SOURCE_COLUMNS = [
    "source_title",
    "source_url",
    "source_csv_url",
]

PRIMARY_NEED_EXCLUDE = {
    "",
    "total",
    "missing",
    "unclassified",
    "no sen",
    "no identified sen",
    "ehc plan",
    "education, health and care plans",
    "sen support",
    "sen support / sen without an ehc plan",
}


PRIMARY_NEED_STORY_METRICS = {
    "sess_overall_percent",
    "sess_authorised_percent",
    "sess_unauthorised_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "sess_auth_illness_rate",
    "sess_auth_appointments_rate",
    "sess_auth_excluded_rate",
    "sess_auth_temp_reduced_timetable_rate",
}

METRICS: list[MetricSpec] = [
    # Attendance by SEN / current attendance context
    MetricSpec(
        column="attendance_perc",
        label="Attendance %",
        direction="higher",
        metric_type="percent",
        numerator="present_sessions",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="overall_absence_perc",
        label="Overall absence %",
        direction="lower",
        metric_type="percent",
        numerator="overall_absence",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="authorised_absence_perc",
        label="Authorised absence %",
        direction="lower",
        metric_type="percent",
        numerator="authorised_absence",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="unauthorised_absence_perc",
        label="Unauthorised absence %",
        direction="lower",
        metric_type="percent",
        numerator="unauthorised_absence",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="appointments_perc",
        label="Appointments %",
        direction="lower",
        metric_type="percent",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="illness_perc",
        label="Illness %",
        direction="lower",
        metric_type="percent",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="auth_excluded_perc",
        label="Authorised excluded %",
        direction="lower",
        metric_type="percent",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="auth_part_time_perc",
        label="Temporary reduced timetable %",
        direction="lower",
        metric_type="percent",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),

    # Attendance reason counts
    MetricSpec(
        column="reason_c2_authorised_temp_reduced_timetable",
        label="C2 temporary reduced timetable sessions",
        direction="lower",
        metric_type="count",
    ),
    MetricSpec(
        column="reason_b_aea_education_off_site",
        label="B off-site education sessions",
        direction="neutral",
        metric_type="count",
    ),
    MetricSpec(
        column="reason_k_aea_education_arranged_by_la",
        label="K LA arranged education sessions",
        direction="neutral",
        metric_type="count",
    ),

    # Absence by characteristic
    MetricSpec(
        column="sess_overall_percent",
        label="Absence %",
        direction="lower",
        metric_type="percent",
        numerator="sess_overall",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="sess_authorised_percent",
        label="Authorised absence %",
        direction="lower",
        metric_type="percent",
        numerator="sess_authorised",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="sess_unauthorised_percent",
        label="Unauthorised absence %",
        direction="lower",
        metric_type="percent",
        numerator="sess_unauthorised",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="enrolments_pa_10_exact_percent",
        label="Persistent absence 10%+",
        direction="lower",
        metric_type="percent",
        numerator="enrolments_pa_10_exact",
        denominator="enrolments",
        denominator_label="Enrolments",
    ),
    MetricSpec(
        column="enrolments_pa_50_exact_percent",
        label="Severe absence 50%+",
        direction="lower",
        metric_type="percent",
        numerator="enrolments_pa_50_exact",
        denominator="enrolments",
        denominator_label="Enrolments",
    ),
    MetricSpec(
        column="sess_auth_illness_rate",
        label="Illness rate",
        direction="lower",
        metric_type="rate",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="sess_auth_appointments_rate",
        label="Appointments rate",
        direction="lower",
        metric_type="rate",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="sess_auth_excluded_rate",
        label="Authorised excluded rate",
        direction="lower",
        metric_type="rate",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="sess_auth_temp_reduced_timetable_rate",
        label="Reduced timetable rate",
        direction="lower",
        metric_type="rate",
        denominator="sess_possible",
        denominator_label="Possible sessions",
    ),

    # Suspensions and exclusions
    MetricSpec(
        column="susp_rate",
        label="Suspension rate",
        direction="lower",
        metric_type="rate",
        denominator="headcount",
        denominator_label="Headcount",
    ),
    MetricSpec(
        column="one_plus_susp_rate",
        label="One or more suspension rate",
        direction="lower",
        metric_type="rate",
        denominator="headcount",
        denominator_label="Headcount",
    ),
    MetricSpec(
        column="perm_excl_rate",
        label="Permanent exclusion rate",
        direction="lower",
        metric_type="rate",
        denominator="headcount",
        denominator_label="Headcount",
    ),

    # SEN profile
    MetricSpec(
        column="number_of_pupils",
        label="Number of pupils",
        direction="neutral",
        metric_type="count",
    ),
    MetricSpec(
    column="reason_c2_authorised_temp_reduced_timetable_per_1000_sessions",
    label="C2 temporary reduced timetable sessions per 1,000 possible sessions",
    direction="lower",
    metric_type="rate_per_1000_sessions",
    numerator="reason_c2_authorised_temp_reduced_timetable",
    denominator="possible_sessions",
    denominator_label="Possible sessions",
    ),


    # per session aggr benchmarking values
    MetricSpec(
        column="reason_b_aea_education_off_site_per_1000_sessions",
        label="B off-site education sessions per 1,000 possible sessions",
        direction="neutral",
        metric_type="rate_per_1000_sessions",
        numerator="reason_b_aea_education_off_site",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
    MetricSpec(
        column="reason_k_aea_education_arranged_by_la_per_1000_sessions",
        label="K LA-arranged education sessions per 1,000 possible sessions",
        direction="neutral",
        metric_type="rate_per_1000_sessions",
        numerator="reason_k_aea_education_arranged_by_la",
        denominator="possible_sessions",
        denominator_label="Possible sessions",
    ),
]



def slim_for_browser(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in BROWSER_COLUMNS if c in df.columns]
    return df[cols].copy()


def add_sen_type_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise where specific SEN classification held

    absence_characteristics:
      send_detail_display = SEN primary need
      send_category = Autistic spectrum disorder, SEMH, MLD, etc

    sen_profile:
      send_category = SEN status/provision
      send_detail_display = Autistic Spectrum Disorder, SEMH, MLD, etc
    """
    out = df

    if "sen_type_label" not in out.columns:
        out["sen_type_label"] = None

    source_domain = out.get("source_domain", pd.Series("", index=out.index)).astype("string").str.lower()
    detail = out.get("send_detail_display", pd.Series("", index=out.index)).astype("string")
    category = out.get("send_category", pd.Series("", index=out.index)).astype("string")

    detail_l = detail.fillna("").str.strip().str.lower()
    category_l = category.fillna("").str.strip().str.lower()

    # Absence characteristics primary need rows hold need type in send_category
    absence_primary_need = detail_l.eq("sen primary need")
    out.loc[absence_primary_need, "sen_type_label"] = category[absence_primary_need]

    # SEN profile rows hold need type in send_detail_display
    sen_profile_need = source_domain.eq("sen_profile") & ~detail_l.isin(PRIMARY_NEED_EXCLUDE)
    out.loc[sen_profile_need, "sen_type_label"] = detail[sen_profile_need]

    # Remove low-value labels from specific need field
    sen_type_l = out["sen_type_label"].fillna("").astype(str).str.strip().str.lower()
    out.loc[sen_type_l.isin(PRIMARY_NEED_EXCLUDE), "sen_type_label"] = None

    return out


def safe_file_part(value: str) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def write_la_metric_files(
    la_metrics: pd.DataFrame,
    pretty: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Split LA benchmark rows into 1 JSON file per metric

    avoids loading single v.large LA benchmark file in browser
    """
    if LA_BY_METRIC_DIR.exists():
        shutil.rmtree(LA_BY_METRIC_DIR)

    LA_BY_METRIC_DIR.mkdir(parents=True, exist_ok=True)

    metric_files: dict[str, dict[str, Any]] = {}

    if la_metrics.empty:
        return metric_files

    for metric, part in la_metrics.groupby("metric", dropna=False, sort=True):
        metric = str(metric)
        filename = f"{safe_file_part(metric)}.json"
        out_path = LA_BY_METRIC_DIR / filename

        metric_label = None
        if "metric_label" in part.columns and part["metric_label"].notna().any():
            metric_label = str(part["metric_label"].dropna().iloc[0])

        payload = {
            "generated_at": now_utc(),
            "metric": metric,
            "metric_label": metric_label or metric,
            "record_count": int(len(part)),
            "source_roles": sorted(
                str(v) for v in part.get("source_role", pd.Series(dtype=object)).dropna().unique()
            ),
            "source_domains": sorted(
                str(v) for v in part.get("source_domain", pd.Series(dtype=object)).dropna().unique()
            ),
            "time_periods": sorted(
                str(v) for v in part.get("time_period", pd.Series(dtype=object)).dropna().unique()
            ),
            "records": records_to_jsonable(part),
        }

        write_json(out_path, payload, pretty=pretty)

        metric_files[metric] = {
            "metric": metric,
            "metric_label": metric_label or metric,
            "file": f"data/benchmarks/la_by_metric/{filename}",
            "record_count": int(len(part)),
        }

    return metric_files


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe_value(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

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
    return [
        {str(k): json_safe_value(v) for k, v in row.items()}
        for row in records
    ]


def write_json(path: Path, payload: dict[str, Any], pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
        else:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    print(f"Saved {path.relative_to(PROJECT_ROOT)}")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def load_region_records(manifest: dict[str, Any]) -> pd.DataFrame:
    frames = []

    for region in manifest.get("regions", []):
        file_ref = region.get("file")

        if not file_ref:
            continue

        path = DOCS_DATA_DIR / file_ref

        if not path.exists():
            print(f"WARNING: region file missing: {path}")
            continue

        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("records", [])

        if not rows:
            continue

        frames.append(pd.DataFrame(rows))

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)

    return df


def coerce_for_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    out = df

    for col in CORE_DIMENSIONS + LA_COLUMNS + SOURCE_COLUMNS:
        if col not in out.columns:
            out[col] = None

    # Keep as strings even if pandas sees num-looking vals
    for col in [
        "time_period",
        "academic_year",
        "new_la_code",
        "old_la_code",
        "region_code",
    ]:
        if col in out.columns:
            out[col] = out[col].where(out[col].isna(), out[col].astype(str))

    metric_related = set()
    for spec in METRICS:
        metric_related.add(spec.column)
        if spec.numerator:
            metric_related.add(spec.numerator)
        if spec.denominator:
            metric_related.add(spec.denominator)

    for col in metric_related:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Normalise bool-like columns for JSON and filters.
    for col in ["send_disaggregated", "current_context"]:
        if col in out.columns:
            out[col] = out[col].map(normalise_bool_like)

    out = add_derived_reason_rates(out)

    out = add_derived_reason_rates(out)
    out = add_sen_type_label(out)

    return out

def normalise_provision_label(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"ehc plan", "education, health and care plans"}:
        return "EHC plan"

    if text in {"sen support", "sen support / sen without an ehc plan"}:
        return "SEN support"

    if text in {"no sen", "no identified sen"}:
        return "No SEN"

    return str(value or "").strip()


def write_provision_gap_story_files(la_metrics: pd.DataFrame, pretty: bool = False) -> dict[str, dict[str, Any]]:
    out_dir = PROVISION_GAP_BY_METRIC_DIR

    if out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    df = la_metrics.copy()
    df["provision_label"] = df["send_category"].map(normalise_provision_label)

    df = df[df["provision_label"].isin(["No SEN", "SEN support", "EHC plan"])].copy()
    df["send_category"] = df["provision_label"]

    df = slim_for_browser(df)

    files = {}

    for metric, part in df.groupby("metric", dropna=False, sort=True):
        metric = str(metric)
        filename = f"{safe_file_part(metric)}.json"
        out_path = out_dir / filename

        payload = {
            "generated_at": now_utc(),
            "metric": metric,
            "metric_label": str(part["metric_label"].dropna().iloc[0]) if part["metric_label"].notna().any() else metric,
            "record_count": int(len(part)),
            "records": records_to_jsonable(part),
        }

        write_json(out_path, payload, pretty=pretty)

        files[metric] = {
            "metric": metric,
            "metric_label": payload["metric_label"],
            "file": f"data/benchmarks/story/provision_gap_by_metric/{filename}",
            "record_count": int(len(part)),
        }

    return files


def write_primary_need_story_files(la_metrics: pd.DataFrame, pretty: bool = False) -> dict[str, Any]:
    out_dir = PRIMARY_NEED_BY_METRIC_REGION_DIR

    if out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    df = df[df["metric"].isin(PRIMARY_NEED_STORY_METRICS)].copy()

    df = la_metrics.copy()
    df = df[df["sen_type_label"].notna()].copy()
    df = slim_for_browser(df)

    files: dict[str, Any] = {}

    if df.empty:
        return files

    for metric, metric_part in df.groupby("metric", dropna=False, sort=True):
        metric = str(metric)
        metric_dir = out_dir / safe_file_part(metric)
        metric_dir.mkdir(parents=True, exist_ok=True)

        metric_files = {}

        for region_code, part in metric_part.groupby("region_code", dropna=False, sort=True):
            region_code = str(region_code or "unknown")
            filename = f"{safe_file_part(region_code)}.json"
            out_path = metric_dir / filename

            metric_label = str(part["metric_label"].dropna().iloc[0]) if part["metric_label"].notna().any() else metric
            region_label = str(part["region_label"].dropna().iloc[0]) if part["region_label"].notna().any() else region_code

            payload = {
                "generated_at": now_utc(),
                "metric": metric,
                "metric_label": metric_label,
                "region_code": region_code,
                "region_label": region_label,
                "record_count": int(len(part)),
                "sen_type_labels": sorted(str(v) for v in part["sen_type_label"].dropna().unique()),
                "records": records_to_jsonable(part),
            }

            write_json(out_path, payload, pretty=pretty)

            metric_files[region_code] = {
                "region_code": region_code,
                "region_label": region_label,
                "file": f"data/benchmarks/story/primary_need_by_metric_region/{safe_file_part(metric)}/{filename}",
                "record_count": int(len(part)),
            }

        files[metric] = {
            "metric": metric,
            "metric_label": str(metric_part["metric_label"].dropna().iloc[0]) if metric_part["metric_label"].notna().any() else metric,
            "regions": metric_files,
            "record_count": int(len(metric_part)),
        }

    return files


def normalise_bool_like(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n"}:
        return False

    if text in {"", "nan", "none", "null"}:
        return None

    return value

def add_derived_reason_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived attendance reason rates per 1,000 possible sessions.

    These are better for benchmarking than raw session counts because they
    adjust for the size of the pupil/session denominator.
    """
    out = df

    if "possible_sessions" not in out.columns:
        return out

    possible = pd.to_numeric(out["possible_sessions"], errors="coerce")

    derived_specs = {
        "reason_c2_authorised_temp_reduced_timetable": (
            "reason_c2_authorised_temp_reduced_timetable_per_1000_sessions"
        ),
        "reason_b_aea_education_off_site": (
            "reason_b_aea_education_off_site_per_1000_sessions"
        ),
        "reason_k_aea_education_arranged_by_la": (
            "reason_k_aea_education_arranged_by_la_per_1000_sessions"
        ),
    }

    for source_col, derived_col in derived_specs.items():
        if source_col not in out.columns:
            continue

        numerator = pd.to_numeric(out[source_col], errors="coerce")

        out[derived_col] = (numerator / possible) * 1000
        out.loc[possible.isna() | possible.eq(0), derived_col] = pd.NA

    return out

def safe_group_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [col for col in cols if col in df.columns]


def compute_group_metric(group: pd.DataFrame, spec: MetricSpec) -> tuple[float | None, float | None, float | None]:
    """
    Return:
        value, numerator_sum, denominator_sum

    For % metrics where numerator and denominator available,
    recalc from summed numerators and denominators

    If numerator not available but denominator is use weighted mean

    Otherwise simple mean for rates/% or sum for count metrics
    """
    value_col = spec.column

    if value_col not in group.columns:
        return None, None, None

    values = pd.to_numeric(group[value_col], errors="coerce")
    valid = values.notna()

    if valid.sum() == 0:
        return None, None, None

    numerator_sum = None
    denominator_sum = None

    if spec.numerator and spec.denominator and spec.numerator in group.columns and spec.denominator in group.columns:
        numerator = pd.to_numeric(group[spec.numerator], errors="coerce")
        denominator = pd.to_numeric(group[spec.denominator], errors="coerce")

        mask = numerator.notna() & denominator.notna() & denominator.ne(0)

        if mask.any():
            numerator_sum = float(numerator[mask].sum())
            denominator_sum = float(denominator[mask].sum())

            if denominator_sum != 0:
                multiplier = 1000 if spec.metric_type == "rate_per_1000_sessions" else 100
                value = (numerator_sum / denominator_sum) * multiplier
                return round(value, 6), round(numerator_sum, 6), round(denominator_sum, 6)

    if spec.denominator and spec.denominator in group.columns:
        denominator = pd.to_numeric(group[spec.denominator], errors="coerce")
        mask = valid & denominator.notna() & denominator.gt(0)

        if mask.any():
            denominator_sum = float(denominator[mask].sum())

            if denominator_sum != 0:
                value = float((values[mask] * denominator[mask]).sum() / denominator_sum)
                return round(value, 6), None, round(denominator_sum, 6)

    if spec.metric_type == "count":
        value = float(values.sum())
    else:
        value = float(values.mean())

    return round(value, 6), numerator_sum, denominator_sum


def build_metric_rows(
    df: pd.DataFrame,
    group_cols: list[str],
    metric_specs: list[MetricSpec],
) -> pd.DataFrame:
    """
    Build metric rows using metric-by-metric vectorised groupby operations.

    The previous version grouped once and then looped through every group in
    Python, checking every metric for every group. That becomes very slow once
    absence/SEN-profile data is included. This version only groups rows that
    actually contain the metric currently being built.
    """
    group_cols = safe_group_cols(df, group_cols)

    if not group_cols:
        raise ValueError("No grouping cols available for benchmark build")

    frames: list[pd.DataFrame] = []

    for index, spec in enumerate(metric_specs, start=1):
        if spec.column not in df.columns:
            print(f"  [{index}/{len(metric_specs)}] skip {spec.column}: column not present")
            continue

        value_series = pd.to_numeric(df[spec.column], errors="coerce")

        if value_series.notna().sum() == 0:
            print(f"  [{index}/{len(metric_specs)}] skip {spec.column}: no non-null values")
            continue

        print(f"  [{index}/{len(metric_specs)}] build {spec.column}: {value_series.notna().sum():,} non-null rows")

        needed_cols = list(dict.fromkeys(
            group_cols
            + [spec.column]
            + ([spec.numerator] if spec.numerator else [])
            + ([spec.denominator] if spec.denominator else [])
        ))

        part = df[[col for col in needed_cols if col in df.columns]].copy()
        part["_value"] = value_series

        # Numerator + denominator metrics are recalculated from summed components.
        # This is used for percentages and the derived per-1,000 session rates.
        if spec.numerator and spec.denominator and spec.numerator in part.columns and spec.denominator in part.columns:
            part["_numerator"] = pd.to_numeric(part[spec.numerator], errors="coerce")
            part["_denominator"] = pd.to_numeric(part[spec.denominator], errors="coerce")

            part = part[
                part["_numerator"].notna()
                & part["_denominator"].notna()
                & part["_denominator"].ne(0)
            ]

            if part.empty:
                print(f"      no valid numerator/denominator rows for {spec.column}")
                continue

            grouped = (
                part.groupby(group_cols, dropna=False, sort=False)
                .agg(
                    numerator_sum=("_numerator", "sum"),
                    denominator_sum=("_denominator", "sum"),
                    row_count=("_value", "size"),
                )
                .reset_index()
            )

            multiplier = 1000 if spec.metric_type == "rate_per_1000_sessions" else 100
            grouped = grouped[grouped["denominator_sum"].ne(0)]
            grouped["value"] = (grouped["numerator_sum"] / grouped["denominator_sum"]) * multiplier

        # Denominator-only metrics use a weighted mean.
        elif spec.denominator and spec.denominator in part.columns:
            part["_denominator"] = pd.to_numeric(part[spec.denominator], errors="coerce")
            part = part[
                part["_value"].notna()
                & part["_denominator"].notna()
                & part["_denominator"].gt(0)
            ]

            if part.empty:
                print(f"      no valid weighted rows for {spec.column}")
                continue

            part["_weighted_value"] = part["_value"] * part["_denominator"]

            grouped = (
                part.groupby(group_cols, dropna=False, sort=False)
                .agg(
                    weighted_value_sum=("_weighted_value", "sum"),
                    denominator_sum=("_denominator", "sum"),
                    row_count=("_value", "size"),
                )
                .reset_index()
            )

            grouped = grouped[grouped["denominator_sum"].ne(0)]
            grouped["value"] = grouped["weighted_value_sum"] / grouped["denominator_sum"]
            grouped["numerator_sum"] = None
            grouped = grouped.drop(columns=["weighted_value_sum"])

        # Count metrics are summed.
        elif spec.metric_type == "count":
            part = part[part["_value"].notna()]

            if part.empty:
                print(f"      no count rows for {spec.column}")
                continue

            grouped = (
                part.groupby(group_cols, dropna=False, sort=False)
                .agg(
                    value=("_value", "sum"),
                    row_count=("_value", "size"),
                )
                .reset_index()
            )
            grouped["numerator_sum"] = None
            grouped["denominator_sum"] = None

        # Remaining metrics use a simple mean.
        else:
            part = part[part["_value"].notna()]

            if part.empty:
                print(f"      no mean rows for {spec.column}")
                continue

            grouped = (
                part.groupby(group_cols, dropna=False, sort=False)
                .agg(
                    value=("_value", "mean"),
                    row_count=("_value", "size"),
                )
                .reset_index()
            )
            grouped["numerator_sum"] = None
            grouped["denominator_sum"] = None

        grouped["metric"] = spec.column
        grouped["metric_label"] = spec.label
        grouped["metric_type"] = spec.metric_type
        grouped["direction"] = spec.direction
        grouped["denominator_label"] = spec.denominator_label

        for col in ["value", "numerator_sum", "denominator_sum"]:
            if col in grouped.columns:
                grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(6)

        frames.append(grouped)

        print(f"      built {len(grouped):,} benchmark rows for {spec.column}")

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True, sort=False)


def add_benchmark_context(la_metrics: pd.DataFrame) -> pd.DataFrame:
    if la_metrics.empty:
        return la_metrics

    out = la_metrics.copy()

    context_cols = [
        col for col in CORE_DIMENSIONS + ["metric"]
        if col in out.columns
    ]

    region_context_cols = [
        col for col in context_cols + ["region_code", "region_name", "region_label"]
        if col in out.columns
    ]

    # National comparison within same source/period/phase/SEND/metric
    national = (
        out.groupby(context_cols, dropna=False)["value"]
        .mean()
        .reset_index()
        .rename(columns={"value": "national_mean"})
    )

    out = out.merge(national, on=context_cols, how="left")

    # Region comparison within same source/period/phase/SEND/metric
    if region_context_cols:
        region = (
            out.groupby(region_context_cols, dropna=False)["value"]
            .mean()
            .reset_index()
            .rename(columns={"value": "region_mean"})
        )

        out = out.merge(region, on=region_context_cols, how="left")

    out["diff_from_national"] = out["value"] - out["national_mean"]

    if "region_mean" in out.columns:
        out["diff_from_region"] = out["value"] - out["region_mean"]
    else:
        out["diff_from_region"] = None

    # Ranks, high and low so charts can decide how to present
    out["national_rank_high"] = (
        out.groupby(context_cols, dropna=False)["value"]
        .rank(method="min", ascending=False)
    )

    out["national_rank_low"] = (
        out.groupby(context_cols, dropna=False)["value"]
        .rank(method="min", ascending=True)
    )

    if region_context_cols:
        out["region_rank_high"] = (
            out.groupby(region_context_cols, dropna=False)["value"]
            .rank(method="min", ascending=False)
        )

        out["region_rank_low"] = (
            out.groupby(region_context_cols, dropna=False)["value"]
            .rank(method="min", ascending=True)
        )

    out["benchmark_rank"] = out["national_rank_low"]

    higher_mask = out["direction"].eq("higher")
    neutral_mask = out["direction"].eq("neutral")

    out.loc[higher_mask, "benchmark_rank"] = out.loc[higher_mask, "national_rank_high"]
    out.loc[neutral_mask, "benchmark_rank"] = None

    for col in [
        "national_mean",
        "region_mean",
        "diff_from_national",
        "diff_from_region",
        "national_rank_high",
        "national_rank_low",
        "region_rank_high",
        "region_rank_low",
        "benchmark_rank",
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(6)

    return out


def build_region_metrics(la_metrics: pd.DataFrame) -> pd.DataFrame:
    if la_metrics.empty:
        return la_metrics

    # Region summary should aggregate LA benchmark vals across LAs
    # use simple mean of LA values to avoid (accidental)double weighting
    # across incompatible source types
    group_cols = [
        col for col in CORE_DIMENSIONS + [
            "region_code",
            "region_name",
            "region_label",
            "metric",
            "metric_label",
            "metric_type",
            "direction",
            "denominator_label",
        ]
        if col in la_metrics.columns
    ]

    region = (
        la_metrics.groupby(group_cols, dropna=False)
        .agg(
            value=("value", "mean"),
            la_count=("new_la_code", "nunique"),
            row_count=("row_count", "sum"),
            denominator_sum=("denominator_sum", "sum"),
            numerator_sum=("numerator_sum", "sum"),
        )
        .reset_index()
    )

    context_cols = [
        col for col in CORE_DIMENSIONS + ["metric"]
        if col in region.columns
    ]

    national = (
        region.groupby(context_cols, dropna=False)["value"]
        .mean()
        .reset_index()
        .rename(columns={"value": "national_mean"})
    )

    region = region.merge(national, on=context_cols, how="left")
    region["diff_from_national"] = region["value"] - region["national_mean"]

    region["rank_high"] = (
        region.groupby(context_cols, dropna=False)["value"]
        .rank(method="min", ascending=False)
    )

    region["rank_low"] = (
        region.groupby(context_cols, dropna=False)["value"]
        .rank(method="min", ascending=True)
    )

    region["benchmark_rank"] = region["rank_low"]

    higher_mask = region["direction"].eq("higher")
    neutral_mask = region["direction"].eq("neutral")

    region.loc[higher_mask, "benchmark_rank"] = region.loc[higher_mask, "rank_high"]
    region.loc[neutral_mask, "benchmark_rank"] = None

    for col in [
        "value",
        "national_mean",
        "diff_from_national",
        "rank_high",
        "rank_low",
        "benchmark_rank",
        "denominator_sum",
        "numerator_sum",
    ]:
        if col in region.columns:
            region[col] = pd.to_numeric(region[col], errors="coerce").round(6)

    return region


def reduce_for_json(df: pd.DataFrame) -> pd.DataFrame:
    out = df

    # Keep -time periods- as strings so browser does not display 202,526 from dfe yr
    for col in ["time_period", "academic_year", "new_la_code", "region_code"]:
        if col in out.columns:
            out[col] = out[col].where(out[col].isna(), out[col].astype(str))

    return out


def build_benchmarks(
    pretty: bool = False,
    write_full_la_metric_files: bool = False,
) -> None:
    print("Loading region manifest...")
    manifest = load_manifest()

    print("Loading region records...")
    records = load_region_records(manifest)

    if records.empty:
        raise SystemExit("No region records found. Run build_region_json_from_processed.py first")

    print(f"Loaded region records: {len(records):,}")

    print("Coercing data for benchmarking...")
    df = coerce_for_benchmark(records)

    if "source_domain" in df.columns:
        print("Rows by source_domain after coercion:")
        print(df["source_domain"].value_counts(dropna=False).to_string())

    print("Building LA metric rows...")
    la_group_cols = CORE_DIMENSIONS + LA_COLUMNS + SOURCE_COLUMNS
    la_metrics = build_metric_rows(df, la_group_cols, METRICS)
    print(f"LA metric rows before context: {len(la_metrics):,}")

    print("Adding national and regional benchmark context...")
    la_metrics = add_benchmark_context(la_metrics)
    la_metrics = reduce_for_json(la_metrics)

    print("Building region benchmark rows...")
    region_metrics = build_region_metrics(la_metrics)
    region_metrics = reduce_for_json(region_metrics)

    print(f"LA benchmark rows: {len(la_metrics):,}")
    print(f"Region benchmark rows: {len(region_metrics):,}")

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    print("Writing LA benchmark metric slices...")
    la_metric_files = {}

    if write_full_la_metric_files:
        print("Writing full LA benchmark metric slices...")
        la_metric_files = write_la_metric_files(la_metrics, pretty=pretty)
    else:
        print("Skipping full LA benchmark metric slices. Use --write-full-la-metric-files to write them")

    print("Writing provision gap story files...")
    provision_gap_files = write_provision_gap_story_files(la_metrics, pretty=pretty)

    print("Writing primary need story files...")
    primary_need_files = write_primary_need_story_files(la_metrics, pretty=pretty)

    region_payload = {
        "generated_at": now_utc(),
        "title": "Region benchmark summary",
        "description": (
            "Region-level benchmark rows generated from LA benchmark values"
        ),
        "record_count": int(len(region_metrics)),
        "records": records_to_jsonable(region_metrics),
    }

    benchmark_manifest = {
        "generated_at": now_utc(),
        "title": "Benchmark manifest",
        "source_manifest": "data/la_send_manifest.json",
        "outputs": {
            "region_benchmark_summary": "data/benchmarks/region_benchmark_summary.json",
            "la_by_metric": "data/benchmarks/la_by_metric/",
        },
        "la_metric_files": la_metric_files,
        "metric_count": len(METRICS),
        "metrics": [
            {
                "column": spec.column,
                "label": spec.label,
                "direction": spec.direction,
                "metric_type": spec.metric_type,
                "numerator": spec.numerator,
                "denominator": spec.denominator,
                "denominator_label": spec.denominator_label,
            }
            for spec in METRICS
        ],
        "la_record_count": int(len(la_metrics)),
        "region_record_count": int(len(region_metrics)),
        "source_domains": manifest.get("source_domains", []),
        "source_roles": manifest.get("source_roles", []),
        "cadences": manifest.get("cadences", []),
        "freshness_tiers": manifest.get("freshness_tiers", []),
    }

    write_json(BENCHMARK_DIR / "region_benchmark_summary.json", region_payload, pretty=pretty)
    write_json(BENCHMARK_DIR / "benchmark_manifest.json", benchmark_manifest, pretty=pretty)

    print(f"Input rows: {len(df):,}")
    print(f"LA benchmark rows: {len(la_metrics):,}")
    print(f"Region benchmark rows: {len(region_metrics):,}")
    print(f"LA metric files: {len(la_metric_files):,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build LA and region benchmark JSON from region-split LA SEND data"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write indented JSON. Default writes minified JSON",
    )
    parser.add_argument(
        "--write-full-la-metric-files",
        action="store_true",
        help="Write full docs/data/benchmarks/la_by_metric/*.json files. These are large debug outputs and not needed for the browser story pages",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_benchmarks(
        pretty=args.pretty,
        write_full_la_metric_files=args.write_full_la_metric_files,
    )

if __name__ == "__main__":
    main()