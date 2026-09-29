#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

LOCAL_IN = POC / "l0_geometry_local.json"
CSV_IN = POC / "l0_block_plan.csv"
FRAME_IN = POC / "locked_frame.json"
POLICY_IN = POC / "massing_v002_policy.json"

OUT_DIR = PROJECT / "outputs" / "massing"
OUT_FILE = OUT_DIR / "Redfield_POC_001_Massing_v002.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_Massing_v002.manifest.json"
CLASS_OUT = POC / "massing_v002_building_classes.json"
REPORT_OUT = PROJECT / "validation" / "poc001_massing_v002_validation.json"

codec_path = ROOT / "pipeline" / "export" / "litematic_codec.py"
spec = importlib.util.spec_from_file_location("earthforge_litematic_codec", codec_path)
codec = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(codec)

Point = Tuple[float, float]
Cell2 = Tuple[int, int]
Cell3 = Tuple[int, int, int]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def point_in_polygon(px: float, pz: float, poly: Sequence[Point]) -> bool:
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if ((zi > pz) != (zj > pz)):
            denom = zj - zi
            if abs(denom) < 1e-12:
                denom = 1e-12
            cross = (xj - xi) * (pz - zi) / denom + xi
            if px < cross:
                inside = not inside
        j = i
    return inside


def raster_polygon(poly: Sequence[Point]) -> set[Cell2]:
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    out = set()
    for x in range(math.floor(min(xs)), math.ceil(max(xs)) + 1):
        for z in range(math.floor(min(zs)), math.ceil(max(zs)) + 1):
            if point_in_polygon(x + 0.5, z + 0.5, poly):
                out.add((x, z))
    return out


def distance_point_segment(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    wx, wz = px - ax, pz - az
    denom = vx * vx + vz * vz
    if denom <= 1e-12:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, (wx * vx + wz * vz) / denom))
    cx, cz = ax + t * vx, az + t * vz
    return math.hypot(px - cx, pz - cz)


def raster_line(coords: Sequence[Point], half_width: float, bounds) -> set[Cell2]:
    if len(coords) < 2:
        return set()
    min_x, min_z, max_x, max_z = bounds
    out = set()
    for x in range(math.floor(min_x), math.ceil(max_x) + 1):
        for z in range(math.floor(min_z), math.ceil(max_z) + 1):
            px, pz = x + 0.5, z + 0.5
            if min(
                distance_point_segment(px, pz, *coords[i], *coords[i + 1])
                for i in range(len(coords) - 1)
            ) <= half_width:
                out.add((x, z))
    return out


def read_l0_cells():
    cells = {}
    with CSV_IN.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cells[(int(row["x"]), int(row["z"]))] = (row["role"], row["block"])
    return cells


def main() -> int:
    local = load_json(LOCAL_IN)
    frame = load_json(FRAME_IN)
    policy = load_json(POLICY_IN)
    l0 = read_l0_cells()

    ref = frame["future_litematica_registration"]
    ref_x = int(ref["player_feet_x"])
    ref_z = int(ref["player_feet_z"])

    pb = frame["plan_bounds_blocks"]
    project_bounds = (
        int(pb["min_x"]),
        int(pb["min_z"]),
        int(pb["max_x"]),
        int(pb["max_z"]),
    )

    # Ground plan in PROJECT coordinates first.
    ground: Dict[Cell2, str] = {}

    # Retain the L0 avenue/alley/crossing/anchor cells.
    keep_roles = {"avenue", "alley", "crossing", "project_anchor"}
    for cell, (role, block) in l0.items():
        if role in keep_roles:
            ground[cell] = block

    # Rebuild Main Street at the narrower v002 review width.
    main_features = [t for t in local["transport"] if t.get("role") == "main_street"]
    if not main_features:
        raise ValueError("Main Street local geometry is missing")
    main_half = float(policy["road"]["main_street_paved_half_width_m"])
    for feature in main_features:
        pts = [tuple(p) for p in feature["line_xz_m"]]
        for cell in raster_line(pts, main_half, project_bounds):
            ground[cell] = "minecraft:black_concrete"

    # Expand source sidewalk lines toward the curb. Buildings later overwrite overlap.
    sidewalk_half = float(policy["sidewalk"]["source_line_half_width_m"])
    for feature in local["transport"]:
        role = feature.get("role")
        if role == "sidewalk":
            pts = [tuple(p) for p in feature["line_xz_m"]]
            for cell in raster_line(pts, sidewalk_half, project_bounds):
                ground[cell] = "minecraft:smooth_stone"

    # Put crossings back over the road/sidewalk.
    for cell, (role, block) in l0.items():
        if role == "crossing":
            ground[cell] = block

    # Keep geographic anchor visible.
    for cell, (role, block) in l0.items():
        if role == "project_anchor":
            ground[cell] = block

    mass = policy["massing"]
    frontage_limit = float(mass["primary_frontage_max_distance_from_main_m"])
    primary_h = int(mass["primary_wall_height_blocks"])
    secondary_h = int(mass["secondary_wall_height_blocks"])

    project_blocks: Dict[Cell3, str] = {}
    for (x, z), block in ground.items():
        project_blocks[(x, -1, z)] = block

    classes = []
    primary_count = 0
    secondary_count = 0

    for building in local["buildings"]:
        poly = [tuple(p) for p in building["polygon_xz_m"]]
        if not poly:
            continue

        footprint = raster_polygon(poly)
        min_front_dist = min(abs(x) for x, _z in poly)

        if min_front_dist <= frontage_limit:
            cls = "primary_frontage"
            wall_h = primary_h
            wall_block = mass["primary_wall_block"]
            primary_count += 1
        else:
            cls = "secondary_rear"
            wall_h = secondary_h
            wall_block = mass["secondary_wall_block"]
            secondary_count += 1

        roof_y = wall_h
        roof_block = mass["roof_block"]

        # Foundation / floor replaces grass at ground.
        for x, z in footprint:
            project_blocks[(x, -1, z)] = wall_block

        # Solid diagnostic mass. This is intentional for silhouette review.
        for y in range(0, wall_h):
            for x, z in footprint:
                project_blocks[(x, y, z)] = wall_block

        for x, z in footprint:
            project_blocks[(x, roof_y, z)] = roof_block

        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        classes.append({
            "osm_id": building["osm_id"],
            "class": cls,
            "minimum_front_distance_m": round(min_front_dist, 3),
            "wall_height_blocks": wall_h,
            "roof_y": roof_y,
            "footprint_cells": len(footprint),
            "local_bounds_m": {
                "min_x": round(min(xs), 3),
                "max_x": round(max(xs), 3),
                "min_z": round(min(zs), 3),
                "max_z": round(max(zs), 3),
            },
            "address": None,
            "address_match_status": "deferred"
        })

    # Translate PROJECT coordinates to SCHEMATIC coordinates using the SAME reference as v001.
    schematic_blocks: Dict[Cell3, str] = {}
    for (px, py, pz), block in project_blocks.items():
        schematic_blocks[(px - ref_x, py, pz - ref_z)] = block

    # Permanent registration marker wins at its fixed schematic position.
    marker = (0, -1, 0)
    marker_block = policy["registration"]["marker_block"]
    schematic_blocks[marker] = marker_block

    # Preserve the exact horizontal region frame from v001.
    min_sx = int(pb["min_x"]) - ref_x
    max_sx = int(pb["max_x"]) - ref_x
    min_sz = int(pb["min_z"]) - ref_z
    max_sz = int(pb["max_z"]) - ref_z
    max_y = max(y for _x, y, _z in schematic_blocks)

    bounds = (min_sx, -1, min_sz, max_sx, max_y, max_sz)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_info = codec.write_single_region_litematic(
        path=OUT_FILE,
        blocks=schematic_blocks,
        bounds=bounds,
        region_name="REDFIELD_POC_001_MASSING_V002",
        schematic_name="Redfield POC 001 - Massing v002",
        description="EarthForge Redfield block-only massing test. Same yellow registration origin as L0 v001. No Microblocks.",
        data_version=4903,
        version=6,
        subversion=1,
    )

    read_back, meta = codec.read_back_block_map(OUT_FILE, "REDFIELD_POC_001_MASSING_V002")
    exact = read_back == schematic_blocks
    marker_ok = read_back.get(marker) == marker_block

    if not exact:
        raise ValueError("Read-back block map differs from v002 source map")
    if not marker_ok:
        raise ValueError("Permanent yellow registration marker failed validation")

    class_doc = {
        "schema_version": 1,
        "export_id": policy["export_id"],
        "classification_rule": f"primary_frontage when minimum |X| <= {frontage_limit} m",
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "buildings": sorted(classes, key=lambda x: (x["local_bounds_m"]["min_z"], x["local_bounds_m"]["min_x"]))
    }
    CLASS_OUT.write_text(json.dumps(class_doc, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "export_id": policy["export_id"],
        "status": "valid",
        "file": str(OUT_FILE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": write_info["sha256"],
        "region_position": write_info["region_position"],
        "region_size": write_info["region_size"],
        "volume": write_info["volume"],
        "non_air_blocks": write_info["non_air_blocks"],
        "palette": write_info["palette"],
        "bits_per_block": write_info["bits_per_block"],
        "ground_review": {
            "main_street_paved_half_width_m": main_half,
            "main_street_paved_width_m": main_half * 2.0,
            "sidewalk_source_half_width_m": sidewalk_half
        },
        "massing": {
            "primary_frontage_buildings": primary_count,
            "secondary_rear_buildings": secondary_count,
            "primary_wall_height_blocks": primary_h,
            "secondary_wall_height_blocks": secondary_h,
            "individual_story_counts_claimed": False
        },
        "registration": {
            "marker_position": list(marker),
            "marker_block": marker_block,
            "verified": marker_ok
        },
        "checks": {
            "exact_block_map": exact,
            "registration_marker": marker_ok,
            "same_horizontal_frame_as_v001": True,
            "microblocks_used": False
        },
        "errors": []
    }
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "export_id": policy["export_id"],
        "file": report["file"],
        "sha256": report["sha256"],
        "region_position": report["region_position"],
        "region_size": report["region_size"],
        "placement": {
            "instruction": "Stand on the existing yellow registration block from v001 and set the v002 placement origin to the player-feet block.",
            "rotation": 0,
            "mirror": "none",
            "marker_relative_to_origin": [0, -1, 0],
            "replace_blocks": "ALL"
        },
        "diagnostic_only": True
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("EarthForge Redfield POC 001 Massing v002 generated and validated.")
    print(f"  File             : {report['file']}")
    print(f"  SHA256           : {report['sha256']}")
    print(f"  Region pos       : {report['region_position']}")
    print(f"  Region size      : {report['region_size']}")
    print(f"  Non-air blocks   : {report['non_air_blocks']}")
    print(f"  Primary buildings: {primary_count}")
    print(f"  Rear structures  : {secondary_count}")
    print(f"  Main paved width : {main_half * 2.0:.1f} blocks")
    print(f"  Marker           : {list(marker)} {marker_block}")
    print("  Read-back        : PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
