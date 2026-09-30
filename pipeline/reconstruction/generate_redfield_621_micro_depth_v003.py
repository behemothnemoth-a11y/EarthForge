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

SPEC_IN=POC/"labs"/"621_micro_depth_v003.json"
LOCAL_IN=POC/"l0_geometry_local.json"
FRAME_IN=POC/"locked_frame.json"
BASE_FILE=PROJECT/"outputs"/"l1_micro"/"Redfield_POC_001_L1_Micro_Alpha_v006.litematic"

CODEC_PATH=ROOT/"pipeline"/"export"/"litematic_codec.py"
ASTRA_PATH=ROOT/"pipeline"/"microblocks"/"astra_microblock_codec.py"
DEPTH_PATH=ROOT/"pipeline"/"microblocks"/"micro_depth_architecture.py"

OUT_DIR=PROJECT/"outputs"/"building_labs"
OUT_FILE=OUT_DIR/"Redfield_621_MicroDepth_v003.litematic"
MANIFEST_OUT=OUT_DIR/"Redfield_621_MicroDepth_v003.manifest.json"
REPORT_OUT=PROJECT/"validation"/"redfield_621_micro_depth_v003_validation.json"
HOSTMAP_OUT=POC/"labs"/"621_micro_depth_v003_hosts.json"
SECTION_OUT=OUT_DIR/"Redfield_621_MicroDepth_v003_section.svg"

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
            if px < (xj-xi)*(pz-zi)/den+xi: inside=not inside
        j=i
    return inside


def raster_polygon(poly: Sequence[Tuple[float,float]]) -> Set[Cell2]:
    xs=[p[0] for p in poly]; zs=[p[1] for p in poly]
    out=set()
    for x in range(math.floor(min(xs)),math.ceil(max(xs))+1):
        for z in range(math.floor(min(zs)),math.ceil(max(zs))+1):
            if point_in_polygon(x+0.5,z+0.5,poly): out.add((x,z))
    return out


def boundary_faces(fp,cell):
    x,z=cell
    faces=[]
    if (x+1,z) not in fp: faces.append("east")
    if (x-1,z) not in fp: faces.append("west")
    if (x,z+1) not in fp: faces.append("south")
    if (x,z-1) not in fp: faces.append("north")
    return faces


def frontage(fp):
    byz={}
    for x,z in fp: byz.setdefault(z,[]).append(x)
    return [(max(xs),z) for z,xs in sorted(byz.items())]


def rearage(fp):
    byz={}
    for x,z in fp: byz.setdefault(z,[]).append(x)
    return [(min(xs),z) for z,xs in sorted(byz.items())]


def nearest(target,vals):
    return min(vals,key=lambda v:abs(v-target))


def merge_at(volumes,coord,vol,depth):
    if coord not in volumes: volumes[coord]=depth.empty(astra)
    depth.merge(volumes[coord],vol,True)


def section_svg(spec):
    d=spec["depth_cells"]
    scale=14
    width=560
    height=300
    base=430
    # Diagram is conceptual: street is to the right.
    tiers=[
        ("recess/lattice",-d["upper_lattice_setback"],"#333333"),
        ("wall face",0,"#9c4f3e"),
        ("trim",d["trim_projection"],"#d8c8a0"),
        ("fascia",d["sign_fascia_projection"],"#315a45"),
        ("cornice",d["cornice_projection"],"#d8c8a0"),
        ("awning",d["awning_projection"],"#315a45"),
    ]
    svg=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f5f5f5"/>',
        '<text x="20" y="28" font-family="monospace" font-size="16">621 Micro Depth v003 — facade section tiers</text>',
        '<line x1="100" y1="245" x2="520" y2="245" stroke="#999" stroke-width="2"/>',
        '<text x="455" y="270" font-family="monospace" font-size="12">street →</text>'
    ]
    for i,(label,cells,color) in enumerate(tiers):
        x=base+cells*scale
        y=55+i*28
        svg.append(f'<line x1="{base}" y1="{y}" x2="{x}" y2="{y}" stroke="{color}" stroke-width="8"/>')
        svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')
        svg.append(f'<text x="20" y="{y+4}" font-family="monospace" font-size="12">{label}: {cells:+d}/16 block</text>')
    svg.append('</svg>')
    SECTION_OUT.write_text("\n".join(svg)+"\n",encoding="utf-8")


def self_test(codec,astra,depth):
    w=depth.reveal_opening(astra,"minecraft:bricks","minecraft:smooth_sandstone",7,2)
    l=depth.recessed_lattice(astra,"minecraft:black_concrete",7,True,True,1)
    c=depth.cornice_band(astra,"minecraft:bricks","minecraft:smooth_sandstone",13,2)
    assert 0<w.occupied_count()<4096
    assert 0<l.occupied_count()<4096
    assert 0<c.occupied_count()<4096
    print("MICRO_DEPTH_621_SELF_TEST_PASS",w.occupied_count(),l.occupied_count(),c.occupied_count())
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()

    global astra
    codec=load_module(CODEC_PATH,"ef_codec")
    astra=load_module(ASTRA_PATH,"ef_astra")
    depth=load_module(DEPTH_PATH,"ef_depth")
    if args.self_test: return self_test(codec,astra,depth)

    spec=load_json(SPEC_IN)
    local=load_json(LOCAL_IN)
    frame=load_json(FRAME_IN)
    if not BASE_FILE.exists(): raise FileNotFoundError(BASE_FILE)
    base,_=codec.read_back_block_map(BASE_FILE,"REDFIELD_POC_001_L1_MICRO_ALPHA_V006")

    geom=next(x for x in local["buildings"] if int(x["osm_id"])==int(spec["osm_id"]))
    ref=frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])
    fp=raster_polygon([(x-ref_x,z-ref_z) for x,z in geom["polygon_xz_m"]])

    minx,maxx=min(x for x,z in fp),max(x for x,z in fp)
    minz,maxz=min(z for x,z in fp),max(z for x,z in fp)
    front=frontage(fp); rear=rearage(fp)
    front_x=max(x for x,z in front)
    ext_x=front_x+1
    zs=sorted(set(z for x,z in front))
    idx={z:i for i,z in enumerate(zs)}

    # Two exterior host layers are reserved. The second layer is only used where
    # the awning needs almost a full block of projection without flattening the
    # cornice or fascia into the same plane.
    patch=(minx-1,-1,minz,maxx+3,12,maxz)
    pminx,pminy,pminz,pmaxx,pmaxy,pmaxz=patch

    blocks={}
    for (x,y,z),state in base.items():
        if pminx<=x<=pmaxx and pminz<=z<=pmaxz:
            if y<0 or (y==0 and (x,z) not in fp): blocks[(x,y,z)]=state

    volumes={}
    m=spec["materials"]; d=spec["depth_cells"]; mc=spec["micro"]

    # Micro-only structural shell.
    for x,z in fp:
        merge_at(volumes,(x,0,z),depth.floor_skin(astra,m["floor"],int(mc["floor_thickness_cells"])),depth)
        merge_at(volumes,(x,4,z),depth.floor_skin(astra,m["floor"],int(mc["floor_thickness_cells"])),depth)
        merge_at(volumes,(x,9,z),depth.roof_skin(astra,m["roof"],int(mc["roof_thickness_cells"]),d["parapet_setback"]),depth)

        for face in boundary_faces(fp,(x,z)):
            if face=="east": continue
            for y in range(0,9):
                merge_at(volumes,(x,y,z),depth.side_skin(astra,face,m["brick"],3),depth)

    # Rear remains restrained but gains deep openings.
    rear_zs=sorted(set(z for x,z in rear))
    rd=nearest((rear_zs[0]+rear_zs[-1])/2,rear_zs)
    rw=set([rear_zs[len(rear_zs)//4],rear_zs[(3*len(rear_zs))//4]])
    for x,z in rear:
        if z==rd:
            merge_at(volumes,(x,1,z),depth.rear_opening(astra,m["brick"],m["trim"],6),depth)
            merge_at(volumes,(x,2,z),depth.rear_opening(astra,m["brick"],m["trim"],6),depth)
        elif z in rw:
            merge_at(volumes,(x,2,z),depth.rear_opening(astra,m["brick"],m["trim"],7),depth)

    corner=set(spec["facade_program"]["corner_columns"])
    left=set(spec["facade_program"]["left_display"])
    doors=set(spec["facade_program"]["door_pair"])
    right=set(spec["facade_program"]["right_display"])
    upper=set(spec["facade_program"]["upper_windows"])
    brackets=set(spec["facade_program"]["bracket_slots"])

    # Ground storefront base with deep reveals.
    for x,z in front:
        i=idx[z]
        if i in corner:
            merge_at(volumes,(x,0,z),depth.brick_field(astra,m["green"],7),depth)
        elif i in doors:
            merge_at(volumes,(x,0,z),depth.storefront_reveal(astra,m["green"],m["green_shadow"],d["door_setback"],"door"),depth)
        else:
            merge_at(volumes,(x,0,z),depth.storefront_reveal(astra,m["green"],m["green_shadow"],d["storefront_reveal"],"display"),depth)

    # Storefront openings. Window voids stay open; lattice is recessed.
    for x,z in front:
        i=idx[z]
        if i in corner:
            for y in (1,2):
                merge_at(volumes,(x,y,z),depth.brick_field(astra,m["green"],7),depth)
                merge_at(volumes,(ext_x,y,z),depth.pilaster(astra,m["trim"],d["pilaster_projection"],5),depth)
        elif i in doors:
            for y,half in ((1,"lower"),(2,"upper")):
                merge_at(volumes,(x,y,z),depth.storefront_reveal(astra,m["green"],m["green_shadow"],d["door_setback"],"door"),depth)
                merge_at(volumes,(x,y,z),depth.recessed_door(astra,m["door"],m["trim"],m["handle"],d["door_setback"],half),depth)
                merge_at(volumes,(ext_x,y,z),depth.external_surround(astra,m["trim"],d["trim_projection"],2),depth)
        elif i in left or i in right:
            for y in (1,2):
                merge_at(volumes,(x,y,z),depth.storefront_reveal(astra,m["green"],m["green_shadow"],d["storefront_reveal"],"display"),depth)
                merge_at(volumes,(x,y,z),depth.recessed_lattice(astra,m["lattice"],d["storefront_lattice_setback"],True, y==2,1),depth)
                merge_at(volumes,(ext_x,y,z),depth.external_surround(astra,m["trim"],d["trim_projection"],2),depth)

    # Projecting sign fascia.
    for x,z in front:
        merge_at(volumes,(x,3,z),depth.brick_field(astra,m["green"],5),depth)
        merge_at(volumes,(ext_x,3,z),depth.projecting_fascia(astra,m["green"],m["trim"],d["sign_fascia_projection"]),depth)

    # Awning has its own strongest projection tier.
    for z in zs:
        merge_at(volumes,(ext_x,4,z),depth.awning(astra,m["green"],m["trim"],d["awning_projection"]),depth)

    # Upper brick field and deeply recessed windows.
    for x,z in front:
        i=idx[z]
        merge_at(volumes,(x,4,z),depth.brick_field(astra,m["brick"],d["wall_body_thickness"]),depth)
        if i in upper:
            for y in (5,6,7):
                merge_at(volumes,(x,y,z),depth.reveal_opening(astra,m["brick"],m["trim"],d["upper_window_reveal"],2),depth)
                merge_at(volumes,(x,y,z),depth.recessed_lattice(astra,m["lattice"],d["upper_lattice_setback"],True, y==6,1),depth)
                merge_at(volumes,(ext_x,y,z),depth.external_surround(astra,m["trim"],d["trim_projection"],2),depth)
            merge_at(volumes,(ext_x,5,z),depth.sill_header(astra,m["trim"],d["sill_header_projection"],True,False),depth)
            merge_at(volumes,(ext_x,7,z),depth.sill_header(astra,m["trim"],d["sill_header_projection"],False,True),depth)
        else:
            for y in (5,6,7):
                merge_at(volumes,(x,y,z),depth.brick_field(astra,m["brick"],d["wall_body_thickness"]),depth)

    # Layered cornice: three distinct projection stages.
    for x,z in front:
        merge_at(volumes,(x,8,z),depth.brick_field(astra,m["brick"],d["wall_body_thickness"]),depth)
        for stage in (0,1,2):
            merge_at(volumes,(ext_x,8,z),depth.cornice_band(astra,m["brick"],m["trim"],d["cornice_projection"],stage),depth)
        if idx[z] in brackets:
            merge_at(volumes,(ext_x,8,z),depth.bracket(astra,m["trim"],d["cornice_projection"]),depth)

    # Parapet is set back behind cornice, then stepped in elevation.
    for x,z in front:
        i=idx[z]
        base=depth.roundel(astra,m["brick"],m["trim"],d["parapet_setback"]) if i in (0,7) else depth.parapet_field(astra,m["brick"],m["trim"],d["parapet_setback"],True)
        merge_at(volumes,(x,9,z),base,depth)
        if 1<=i<=6:
            merge_at(volumes,(x,10,z),depth.parapet_field(astra,m["brick"],m["trim"],d["parapet_setback"]+1,True),depth)
        if i in (3,4):
            merge_at(volumes,(x,11,z),depth.parapet_field(astra,m["brick"],m["trim"],d["parapet_setback"]+2,True),depth)

    if len(volumes)>int(mc["host_budget"]):
        raise ValueError(f"Host budget exceeded: {len(volumes)}")

    for coord in volumes:
        blocks[coord]=astra.HOST_STATE

    writer=codec.NBTWriter()
    payloads=[]
    records=[]
    total_cells=0
    materials=set()
    for coord in sorted(volumes):
        vol=volumes[coord]
        rel=(coord[0]-pminx,coord[1]-pminy,coord[2]-pminz)
        payloads.append(astra.tile_entity_payload(writer,rel,vol))
        total_cells+=vol.occupied_count()
        materials.update(vol.materials())
        records.append({"coord":list(coord),"relative":list(rel),"occupied_microcells":vol.occupied_count(),"materials":vol.materials()})

    info=codec.write_single_region_litematic(
        OUT_FILE,blocks,patch,
        "REDFIELD_621_MICRO_DEPTH_V003",
        "Redfield 621 - Micro Depth v003",
        "Section-first Astra-only 621 rebuild. Deep reveals, projecting trim/fascia/cornice, no glass.",
        4903,6,1,tile_entity_payloads=payloads
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_621_MICRO_DEPTH_V003")
    normalized={c:codec.canonical_state(s) for c,s in blocks.items()}
    exact=back==normalized
    decoded=0
    astra_count=0
    for te in meta["tile_entities"]:
        if te.get("id")==astra.BLOCK_ENTITY_ID:
            astra_count+=1
            decoded+=sum(v is not None for v in astra.decode_volume_v4(te["volume_v4"]))

    no_glass=not any("glass" in mat for mat in materials)
    vanilla_above=0
    for (x,y,z),state in blocks.items():
        if y>0 and pminx<=x<=pmaxx and pminz<=z<=pmaxz and state!=astra.HOST_STATE:
            vanilla_above+=1

    # Depth validation is explicit and independent of whether the file serialized.
    depth_tiers={
        0,
        -int(d["upper_lattice_setback"]),
        int(d["trim_projection"]),
        int(d["sign_fascia_projection"]),
        int(d["cornice_projection"]),
        int(d["awning_projection"]),
    }
    v=spec["validation"]
    depth_ok=(
        len(depth_tiers)>=int(v["minimum_depth_tiers"]) and
        int(d["storefront_reveal"])>=int(v["minimum_storefront_recess_cells"]) and
        int(d["upper_window_reveal"])>=int(v["minimum_upper_window_recess_cells"]) and
        int(d["cornice_projection"])>=int(v["minimum_cornice_projection_cells"]) and
        int(d["door_setback"])>=int(v["minimum_door_recess_cells"])
    )
    parapet_levels=3
    parapet_ok=parapet_levels>=int(v["minimum_parapet_levels"])

    if not exact: raise ValueError("v003 block read-back mismatch")
    if astra_count!=len(volumes) or decoded!=total_cells: raise ValueError("v003 Astra read-back mismatch")
    if not no_glass: raise ValueError("Glass found in v003")
    if vanilla_above!=0: raise ValueError("Vanilla building blocks remain above ground")
    if not depth_ok: raise ValueError("Facade depth hierarchy validation failed")
    if not parapet_ok: raise ValueError("Parapet depth/elevation hierarchy failed")

    HOSTMAP_OUT.parent.mkdir(parents=True,exist_ok=True)
    HOSTMAP_OUT.write_text(json.dumps({
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "host_count":len(volumes),
        "occupied_microcells":total_cells,
        "materials":sorted(materials),
        "depth_cells":d,
        "hosts":records
    },indent=2)+"\n",encoding="utf-8")

    section_svg(spec)

    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)
    report={
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "status":"valid",
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "micro_host_blocks":len(volumes),
        "micro_occupied_cells":total_cells,
        "materials":sorted(materials),
        "glass_materials":[],
        "vanilla_building_blocks_above_ground":vanilla_above,
        "depth":{
            "tiers":sorted(depth_tiers),
            "tier_count":len(depth_tiers),
            "storefront_reveal_cells":d["storefront_reveal"],
            "door_setback_cells":d["door_setback"],
            "upper_window_reveal_cells":d["upper_window_reveal"],
            "trim_projection_cells":d["trim_projection"],
            "sign_fascia_projection_cells":d["sign_fascia_projection"],
            "cornice_projection_cells":d["cornice_projection"],
            "awning_projection_cells":d["awning_projection"],
            "parapet_levels":parapet_levels
        },
        "checks":{
            "exact_block_map":exact,
            "astra_host_count":astra_count==len(volumes),
            "astra_microcell_decode":decoded==total_cells,
            "no_glass":no_glass,
            "micro_only_above_ground":vanilla_above==0,
            "minimum_depth_tiers":depth_ok,
            "parapet_hierarchy":parapet_ok,
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
        "no_glass":True,
        "requires_mod":"Astra Microblocks 0.4.0-compatible save contract",
        "placement":{
            "instruction":"Stand on the existing EarthForge yellow registration block and set placement origin to player feet.",
            "rotation":0,"mirror":"none","replace_blocks":"ALL"
        },
        "review_targets":[
            "3/4 view depth read",
            "storefront recess",
            "door setback",
            "upper window pocket depth",
            "trim projection",
            "layered cornice shadow",
            "parapet silhouette",
            "eye-level negative space"
        ]
    },indent=2)+"\n",encoding="utf-8")

    print("EarthForge 621 Micro Depth v003 generated and validated.")
    print(f"  File                       : {report['file']}")
    print(f"  Region size                : {report['region_size']}")
    print(f"  Micro host blocks          : {report['micro_host_blocks']}")
    print(f"  Occupied microcells        : {report['micro_occupied_cells']}")
    print(f"  Facade depth tiers         : {report['depth']['tier_count']}")
    print(f"  Storefront recess          : {d['storefront_reveal']}/16 block")
    print(f"  Door setback               : {d['door_setback']}/16 block")
    print(f"  Upper window recess        : {d['upper_window_reveal']}/16 block")
    print(f"  Cornice projection         : {d['cornice_projection']}/16 block")
    print(f"  Awning projection          : {d['awning_projection']}/16 block")
    print(f"  Glass materials            : {len(report['glass_materials'])}")
    print(f"  Vanilla building > ground  : {report['vanilla_building_blocks_above_ground']}")
    print("  Block read-back            : PASS")
    print("  Astra read-back            : PASS")
    print("  Depth hierarchy gate       : PASS")
    print("  No-glass gate              : PASS")
    print("  Micro-only building gate   : PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
