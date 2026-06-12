python scripts/build_json_preview_from_processed.py data/processed/la_send_measure_long.csv.gz --max-records-per-file 100000

check size:
ls -lh docs/data/la_send_latest_summary.json

check shape:
python - <<'PY'
import json
from pathlib import Path

p = Path("docs/data/la_send_latest_summary.json")
data = json.loads(p.read_text(encoding="utf-8"))

print("json_size_mb:", round(p.stat().st_size / 1024 / 1024, 2))
print("records:", len(data.get("records", [])))
print("long_record_count:", data.get("long_record_count"))
print("wide_records:", len(data.get("wide_records", [])))
print("wide_measure_columns:", data.get("wide_measure_columns", []))
PY