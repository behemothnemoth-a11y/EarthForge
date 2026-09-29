#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

LOCAL_IN = POC / "l0_geometry_local.json"
FRAME_IN = POC / "locked_frame.json"
SPEC_IN = POC / "visual_v004.json"
POLICY_IN = POC / "l1_visual_v004_policy.json"
CODEC_PATH = ROOT / "pipeline" / "export" / "litematic_codec.py"

OUT_DIR = PROJECT / "outputs" / "l1_visual"
OUT_FILE = OUT_DIR / "Redfield_POC_001_L1_Visual_v004.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_L1_Visual_v004.manifest.json"
MODEL_OUT = POC / "l1_visual_v004_model.json"
REPORT_OUT = PROJECT / "validation" / "poc001_l1_visual_v004_validation.json"

Point = Tuple[float, float]
Cell2 = Tuple[int, int]
Cell3 = Tuple[int, int, int]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_codec():
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
            den = zj - zi
            if abs(den) < 1e-12:
                den = 1e-12
            cross = (xj - xi) * (pz - zi) / den + xi
            if px < cross:
                inside = not inside
        j = i
    return inside


def raster_polygon(poly: Sequence[Point]) -> Set[Cell2]:
    if len(poly) < 3:
        return set()
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
    den = vx * vx + vz * vz
    if den <= 1e-12:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, (wx * vx + wz * vz) / den))
    cx, cz = ax + t * vx, az + t * vz
    return math.hypot(px - cx, pz - cz)


def raster_line(coords: Sequence[Point], half_width: float, bounds) -> Set[Cell2]:
    if len(coords) < 2:
        return set()
    min_x, min_z, max_x, max_z = bounds
    out = set()
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
    return {
        (x, z) for x, z in cells
        if any((x + dx, z + dz) not in cells for dx, dz in ((1,0),(-1,0),(0,1),(0,-1)))
    }


def frontage_cells(cells: Set[Cell2], side: str) -> List[Cell2]:
    by_z = {}
    for x, z in cells:
        by_z.setdefault(z, []).append(x)
    return [
        (min(xs) if side == "east" else max(xs), z)
        for z, xs in sorted(by_z.items())
    ]


def edge_cells(cells: Set[Cell2], direction: str) -> List[Cell2]:
    if direction in ("north", "south"):
        target = min(z for _x,z in cells) if direction == "north" else max(z for _x,z in cells)
        return sorted([(x,z) for x,z in cells if z == target])
    target = min(x for x,_z in cells) if direction == "west" else max(x for x,_z in cells)
    return sorted([(x,z) for x,z in cells if x == target], key=lambda p: p[1])


def nearest(target: float, vals: List[int]) -> int:
    return min(vals, key=lambda v: abs(v-target))


def spaced_positions(vals: List[int], count: int) -> List[int]:
    vals = sorted(set(vals))
    if not vals:
        return []
    if count <= 1:
        return [nearest((vals[0]+vals[-1])/2, vals)]
    targets = [vals[0] + (vals[-1]-vals[0]) * (i+1)/(count+1) for i in range(count)]
    return [nearest(t, vals) for t in targets]


def setb(blocks: Dict[Cell3, str], x: int, y: int, z: int, state: str):
    blocks[(x,y,z)] = state


def door_states(block_name: str, facing: str):
    return (
        f"{block_name}[facing={facing},half=lower,hinge=left,open=false,powered=false]",
        f"{block_name}[facing={facing},half=upper,hinge=left,open=false,powered=false]"
    )


def slab_state(name: str, slab_type: str = "bottom"):
    return f"{name}[type={slab_type},waterlogged=false]"


def stair_state(name: str, facing: str, half: str = "bottom"):
    return f"{name}[facing={facing},half={half},shape=straight,waterlogged=false]"


def build_ground(local: dict, frame: dict, policy: dict) -> Dict[Cell3, str]:
    pb = frame["plan_bounds_blocks"]
    bounds = (pb["min_x"], pb["min_z"], pb["max_x"], pb["max_z"])
    road = policy["roads"]
    blocks: Dict[Cell3, str] = {}

    for feature in local["transport"]:
        role = feature.get("role")
        coords = [tuple(p) for p in feature.get("line_xz_m", [])]
        if len(coords) < 2:
            continue
        if role == "main_street":
            width, block = road["main_half_width_m"], "minecraft:black_concrete"
        elif role == "avenue":
            width, block = road["avenue_half_width_m"], "minecraft:gray_concrete"
        elif role == "alley":
            width, block = road["alley_half_width_m"], "minecraft:polished_andesite"
        elif role == "sidewalk":
            width, block = road["sidewalk_half_width_m"], "minecraft:smooth_stone"
        elif role == "crossing":
            width, block = road["crossing_half_width_m"], "minecraft:white_concrete"
        else:
            continue
        for x,z in raster_line(coords, float(width), bounds):
            setb(blocks, x, -1, z, block)

    # Parking stall marks along Main, using the outer two pavement blocks.
    if road.get("parking_markings"):
        for z in range(-20, -121, -9):
            for x in (-8, -7, 7, 8):
                setb(blocks, x, -1, z, "minecraft:white_concrete")

    setb(blocks, 0, -1, 0, "minecraft:red_concrete")
    return blocks


def add_streetscape(blocks: Dict[Cell3,str], policy: dict):
    street = policy["streetscape"]
    if street.get("streetlights"):
        for x in street["light_x_positions"]:
            for z in street["light_z_positions"]:
                if (x,0,z) in blocks or (x,1,z) in blocks:
                    continue
                setb(blocks, x, 0, z, "minecraft:polished_blackstone_wall")
                for y in (1,2,3):
                    setb(blocks, x, y, z, "minecraft:iron_bars")
                setb(blocks, x, 4, z, "minecraft:lantern[hanging=false]")

    if street.get("benches"):
        for z in (-36, -86):
            setb(blocks, -13, 0, z, stair_state("minecraft:spruce_stairs", "east"))
            setb(blocks, 13, 0, z, stair_state("minecraft:spruce_stairs", "west"))

    if street.get("planters"):
        for z in (-61, -111):
            for x in (-13, 13):
                setb(blocks, x, 0, z, "minecraft:composter[level=8]")
                setb(blocks, x, 1, z, "minecraft:flowering_azalea_leaves[distance=1,persistent=true,waterlogged=false]")


def add_side_windows(blocks, footprint, direction, height, glass, spacing=4):
    edge = edge_cells(footprint, direction)
    if not edge:
        return
    if direction in ("north","south"):
        base = min(x for x,_z in edge)
        for x,z in edge:
            if (x-base) % spacing in (1,2):
                for y in (1,2):
                    if y < height:
                        setb(blocks, x,y,z,glass)
    else:
        base = min(z for _x,z in edge)
        for x,z in edge:
            if (z-base) % spacing in (1,2):
                for y in (1,2):
                    if y < height:
                        setb(blocks,x,y,z,glass)


def build_visual_building(blocks: Dict[Cell3,str], footprint: Set[Cell2], entry: dict):
    if not footprint:
        return

    h = int(entry["height"])
    wall = entry["wall"]
    wall2 = entry.get("wall_secondary", wall)
    trim = entry["trim"]
    glass = entry["glass"]
    side = entry["side"]
    profile = entry["profile"]
    storeys = int(entry["storeys"])
    roof = "minecraft:polished_deepslate"
    boundary = boundary_cells(footprint)

    # Floor + roof.
    for x,z in footprint:
        setb(blocks,x,-1,z,wall)
        setb(blocks,x,h,z,roof)

    # Hollow perimeter.
    for x,z in boundary:
        for y in range(0,h):
            setb(blocks,x,y,z,wall)

    front = frontage_cells(footprint, side)
    if not front:
        return
    zs = sorted(set(z for _x,z in front))
    zmin,zmax = zs[0],zs[-1]
    span = max(1,zmax-zmin)
    bays = max(2,int(entry.get("bays",4)))
    bay_centers = spaced_positions(zs,bays)
    door_count = 2 if profile in ("paired_north_historic","wide_market","wide_low") else 1
    doors = set(spaced_positions(zs,door_count))
    facing = "west" if side=="east" else "east"
    street_dx = -1 if side=="east" else 1

    lower_door, upper_door = door_states(entry["door"], facing)

    # Profile-specific split, useful for Leo and paired storefronts.
    split = zmin + span * 0.67
    split_half = zmin + span * 0.50

    for x,z in front:
        # Main lower storefront.
        if z in doors:
            setb(blocks,x,0,z,wall)
            setb(blocks,x,1,z,lower_door)
            setb(blocks,x,2,z,upper_door)
        else:
            # Vertical supports at bay boundaries/centers.
            is_support = any(abs(z-c) <= 0 for c in bay_centers)
            lower_material = wall
            if profile=="leos_current" and z > split:
                lower_material = wall2
            elif profile=="paired_north_historic":
                lower_material = wall2 if z <= split_half else entry.get("wall_tertiary",wall2)

            setb(blocks,x,0,z,lower_material)
            for y in (1,2):
                setb(blocks,x,y,z, lower_material if is_support else glass)

        # Sign / transom zone.
        sign_y = 3
        if sign_y < h:
            sign_mat = trim
            if profile=="leos_current":
                sign_mat = "minecraft:black_concrete" if z <= split else wall2
            elif profile in ("modern_low","midcentury_low"):
                sign_mat = wall2
            elif profile=="paired_north_historic":
                sign_mat = wall2 if z <= split_half else entry.get("wall_tertiary",wall2)
            setb(blocks,x,sign_y,z,sign_mat)

        # Upper floors for historic/taller buildings.
        if storeys >= 2:
            for y in range(4,h-1):
                if y in (4,5,6):
                    nearest_bay = min(abs(z-c) for c in bay_centers)
                    if nearest_bay <= 1 and z not in doors:
                        setb(blocks,x,y,z,glass)
                    else:
                        setb(blocks,x,y,z,wall)
                else:
                    setb(blocks,x,y,z,wall)

        # Continuous top band.
        if h-1 >= 0:
            setb(blocks,x,h-1,z,trim)

    # Projecting awning.
    if entry.get("awning"):
        awn = slab_state(entry["awning"],"bottom")
        awn_y = 4 if h >= 7 else 3
        for x,z in front:
            if (z-zmin) % 1 == 0:
                setb(blocks,x+street_dx,awn_y,z,awn)

    # Window sills + cornice.
    sill = slab_state("minecraft:smooth_stone_slab","bottom")
    cornice = slab_state("minecraft:smooth_stone_slab","top")
    for x,z in front:
        if storeys >= 2 and any(abs(z-c)<=1 for c in bay_centers):
            setb(blocks,x+street_dx,4,z,sill)
        setb(blocks,x+street_dx,h,z,cornice)

    # Profile-specific silhouettes.
    if profile=="city_hall_bank":
        # Strong symmetrical civic front, heavier base, raised center parapet.
        center = nearest((zmin+zmax)/2,zs)
        for x,z in front:
            setb(blocks,x,0,z,"minecraft:stone_bricks")
            if abs(z-center) <= 1:
                for y in range(1,min(h,8)):
                    setb(blocks,x,y,z,"minecraft:smooth_sandstone" if y in (1,7) else glass)
                setb(blocks,x,h+1,z,"minecraft:chiseled_stone_bricks")
                setb(blocks,x,h+2,z,"minecraft:smooth_sandstone")
        add_side_windows(blocks,footprint,"north",h,glass,4)

    elif profile=="leos_current":
        # Photo-supported low facade with strong contrasting right-hand bay.
        add_side_windows(blocks,footprint,"south",h,glass,5)

    elif profile=="paired_north_historic":
        # Two apparent storefronts in one footprint, taller historic cornice.
        center = nearest((zmin+zmax)/2,zs)
        for x,z in front:
            if abs(z-center)<=1:
                for y in range(0,h):
                    setb(blocks,x,y,z,trim)
            if abs(z-center)<=2:
                setb(blocks,x+street_dx,h+1,z,stair_state("minecraft:brick_stairs",facing,"bottom"))
        add_side_windows(blocks,footprint,"north",h,glass,4)

    elif profile=="north_historic":
        # Decorative brick cap reminiscent of downtown historic fronts.
        for x,z in front:
            if any(abs(z-c)<=1 for c in bay_centers):
                setb(blocks,x,h+1,z,"minecraft:bricks")

    elif profile in ("modern_low","midcentury_low"):
        # Strong horizontal fascia, fewer historic cornice elements.
        for x,z in front:
            setb(blocks,x,h,z,wall2)

    # Corner side glazing for 603 New York Life.
    if profile=="modern_low":
        add_side_windows(blocks,footprint,"south",h,glass,5)


def build_rear(blocks, footprint, height, wall):
    boundary = boundary_cells(footprint)
    for x,z in footprint:
        setb(blocks,x,-1,z,wall)
        setb(blocks,x,height,z,"minecraft:deepslate_tiles")
    for x,z in boundary:
        for y in range(height):
            setb(blocks,x,y,z,wall)


def validate_ids(local, spec):
    geo_ids = {int(x["osm_id"]) for x in local["buildings"]}
    ids = {int(x["osm_id"]) for x in spec["entries"]} | {int(x["osm_id"]) for x in spec["secondary"]}
    if ids != geo_ids:
        raise ValueError(f"Visual spec coverage mismatch missing={sorted(geo_ids-ids)} extra={sorted(ids-geo_ids)}")


def self_test():
    # Validate property-bearing block state round-trip at generator level.
    fp = {(x,z) for x in range(3,11) for z in range(-8,-1)}
    entry = {
        "side":"east","profile":"historic_two_story","height":9,"storeys":2,
        "wall":"minecraft:bricks","wall_secondary":"minecraft:bricks",
        "trim":"minecraft:smooth_stone","glass":"minecraft:black_stained_glass",
        "door":"minecraft:dark_oak_door","awning":"minecraft:dark_oak_slab",
        "bays":4
    }
    blocks={}
    build_visual_building(blocks,fp,entry)
    assert any("dark_oak_door[" in s for s in blocks.values())
    assert any("slab[" in s for s in blocks.values())
    assert any(s=="minecraft:black_stained_glass" for s in blocks.values())
    print("L1_VISUAL_SELF_TEST_PASS",len(blocks))
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        return self_test()

    local=load_json(LOCAL_IN)
    frame=load_json(FRAME_IN)
    spec=load_json(SPEC_IN)
    policy=load_json(POLICY_IN)
    codec=load_codec()
    validate_ids(local,spec)

    geom={int(x["osm_id"]):x for x in local["buildings"]}
    blocks=build_ground(local,frame,policy)

    # Buildings overwrite sidewalks where source footprint reaches storefront line.
    model=[]
    primary_by_id={int(x["osm_id"]):x for x in spec["entries"]}
    for entry in spec["entries"]:
        oid=int(entry["osm_id"])
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        build_visual_building(blocks,fp,entry)
        model.append({
            "osm_id":oid,
            "addresses":entry["addresses"],
            "name":entry["name"],
            "profile":entry["profile"],
            "height":entry["height"],
            "storeys":entry["storeys"],
            "visual_confidence":entry["visual_confidence"],
            "footprint_cells":len(fp)
        })

    for rear in spec["secondary"]:
        oid=int(rear["osm_id"])
        parent=primary_by_id[int(rear["parent_osm_id"])]
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        build_rear(blocks,fp,int(rear["height"]),parent["wall"])
        model.append({
            "osm_id":oid,
            "parent_osm_id":rear["parent_osm_id"],
            "profile":"rear_addition",
            "height":rear["height"],
            "visual_confidence":"inferred",
            "footprint_cells":len(fp)
        })

    add_streetscape(blocks,policy)

    ref=frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])
    schematic={(x-ref_x,y,z-ref_z):state for (x,y,z),state in blocks.items()}
    marker=tuple(policy["registration"]["marker_schematic"])
    marker_block=policy["registration"]["marker_block"]
    schematic[marker]=marker_block

    pb=frame["plan_bounds_blocks"]
    min_x,max_x=int(pb["min_x"])-ref_x,int(pb["max_x"])-ref_x
    min_z,max_z=int(pb["min_z"])-ref_z,int(pb["max_z"])-ref_z
    max_y=max(y for _x,y,_z in schematic)

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    info=codec.write_single_region_litematic(
        OUT_FILE, schematic, (min_x,-1,min_z,max_x,max_y,max_z),
        "REDFIELD_POC_001_L1_VISUAL_V004",
        "Redfield POC 001 - L1 Visual v004",
        "Normal-block visual reconstruction with stateful details, streetscape and partial photo support. No Microblocks.",
        4903,6,1
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_POC_001_L1_VISUAL_V004")
    normalized={c:codec.canonical_state(s) for c,s in schematic.items()}
    exact=back==normalized
    marker_ok=back.get(marker)==marker_block
    if not exact:
        # compact diagnostic only
        missing=set(normalized.items())-set(back.items())
        extra=set(back.items())-set(normalized.items())
        raise ValueError(f"Read-back mismatch missing={len(missing)} extra={len(extra)}")
    if not marker_ok:
        raise ValueError("Registration marker failed")

    MODEL_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":policy["export_id"],
        "entries":model,
        "all_facades_photo_verified":False
    },indent=2)+"\n",encoding="utf-8")

    confidence={}
    for x in spec["entries"]:
        confidence[x["visual_confidence"]]=confidence.get(x["visual_confidence"],0)+1

    report={
        "schema_version":1,
        "export_id":policy["export_id"],
        "status":"valid",
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "non_air_blocks":info["non_air_blocks"],
        "palette_size":len(info["palette"]),
        "stateful_palette_entries":sum(1 for s in info["palette"] if "[" in s),
        "visual_confidence_counts":confidence,
        "primary_sites":len(spec["entries"]),
        "secondary_structures":len(spec["secondary"]),
        "streetscape":{
            "streetlights":policy["streetscape"]["streetlights"],
            "planters":policy["streetscape"]["planters"],
            "benches":policy["streetscape"]["benches"],
            "parking_markings":policy["roads"]["parking_markings"]
        },
        "registration":{
            "marker_position":list(marker),
            "marker_block":marker_block,
            "verified":marker_ok
        },
        "checks":{
            "visual_spec_covers_geometry":True,
            "exact_block_map":exact,
            "registration_marker":marker_ok,
            "block_states_round_trip":True,
            "microblocks_used":False
        },
        "errors":[]
    }
    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    MANIFEST_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":policy["export_id"],
        "file":report["file"],
        "sha256":report["sha256"],
        "region_position":report["region_position"],
        "region_size":report["region_size"],
        "placement":{
            "instruction":"Stand on the existing yellow registration block and set placement origin to player feet.",
            "rotation":0,"mirror":"none","replace_blocks":"ALL"
        },
        "review_targets":[
            "Leo facade resemblance",
            "north historic storefront rhythm",
            "City Hall civic silhouette",
            "road and parking proportions",
            "streetlight/planter scale",
            "which remaining facades need direct Street View correction"
        ]
    },indent=2)+"\n",encoding="utf-8")

    print("EarthForge Redfield POC 001 L1 Visual v004 generated and validated.")
    print(f"  File                : {report['file']}")
    print(f"  SHA256              : {report['sha256']}")
    print(f"  Region pos          : {report['region_position']}")
    print(f"  Region size         : {report['region_size']}")
    print(f"  Non-air blocks      : {report['non_air_blocks']}")
    print(f"  Palette size        : {report['palette_size']}")
    print(f"  Stateful palette    : {report['stateful_palette_entries']}")
    print(f"  Photo-supported     : {confidence.get('photo_supported',0)}")
    print(f"  History-supported   : {confidence.get('history_supported',0)}")
    print(f"  Inferred            : {confidence.get('inferred',0)}")
    print(f"  Marker              : {list(marker)} {marker_block}")
    print("  Read-back           : PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
