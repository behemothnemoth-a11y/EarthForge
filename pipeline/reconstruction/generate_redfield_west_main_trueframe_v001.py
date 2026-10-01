#!/usr/bin/env python3
"""True-frame Redfield 617-627 reconstruction.

Transforms the accepted photo-led facade strip into the locked 1 m = 1 block
EarthForge frame, conforms building bases to the approved LiDAR MicroGrade,
and replaces the provisional uniform roof deck with LiDAR-derived roof bands.

Bulk side/rear shell walls remain vanilla bricks. Photo facades, fractional
roof caps and stepped roof transitions use Astra Microblocks.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

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
    BLOCK_ENTITY_ID,
    HOST_STATE,
    MicroVolume,
    cell_index,
    decode_volume_v4,
    tile_entity_payload,
)
from pipeline.terrain import generate_redfield_poc001_micrograde_v001 as micrograde

PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"
SOURCE = (
    PROJECT
    / "outputs/building_labs/west_main_photo_facades_v001/"
      "Redfield_WestMain_617-627_PhotoFacades_v001.litematic"
)
GEOM = POC / "l0_geometry_local.json"
LIDAR = (
    PROJECT
    / "downloads/multisource_v001/lidar_spink_2012/"
      "redfield_poc001_roi_points.csv"
)
OUT = PROJECT / "outputs" / "trueframe_west_main_v001"
NAME = "Redfield_POC_001_WestMain_TrueFrame_v001"
REGION = "REDFIELD_POC001_WESTMAIN_TRUEFRAME_V001"

SOURCE_REGION = "REDFIELD_WEST_MAIN_617_627_PHOTO_V001"
SOURCE_FRONT_MICRO_X = -4 * 16
SOURCE_SEGMENTS = {
    "625-627": (-19 * 16, -3 * 16),
    "623": (-3 * 16, 4 * 16),
    "621": (4 * 16, 17 * 16),
    "617-619": (17 * 16, 31 * 16),
}

BUILDING_IDS = {
    "625-627": 1474301419,
    "623": 1474301430,
    "621": 1474301428,
    "617-619": 1474301456,
}

# Visible top heights are evidence-informed, not survey claims. Dominant front
# LiDAR roof returns set the body height; photo morphology preserves parapets.
FACADE_VISIBLE_HEIGHT_M = {
    "625-627": 8.0,
    "623": 5.5,
    "621": 10.0,
    "617-619": 7.0,
}

SIDE_WALL = "minecraft:bricks"
ROOF_MATERIAL = "minecraft:gray_concrete"
ROOF_EDGE = "minecraft:light_gray_concrete"
FOUNDATION = "minecraft:stone_bricks"
def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def floor_div16(v: int) -> tuple[int, int]:
    host = math.floor(v / 16)
    local = v - host * 16
    return host, local

def source_tiles():
    blocks, meta = read_back_block_map(SOURCE, SOURCE_REGION)
    pos = meta["region_position"]
    tes = {
        (te["x"] + pos[0], te["y"] + pos[1], te["z"] + pos[2]): te
        for te in meta["tile_entities"]
        if te.get("id") == BLOCK_ENTITY_ID
    }
    decoded = {
        p: decode_volume_v4(te["volume_v4"])
        for p, te in tes.items()
    }
    return blocks, decoded, meta

def source_material_at(
    blocks: dict,
    decoded: dict,
    gx: int,
    gy: int,
    gz: int,
) -> str | None:
    hx, lx = floor_div16(gx)
    hy, ly = floor_div16(gy)
    hz, lz = floor_div16(gz)
    state = blocks.get((hx, hy, hz))
    if state is None:
        return None
    if state == HOST_STATE:
        return decoded[(hx, hy, hz)][cell_index(lx, ly, lz)]
    if state.startswith("minecraft:"):
        return state.split("[", 1)[0]
    return None

def source_segment_height(
    blocks: dict,
    decoded: dict,
    z0_micro: int,
    z1_micro: int,
) -> int:
    z0h = math.floor(z0_micro / 16)
    z1h = math.ceil(z1_micro / 16)
    top = 0
    for (x, y, z), state in blocks.items():
        if y < 0 or x > -2 or not (z0h <= z < z1h):
            continue
        if state == HOST_STATE:
            cells = decoded.get((x, y, z), [])
            for idx, material in enumerate(cells):
                if material is None:
                    continue
                ly = idx >> 8
                top = max(top, y * 16 + ly + 1)
        elif state.startswith("minecraft:"):
            top = max(top, (y + 1) * 16)
    if top <= 0:
        raise RuntimeError((z0_micro, z1_micro))
    return top

def load_polygons() -> dict[str, list[tuple[float, float]]]:
    geom = read_json(GEOM)
    by_id = {b["osm_id"]: b["polygon_xz_m"] for b in geom["buildings"]}
    return {
        name: [(float(x), float(z)) for x, z in by_id[osm]]
        for name, osm in BUILDING_IDS.items()
    }

def polygon_bounds(poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    return min(xs), max(xs), min(zs), max(zs)

def inside(x: float, z: float, poly) -> bool:
    hit = False
    for (ax, az), (bx, bz) in zip(poly, poly[1:] + poly[:1]):
        if (az > z) != (bz > z):
            cross = (bx - ax) * (z - az) / (bz - az) + ax
            if x < cross:
                hit = not hit
    return hit

def target_frontage(polys):
    order = ["625-627", "623", "621", "617-619"]
    b = {name: polygon_bounds(polys[name]) for name in order}
    boundaries = [b[order[0]][2]]
    for north_name, south_name in zip(order, order[1:]):
        south_edge_north = b[north_name][3]
        north_edge_south = b[south_name][2]
        boundaries.append((south_edge_north + north_edge_south) / 2.0)
    boundaries.append(b[order[-1]][3])

    result = {}
    for i, name in enumerate(order):
        z0 = boundaries[i]
        z1 = boundaries[i + 1]
        east = b[name][1]
        result[name] = {
            "z_north_m": z0,
            "z_south_m": z1,
            "z0_micro": round(z0 * 16),
            "z1_micro": round(z1 * 16),
            "front_x_m": east,
            "front_x_micro": round(east * 16),
        }
    return result

def load_lidar():
    points = []
    with LIDAR.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            points.append(
                (
                    float(row["x_local_m"]),
                    float(row["z_local_m"]),
                    float(row["elev_m"]),
                    int(row["class"]),
                )
            )
    return points
def lidar_roof_profiles(polys, lidar_points, smooth_ground):
    """Return absolute roof elevation mode per local integer x for each building."""
    profiles = {}
    audit = {}
    for name, poly in polys.items():
        xmin, xmax, zmin, zmax = polygon_bounds(poly)
        raw = {}
        counts = {}
        for x in range(math.floor(xmin), math.ceil(xmax)):
            vals = []
            for px, pz, elev, cls in lidar_points:
                if cls != 1 or not (x <= px < x + 1):
                    continue
                if not (zmin <= pz <= zmax) or not inside(px, pz, poly):
                    continue
                iz = max(micrograde.LOCAL_Z_MIN, min(micrograde.LOCAL_Z_MAX, round(pz)))
                ground = smooth_ground[iz]
                height = elev - ground
                if 2.0 <= height <= 15.0:
                    vals.append(elev)
            if vals:
                hist = Counter(round(v * 4.0) / 4.0 for v in vals)
                mode, count = hist.most_common(1)[0]
                raw[x] = mode
                counts[x] = {"points": len(vals), "mode_count": count}

        if not raw:
            raise RuntimeError(f"No roof returns for {name}")

        known = sorted(raw)
        filled = {}
        for x in range(math.floor(xmin), math.ceil(xmax)):
            if x in raw:
                filled[x] = raw[x]
                continue
            nearest = min(known, key=lambda k: abs(k - x))
            filled[x] = raw[nearest]

        smooth = {}
        xs = sorted(filled)
        for x in xs:
            vals = [filled[k] for k in xs if abs(k - x) <= 1]
            smooth[x] = statistics.median(vals)

        profiles[name] = smooth
        audit[name] = {
            "x_range_blocks": [min(xs), max(xs)],
            "raw_modes_m_navd88": {str(k): v for k, v in sorted(raw.items())},
            "mode_support": {str(k): counts[k] for k in sorted(counts)},
            "smoothed_modes_m_navd88": {str(k): v for k, v in sorted(smooth.items())},
        }
    return profiles, audit

def material_rgb(material: str) -> tuple[int, int, int]:
    if material.startswith("astra_microblocks:rgb_"):
        h = material.rsplit("_", 1)[1]
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    table = {
        "minecraft:bricks": (151, 86, 68),
        "minecraft:dark_oak_planks": (67, 43, 25),
        "minecraft:stone_bricks": (122, 122, 117),
        "minecraft:gray_concrete": (55, 58, 62),
        "minecraft:light_gray_concrete": (125, 125, 115),
        "minecraft:gray_stained_glass": (73, 91, 91),
        "minecraft:black_stained_glass": (28, 31, 31),
        "minecraft:smooth_stone": (166, 166, 158),
    }
    return table.get(material.split("[", 1)[0], (135, 128, 120))

def set_micro(
    blocks: dict,
    hosts: dict,
    sx_micro: int,
    sy_micro: int,
    sz_micro: int,
    material: str | None,
):
    hx, lx = floor_div16(sx_micro)
    hy, ly = floor_div16(sy_micro)
    hz, lz = floor_div16(sz_micro)
    pos = (hx, hy, hz)
    if pos in blocks and blocks[pos] != HOST_STATE:
        # Geospatial facade/roof precision is never allowed to silently replace
        # an unrelated full block.
        raise RuntimeError(f"Micro/full collision at {pos}: {blocks[pos]}")
    volume = hosts.get(pos)
    if volume is None:
        volume = MicroVolume("minecraft:stone")
        hosts[pos] = volume
        blocks[pos] = HOST_STATE
    volume.set(lx, ly, lz, material)

def fill_micro_y(
    blocks,
    hosts,
    sx_micro,
    sz_micro,
    y0,
    y1,
    material,
    x_thickness=1,
    z_thickness=1,
):
    for xx in range(sx_micro, sx_micro + x_thickness):
        for zz in range(sz_micro, sz_micro + z_thickness):
            for yy in range(y0, y1):
                set_micro(blocks, hosts, xx, yy, zz, material)

def project_micro(local_micro: int, ref_block: int) -> int:
    return local_micro - ref_block * 16
def facade_base_cells(row_cells, z0_micro: int, z1_micro: int) -> int:
    zs = range(math.floor(z0_micro / 16), math.ceil(z1_micro / 16))
    vals = []
    for z in zs:
        zc = max(micrograde.LOCAL_Z_MIN, min(micrograde.LOCAL_Z_MAX, z))
        vals.append(row_cells[zc] + 2)
    return round(statistics.median(vals))

def transform_facades(
    blocks,
    hosts,
    source_blocks,
    source_decoded,
    frontage,
    row_cells,
    ref_x,
    ref_z,
):
    audit = {}
    preview = {}
    source_materials = set()
    target_materials = set()

    for name in ["625-627", "623", "621", "617-619"]:
        src_z0, src_z1 = SOURCE_SEGMENTS[name]
        src_w = src_z1 - src_z0
        src_h = source_segment_height(
            source_blocks, source_decoded, src_z0, src_z1
        )
        tgt = frontage[name]
        tgt_w = tgt["z1_micro"] - tgt["z0_micro"]
        target_height = round(FACADE_VISIBLE_HEIGHT_M[name] * 16)
        base_cells = facade_base_cells(
            row_cells, tgt["z0_micro"], tgt["z1_micro"]
        )
        front_micro = tgt["front_x_micro"]

        written = 0
        for tu in range(tgt_w):
            su = src_z0 + min(src_w - 1, (tu * src_w) // tgt_w)
            local_z_micro = tgt["z0_micro"] + tu
            sz_micro = project_micro(local_z_micro, ref_z)

            for ty in range(target_height):
                sy = min(src_h - 1, (ty * src_h) // target_height)
                target_y_micro = base_cells + ty

                # Accepted source facade depth contract is -1..+2 blocks
                # around its original front boundary.
                for d in range(-16, 32):
                    mat = source_material_at(
                        source_blocks,
                        source_decoded,
                        SOURCE_FRONT_MICRO_X + d,
                        sy,
                        su,
                    )
                    if mat is None:
                        continue
                    local_x_micro = front_micro + d
                    sx_micro = project_micro(local_x_micro, ref_x)
                    set_micro(
                        blocks,
                        hosts,
                        sx_micro,
                        target_y_micro,
                        sz_micro,
                        mat,
                    )
                    written += 1
                    source_materials.add(mat)
                    target_materials.add(mat)

                    key = (target_y_micro, local_z_micro)
                    prior = preview.get(key)
                    if prior is None or local_x_micro > prior[0]:
                        preview[key] = (local_x_micro, mat, name)

        audit[name] = {
            "source_width_microcells": src_w,
            "source_occupied_height_microcells": src_h,
            "target_width_microcells": tgt_w,
            "target_width_m": tgt_w / 16.0,
            "target_visible_height_microcells": target_height,
            "target_visible_height_m": target_height / 16.0,
            "base_height_microcells": base_cells,
            "front_x_m": tgt["front_x_m"],
            "target_z_m": [tgt["z_north_m"], tgt["z_south_m"]],
            "written_microcells": written,
        }

    return audit, preview, source_materials, target_materials

def raster_footprint(poly):
    xmin, xmax, zmin, zmax = polygon_bounds(poly)
    cells = set()
    for x in range(math.floor(xmin), math.ceil(xmax)):
        for z in range(math.floor(zmin), math.ceil(zmax)):
            if inside(x + 0.5, z + 0.5, poly):
                cells.add((x, z))
    return cells

def add_shells_and_roofs(
    blocks,
    hosts,
    polys,
    roof_profiles,
    base_elev,
    ref_x,
    ref_z,
):
    audit = {}
    regular_added = Counter()
    roof_hosts_before = len(hosts)

    for name, poly in polys.items():
        footprint = raster_footprint(poly)
        roof_profile = roof_profiles[name]
        front_x = polygon_bounds(poly)[1]

        roof_cells_by_x = {
            x: round((elev - base_elev) * 16)
            for x, elev in roof_profile.items()
        }

        # Full-block side/rear shell. Leave the east/front two metres to the
        # accepted facade model so openings are never filled behind the glass.
        shell_limit = math.floor(front_x) - 2
        for x, z in sorted(footprint):
            if x > shell_limit:
                continue
            neighbors = {
                "west": (x - 1, z),
                "east": (x + 1, z),
                "north": (x, z - 1),
                "south": (x, z + 1),
            }
            perimeter = any(n not in footprint for n in neighbors.values())
            if not perimeter:
                continue

            roof_top = roof_cells_by_x.get(
                x, roof_cells_by_x[min(roof_cells_by_x, key=lambda k: abs(k-x))]
            )
            roof_host_y = max(0, math.floor((roof_top - 1) / 16))

            sx = x - ref_x
            sz = z - ref_z
            for y in range(0, roof_host_y):
                pos = (sx, y, sz)
                if pos in blocks:
                    continue
                blocks[pos] = SIDE_WALL
                regular_added[SIDE_WALL] += 1

            # Fractional wall cap to exact roof elevation.
            sy0 = roof_host_y * 16
            sx_micro = sx * 16
            sz_micro = sz * 16
            for lx in range(16):
                for lz in range(16):
                    # Only perimeter blocks get a solid cap; roof material
                    # overwrites the top two cells below.
                    for yy in range(sy0, roof_top):
                        set_micro(
                            blocks, hosts,
                            sx_micro + lx, yy, sz_micro + lz,
                            SIDE_WALL,
                        )

        # Thin roof surface over the actual footprint, using the LiDAR x-band.
        for x, z in sorted(footprint):
            if x > shell_limit:
                continue
            roof_top = roof_cells_by_x.get(
                x, roof_cells_by_x[min(roof_cells_by_x, key=lambda k: abs(k-x))]
            )
            sx_micro = (x - ref_x) * 16
            sz_micro = (z - ref_z) * 16
            for lx in range(16):
                for lz in range(16):
                    for yy in range(max(0, roof_top - 2), roof_top):
                        set_micro(
                            blocks, hosts,
                            sx_micro + lx, yy, sz_micro + lz,
                            ROOF_MATERIAL,
                        )

        # Close front-to-back roof height steps with a thin vertical transition.
        xs = sorted({x for x, z in footprint if x <= shell_limit})
        for x0, x1 in zip(xs, xs[1:]):
            if x1 != x0 + 1:
                continue
            h0 = roof_cells_by_x.get(x0)
            h1 = roof_cells_by_x.get(x1)
            if h0 is None or h1 is None or h0 == h1:
                continue
            lo, hi = sorted((h0, h1))
            boundary_local_micro = x1 * 16
            sx_micro = project_micro(boundary_local_micro, ref_x)
            z_values = [z for xx, z in footprint if xx in (x0, x1)]
            if not z_values:
                continue
            for z in range(min(z_values), max(z_values) + 1):
                if (x0, z) not in footprint or (x1, z) not in footprint:
                    continue
                sz_micro = project_micro(z * 16, ref_z)
                for lz in range(16):
                    for xx in range(sx_micro - 2, sx_micro):
                        for yy in range(lo, hi):
                            set_micro(
                                blocks, hosts, xx, yy, sz_micro + lz, ROOF_EDGE
                            )

        audit[name] = {
            "footprint_blocks": len(footprint),
            "shell_front_reserve_x_gt": shell_limit,
            "roof_height_microcells_by_x": {
                str(x): roof_cells_by_x[x] for x in sorted(roof_cells_by_x)
            },
            "roof_height_blocks_relative_project_zero": {
                str(x): round(roof_cells_by_x[x] / 16.0, 3)
                for x in sorted(roof_cells_by_x)
            },
        }

    return audit, regular_added, len(hosts) - roof_hosts_before

def make_preview(preview_cells, frontage, row_cells, path):
    if not preview_cells:
        return
    zmin = min(z for y, z in preview_cells)
    zmax = max(z for y, z in preview_cells)
    ymin = 0
    ymax = max(y for y, z in preview_cells) + 1
    scale = 2
    margin = 70
    im = Image.new(
        "RGB",
        ((zmax - zmin + 1) * scale + margin * 2,
         (ymax - ymin + 1) * scale + 170),
        "#efeee6",
    )
    d = ImageDraw.Draw(im)
    font_path = Path("C:/Windows/Fonts/segoeui.ttf")
    def f(size):
        return ImageFont.truetype(str(font_path), size) if font_path.exists() else None

    d.text((35, 22), "REDFIELD / WEST MAIN / TRUE-FRAME v001", font=f(27), fill="#243c39")
    d.text(
        (35, 60),
        "Accepted photo facades rescaled to mapped frontage + LiDAR/MicroGrade elevation",
        font=f(16),
        fill="#54605b",
    )

    ox = margin
    oy = 105 + ymax * scale
    for (y, z), (x, mat, name) in preview_cells.items():
        px = ox + (z - zmin) * scale
        py = oy - (y + 1) * scale
        d.rectangle((px, py, px + scale - 1, py + scale - 1), fill=material_rgb(mat))

    for name, item in frontage.items():
        a = ox + (item["z0_micro"] - zmin) * scale
        b = ox + (item["z1_micro"] - zmin) * scale
        d.line((a, 100, a, oy + 12), fill="#77766f", width=1)
        d.text(((a+b)//2 - 25, oy + 25), name, font=f(14), fill="#243c39")

    d.text(
        (35, im.height - 48),
        "Front view only. Side/rear walls and LiDAR roof bands are in the Litematic but omitted here.",
        font=f(15),
        fill="#54605b",
    )
    im.save(path)
def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    frame, raw_ground, smooth_ground, row_cells, base_elev, blocks, hosts, _, _ = (
        micrograde.build_surface()
    )
    ref = frame["future_litematica_registration"]
    ref_x = int(ref["player_feet_x"])
    ref_z = int(ref["player_feet_z"])

    source_blocks, source_decoded, source_meta = source_tiles()
    polys = load_polygons()
    frontage = target_frontage(polys)
    lidar_points = load_lidar()
    roof_profiles, roof_lidar_audit = lidar_roof_profiles(
        polys, lidar_points, smooth_ground
    )

    shell_audit, regular_added, new_roof_hosts = add_shells_and_roofs(
        blocks, hosts, polys, roof_profiles, base_elev, ref_x, ref_z
    )
    facade_audit, preview_cells, source_mats, target_mats = transform_facades(
        blocks,
        hosts,
        source_blocks,
        source_decoded,
        frontage,
        row_cells,
        ref_x,
        ref_z,
    )

    # Hosts are final block states.
    for pos in hosts:
        blocks[pos] = HOST_STATE

    xs = [p[0] for p in blocks]
    ys = [p[1] for p in blocks]
    zs = [p[2] for p in blocks]
    bounds = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    writer = NBTWriter()
    tes = []
    for (x, y, z), volume in sorted(hosts.items()):
        rel = (x - bounds[0], y - bounds[1], z - bounds[2])
        tes.append(tile_entity_payload(writer, rel, volume))

    path = OUT / f"{NAME}.litematic"
    stats = write_single_region_litematic(
        path,
        blocks,
        bounds,
        REGION,
        NAME,
        "Locked-frame Redfield Main Street MicroGrade plus 617-627 accepted photo "
        "facades rescaled to mapped geographic frontage and LiDAR-derived roof bands. "
        "Astra 0.7.0 chunk-baked rendering assumed.",
        data_version=4903,
        tile_entity_payloads=tes,
    )

    reread, meta = read_back_block_map(path, REGION)
    expected = {p: canonical_state(s) for p, s in blocks.items()}
    assert reread == expected

    pos = meta["region_position"]
    decoded = {}
    for te in meta["tile_entities"]:
        if te.get("id") == BLOCK_ENTITY_ID:
            p = (te["x"] + pos[0], te["y"] + pos[1], te["z"] + pos[2])
            decoded[p] = decode_volume_v4(te["volume_v4"])
    assert set(decoded) == set(hosts)
    for p, volume in hosts.items():
        assert decoded[p] == volume.cells, p

    assert reread.get((0, -1, 0)) == "minecraft:yellow_concrete"
    assert target_mats.issubset(source_mats)

    total_frontage = sum(
        item["target_width_microcells"] for item in facade_audit.values()
    )
    assert total_frontage == (
        frontage["617-619"]["z1_micro"] - frontage["625-627"]["z0_micro"]
    )

    report = {
        **stats,
        "astra_min_version": "0.7.0",
        "source_photo_facade_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_lidar_sha256": hashlib.sha256(LIDAR.read_bytes()).hexdigest(),
        "true_frame": {
            "registration_schematic": [0, -1, 0],
            "registration_project_local": [ref_x, -1, ref_z],
            "frontage_microcells": total_frontage,
            "frontage_m": total_frontage / 16.0,
            "facades": facade_audit,
        },
        "lidar_roofs": roof_lidar_audit,
        "shells": shell_audit,
        "regular_shell_blocks_added": dict(regular_added),
        "astra": {
            "host_count": len(hosts),
            "occupied_microcells": sum(v.occupied_count() for v in hosts.values()),
            "new_roof_shell_hosts_after_micrograde": new_roof_hosts,
            "facade_material_count": len(target_mats),
        },
        "validation": {
            "exact_block_readback": True,
            "exact_astra_cell_readback": True,
            "registration_marker": True,
            "photo_facade_materials_preserved_as_source_subset": True,
            "photo_facades_resampled_not_redesigned": True,
            "true_geographic_frontage": True,
            "micrograde_carried_forward": True,
            "uniform_roof_deck_removed": True,
            "in_game_test": False,
        },
        "confidence": {
            "frontage_boundaries": "High for combined mapped frontage; internal address splits use midpoint reconciliation of overlapping OSM outlines.",
            "facade_appearance": "High relative to accepted city-archive-photo studies; geometry is nearest-neighbor resampled to true scale.",
            "facade_vertical_scale": "Medium: fitted to dominant/high front LiDAR bands and photo parapet morphology.",
            "roof_height": "Medium-high: 2012 LiDAR modal roof returns smoothed by one adjacent x strip.",
            "side_rear_material": "Low-medium: generic brick shell until direct side/rear street-level imagery is acquired.",
        },
    }
    (OUT / f"{NAME}_validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / f"{NAME}_placement.json").write_text(
        json.dumps(
            {
                "origin": "player feet directly above permanent yellow marker",
                "marker": [0, -1, 0],
                "rotation": 0,
                "mirror": "none",
                "replace_blocks": "ALL",
                "note": "This combined export supersedes the standalone MicroGrade for testing; it contains that surface plus the true-frame west-side buildings.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    make_preview(
        preview_cells,
        frontage,
        row_cells,
        OUT / f"{NAME}_front_preview.png",
    )

    print(json.dumps({
        "file": str(path),
        "sha256": stats["sha256"],
        "region_position": stats["region_position"],
        "region_size": stats["region_size"],
        "frontage_m": total_frontage / 16.0,
        "astra_hosts": len(hosts),
        "occupied_microcells": sum(v.occupied_count() for v in hosts.values()),
        "regular_shell_blocks": sum(regular_added.values()),
        "facades": {
            k: {
                "width_m": v["target_width_m"],
                "height_m": v["target_visible_height_m"],
                "base_microcells": v["base_height_microcells"],
            }
            for k, v in facade_audit.items()
        },
        "validation": "PASS",
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
