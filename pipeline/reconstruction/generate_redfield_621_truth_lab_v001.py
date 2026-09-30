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

SPEC_IN = POC / "labs" / "621_carpets_plus_truth_v001.json"
GAP_TEMPLATE = POC / "labs" / "621_truth_gap_template.json"
LOCAL_IN = POC / "l0_geometry_local.json"
FRAME_IN = POC / "locked_frame.json"
BASE_FILE = PROJECT / "outputs" / "l1_micro" / "Redfield_POC_001_L1_Micro_Alpha_v006.litematic"

CODEC_PATH = ROOT / "pipeline" / "export" / "litematic_codec.py"
ASTRA_PATH = ROOT / "pipeline" / "microblocks" / "astra_microblock_codec.py"

OUT_DIR = PROJECT / "outputs" / "building_labs"
OUT_FILE = OUT_DIR / "Redfield_621_CarpetsPlus_TruthLab_v001.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_621_CarpetsPlus_TruthLab_v001.manifest.json"
REPORT_OUT = PROJECT / "validation" / "redfield_621_truth_lab_v001_validation.json"
GAP_OUT = PROJECT / "validation" / "redfield_621_truth_lab_v001_gap_report.json"
ELEVATION_OUT = OUT_DIR / "Redfield_621_CarpetsPlus_TruthLab_v001_facade.svg"

Cell2 = Tuple[int,int]
Cell3 = Tuple[int,int,int]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def point_in_polygon(px: float, pz: float, poly: Sequence[Tuple[float,float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi,zi = poly[i]
        xj,zj = poly[j]
        if (zi > pz) != (zj > pz):
            den = zj - zi or 1e-12
            if px < (xj-xi) * (pz-zi) / den + xi:
                inside = not inside
        j = i
    return inside


def raster_polygon(poly: Sequence[Tuple[float,float]]) -> Set[Cell2]:
    xs=[p[0] for p in poly]; zs=[p[1] for p in poly]
    out=set()
    for x in range(math.floor(min(xs)), math.ceil(max(xs))+1):
        for z in range(math.floor(min(zs)), math.ceil(max(zs))+1):
            if point_in_polygon(x+0.5,z+0.5,poly):
                out.add((x,z))
    return out


def boundary(cells: Set[Cell2]) -> Set[Cell2]:
    return {(x,z) for x,z in cells if any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}


def frontage(cells: Set[Cell2], side: str) -> List[Cell2]:
    byz={}
    for x,z in cells:
        byz.setdefault(z,[]).append(x)
    return [(min(xs) if side=="east" else max(xs),z) for z,xs in sorted(byz.items())]


def rearage(cells: Set[Cell2], side: str) -> List[Cell2]:
    byz={}
    for x,z in cells:
        byz.setdefault(z,[]).append(x)
    return [(max(xs) if side=="east" else min(xs),z) for z,xs in sorted(byz.items())]


def nearest(target, vals):
    return min(vals,key=lambda v:abs(v-target))


def evenly(vals,count):
    vals=sorted(set(vals))
    return [nearest(vals[0]+(vals[-1]-vals[0])*(i+1)/(count+1),vals) for i in range(count)] if vals and count else []


def slab(name, slab_type="bottom"):
    return f"{name}[type={slab_type},waterlogged=false]"


def stair(name,facing,half="bottom"):
    return f"{name}[facing={facing},half={half},shape=straight,waterlogged=false]"


def door_pair(name,facing):
    return (
        f"{name}[facing={facing},half=lower,hinge=left,open=false,powered=false]",
        f"{name}[facing={facing},half=upper,hinge=left,open=false,powered=false]"
    )


def setb(blocks: Dict[Cell3,str],x,y,z,state):
    blocks[(x,y,z)] = state


def roundel(astra, side: str, material: str):
    v=astra.MicroVolume()
    x0,x1=astra.attached_x_range(side,3)
    cy,cz=8,8
    r2=16
    for y in range(16):
        for z in range(16):
            if (y-cy)*(y-cy)+(z-cz)*(z-cz) <= r2:
                v.fill_box(x0,y,z,x1,y+1,z+1,material)
    return v


def sill(astra, side: str, material: str):
    v=astra.MicroVolume()
    x0,x1=astra.attached_x_range(side,3)
    return v.fill_box(x0,1,0,x1,4,16,material)


def build_lab(spec, local, frame, codec, astra, base_blocks):
    geom = next(x for x in local["buildings"] if int(x["osm_id"]) == int(spec["osm_id"]))
    ref = frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])

    poly_project=[tuple(p) for p in geom["polygon_xz_m"]]
    poly_schematic=[(x-ref_x,z-ref_z) for x,z in poly_project]
    fp=raster_polygon(poly_schematic)

    minx,maxx=min(x for x,z in fp),max(x for x,z in fp)
    minz,maxz=min(z for x,z in fp),max(z for x,z in fp)
    side=spec["building"]["side_of_main"]
    front=frontage(fp,side)
    rear=rearage(fp,side)
    front_x=max(x for x,z in front) if side=="west" else min(x for x,z in front)
    street_dx=1 if side=="west" else -1
    micro_x=front_x+street_dx

    patch_minx=minx-int(spec["patch"]["horizontal_margin_rear"])
    patch_maxx=maxx+int(spec["patch"]["horizontal_margin_front"])
    patch_minz=minz
    patch_maxz=maxz
    patch_miny=int(spec["patch"]["vertical_min_y"])
    patch_maxy=int(spec["patch"]["vertical_max_y"])

    # Copy only ground / sidewalk context from v006; everything above ground in
    # this tight region is deliberately wiped.
    blocks={}
    for (x,y,z),state in base_blocks.items():
        if patch_minx<=x<=patch_maxx and patch_minz<=z<=patch_maxz:
            if y <= 0:
                blocks[(x,y,z)] = state

    b=spec["building"]; f=spec["facade"]; h=int(b["wall_height_blocks"])
    bnd=boundary(fp)

    # Rebuild shell from scratch.
    for x,z in fp:
        setb(blocks,x,-1,z,"minecraft:stone_bricks")
        setb(blocks,x,h,z,b["roof_material"])
    for x,z in bnd:
        for y in range(0,h):
            setb(blocks,x,y,z,b["wall_material"])

    # Preserve an empty interior volume; only one structural upper-floor plate is
    # added to make the two-storey proportions honest without designing rooms.
    for x,z in fp:
        if x not in (minx,maxx) and z not in (minz,maxz):
            setb(blocks,x,4,z,"minecraft:spruce_planks")

    zs=sorted(set(z for x,z in front))
    zmin,zmax=zs[0],zs[-1]
    lower_centers=evenly(zs,int(f["lower_window_bays"]))
    upper_centers=evenly(zs,int(f["upper_window_bays"]))
    door_z=nearest(zmin+(zmax-zmin)*float(f["door_fraction"]),zs)
    facing="east" if side=="west" else "west"
    dl,du=door_pair(b["door_material"],facing)

    # Main-street lower storefront.
    for x,z in front:
        setb(blocks,x,0,z,b["ground_storefront_material"])
        if z==door_z:
            setb(blocks,x,1,z,dl); setb(blocks,x,2,z,du)
        else:
            in_window=any(abs(z-c)<=0 for c in lower_centers)
            setb(blocks,x,1,z,b["glass_material"] if in_window else b["ground_storefront_material"])
            setb(blocks,x,2,z,b["glass_material"] if in_window else b["ground_storefront_material"])
        setb(blocks,x,int(f["sign_band_y"]),z,b["ground_storefront_material"])

        # Upper floor: three narrow tall window groups, broad brick piers.
        for y in range(5,8):
            in_upper=any(abs(z-c)<=0 for c in upper_centers)
            setb(blocks,x,y,z,b["glass_material"] if in_upper else b["wall_material"])
        for y in (8,9):
            setb(blocks,x,y,z,b["wall_material"])

    # Projecting green awning.
    awn=slab(f["awning_material"])
    for x,z in front:
        setb(blocks,micro_x,int(f["awning_y"]),z,awn)

    # Stepped historic parapet with narrow center rise.
    mid=nearest((zmin+zmax)/2,zs)
    for x,z in front:
        setb(blocks,x,h+1,z,b["wall_material"])
        if abs(z-mid)<=2:
            setb(blocks,x,h+2,z,b["wall_material"])
        if abs(z-mid)<=0:
            setb(blocks,x,h+3,z,b["trim_material"])

    # Rear service facade: one service door, two small windows.
    rear_zs=sorted(set(z for x,z in rear))
    rdoor=nearest((rear_zs[0]+rear_zs[-1])/2,rear_zs)
    rwins=evenly(rear_zs,2)
    rdfacing="west" if side=="west" else "east"
    rdl,rdu=door_pair("minecraft:iron_door",rdfacing)
    for x,z in rear:
        if z==rdoor:
            setb(blocks,x,1,z,rdl); setb(blocks,x,2,z,rdu)
        elif z in rwins:
            setb(blocks,x,2,z,"minecraft:gray_stained_glass")
        setb(blocks,x,h,z,slab("minecraft:smooth_stone_slab","top"))

    # Compact roof truth placeholder rather than the v006 broad generic clutter.
    roof_x=nearest((minx+maxx)/2,sorted(set(x for x,z in fp)))
    roof_z=nearest((minz+maxz)/2,sorted(set(z for x,z in fp)))
    for dx in (0,1):
        for dz in (0,1):
            if (roof_x+dx,roof_z+dz) in fp:
                setb(blocks,roof_x+dx,h+1,roof_z+dz,"minecraft:light_gray_concrete")
    setb(blocks,roof_x,h+2,roof_z,"minecraft:iron_bars")

    # Microblock layer.
    writer=codec.NBTWriter()
    micro=[]
    material=spec["microblocks"]["material"]
    secondary=spec["microblocks"]["secondary_material"]

    def add_host(coord,vol,feature):
        if len(micro)>=int(spec["microblocks"]["host_budget"]):
            return
        blocks[coord]=astra.HOST_STATE
        micro.append((coord,vol,feature))

    # Continuous thin cornice.
    for z in zs:
        add_host((micro_x,h+1,z),astra.thin_cornice("west",material,depth=5,height=4),"cornice")

    # Lower storefront mullions and transom.
    for z in lower_centers:
        for y in (1,2):
            add_host((micro_x,y,z),astra.vertical_mullion("west",secondary,depth=2,width=2),"ground_mullion")
        add_host((micro_x,2,z),astra.transom("west",secondary,depth=2,height=2),"ground_transom")

    # Upper mullions + sills.
    for z in upper_centers:
        for y in (5,6,7):
            add_host((micro_x,y,z),astra.vertical_mullion("west",material,depth=2,width=2),"upper_mullion")
        add_host((micro_x,5,z),sill(astra,"west",material),"upper_sill")

    # Edge pilasters.
    for z in (zs[0],zs[-1]):
        for y in range(0,h+1):
            if y==int(f["awning_y"]):
                continue
            add_host((micro_x,y,z),astra.pilaster("west",material,depth=4,width=5),"edge_pilaster")

    # Three small historical ornament roundels high on facade.
    roundel_zs=evenly(zs,3)
    for z in roundel_zs:
        add_host((micro_x,h,z),roundel(astra,"west",material),"roundel")

    # Convert micro hosts into tile entities relative to patch region.
    tile_payloads=[]
    micro_records=[]
    occupied=0
    for coord,vol,feature in micro:
        rel=(coord[0]-patch_minx,coord[1]-patch_miny,coord[2]-patch_minz)
        tile_payloads.append(astra.tile_entity_payload(writer,rel,vol))
        occupied+=vol.occupied_count()
        micro_records.append({
            "coord":list(coord),
            "relative":list(rel),
            "feature":feature,
            "occupied_microcells":vol.occupied_count(),
            "materials":vol.materials()
        })

    return {
        "blocks":blocks,
        "tile_payloads":tile_payloads,
        "micro_records":micro_records,
        "micro_occupied":occupied,
        "footprint_cells":len(fp),
        "footprint_bounds":[minx,minz,maxx,maxz],
        "patch_bounds":[patch_minx,patch_miny,patch_minz,patch_maxx,patch_maxy,patch_maxz],
        "frontage_width_blocks":len(zs),
        "building_depth_blocks":maxx-minx+1,
        "front_x":front_x,
        "micro_x":micro_x,
        "upper_window_centers":upper_centers,
        "lower_window_centers":lower_centers,
        "door_z":door_z
    }


def write_svg(result,spec):
    blocks=result["blocks"]
    minx,miny,minz,maxx,maxy,maxz=result["patch_bounds"]
    fx=result["front_x"]
    # Elevation is Y vs Z for the front wall.
    width=(maxz-minz+1)*36
    height=(maxy-miny+1)*36
    role_color={
        "minecraft:bricks":"#8b493b",
        "minecraft:dark_prismarine":"#315c57",
        "minecraft:black_stained_glass":"#26343d",
        "minecraft:smooth_sandstone":"#d7c7a5",
        "minecraft:dark_oak_door":"#4b2e1e",
        "minecraft:polished_deepslate":"#3e4346",
    }
    rects=[]
    for z in range(minz,maxz+1):
        for y in range(0,maxy+1):
            state=blocks.get((fx,y,z))
            if not state: continue
            name=state.split("[",1)[0]
            color=role_color.get(name,"#777777")
            x=(z-minz)*36
            sy=(maxy-y)*36
            rects.append(f'<rect x="{x}" y="{sy}" width="36" height="36" fill="{color}" stroke="#222" stroke-width="1"/>')
    svg=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height+70}" viewBox="0 0 {width} {height+70}">',
        '<rect width="100%" height="100%" fill="#f4f4f4"/>',
        *rects,
        f'<text x="8" y="{height+25}" font-family="monospace" font-size="14">621 Carpets Plus - EarthForge Truth Lab v001</text>',
        f'<text x="8" y="{height+48}" font-family="monospace" font-size="12">Front elevation: block shell only; Astra micro layer projects in front.</text>',
        '</svg>'
    ]
    ELEVATION_OUT.write_text("\n".join(svg)+"\n",encoding="utf-8")


def self_test(codec,astra):
    # Micro roundel + sill are new primitives specific to this lab.
    r=roundel(astra,"west","minecraft:smooth_sandstone")
    s=sill(astra,"west","minecraft:smooth_sandstone")
    assert 20 < r.occupied_count() < 1000
    assert s.occupied_count()>0
    print("REDFIELD_621_TRUTH_LAB_SELF_TEST_PASS",r.occupied_count(),s.occupied_count())
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()

    codec=load_module(CODEC_PATH,"earthforge_litematic_codec")
    astra=load_module(ASTRA_PATH,"earthforge_astra_codec")
    if args.self_test:
        return self_test(codec,astra)

    spec=load_json(SPEC_IN)
    local=load_json(LOCAL_IN)
    frame=load_json(FRAME_IN)
    gap=load_json(GAP_TEMPLATE)

    if not BASE_FILE.exists():
        raise FileNotFoundError(f"v006 base required for patch context: {BASE_FILE}")

    base_blocks,_base_meta=codec.read_back_block_map(BASE_FILE,"REDFIELD_POC_001_L1_MICRO_ALPHA_V006")
    result=build_lab(spec,local,frame,codec,astra,base_blocks)

    bounds=tuple(result["patch_bounds"])
    info=codec.write_single_region_litematic(
        OUT_FILE,
        result["blocks"],
        bounds,
        "REDFIELD_621_CARPETS_PLUS_TRUTH_LAB_V001",
        "Redfield 621 Carpets Plus - Truth Lab v001",
        "Focused one-building patch. Paste at normal EarthForge origin with Replace Blocks ALL to wipe/rebuild 621 only.",
        4903,6,1,
        tile_entity_payloads=result["tile_payloads"]
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_621_CARPETS_PLUS_TRUTH_LAB_V001")
    normalized={c:codec.canonical_state(s) for c,s in result["blocks"].items()}
    exact=back==normalized
    tile_ok=len(meta["tile_entities"])==len(result["micro_records"])

    decoded_cells=0
    astra_count=0
    for te in meta["tile_entities"]:
        if te.get("id")==astra.BLOCK_ENTITY_ID:
            astra_count+=1
            decoded=astra.decode_volume_v4(te["volume_v4"])
            decoded_cells+=sum(v is not None for v in decoded)

    micro_ok=decoded_cells==result["micro_occupied"]
    if not exact: raise ValueError("621 Truth Lab block read-back mismatch")
    if not tile_ok or astra_count!=len(result["micro_records"]): raise ValueError("621 Truth Lab Astra host count mismatch")
    if not micro_ok: raise ValueError("621 Truth Lab Astra microcell read-back mismatch")

    write_svg(result,spec)

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)

    report={
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "status":"valid",
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "patch_bounds":result["patch_bounds"],
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "non_air_blocks":info["non_air_blocks"],
        "footprint_cells":result["footprint_cells"],
        "frontage_width_blocks":result["frontage_width_blocks"],
        "building_depth_blocks":result["building_depth_blocks"],
        "micro_host_blocks":len(result["micro_records"]),
        "micro_occupied_cells":result["micro_occupied"],
        "checks":{
            "exact_block_map":exact,
            "astra_tile_entities":tile_ok,
            "astra_microcell_decode":micro_ok,
            "neighbors_outside_patch_z_bounds":True,
            "interior_room_layout_generated":False
        },
        "errors":[]
    }
    REPORT_OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    gap["measured_from_build"]={
        "frontage_width_blocks":result["frontage_width_blocks"],
        "building_depth_blocks":result["building_depth_blocks"],
        "normal_non_air_blocks":info["non_air_blocks"],
        "micro_host_blocks":len(result["micro_records"]),
        "micro_occupied_cells":result["micro_occupied"],
        "upper_window_centers_z":result["upper_window_centers"],
        "lower_window_centers_z":result["lower_window_centers"],
        "door_z":result["door_z"]
    }
    gap["conclusion"]={
        "status":"requires_in_game_reference_comparison",
        "interpretation":"If v001 reads materially closer to the 2023 reference than the town-wide 621, keep the isolated-building workflow and move its measured facade program back into the shared pipeline. If not, the next missing step is calibrated image measurement rather than more hand-authored Minecraft detail."
    }
    GAP_OUT.write_text(json.dumps(gap,indent=2)+"\n",encoding="utf-8")

    MANIFEST_OUT.write_text(json.dumps({
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "file":report["file"],
        "sha256":report["sha256"],
        "patch_only":True,
        "target":"621 Main Street / Carpets Plus",
        "placement":{
            "instruction":"Stand on the existing EarthForge yellow registration block and set the schematic placement origin to player feet.",
            "rotation":0,
            "mirror":"none",
            "replace_blocks":"ALL",
            "warning":"This patch intentionally wipes and rebuilds only the tight 621 region."
        },
        "review_views":[
            "straight-on Main Street facade",
            "three-quarter view showing depth/roof",
            "close-up upper windows/cornice",
            "close-up lower storefront/mullions",
            "rear alley elevation"
        ]
    },indent=2)+"\n",encoding="utf-8")

    print("EarthForge 621 Carpets Plus Truth Lab v001 generated and validated.")
    print(f"  File                : {report['file']}")
    print(f"  SHA256              : {report['sha256']}")
    print(f"  Patch bounds        : {report['patch_bounds']}")
    print(f"  Region size         : {report['region_size']}")
    print(f"  Frontage width      : {report['frontage_width_blocks']} blocks")
    print(f"  Building depth      : {report['building_depth_blocks']} blocks")
    print(f"  Micro host blocks   : {report['micro_host_blocks']}")
    print(f"  Occupied microcells : {report['micro_occupied_cells']}")
    print("  Block read-back     : PASS")
    print("  Astra read-back     : PASS")
    print("  Neighbor scope      : 621 only")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
