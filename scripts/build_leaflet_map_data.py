#!/usr/bin/env python3
"""
Build compact Leaflet map data for LA SEND benchmarking.

Purpose
-------
Creates browser-friendly map files for an additional MkDocs/Leaflet page.

This script does NOT publish the large source region JSONs or full benchmark rows.
It produces:
  - one slim LA boundary GeoJSON
  - one compact value file per metric and region
  - one compact "all regions" value file per metric
  - one map manifest for the Leaflet page

Expected command
----------------
python scripts/build_leaflet_map_data.py \
  --geo data/geo/lad_may_2025_uk_bgc_v2.geojson

Optional
--------
python scripts/build_leaflet_map_data.py --pretty
python scripts/build_leaflet_map_data.py --include-all-boundaries
python scripts/build_leaflet_map_data.py --metrics sess_overall_percent enrolments_pa_10_exact_percent

Input assumptions
-----------------
1. The benchmark story build has already run.
2. docs/data/benchmarks/benchmark_manifest.json exists.
3. benchmark_manifest.json contains provision_gap_files, preferably region-split.
4. The ONS LAD GeoJSON has already been downloaded locally.

Recommended boundary source
---------------------------
ONS Open Geography / data.gov.uk:
Local Authority Districts (May 2025) Boundaries UK BGC (V2)
BGC = Generalised 20m, clipped to coastline, better for browser maps than full resolution BFC.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"
BENCHMARK_MANIFEST_PATH = DOCS_DATA_DIR / "benchmarks" / "benchmark_manifest.json"

MAPS_DIR = DOCS_DATA_DIR / "maps"
MAP_VALUES_DIR = MAPS_DIR / "la_gap_by_metric_region"
MAP_BOUNDARIES_PATH = MAPS_DIR / "la_boundaries_slim.geojson"
MAP_MANIFEST_PATH = MAPS_DIR / "la_send_map_manifest.json"

DEFAULT_GEO_PATH = PROJECT_ROOT / "data" / "geo" / "lad_may_2025_uk_bgc_v2.geojson"

DEFAULT_MAP_METRICS = [
    "attendance_perc",
    "overall_absence_perc",
    "sess_overall_percent",
    "enrolments_pa_10_exact_percent",
    "enrolments_pa_50_exact_percent",
    "susp_rate",
    "one_plus_susp_rate",
    "perm_excl_rate",
]

PROVISION_SEND_GROUPS = [
    "EHC plan",
    "SEN support",
]

# For future dev. present in output manifest
# so Leaflet page can grow without changing high-level contract
EXTENSION_PLACEHOLDERS = {
    "primary_need": {
        "status": "placeholder",
        "description": (
            "Future map mode for SEN primary need values. Expected source: "
            "benchmark_manifest.primary_need_files, joined by new_la_code and region_code."
        ),
    },
    "region_summary": {
        "status": "placeholder",
        "description": (
            "Future map mode for region-level choropleth or region overview cards. "
            "Expected source: a separate compact region boundary/value output."
        ),
    },
    "time_series": {
        "status": "placeholder",
        "description": (
            "Future map mode for LA change over time. Expected source: compact per-LA "
            "metric rows grouped by time_period and education_phase."
        ),
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel_to_docs(path: Path) -> str:
    return path.relative_to(DOCS_DATA_DIR.parent).as_posix()


def json_safe_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    return value


def write_json(path: Path, payload: dict[str, Any], pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
        else:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    print(f"Saved {path.relative_to(PROJECT_ROOT)}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def read_records_from_docs_file(file_ref: str) -> list[dict[str, Any]]:
    """
    file_ref expected like:
      data/benchmarks/story/provision_gap_by_metric_region/sess_overall_percent/E12000004.json
    """
    path = DOCS_DATA_DIR.parent / file_ref

    if not path.exists():
        raise FileNotFoundError(f"Ref data file not found: {path}")

    payload = load_json(path)
    records = payload.get("records", [])

    if not isinstance(records, list):
        return []

    return records


def normalise_send_category(value: Any) -> str:
    text = str(value or "").strip().lower()

    if not text:
        return ""

    if (
        text == "ehc plan"
        or "statement or ehc" in text
        or "statement/ehc" in text
        or "statement of sen" in text
        or "education health and care" in text
        or "education, health and care" in text
    ):
        return "EHC plan"

    if text == "sen support" or "sen support" in text:
        return "SEN support"

    if (
        text == "no sen"
        or "no identified sen" in text
        or "without sen" in text
    ):
        return "No SEN"

    return str(value or "").strip()


def metric_meta_from_manifest(manifest: dict[str, Any], metric: str) -> dict[str, Any]:
    for item in manifest.get("metrics", []):
        if item.get("column") == metric:
            return item

    return {
        "column": metric,
        "label": metric,
        "direction": "neutral",
        "metric_type": "value",
    }


def available_provision_metric_entry(manifest: dict[str, Any], metric: str) -> dict[str, Any] | None:
    """
    Prefer slim story output, but keep fallback to older la_metric_files
    while still figuring pipeline
    """
    return (
        manifest.get("provision_gap_files", {}).get(metric)
        or manifest.get("la_metric_files", {}).get(metric)
    )


def iter_metric_region_sources(metric_entry: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """
    Return list of (region_key, region_info).

    Supports both:
      1. region-split entry: {"regions": {"E12000004": {"file": ...}}}
      2. older single-file entry: {"file": ...}
    """
    if not metric_entry:
        return []

    regions = metric_entry.get("regions")

    if isinstance(regions, dict) and regions:
        return [(str(region_code), info) for region_code, info in regions.items()]

    file_ref = metric_entry.get("file")

    if file_ref:
        return [("all_regions", {"file": file_ref, "region_code": "all_regions", "region_label": "All regions"})]

    return []


def pair_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """
    matching selected SEND provision rows to No SEN baseline

    close to benchmarking page logic, but exclude
    source_key where slim story files no longer have it. If source_key is
    available its included
    """
    return (
        row.get("source_key") or "",
        row.get("time_period") or "",
        row.get("time_identifier") or "",
        row.get("academic_year") or "",
        row.get("education_phase") or "",
        row.get("phase_type_grouping") or "",
        row.get("metric") or "",
        row.get("new_la_code") or row.get("la_name") or "",
    )


def aggregate_map_rows(records: list[dict[str, Any]], metric: str, send_group: str) -> list[dict[str, Any]]:
    """
    From provision rows, make compressed 1-row-per-LA-period-phase rows

    may be multiple source slices per LA for selected period/phase. We
    first pair SEND group and No SEN at detailed(slice) level, then avg
    repeate slices for same LA/period/phase to keep map payload small
    """
    pairs: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in records:
        if row.get("metric") and row.get("metric") != metric:
            continue

        category = normalise_send_category(row.get("send_category"))

        if category not in {"No SEN", send_group}:
            continue

        key = pair_key(row)

        if key not in pairs:
            pairs[key] = {
                "new_la_code": row.get("new_la_code"),
                "la_name": row.get("la_name"),
                "region_code": row.get("region_code"),
                "region_name": row.get("region_name"),
                "region_label": row.get("region_label"),
                "metric": metric,
                "metric_label": row.get("metric_label") or metric,
                "metric_type": row.get("metric_type"),
                "direction": row.get("direction"),
                "time_period": row.get("time_period"),
                "time_identifier": row.get("time_identifier"),
                "academic_year": row.get("academic_year"),
                "education_phase": row.get("education_phase"),
                "phase_type_grouping": row.get("phase_type_grouping"),
                "send_group": send_group,
                "send_value": None,
                "no_sen_value": None,
            }

        value = row.get("value")

        try:
            value_num = float(value)
        except (TypeError, ValueError):
            continue

        if category == send_group:
            pairs[key]["send_value"] = value_num

        if category == "No SEN":
            pairs[key]["no_sen_value"] = value_num

    detailed = []

    for item in pairs.values():
        send_value = item.get("send_value")
        no_sen_value = item.get("no_sen_value")

        if send_value is None or no_sen_value is None:
            continue

        item["gap_to_no_sen"] = send_value - no_sen_value
        detailed.append(item)

    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in detailed:
        key = (
            row.get("new_la_code") or row.get("la_name") or "",
            row.get("region_code") or row.get("region_name") or "",
            row.get("metric") or "",
            row.get("send_group") or "",
            row.get("time_period") or "",
            row.get("time_identifier") or "",
            row.get("academic_year") or "",
            row.get("education_phase") or "",
            row.get("phase_type_grouping") or "",
        )

        if key not in grouped:
            grouped[key] = {
                "new_la_code": row.get("new_la_code"),
                "la_name": row.get("la_name"),
                "region_code": row.get("region_code"),
                "region_name": row.get("region_name"),
                "region_label": row.get("region_label"),
                "metric": row.get("metric"),
                "metric_label": row.get("metric_label"),
                "metric_type": row.get("metric_type"),
                "direction": row.get("direction"),
                "time_period": row.get("time_period"),
                "time_identifier": row.get("time_identifier"),
                "academic_year": row.get("academic_year"),
                "education_phase": row.get("education_phase"),
                "phase_type_grouping": row.get("phase_type_grouping"),
                "send_group": row.get("send_group"),
                "_send_sum": 0.0,
                "_no_sen_sum": 0.0,
                "_gap_sum": 0.0,
                "source_slice_count": 0,
            }

        grouped_row = grouped[key]
        grouped_row["_send_sum"] += float(row["send_value"])
        grouped_row["_no_sen_sum"] += float(row["no_sen_value"])
        grouped_row["_gap_sum"] += float(row["gap_to_no_sen"])
        grouped_row["source_slice_count"] += 1

    out = []

    for row in grouped.values():
        count = row["source_slice_count"]

        if count <= 0:
            continue

        clean = {
            "new_la_code": row.get("new_la_code"),
            "la_name": row.get("la_name"),
            "region_code": row.get("region_code"),
            "region_name": row.get("region_name"),
            "region_label": row.get("region_label"),
            "metric": row.get("metric"),
            "metric_label": row.get("metric_label"),
            "metric_type": row.get("metric_type"),
            "direction": row.get("direction"),
            "time_period": row.get("time_period"),
            "time_identifier": row.get("time_identifier"),
            "academic_year": row.get("academic_year"),
            "education_phase": row.get("education_phase"),
            "phase_type_grouping": row.get("phase_type_grouping"),
            "send_group": row.get("send_group"),
            "send_value": round(row["_send_sum"] / count, 6),
            "no_sen_value": round(row["_no_sen_sum"] / count, 6),
            "gap_to_no_sen": round(row["_gap_sum"] / count, 6),
            "source_slice_count": count,
        }

        out.append({k: json_safe_value(v) for k, v in clean.items()})

    out.sort(key=lambda r: (
        str(r.get("region_name") or ""),
        str(r.get("la_name") or ""),
        str(r.get("send_group") or ""),
        str(r.get("time_period") or ""),
        str(r.get("education_phase") or ""),
    ))

    return out


def output_metric_region_file(metric: str, region_code: str, records: list[dict[str, Any]], pretty: bool) -> dict[str, Any]:
    metric_dir = MAP_VALUES_DIR / safe_file_part(metric)
    metric_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_file_part(region_code)}.json"
    out_path = metric_dir / filename

    region_label = region_code

    for row in records:
        if row.get("region_label") or row.get("region_name"):
            region_label = row.get("region_label") or row.get("region_name")
            break

    payload = {
        "generated_at": now_utc(),
        "metric": metric,
        "metric_label": records[0].get("metric_label") if records else metric,
        "region_code": region_code,
        "region_label": region_label,
        "record_count": len(records),
        "send_groups": sorted({str(r.get("send_group")) for r in records if r.get("send_group")}),
        "time_periods": sorted({str(r.get("time_period")) for r in records if r.get("time_period")}),
        "education_phases": sorted({str(r.get("education_phase")) for r in records if r.get("education_phase")}),
        "records": records,
    }

    write_json(out_path, payload, pretty=pretty)

    return {
        "region_code": region_code,
        "region_label": region_label,
        "file": rel_to_docs(out_path),
        "record_count": len(records),
    }


def safe_file_part(value: str) -> str:
    text = str(value or "unknown").strip().lower()
    chars = []

    for ch in text:
        if ch.isalnum() or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")

    cleaned = "".join(chars)

    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")

    cleaned = cleaned.strip("_")
    return cleaned or "unknown"


def build_metric_map_files(
    manifest: dict[str, Any],
    metric: str,
    pretty: bool,
) -> tuple[dict[str, Any], set[str], dict[str, dict[str, Any]]]:
    metric_entry = available_provision_metric_entry(manifest, metric)

    if not metric_entry:
        print(f"WARNING: metric not found in provision gap files: {metric}")
        return {}, set(), {}

    metric_meta = metric_meta_from_manifest(manifest, metric)
    region_sources = iter_metric_region_sources(metric_entry)

    metric_manifest: dict[str, Any] = {
        "metric": metric,
        "metric_label": metric_entry.get("metric_label") or metric_meta.get("label") or metric,
        "metric_type": metric_meta.get("metric_type"),
        "direction": metric_meta.get("direction"),
        "type": "provision_gap",
        "regions": {},
        "all_regions": None,
        "record_count": 0,
    }

    all_rows: list[dict[str, Any]] = []
    la_codes: set[str] = set()
    la_lookup: dict[str, dict[str, Any]] = {}

    for region_code, region_info in region_sources:
        file_ref = region_info.get("file")

        if not file_ref:
            continue

        source_records = read_records_from_docs_file(file_ref)

        map_rows: list[dict[str, Any]] = []

        for send_group in PROVISION_SEND_GROUPS:
            map_rows.extend(aggregate_map_rows(source_records, metric=metric, send_group=send_group))

        if not map_rows:
            print(f"WARNING: no map rows for {metric} {region_code}")
            continue

        # If reading from old all-region source, split into actual regions for the map manifest.
        split_by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in map_rows:
            actual_region = row.get("region_code") or row.get("region_name") or region_code
            split_by_region[str(actual_region)].append(row)

        for actual_region_code, part in split_by_region.items():
            region_file_info = output_metric_region_file(
                metric=metric,
                region_code=actual_region_code,
                records=part,
                pretty=pretty,
            )

            metric_manifest["regions"][actual_region_code] = region_file_info
            metric_manifest["record_count"] += int(region_file_info["record_count"])

        all_rows.extend(map_rows)

        for row in map_rows:
            code = row.get("new_la_code")

            if code:
                code = str(code)
                la_codes.add(code)

                if code not in la_lookup:
                    la_lookup[code] = {
                        "new_la_code": code,
                        "la_name": row.get("la_name"),
                        "region_code": row.get("region_code"),
                        "region_name": row.get("region_name"),
                        "region_label": row.get("region_label"),
                    }

    if all_rows:
        all_regions_info = output_metric_region_file(
            metric=metric,
            region_code="all_regions",
            records=all_rows,
            pretty=pretty,
        )
        all_regions_info["region_label"] = "All regions"
        metric_manifest["all_regions"] = all_regions_info

    return metric_manifest, la_codes, la_lookup


def detect_property(properties: dict[str, Any], candidates: list[str]) -> str | None:
    lowered = {str(k).lower(): k for k in properties.keys()}

    for candidate in candidates:
        if candidate in properties:
            return candidate

        key = lowered.get(candidate.lower())

        if key:
            return key

    return None


def get_lad_properties(feature: dict[str, Any]) -> tuple[str | None, str | None]:
    props = feature.get("properties", {}) or {}

    code_key = detect_property(props, [
        "new_la_code",
        "lad25cd",
        "LAD25CD",
        "lad24cd",
        "LAD24CD",
        "lad23cd",
        "LAD23CD",
        "ctyua25cd",
        "CTYUA25CD",
        "ladcd",
        "LADCD",
    ])

    name_key = detect_property(props, [
        "la_name",
        "lad25nm",
        "LAD25NM",
        "lad24nm",
        "LAD24NM",
        "lad23nm",
        "LAD23NM",
        "ctyua25nm",
        "CTYUA25NM",
        "ladnm",
        "LADNM",
    ])

    code = props.get(code_key) if code_key else None
    name = props.get(name_key) if name_key else None

    return (str(code) if code else None, str(name) if name else None)


def slim_boundary_feature(
    feature: dict[str, Any],
    la_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    code, name = get_lad_properties(feature)

    if not code:
        return None

    lookup = la_lookup.get(code, {})

    clean = {
        "type": "Feature",
        "properties": {
            "new_la_code": code,
            "la_name": lookup.get("la_name") or name or code,
            "region_code": lookup.get("region_code"),
            "region_name": lookup.get("region_name"),
            "region_label": lookup.get("region_label") or lookup.get("region_name"),
        },
        "geometry": feature.get("geometry"),
    }

    return clean


def write_slim_boundaries(
    geo_path: Path,
    needed_la_codes: set[str],
    la_lookup: dict[str, dict[str, Any]],
    include_all_boundaries: bool,
    pretty: bool,
) -> dict[str, Any]:
    source = load_json(geo_path)

    if source.get("type") != "FeatureCollection":
        raise ValueError(f"Expected FeatureCollection GeoJSON: {geo_path}")

    source_features = source.get("features", [])

    if not isinstance(source_features, list):
        raise ValueError(f"GeoJSON features is not a list: {geo_path}")

    out_features = []
    missing_codes = set(needed_la_codes)

    for feature in source_features:
        code, _name = get_lad_properties(feature)

        if not code:
            continue

        if not include_all_boundaries and code not in needed_la_codes:
            continue

        slim = slim_boundary_feature(feature, la_lookup)

        if not slim:
            continue

        out_features.append(slim)
        missing_codes.discard(code)

    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "generated_at": now_utc(),
            "source_file": str(geo_path),
            "filtered_to_benchmark_las": not include_all_boundaries,
            "feature_count": len(out_features),
            "missing_benchmark_la_codes": sorted(missing_codes),
        },
        "features": out_features,
    }

    write_json(MAP_BOUNDARIES_PATH, payload, pretty=pretty)

    if missing_codes:
        print("WARNING: benchmark LA codes missing from GeoJSON boundary file:")
        for code in sorted(missing_codes):
            print(f"  {code} {la_lookup.get(code, {}).get('la_name') or ''}")

    return {
        "file": rel_to_docs(MAP_BOUNDARIES_PATH),
        "feature_count": len(out_features),
        "missing_benchmark_la_codes": sorted(missing_codes),
    }


def build_map_data(
    geo_path: Path,
    metrics: list[str],
    include_all_boundaries: bool = False,
    pretty: bool = False,
) -> None:
    print("Loading benchmark manifest...")
    manifest = load_json(BENCHMARK_MANIFEST_PATH)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    metric_files: dict[str, Any] = {}
    all_la_codes: set[str] = set()
    la_lookup: dict[str, dict[str, Any]] = {}

    print("Building compact LA map value files...")
    for metric in metrics:
        metric_manifest, la_codes, metric_la_lookup = build_metric_map_files(
            manifest=manifest,
            metric=metric,
            pretty=pretty,
        )

        if not metric_manifest:
            continue

        metric_files[metric] = metric_manifest
        all_la_codes.update(la_codes)

        for code, item in metric_la_lookup.items():
            la_lookup.setdefault(code, item)

    if not metric_files:
        raise SystemExit("No map metric files created. Check benchmark_manifest.provision_gap_files")

    print("Writing slim LA boundary GeoJSON...")
    boundary_info = write_slim_boundaries(
        geo_path=geo_path,
        needed_la_codes=all_la_codes,
        la_lookup=la_lookup,
        include_all_boundaries=include_all_boundaries,
        pretty=pretty,
    )

    map_manifest = {
        "generated_at": now_utc(),
        "title": "LA SEND Leaflet map manifest",
        "description": (
            "map-specific outputs for Leaflet LA choropleth views "
            "Opt A: LA polygons filtered/highlighted by selected region"
        ),
        "source_benchmark_manifest": "data/benchmarks/benchmark_manifest.json",
        "boundary_source_file": str(geo_path),
        "boundary_file": boundary_info["file"],
        "boundary_feature_count": boundary_info["feature_count"],
        "missing_benchmark_la_codes": boundary_info["missing_benchmark_la_codes"],
        "default_metric": "sess_overall_percent" if "sess_overall_percent" in metric_files else next(iter(metric_files)),
        "default_send_group": "EHC plan",
        "map_modes": {
            "provision_gap": {
                "status": "available",
                "description": "LA SEND provision group value minus No SEN value.",
                "value_field": "gap_to_no_sen",
                "files": "metric_files",
            },
            **EXTENSION_PLACEHOLDERS,
        },
        "metrics": [
            {
                "metric": metric,
                "metric_label": info.get("metric_label") or metric,
                "metric_type": info.get("metric_type"),
                "direction": info.get("direction"),
                "type": info.get("type"),
                "record_count": info.get("record_count", 0),
                "region_count": len(info.get("regions", {})),
            }
            for metric, info in metric_files.items()
        ],
        "metric_files": metric_files,
    }

    write_json(MAP_MANIFEST_PATH, map_manifest, pretty=pretty)

    print("")
    print("Done.")
    print(f"Metrics written: {len(metric_files)}")
    print(f"LA codes covered: {len(all_la_codes)}")
    print(f"Boundary features written: {boundary_info['feature_count']}")
    print(f"Map manifest: {MAP_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Leaflet map data off LA SEND benchmark story files"
    )
    parser.add_argument(
        "--geo",
        type=Path,
        default=DEFAULT_GEO_PATH,
        help=(
            "Path to local ONS LAD GeoJSON. Default: "
            "data/geo/lad_may_2025_uk_bgc_v2.geojson"
        ),
    )
    parser.add_argument(
        "--metrics",
        nargs="*",
        default=DEFAULT_MAP_METRICS,
        help="Metrics to build, defaults to initial map metric set",
    )
    parser.add_argument(
        "--include-all-boundaries",
        action="store_true",
        help=(
            "Keep every feature from boundary GeoJSON. Default filters to LAs "
            "present in benchmark map vals"
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write indented JSON. Default writes minified JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_map_data(
        geo_path=args.geo,
        metrics=args.metrics,
        include_all_boundaries=args.include_all_boundaries,
        pretty=args.pretty,
    )


if __name__ == "__main__":
    main()