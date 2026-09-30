#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Dict, Sequence, Set, Tuple

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"redfield_sd"
POC=PROJECT/"poc_001"

SPEC_IN=POC/"labs"/"621_micro_only_v002.json"
LOCAL_IN=POC/"l0_geometry_local.json"
FRAME_IN=POC/"locked_frame.json"
BASE_FILE=PROJECT/"outputs"/"l1_micro"/"Redfield_POC_001_L1_Micro_Alpha_v006.litematic"

CODEC_PATH=ROOT/"pipeline"/"export"/"litematic_codec.py"
ASTRA_PATH=ROOT/"pipeline"/"microblocks"/"astra_microblock_codec.py"
ARCH_PATH=ROOT/"pipeline"/"microblocks"/"micro_architecture.py"

OUT_DIR=PROJECT/"outputs"/"building_labs"
OUT_FILE=OUT_DIR/"Redfield_621_MicroOnly_v002.litematic"
MANIFEST_OUT=OUT_DIR/"Redfield_621_MicroOnly_v002.manifest.json"
REPORT_OUT=PROJECT/"validation"/"redfield_621_micro_only_v002_validation.json"
HOSTMAP_OUT=POC/"labs"/"621_micro_only_v002_hosts.json"

Cell2=Tuple[int,int]
Cell3=Tuple[int,int,int]


def load_json(p): return json.loads(p.read_text(encoding="utf-8"))


def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def point_in_polygon(px,pz,poly):
    inside=False
    j=len(poly)-1
    for i in range(len(poly)):
        xi,zi=poly[i]; xj,zj=poly[j]
        if (zi>pz)!=(zj>pz):
            den=zj-zi or 1e-12
            if px < (xj-xi)*(pz-zi)/den + xi: inside=not inside
        j=i
    return inside


def raster_polygon(poly: Sequence[Tuple[float,float]]) -> Set[Cell2]:
    xs=[p[0] for p in poly]; zs=[p[1] for p in poly]
    out=set()
    for x in range(math.floor(min(xs)),math.ceil(max(xs))+1):
        for z in range(math.floor(min(zs)),math.ceil(max(zs))+1):
            if point_in_polygon(x+0.5,z+0.5,poly):
                out.add((x,z))
    return out


def boundary_faces(fp:Set[Cell2],cell:Cell2):
    x,z=cell
    faces=[]
    if (x+1,z) not in fp: faces.append("east")
    if (x-1,z) not in fp: faces.append("west")
    if (x,z+1) not in fp: faces.append("south")
    if (x,z-1) not in fp: faces.append("north")
    return faces


def frontage(fp:Set[Cell2]):
    byz={}
    for x,z in fp: byz.setdefault(z,[]).append(x)
    return [(max(xs),z) for z,xs in sorted(byz.items())]


def rearage(fp:Set[Cell2]):
    byz={}
    for x,z in fp: byz.setdefault(z,[]).append(x)
    return [(min(xs),z) for z,xs in sorted(byz.items())]


def nearest(target,vals):
    return min(vals,key=lambda v:abs(v-target))


def merge_at(volumes,coord,vol,arch):
    if coord not in volumes:
        volumes[coord]=arch.empty(astra)
    arch.merge(volumes[coord],vol,overwrite=True)


def self_test(codec,astra,arch):
    v=arch.storefront_window(astra,"minecraft:green_concrete","minecraft:smooth_sandstone",False)
    assert 0 < v.occupied_count() < 4096
    assert "minecraft:green_concrete" in v.materials()
    assert not any("glass" in m for m in v.materials())
    d=arch.door_panel(astra,"minecraft:dark_oak_planks","minecraft:smooth_sandstone","minecraft:gold_block","lower")
    assert d.occupied_count()>0
    print("MICRO_ONLY_621_SELF_TEST_PASS",v.occupied_count(),d.occupied_count())
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()

    global astra
    codec=load_module(CODEC_PATH,"ef_codec")
    astra=load_module(ASTRA_PATH,"ef_astra")
    arch=load_module(ARCH_PATH,"ef_arch")

    if args.self_test:
        return self_test(codec,astra,arch)

    spec=load_json(SPEC_IN)
    local=load_json(LOCAL_IN)
    frame=load_json(FRAME_IN)

    if not BASE_FILE.exists():
        raise FileNotFoundError(f"Required base context missing: {BASE_FILE}")

    base,_=codec.read_back_block_map(BASE_FILE,"REDFIELD_POC_001_L1_MICRO_ALPHA_V006")

    geom=next(x for x in local["buildings"] if int(x["osm_id"])==int(spec["osm_id"]))
    ref=frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])

    poly=[(x-ref_x,z-ref_z) for x,z in geom["polygon_xz_m"]]
    fp=raster_polygon(poly)
    minx,maxx=min(x for x,z in fp),max(x for x,z in fp)
    minz,maxz=min(z for x,z in fp),max(z for x,z in fp)
    front=frontage(fp)
    rear=rearage(fp)
    front_x=max(x for x,z in front)
    external_x=front_x+1
    zs=sorted(set(z for x,z in front))

    # Tight patch with one block in front for awning/cornice projection.
    patch=(minx-1,-1,minz,maxx+2,12,maxz)
    pminx,pminy,pminz,pmaxx,pmaxy,pmaxz=patch

    # Copy only sub-ground / surrounding ground context.
    blocks={}
    for (x,y,z),state in base.items():
        if pminx<=x<=pmaxx and pminz<=z<=pmaxz:
            if y<0 or (y==0 and (x,z) not in fp):
                blocks[(x,y,z)]=state

    volumes={}
    m=spec["materials"]
    mc=spec["micro"]
    wall_t=int(mc["wall_thickness_cells"])
    floor_t=int(mc["floor_thickness_cells"])
    roof_t=int(mc["roof_thickness_cells"])

    # Structural floor skins and exterior shell.
    for x,z in fp:
        merge_at(volumes,(x,0,z),arch.floor_skin(astra,m["floor"],floor_t,top=False),arch)
        merge_at(volumes,(x,4,z),arch.floor_skin(astra,m["floor"],floor_t,top=False),arch)
        merge_at(volumes,(x,9,z),arch.roof_skin(astra,m["roof"],roof_t),arch)

        for face in boundary_faces(fp,(x,z)):
            # Main facade is authored separately.
            if face=="east":
                continue
            for y in range(0,9):
                merge_at(volumes,(x,y,z),arch.face_panel(astra,face,m["brick"],wall_t),arch)

    # Rear service details override/augment west skin.
    rear_zs=sorted(set(z for x,z in rear))
    rdoor=nearest((rear_zs[0]+rear_zs[-1])/2,rear_zs)
    rw1=rear_zs[max(0,len(rear_zs)//4)]
    rw2=rear_zs[min(len(rear_zs)-1,(3*len(rear_zs))//4)]
    for x,z in rear:
        if z==rdoor:
            merge_at(volumes,(x,1,z),arch.rear_door(astra,m["door"],m["trim"]),arch)
            merge_at(volumes,(x,2,z),arch.rear_door(astra,m["door"],m["trim"]),arch)
        elif z in (rw1,rw2):
            merge_at(volumes,(x,2,z),arch.rear_window(astra,m["brick"],m["trim"]),arch)

    # Main facade 8-block program.
    idx={z:i for i,z in enumerate(zs)}
    corner=set(spec["facade"]["storefront_pattern"]["corner_columns"])
    left=set(spec["facade"]["storefront_pattern"]["left_window"])
    doors=set(spec["facade"]["storefront_pattern"]["door"])
    right=set(spec["facade"]["storefront_pattern"]["right_window"])

    # y0 storefront base.
    for x,z in front:
        i=idx[z]
        if i in corner:
            merge_at(volumes,(x,0,z),arch.thin_front_panel(astra,m["green"],5),arch)
            merge_at(volumes,(x,0,z),arch.face_panel(astra,"east",m["trim"],2),arch)
        else:
            merge_at(volumes,(x,0,z),arch.thin_front_panel(astra,m["green"],4),arch)

    # Storefront openings y1-y2; NO GLASS.
    for x,z in front:
        i=idx[z]
        if i in corner:
            merge_at(volumes,(x,1,z),arch.face_panel(astra,"east",m["green"],5),arch)
            merge_at(volumes,(x,2,z),arch.face_panel(astra,"east",m["green"],5),arch)
        elif i in doors:
            merge_at(volumes,(x,1,z),arch.door_panel(astra,m["door"],m["trim"],m["handle"],"lower"),arch)
            merge_at(volumes,(x,2,z),arch.door_panel(astra,m["door"],m["trim"],m["handle"],"upper"),arch)
        elif i in left or i in right:
            merge_at(volumes,(x,1,z),arch.storefront_window(astra,m["green"],m["trim"],False,4),arch)
            merge_at(volumes,(x,2,z),arch.storefront_window(astra,m["green"],m["trim"],False,4),arch)

    # Sign band y3.
    for x,z in front:
        merge_at(volumes,(x,3,z),arch.sign_band(astra,m["green"],m["trim"]),arch)

    # Transition / upper floor y4.
    for x,z in front:
        merge_at(volumes,(x,4,z),arch.face_panel(astra,"east",m["brick"],wall_t),arch)

    # Three tall upper window openings at chosen block columns.
    window_indices=set(spec["facade"]["upper_windows"])
    for x,z in front:
        i=idx[z]
        if i in window_indices:
            merge_at(volumes,(x,5,z),arch.frame_segment(astra,m["trim"],"bottom",3,2,m["metal"]),arch)
            merge_at(volumes,(x,6,z),arch.frame_segment(astra,m["trim"],"full",3,2,m["metal"]),arch)
            merge_at(volumes,(x,7,z),arch.frame_segment(astra,m["trim"],"top",3,2,m["metal"]),arch)
        else:
            for y in (5,6,7):
                merge_at(volumes,(x,y,z),arch.face_panel(astra,"east",m["brick"],wall_t),arch)

    # Cornice y8.
    for x,z in front:
        merge_at(volumes,(x,8,z),arch.cornice(astra,m["brick"],m["trim"]),arch)

    # Brackets every other facade block, projected in front.
    for z in zs[::2]:
        merge_at(volumes,(external_x,8,z),arch.bracket(astra,m["trim"]),arch)

    # Awning across storefront.
    for z in zs:
        merge_at(volumes,(external_x,4,z),arch.awning(astra,m["green"],m["trim"],int(mc["awning_depth_cells"])),arch)

    # Parapet y9-y11.
    mid=(len(zs)-1)/2
    for x,z in front:
        i=idx[z]
        panel=arch.roundel_panel(astra,m["brick"],m["trim"]) if i in (0,7) else arch.parapet_panel(astra,m["brick"],m["trim"],True)
        merge_at(volumes,(x,9,z),panel,arch)

        if 1 <= i <= 6:
            merge_at(volumes,(x,10,z),arch.parapet_panel(astra,m["brick"],m["trim"],True),arch)
        if i in (3,4):
            merge_at(volumes,(x,11,z),arch.parapet_panel(astra,m["brick"],m["trim"],True),arch)

    if len(volumes)>int(mc["host_budget"]):
        raise ValueError(f"Host budget exceeded: {len(volumes)} > {mc['host_budget']}")

    # No building block above ground may be vanilla.
    for coord,vol in volumes.items():
        blocks[coord]=astra.HOST_STATE

    writer=codec.NBTWriter()
    tile_payloads=[]
    host_records=[]
    total_cells=0
    materials=set()

    for coord in sorted(volumes):
        vol=volumes[coord]
        rel=(coord[0]-pminx,coord[1]-pminy,coord[2]-pminz)
        tile_payloads.append(astra.tile_entity_payload(writer,rel,vol))
        total_cells+=vol.occupied_count()
        materials.update(vol.materials())
        host_records.append({
            "coord":list(coord),
            "relative":list(rel),
            "occupied_microcells":vol.occupied_count(),
            "materials":vol.materials()
        })

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    info=codec.write_single_region_litematic(
        OUT_FILE,
        blocks,
        patch,
        "REDFIELD_621_MICRO_ONLY_V002",
        "Redfield 621 - Micro Only v002",
        "Astra-only building envelope and facade. No glass. Patch uses normal EarthForge global origin.",
        4903,6,1,
        tile_entity_payloads=tile_payloads
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_621_MICRO_ONLY_V002")
    normalized={c:codec.canonical_state(s) for c,s in blocks.items()}
    exact=back==normalized

    decoded=0
    astra_count=0
    for te in meta["tile_entities"]:
        if te.get("id")==astra.BLOCK_ENTITY_ID:
            astra_count+=1
            cells=astra.decode_volume_v4(te["volume_v4"])
            decoded+=sum(v is not None for v in cells)

    micro_ok=(astra_count==len(volumes) and decoded==total_cells)
    no_glass=not any("glass" in mat for mat in materials)
    vanilla_building_above_ground=0
    for (x,y,z),state in blocks.items():
        if y>0 and pminx<=x<=pmaxx and pminz<=z<=pmaxz and state!=astra.HOST_STATE:
            vanilla_building_above_ground+=1

    if not exact: raise ValueError("Micro-only patch block read-back mismatch")
    if not micro_ok: raise ValueError("Micro-only Astra volume read-back mismatch")
    if not no_glass: raise ValueError("Glass material found in micro-only palette")
    if vanilla_building_above_ground!=0: raise ValueError("Vanilla blocks remain above ground in micro-only building")

    HOSTMAP_OUT.parent.mkdir(parents=True,exist_ok=True)
    HOSTMAP_OUT.write_text(json.dumps({
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "host_count":len(volumes),
        "occupied_microcells":total_cells,
        "materials":sorted(materials),
        "hosts":host_records
    },indent=2)+"\n",encoding="utf-8")

    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)
    report={
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "status":"valid",
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "patch_bounds":list(patch),
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "micro_host_blocks":len(volumes),
        "micro_occupied_cells":total_cells,
        "micro_materials":sorted(materials),
        "glass_materials":[],
        "vanilla_building_blocks_above_ground":vanilla_building_above_ground,
        "checks":{
            "exact_block_map":exact,
            "astra_host_count":astra_count==len(volumes),
            "astra_microcell_decode":decoded==total_cells,
            "no_glass":no_glass,
            "building_above_ground_is_micro_only":vanilla_building_above_ground==0,
            "interior_room_layout_generated":False
        },
        "errors":[]
    }
    REPORT_OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    MANIFEST_OUT.write_text(json.dumps({
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "file":report["file"],
        "sha256":report["sha256"],
        "patch_only":True,
        "requires_mod":"Astra Microblocks 0.4.0-compatible save contract",
        "no_glass":True,
        "placement":{
            "instruction":"Stand on the existing EarthForge yellow registration block and set placement origin to player feet.",
            "rotation":0,
            "mirror":"none",
            "replace_blocks":"ALL"
        },
        "review_targets":[
            "overall resemblance to approved ornate target",
            "storefront frame proportions",
            "upper window trim/lattice",
            "cornice depth",
            "parapet silhouette",
            "micro-only wall/roof visual quality",
            "performance with one complete micro-only building"
        ]
    },indent=2)+"\n",encoding="utf-8")

    print("EarthForge 621 Micro-Only v002 generated and validated.")
    print(f"  File                       : {report['file']}")
    print(f"  SHA256                     : {report['sha256']}")
    print(f"  Region size                : {report['region_size']}")
    print(f"  Micro host blocks          : {report['micro_host_blocks']}")
    print(f"  Occupied microcells        : {report['micro_occupied_cells']}")
    print(f"  Micro materials            : {len(report['micro_materials'])}")
    print(f"  Glass materials            : {len(report['glass_materials'])}")
    print(f"  Vanilla building > ground  : {report['vanilla_building_blocks_above_ground']}")
    print("  Block read-back            : PASS")
    print("  Astra read-back            : PASS")
    print("  No-glass gate              : PASS")
    print("  Micro-only building gate   : PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
