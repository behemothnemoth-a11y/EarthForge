#!/usr/bin/env python3
"""LiDAR-driven Astra micrograde for Redfield Main Street, 7th to 6th.

This is a geospatial base layer in the original locked EarthForge frame.
It does not move or edit the accepted photo-facade studies.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter,
    canonical_state,
    read_back_block_map,
    write_single_region_litematic,
)
from pipeline.microblocks.astra_microblock_codec import (
    HOST_STATE,
    MicroVolume,
    decode_volume_v4,
    tile_entity_payload,
)

PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"
FRAME = POC / "locked_frame.json"
BLOCK_PLAN = POC / "l0_block_plan.csv"
LIDAR = PROJECT / "downloads" / "multisource_v001" / "lidar_spink_2012" / "redfield_poc001_roi_points.csv"

NAME = "Redfield_POC_001_MainStreet_MicroGrade_v001"
REGION = "REDFIELD_POC001_MAINSTREET_MICROGRADE_V001"
OUT = PROJECT / "outputs" / "geospatial_micro_v001"
LOCAL_Z_MIN = -132
LOCAL_Z_MAX = 0
ROAD_X = range(-9, 10)
CURB_X = (-10, 10)
WEST_SIDEWALK_X = range(-16, -10)
EAST_SIDEWALK_X = range(11, 17)

MATERIAL = {
    "road_base": "minecraft:gray_concrete",
    "sidewalk_base": "minecraft:smooth_stone",
    "asphalt_micro": "astra_microblocks:rgb_55585a",
    "curb_micro": "astra_microblocks:rgb_c8c5bb",
    "sidewalk_micro": "astra_microblocks:rgb_b7b4aa",
    "marker": "minecraft:yellow_concrete",
}

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def load_roles() -> dict[tuple[int, int], str]:
    roles = {}
    with BLOCK_PLAN.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            roles[(int(row["x"]), int(row["z"]))] = row["role"]
    return roles

def load_ground_points() -> list[tuple[float, float, float]]:
    if not LIDAR.exists():
        raise FileNotFoundError(
            f"LiDAR ROI missing: {LIDAR}. Run the Redfield multisource acquisition first."
        )
    out = []
    with LIDAR.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if int(row["class"]) == 2:
                out.append((
                    float(row["x_local_m"]),
                    float(row["z_local_m"]),
                    float(row["elev_m"]),
                ))
    if not out:
        raise RuntimeError("No class-2 ground points found")
    return out
def raw_row_profile(points: list[tuple[float, float, float]]) -> dict[int, float]:
    profile = {}
    for z in range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1):
        vals = [
            elev for x, zz, elev in points
            if -6.0 <= x <= 6.0 and abs(zz - z) <= 0.8
        ]
        if len(vals) < 3:
            vals = [
                elev for x, zz, elev in points
                if -7.0 <= x <= 7.0 and abs(zz - z) <= 1.6
            ]
        if vals:
            profile[z] = statistics.median(vals)

    known = sorted(profile)
    if not known:
        raise RuntimeError("No Main Street ground profile rows could be measured")

    for z in range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1):
        if z in profile:
            continue
        lo = max((k for k in known if k < z), default=None)
        hi = min((k for k in known if k > z), default=None)
        if lo is None:
            profile[z] = profile[hi]
        elif hi is None:
            profile[z] = profile[lo]
        else:
            t = (z - lo) / (hi - lo)
            profile[z] = profile[lo] * (1 - t) + profile[hi] * t
    return profile

def smooth_profile(raw: dict[int, float]) -> dict[int, float]:
    smooth = {}
    for z in range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1):
        vals = [
            raw[zz]
            for zz in range(max(LOCAL_Z_MIN, z - 2), min(LOCAL_Z_MAX, z + 2) + 1)
        ]
        smooth[z] = statistics.median(vals)
    return smooth

def quantize_profile(smooth: dict[int, float]) -> tuple[dict[int, int], float]:
    base = min(smooth.values())
    cells = {
        z: max(0, int(round((elev - base) * 16.0)))
        for z, elev in smooth.items()
    }
    return cells, base

def crown_cells(x: int) -> int:
    # One microcell of crown through the center third; deliberately subtle.
    return 1 if abs(x) <= 3 else 0

def project_to_schematic(local_x: int, local_z: int, ref_x: int, ref_z: int) -> tuple[int, int]:
    return local_x - ref_x, local_z - ref_z
def fill_micro_column(
    hosts: dict[tuple[int, int, int], MicroVolume],
    sx: int,
    sz: int,
    extra_cells: int,
    material: str,
) -> None:
    """Fill only the sub-block height above the full y=-1 base block."""
    remaining = int(extra_cells)
    hy = 0
    while remaining > 0:
        count = min(16, remaining)
        key = (sx, hy, sz)
        volume = hosts.get(key)
        if volume is None:
            volume = MicroVolume("minecraft:gray_concrete")
            hosts[key] = volume
        volume.fill_box(0, 0, 0, 16, count, 16, material)
        remaining -= count
        hy += 1

def build_surface():
    frame = read_json(FRAME)
    ref = frame["future_litematica_registration"]
    ref_x = int(ref["player_feet_x"])
    ref_z = int(ref["player_feet_z"])
    roles = load_roles()
    points = load_ground_points()
    raw = raw_row_profile(points)
    smooth = smooth_profile(raw)
    row_cells, base_elev = quantize_profile(smooth)

    blocks: dict[tuple[int, int, int], str] = {}
    hosts: dict[tuple[int, int, int], MicroVolume] = {}
    column_meta = []
    skipped_for_building = 0

    # Permanent project registration marker.
    blocks[(0, -1, 0)] = MATERIAL["marker"]

    def add_column(local_x: int, local_z: int, kind: str, height_cells: int):
        nonlocal skipped_for_building
        if roles.get((local_x, local_z)) == "building_footprint":
            skipped_for_building += 1
            return

        sx, sz = project_to_schematic(local_x, local_z, ref_x, ref_z)
        if kind == "road":
            base_block = MATERIAL["road_base"]
            micro_mat = MATERIAL["asphalt_micro"]
        elif kind == "curb":
            base_block = MATERIAL["sidewalk_base"]
            micro_mat = MATERIAL["curb_micro"]
        else:
            base_block = MATERIAL["sidewalk_base"]
            micro_mat = MATERIAL["sidewalk_micro"]

        blocks[(sx, -1, sz)] = base_block
        fill_micro_column(hosts, sx, sz, height_cells, micro_mat)
        column_meta.append((local_x, local_z, kind, height_cells, sx, sz))

    for z in range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1):
        base_cells = row_cells[z]

        for x in ROAD_X:
            add_column(x, z, "road", base_cells + crown_cells(x))

        for x in CURB_X:
            add_column(x, z, "curb", base_cells + 2)

        for x in WEST_SIDEWALK_X:
            add_column(x, z, "sidewalk", base_cells + 2)
        for x in EAST_SIDEWALK_X:
            add_column(x, z, "sidewalk", base_cells + 2)

    # Astra hosts replace air above the regular base layer.
    for pos in hosts:
        if pos in blocks:
            raise AssertionError(f"Micro host collides with full block: {pos}")
        blocks[pos] = HOST_STATE

    return frame, raw, smooth, row_cells, base_elev, blocks, hosts, column_meta, skipped_for_building
def font(size: int):
    path = Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else None

def make_preview(
    row_cells: dict[int, int],
    smooth: dict[int, float],
    base_elev: float,
    column_meta,
    out_path: Path,
):
    width, height = 1280, 980
    im = Image.new("RGB", (width, height), "#efeee7")
    d = ImageDraw.Draw(im)
    d.text((45, 28), "REDFIELD / MAIN STREET MICROGRADE v001", font=font(30), fill="#243c39")
    d.text(
        (45, 72),
        "LiDAR-driven longitudinal grade + microblock curb/sidewalk surface",
        font=font(18),
        fill="#54605b",
    )

    # Plan strip
    left, top = 80, 130
    cell_x = 15
    cell_z = 5
    for x, z, kind, hcells, sx, sz in column_meta:
        px = left + (x + 16) * cell_x
        py = top + (z - LOCAL_Z_MIN) * cell_z
        if kind == "road":
            shade = 65 + min(60, hcells * 3)
            color = (shade, shade + 2, shade + 3)
        elif kind == "curb":
            color = (205, 200, 187)
        else:
            color = (185, 181, 170)
        d.rectangle((px, py, px + cell_x - 1, py + cell_z - 1), fill=color)

    d.text((80, 805), "South / Main x 7th", font=font(15), fill="#243c39")
    d.text((80, 118), "North / Main x 6th", font=font(15), fill="#243c39")
    d.text((575, 420), "road", font=font(15), fill="#243c39")
    d.text((390, 420), "west sidewalk", font=font(15), fill="#243c39")
    d.text((690, 420), "east sidewalk", font=font(15), fill="#243c39")

    # Elevation profile
    x0, y0 = 820, 160
    pw, ph = 390, 620
    zvals = list(range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1))
    hvals = [row_cells[z] / 16.0 for z in zvals]
    hmin, hmax = min(hvals), max(hvals)
    if hmax == hmin:
        hmax += 1
    pts = []
    for z, h in zip(zvals, hvals):
        py = y0 + (z - LOCAL_Z_MIN) / (LOCAL_Z_MAX - LOCAL_Z_MIN) * ph
        px = x0 + (h - hmin) / (hmax - hmin) * pw
        pts.append((px, py))
    d.line(pts, fill="#7a4938", width=4)
    d.rectangle((x0, y0, x0 + pw, y0 + ph), outline="#787870", width=2)
    d.text((x0, y0 - 35), "relative road elevation", font=font(17), fill="#243c39")
    d.text(
        (x0, y0 + ph + 18),
        f"range {hmax-hmin:.3f} m at 1/16-block resolution",
        font=font(15),
        fill="#54605b",
    )
    d.text(
        (45, 890),
        f"LiDAR base elevation {base_elev:.3f} m NAVD88 is normalized to Minecraft surface 0.",
        font=font(15),
        fill="#54605b",
    )
    d.text(
        (45, 920),
        "Horizontal curb/sidewalk width remains the current EarthForge truth policy pending direct Google/Mapillary frontage verification.",
        font=font(15),
        fill="#54605b",
    )
    im.save(out_path)
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (
        frame, raw, smooth, row_cells, base_elev, blocks, hosts,
        column_meta, skipped_for_building,
    ) = build_surface()

    xs = [p[0] for p in blocks]
    ys = [p[1] for p in blocks]
    zs = [p[2] for p in blocks]
    bounds = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    writer = NBTWriter()
    tile_entities = []
    for (x, y, z), volume in sorted(hosts.items()):
        rel = (x - bounds[0], y - bounds[1], z - bounds[2])
        tile_entities.append(tile_entity_payload(writer, rel, volume))

    path = OUT / f"{NAME}.litematic"
    stats = write_single_region_litematic(
        path,
        blocks,
        bounds,
        REGION,
        NAME,
        "True-frame Redfield Main Street micrograde from 2012 SDGS LiDAR. "
        "Dense Astra hosts are permitted under Astra 0.7.0 chunk-baked rendering. "
        "Accepted photo facades are not included or modified.",
        data_version=4903,
        tile_entity_payloads=tile_entities,
    )

    check, meta = read_back_block_map(path, REGION)
    expected = {p: canonical_state(s) for p, s in blocks.items()}
    assert check == expected

    decoded_hosts = {}
    px, py, pz = meta["region_position"]
    for te in meta["tile_entities"]:
        if te.get("id") != "astra_microblocks:test_host":
            continue
        pos = (te["x"] + px, te["y"] + py, te["z"] + pz)
        decoded_hosts[pos] = decode_volume_v4(te["volume_v4"])

    assert set(decoded_hosts) == set(hosts)
    for pos, volume in hosts.items():
        assert decoded_hosts[pos] == volume.cells, pos

    marker = check.get((0, -1, 0))
    assert marker == MATERIAL["marker"]

    max_jump = max(
        abs(row_cells[z] - row_cells[z - 1])
        for z in range(LOCAL_Z_MIN + 1, LOCAL_Z_MAX + 1)
    )
    profile_range_cells = max(row_cells.values()) - min(row_cells.values())
    profile_range_m = profile_range_cells / 16.0
    rise_7th_to_6th = smooth[LOCAL_Z_MIN] - smooth[LOCAL_Z_MAX]

    report = {
        **stats,
        "astra_min_version": "0.7.0",
        "rendering_model": "chunk-baked world rendering",
        "project_frame": {
            "anchor": frame["anchor"],
            "orientation": frame["orientation"],
            "registration_project_local": [
                frame["future_litematica_registration"]["player_feet_x"],
                -1,
                frame["future_litematica_registration"]["player_feet_z"],
            ],
            "registration_schematic": [0, -1, 0],
        },
        "surface": {
            "local_z_range": [LOCAL_Z_MIN, LOCAL_Z_MAX],
            "road_x_range": [min(ROAD_X), max(ROAD_X)],
            "curb_x": list(CURB_X),
            "west_sidewalk_x_range": [min(WEST_SIDEWALK_X), max(WEST_SIDEWALK_X)],
            "east_sidewalk_x_range": [min(EAST_SIDEWALK_X), max(EAST_SIDEWALK_X)],
            "base_lidar_elevation_m": base_elev,
            "profile_range_microcells": profile_range_cells,
            "profile_range_m": profile_range_m,
            "main_7th_to_main_6th_rise_m": rise_7th_to_6th,
            "max_adjacent_row_jump_microcells": max_jump,
            "curb_sidewalk_raise_microcells": 2,
            "center_crown_microcells": 1,
            "building_overlap_columns_skipped": skipped_for_building,
        },
        "microblocks": {
            "host_count": len(hosts),
            "occupied_microcells": sum(v.occupied_count() for v in hosts.values()),
            "materials": dict(Counter(mat for v in hosts.values() for mat in v.materials())),
        },
        "validation": {
            "exact_block_readback": True,
            "exact_astra_microcell_readback": True,
            "registration_marker": True,
            "accepted_photo_facades_modified": False,
            "in_game_test": False,
        },
        "source": {
            "lidar_manifest": "projects/redfield_sd/source_manifests/lidar_spink_2012_poc001_v001.json",
            "lidar_roi_sha256": hashlib.sha256(LIDAR.read_bytes()).hexdigest(),
            "horizontal_width_policy": "projects/redfield_sd/poc_001/l1_truth_v005_policy.json",
        },
        "limitations": [
            "2012 LiDAR is used for durable grade/elevation evidence, not current appearance.",
            "Main Street lateral curb/sidewalk widths remain the current EarthForge truth-policy values pending direct current street-level verification.",
            "This export is a geospatial surface layer only; buildings and accepted photo facades are intentionally absent.",
        ],
    }
    (OUT / f"{NAME}_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    profile_rows = [
        {
            "z_local_m": z,
            "raw_elev_m": raw[z],
            "smooth_elev_m": smooth[z],
            "height_microcells": row_cells[z],
        }
        for z in range(LOCAL_Z_MIN, LOCAL_Z_MAX + 1)
    ]
    (OUT / f"{NAME}_profile.json").write_text(json.dumps(profile_rows, indent=2) + "\n", encoding="utf-8")

    make_preview(
        row_cells,
        smooth,
        base_elev,
        column_meta,
        OUT / f"{NAME}_preview.png",
    )

    print(json.dumps({
        "file": str(path),
        "sha256": stats["sha256"],
        "region_position": stats["region_position"],
        "region_size": stats["region_size"],
        "astra_hosts": len(hosts),
        "occupied_microcells": sum(v.occupied_count() for v in hosts.values()),
        "profile_range_m": profile_range_m,
        "rise_7th_to_6th_m": rise_7th_to_6th,
        "max_adjacent_row_jump_cells": max_jump,
        "building_columns_skipped": skipped_for_building,
        "validation": "PASS",
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
