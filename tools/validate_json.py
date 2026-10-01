from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

targets = set()
for pattern in ("*.json", "*.geojson"):
    targets.update((ROOT / "projects").rglob(pattern))
targets.update((ROOT / "schemas").glob("*.json"))
targets = sorted(targets)

failed = False
for path in targets:
    # Ignore private/licensed raw reference areas if JSON metadata ever appears there.
    rel = path.relative_to(ROOT)
    if "references" in rel.parts and "private" in rel.parts:
        continue
    try:
        json.loads(path.read_text(encoding="utf-8"))
        print(f"OK  {rel}")
    except Exception as exc:
        failed = True
        print(f"ERR {rel}: {exc}", file=sys.stderr)

raise SystemExit(1 if failed else 0)
