#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

LOCAL_IN = POC / "l0_geometry_local.json"
FRAME_IN = POC / "locked_frame.json"
MAP_IN = POC / "address_match_v003.json"
POLICY_IN = POC / "l1_alpha_v003_policy.json"

OUT_DIR = PROJECT / "outputs" / "l1_alpha"
OUT_FILE = OUT_DIR / "Redfield_POC_001_L1_Alpha_v003.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_L1_Alpha_v003.manifest.json"
MODEL_OUT = POC / "l1_alpha_v003_building_model.json"
REPORT_OUT = PROJECT / "validation" / "poc001_l1_alpha_v003_validation.json"

CODEC_PATH = ROOT / "pipeline" / "export" / "litematic_codec.py"

Point = Tuple[float, float]
Cell2 = Tuple[int, int]
Cell3 = Tuple[int, int, int]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_codec():
    if not CODEC_PATH.exists():
        raise FileNotFoundError(f"Litematic codec missing: {CODEC_PATH}")
    spec = importlib.util.spec_from_file_location("earthforge_litematic_codec", CODEC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def point_in_polygon(px: float, pz: float, poly: Sequence[Point]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > pz) != (zj > pz):
            denom = zj - zi
            if abs(denom) < 1e-12:
                denom = 1e-12
            x_cross = (xj - xi) * (pz - zi) / denom + xi
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def raster_polygon(poly: Sequence[Point]) -> Set[Cell2]:
    if len(poly) < 3:
        return set()
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    out: Set[Cell2] = set()
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


def raster_line(coords: Sequence[Point], half_width: float, bounds) -> Set[Cell2]:
    if len(coords) < 2:
        return set()
    min_x, min_z, max_x, max_z = bounds
    out: Set[Cell2] = set()
    for x in range(math.floor(min_x), math.ceil(max_x) + 1):
        for z in range(math.floor(min_z), math.ceil(max_z) + 1):
            px, pz = x + 0.5, z + 0.5
            best = min(
                distance_point_segment(px, pz, *coords[i], *coords[i + 1])
                for i in range(len(coords) - 1)
            )
            if best <= half_width:
                out.add((x, z))
    return out


def boundary_cells(cells: Set[Cell2]) -> Set[Cell2]:
    result = set()
    for x, z in cells:
        if any((x + dx, z + dz) not in cells for dx, dz in ((1,0),(-1,0),(0,1),(0,-1))):
            result.add((x, z))
    return result


def frontage_cells(cells: Set[Cell2], side: str) -> List[Cell2]:
    by_z: Dict[int, List[int]] = {}
    for x, z in cells:
        by_z.setdefault(z, []).append(x)

    result = []
    for z, xs in sorted(by_z.items()):
        result.append((min(xs) if side == "east" else max(xs), z))
    return result


def side_edge_cells(cells: Set[Cell2], direction: str) -> List[Cell2]:
    if not cells:
        return []
    if direction in ("south", "north"):
        target = max(z for _x, z in cells) if direction == "south" else min(z for _x, z in cells)
        return sorted([(x, z) for x, z in cells if z == target])
    if direction in ("east", "west"):
        target = max(x for x, _z in cells) if direction == "east" else min(x for x, _z in cells)
        return sorted([(x, z) for x, z in cells if x == target], key=lambda p: p[1])
    return []


def nearest_existing(target: float, values: List[int]) -> int:
    return min(values, key=lambda v: abs(v - target))


def opening_positions(front: List[Cell2], count: int = 1) -> Set[int]:
    zs = sorted(set(z for _x, z in front))
    if not zs:
        return set()
    if count == 1:
        return {nearest_existing((zs[0] + zs[-1]) / 2, zs)}
    targets = [
        zs[0] + (zs[-1] - zs[0]) * (i + 1) / (count + 1)
        for i in range(count)
    ]
    return {nearest_existing(t, zs) for t in targets}


def set_block(blocks: Dict[Cell3, str], x: int, y: int, z: int, name: str):
    blocks[(x, y, z)] = name


def build_ground(local: dict, frame: dict, policy: dict) -> Dict[Cell3, str]:
    pb = frame["plan_bounds_blocks"]
    bounds = (pb["min_x"], pb["min_z"], pb["max_x"], pb["max_z"])
    roads = policy["roads"]

    ground: Dict[Cell3, str] = {}

    for feature in local["transport"]:
        role = feature.get("role")
        coords = [tuple(p) for p in feature.get("line_xz_m", [])]
        if len(coords) < 2:
            continue

        if role == "main_street":
            width = float(roads["main_half_width_m"])
            block = "minecraft:black_concrete"
        elif role == "avenue":
            width = float(roads["avenue_half_width_m"])
            block = "minecraft:gray_concrete"
        elif role == "alley":
            width = float(roads["alley_half_width_m"])
            block = "minecraft:polished_andesite"
        elif role == "sidewalk":
            width = float(roads["sidewalk_half_width_m"])
            block = "minecraft:smooth_stone"
        elif role == "crossing":
            width = float(roads["crossing_half_width_m"])
            block = "minecraft:white_concrete"
        else:
            continue

        for x, z in raster_line(coords, width, bounds):
            ground[(x, -1, z)] = block

    # A simple curb read between intersections; this is still an L1-alpha review feature.
    main = [f for f in local["transport"] if f.get("role") == "main_street"]
    if main:
        xs = [p[0] for f in main for p in f["line_xz_m"]]
        center_x = sum(xs) / len(xs)
        half = float(roads["main_half_width_m"])
        curb_w = int(round(center_x - half - 0.5))
        curb_e = int(round(center_x + half + 0.5))
        inset = int(roads["curb_end_inset_blocks"])
        z_min = int(pb["min_z"]) + inset
        z_max = int(pb["max_z"]) - inset
        for z in range(z_min, z_max + 1):
            ground[(curb_w, -1, z)] = roads["curb_block"]
            ground[(curb_e, -1, z)] = roads["curb_block"]

    # Preserve project anchor.
    ground[(0, -1, 0)] = "minecraft:red_concrete"
    return ground


def build_shell(
    blocks: Dict[Cell3, str],
    footprint: Set[Cell2],
    entry: dict,
    arch: dict,
    rear: bool = False,
):
    if not footprint:
        return

    height = int(entry.get("height", 4 if rear else 5))
    wall = entry.get("wall", "minecraft:stone_bricks")
    trim = entry.get("trim", "minecraft:smooth_stone")
    roof = arch["rear_roof_block"] if rear else arch["roof_block"]

    boundary = boundary_cells(footprint)

    for x, z in footprint:
        set_block(blocks, x, -1, z, wall)
        set_block(blocks, x, height, z, roof)

    for x, z in boundary:
        for y in range(0, height):
            set_block(blocks, x, y, z, wall)

    if rear:
        return

    side = entry["side"]
    front = frontage_cells(footprint, side)
    if not front:
        return

    front_zs = sorted(set(z for _x, z in front))
    z0 = front_zs[0]
    spacing = int(arch["facade_column_spacing"])
    profile = entry.get("profile", "storefront")
    door_count = 2 if profile == "paired_625_627" else 1
    doors = opening_positions(front, door_count)

    accent_primary = entry.get("accent", trim)
    accent_secondary = entry.get("accent_secondary", accent_primary)
    split_z = (front_zs[0] + front_zs[-1]) / 2

    # Standard storefront grammar.
    for x, z in front:
        column = ((z - z0) % spacing == 0)
        accent = accent_primary if z <= split_z else accent_secondary

        for y in arch["front_window_y"]:
            if z in doors:
                set_block(blocks, x, int(y), z, arch["door_placeholder"])
            elif column:
                set_block(blocks, x, int(y), z, wall)
            else:
                set_block(blocks, x, int(y), z, entry["glass"])

        sign_y = int(arch["sign_band_y"])
        if sign_y < height:
            set_block(blocks, x, sign_y, z, accent)

        if height >= 7:
            for y in arch["upper_window_y"]:
                y = int(y)
                if y < height:
                    if column or ((z - z0) % (spacing + 1) == 0):
                        set_block(blocks, x, y, z, wall)
                    else:
                        set_block(blocks, x, y, z, entry["glass"])

        # Parapet/cornice one block above roof along Main frontage.
        set_block(blocks, x, height + int(arch["default_parapet_extra"]), z, trim)

    # More distinct City Hall treatment.
    if profile == "city_hall":
        for x, z in front:
            idx = z - z0
            if idx % 3 == 0:
                for y in range(1, height):
                    set_block(blocks, x, y, z, "minecraft:smooth_quartz")
            elif 1 <= idx % 3 <= 2:
                for y in range(1, min(height, 7)):
                    set_block(blocks, x, y, z, entry["glass"])
            set_block(blocks, x, height + 1, z, "minecraft:chiseled_stone_bricks")

    # Exposed side-wall glazing for corner anchors.
    exposed = None
    if profile in ("leos_corner", "modern_low"):
        exposed = "south"
    elif profile in ("city_hall", "paired_625_627"):
        exposed = "north"

    if exposed:
        edge = side_edge_cells(footprint, exposed)
        if edge:
            base = min(x for x, _z in edge)
            for x, z in edge:
                if (x - base) % 4 in (1, 2):
                    for y in (1, 2):
                        if y < height:
                            set_block(blocks, x, y, z, entry["glass"])


def validate_mapping(local: dict, mapping: dict) -> dict:
    geo_ids = {int(b["osm_id"]) for b in local["buildings"]}
    primary_ids = [int(x["osm_id"]) for x in mapping["primary"]]
    secondary_ids = [int(x["osm_id"]) for x in mapping["secondary"]]
    all_map_ids = set(primary_ids + secondary_ids)

    errors = []
    if len(primary_ids) != len(set(primary_ids)):
        errors.append("Duplicate primary OSM IDs")
    if len(secondary_ids) != len(set(secondary_ids)):
        errors.append("Duplicate secondary OSM IDs")
    if all_map_ids != geo_ids:
        errors.append(
            f"Address mapping IDs do not exactly match selected geometry IDs. "
            f"missing={sorted(geo_ids-all_map_ids)} extra={sorted(all_map_ids-geo_ids)}"
        )
    return {"ok": not errors, "errors": errors}


def self_test() -> int:
    fp = {(x, z) for x in range(2, 8) for z in range(-8, -2)}
    entry = {
        "side": "east", "height": 6, "wall": "minecraft:bricks",
        "trim": "minecraft:smooth_stone", "accent": "minecraft:red_terracotta",
        "glass": "minecraft:black_stained_glass", "profile": "historic_storefront"
    }
    arch = {
        "rear_roof_block": "minecraft:deepslate_tiles",
        "roof_block": "minecraft:polished_deepslate",
        "door_placeholder": "minecraft:dark_oak_planks",
        "default_parapet_extra": 1,
        "front_window_y": [1,2],
        "upper_window_y": [4,5],
        "sign_band_y": 3,
        "facade_column_spacing": 4
    }
    blocks = {}
    build_shell(blocks, fp, entry, arch, False)
    assert any(v == "minecraft:black_stained_glass" for v in blocks.values())
    assert any(v == "minecraft:dark_oak_planks" for v in blocks.values())
    assert any(y == 7 for (_x,y,_z) in blocks)
    print("L1_ALPHA_SELF_TEST_PASS", len(blocks))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    local = load_json(LOCAL_IN)
    frame = load_json(FRAME_IN)
    mapping = load_json(MAP_IN)
    policy = load_json(POLICY_IN)
    codec = load_codec()

    map_check = validate_mapping(local, mapping)
    if not map_check["ok"]:
        raise ValueError("; ".join(map_check["errors"]))

    geom = {int(b["osm_id"]): b for b in local["buildings"]}
    blocks = build_ground(local, frame, policy)

    model_entries = []
    primary_by_id = {int(x["osm_id"]): x for x in mapping["primary"]}

    for entry in mapping["primary"]:
        oid = int(entry["osm_id"])
        poly = [tuple(p) for p in geom[oid]["polygon_xz_m"]]
        footprint = raster_polygon(poly)
        build_shell(blocks, footprint, entry, policy["architecture"], rear=False)
        model_entries.append({
            "osm_id": oid,
            "addresses": entry["addresses"],
            "name": entry["name"],
            "profile": entry["profile"],
            "height": entry["height"],
            "side": entry["side"],
            "footprint_cells": len(footprint),
            "confidence": entry["confidence"],
            "note": entry["note"]
        })

    for secondary in mapping["secondary"]:
        oid = int(secondary["osm_id"])
        parent = primary_by_id[int(secondary["parent_osm_id"])]
        rear_entry = {
            "height": max(3, int(parent["height"]) - 2),
            "wall": parent["wall"],
            "trim": parent["trim"],
            "side": parent["side"],
        }
        poly = [tuple(p) for p in geom[oid]["polygon_xz_m"]]
        footprint = raster_polygon(poly)
        build_shell(blocks, footprint, rear_entry, policy["architecture"], rear=True)
        model_entries.append({
            "osm_id": oid,
            "parent_osm_id": int(secondary["parent_osm_id"]),
            "name": secondary["name"],
            "profile": "rear_addition",
            "height": rear_entry["height"],
            "footprint_cells": len(footprint),
            "confidence": secondary["confidence"]
        })

    ref = frame["future_litematica_registration"]
    ref_x, ref_z = int(ref["player_feet_x"]), int(ref["player_feet_z"])

    schematic: Dict[Cell3, str] = {}
    for (px, py, pz), block in blocks.items():
        schematic[(px - ref_x, py, pz - ref_z)] = block

    marker = tuple(policy["registration"]["marker_schematic"])
    marker_block = policy["registration"]["marker_block"]
    schematic[marker] = marker_block

    pb = frame["plan_bounds_blocks"]
    min_x = int(pb["min_x"]) - ref_x
    max_x = int(pb["max_x"]) - ref_x
    min_z = int(pb["min_z"]) - ref_z
    max_z = int(pb["max_z"]) - ref_z
    min_y = -1
    max_y = max(y for _x,y,_z in schematic)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    info = codec.write_single_region_litematic(
        path=OUT_FILE,
        blocks=schematic,
        bounds=(min_x, min_y, min_z, max_x, max_y, max_z),
        region_name="REDFIELD_POC_001_L1_ALPHA_V003",
        schematic_name="Redfield POC 001 - L1 Alpha v003",
        description="Block-only Redfield L1-alpha: inferred storefront mapping, hollow shells, facade grammar, no Microblocks.",
        data_version=4903,
        version=6,
        subversion=1,
    )

    back, meta = codec.read_back_block_map(OUT_FILE, "REDFIELD_POC_001_L1_ALPHA_V003")
    exact = back == schematic
    marker_ok = back.get(marker) == marker_block

    if not exact:
        raise ValueError("Litematic read-back differs from generated v003 block map")
    if not marker_ok:
        raise ValueError("Registration marker validation failed")

    MODEL_OUT.write_text(json.dumps({
        "schema_version": 1,
        "export_id": policy["export_id"],
        "address_mapping_status": mapping["status"],
        "palette_current_photo_verified": False,
        "story_heights_surveyed": False,
        "entries": model_entries
    }, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "export_id": policy["export_id"],
        "status": "valid",
        "file": str(OUT_FILE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": info["sha256"],
        "region_position": info["region_position"],
        "region_size": info["region_size"],
        "volume": info["volume"],
        "non_air_blocks": info["non_air_blocks"],
        "palette_size": len(info["palette"]),
        "palette": info["palette"],
        "address_mapping": {
            "status": mapping["status"],
            "primary_footprints": len(mapping["primary"]),
            "secondary_structures": len(mapping["secondary"]),
            "survey_verified": False
        },
        "roads": policy["roads"],
        "checks": {
            "mapping_exactly_covers_selected_geometry": map_check["ok"],
            "exact_block_map": exact,
            "registration_marker": marker_ok,
            "microblocks_used": False,
            "hollow_shell_architecture": True
        },
        "registration": {
            "marker_position": list(marker),
            "marker_block": marker_block,
            "verified": marker_ok
        },
        "errors": []
    }
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    MANIFEST_OUT.write_text(json.dumps({
        "schema_version": 1,
        "export_id": policy["export_id"],
        "file": report["file"],
        "sha256": report["sha256"],
        "region_position": report["region_position"],
        "region_size": report["region_size"],
        "placement": {
            "instruction": "Stand on the existing yellow registration block and set placement origin to player feet.",
            "rotation": 0,
            "mirror": "none",
            "replace_blocks": "ALL"
        },
        "review_targets": [
            "street widths",
            "sidewalk width",
            "building/address sequence",
            "skyline rhythm",
            "storefront proportions",
            "City Hall landmark mass",
            "corner-building treatment"
        ]
    }, indent=2) + "\n", encoding="utf-8")

    print("EarthForge Redfield POC 001 L1 Alpha v003 generated and validated.")
    print(f"  File             : {report['file']}")
    print(f"  SHA256           : {report['sha256']}")
    print(f"  Region pos       : {report['region_position']}")
    print(f"  Region size      : {report['region_size']}")
    print(f"  Non-air blocks   : {report['non_air_blocks']}")
    print(f"  Palette size     : {report['palette_size']}")
    print(f"  Storefront sites : {len(mapping['primary'])}")
    print(f"  Rear structures  : {len(mapping['secondary'])}")
    print(f"  Main width       : {policy['roads']['main_half_width_m']*2:.1f} blocks")
    print(f"  Avenue width     : {policy['roads']['avenue_half_width_m']*2:.1f} blocks")
    print(f"  Marker           : {list(marker)} {marker_block}")
    print("  Read-back        : PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
