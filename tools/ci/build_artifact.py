#!/usr/bin/env python3
"""Allowlisted EarthForge artifact builder used by GitHub Actions."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "artifacts"

TARGETS = {
    "lombard_1040_reset_v027": {
        "generator": "pipeline/reconstruction/generate_lombard_1040_reset_v027.py",
        "output_dir": "projects/lombard_sf/outputs/house_1040_reset_v027",
        "artifact": "Lombard_1040_Source_Reset_Astra_v027.litematic",
        "validation": "Lombard_1040_Source_Reset_Astra_v027_validation.json",
        "placement": "Lombard_1040_Source_Reset_Astra_v027_placement.json",
        "required_status": "PASS",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=sorted(TARGETS))
    args = parser.parse_args()
    spec = TARGETS[args.target]

    generator = ROOT / spec["generator"]
    subprocess.run([sys.executable, str(generator)], cwd=ROOT, check=True)

    out = ROOT / spec["output_dir"]
    validation_path = out / spec["validation"]
    report = json.loads(validation_path.read_text(encoding="utf-8"))
    if report.get("status") != spec["required_status"]:
        raise SystemExit(
            f"Artifact validation status is {report.get('status')!r}; "
            f"expected {spec['required_status']!r}"
        )
    failed = [k for k, v in report.get("validation", {}).items() if v is not True]
    if failed:
        raise SystemExit(f"Validation gates failed: {failed}")

    bundle = DIST / args.target
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)

    required = [
        spec["artifact"],
        spec["validation"],
        spec["placement"],
        "Build_notes.md",
    ]
    copied: list[Path] = []
    for name in required:
        src = out / name
        if not src.exists():
            raise SystemExit(f"Required output missing: {src.relative_to(ROOT)}")
        dst = bundle / src.name
        shutil.copy2(src, dst)
        copied.append(dst)

    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.geojson"):
        for src in sorted(out.glob(pattern)):
            dst = bundle / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                copied.append(dst)

    manifest = {
        "schema_version": 1,
        "target": args.target,
        "generator": spec["generator"],
        "validation_status": report["status"],
        "files": [
            {
                "name": p.name,
                "bytes": p.stat().st_size,
                "sha256": sha256(p),
            }
            for p in sorted(copied)
        ],
    }
    (bundle / "SHA256_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
