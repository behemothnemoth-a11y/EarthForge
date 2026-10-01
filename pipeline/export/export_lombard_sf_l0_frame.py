#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.export.litematic_codec import read_back_block_map, write_single_region_litematic

PROJECT = ROOT / "projects" / "lombard_sf"
CONFIG = PROJECT / "terrain" / "l0_frame_config.json"
OUT = PROJECT / "outputs" / "l0_frame" / "Lombard_SF_L0_Frame_v001.litematic"
VALIDATION = PROJECT / "validation" / "lombard_l0_frame_v001_validation.json"

def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def build_blocks(cfg: dict):
    marker = tuple(cfg["registration"]["marker"])
    ox, _, oz = cfg["diagnostic_frame"]["build_offset_blocks"]
    width, _, length = cfg["diagnostic_frame"]["size_blocks"]
    x0, z0 = ox, oz
    x1, z1 = ox + width - 1, oz + length - 1
    c = cfg["colors"]
    blocks = {marker: cfg["registration"]["block"]}

    for x in range(x0, x1 + 1):
        blocks[(x, -1, z0)] = c["perimeter"]
        blocks[(x, -1, z1)] = c["perimeter"]
    for z in range(z0, z1 + 1):
        blocks[(x0, -1, z)] = c["perimeter"]
        blocks[(x1, -1, z)] = c["perimeter"]

    for x in range(x0, min(x0 + 16, x1 + 1)):
        blocks[(x, -1, z0)] = c["east_axis"]
    for z in range(z0, min(z0 + 16, z1 + 1)):
        blocks[(x0, -1, z)] = c["south_axis"]

    # Two orange control beacons deliberately mean “unresolved”.
    blocks[(x0, 0, z0)] = c["unresolved_control"]
    blocks[(x1, 0, z0)] = c["unresolved_control"]
    return blocks, (0, -1, 0, x1, 0, z1)

def main() -> int:
    cfg = load()
    blocks, bounds = build_blocks(cfg)
    meta = write_single_region_litematic(
        OUT, blocks, bounds,
        region_name="lombard_l0_frame",
        schematic_name="Lombard SF L0 Frame v001",
        description="Diagnostic acquisition frame only. Marker at (0,-1,0); no road or terrain interpretation is encoded."
    )
    actual, read_meta = read_back_block_map(OUT, "lombard_l0_frame")
    exact = actual == blocks
    marker_ok = actual.get((0,-1,0)) == cfg["registration"]["block"]
    report = {
        "schema_version":1,
        "artifact_id":cfg["artifact_id"],
        "status":"valid" if exact and marker_ok else "invalid",
        "geometry_truth":False,
        "diagnostic_only":True,
        "file":str(OUT.relative_to(ROOT)).replace("\\","/"),
        "sha256":meta["sha256"],
        "registration":{"marker":[0,-1,0],"marker_ok":marker_ok,"rotation":0,"mirror":"none"},
        "checks":{"exact_block_map":exact,"marker":marker_ok},
        "region":read_meta["region_size"],
        "non_air_blocks":len(actual)
    }
    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "valid":
        raise SystemExit("Lombard L0 frame readback validation failed")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
