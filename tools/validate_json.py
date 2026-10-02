from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
targets = [
    ROOT / "projects" / "redfield_sd" / "project.json",
    ROOT / "projects" / "redfield_sd" / "control_points.json",
    ROOT / "projects" / "redfield_sd" / "bounds.geojson",
    ROOT / "projects" / "lombard_street_sf" / "project.json",
    ROOT / "projects" / "lombard_street_sf" / "control_points.json",
    ROOT / "projects" / "lombard_street_sf" / "road_truth_plan.json",
    ROOT / "projects" / "lombard_street_sf" / "georeference_plan.json",
]
targets += sorted((ROOT / "schemas").glob("*.json"))
targets += sorted((ROOT / "projects" / "lombard_street_sf" / "source_manifests").glob("*.json"))

failed = False
for path in targets:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        print(f"OK  {path.relative_to(ROOT)}")
    except Exception as exc:
        failed = True
        print(f"ERR {path.relative_to(ROOT)}: {exc}", file=sys.stderr)

raise SystemExit(1 if failed else 0)
