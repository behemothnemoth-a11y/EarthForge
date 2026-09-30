#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

BASE_FILE = PROJECT / "outputs" / "l1_truth" / "Redfield_POC_001_L1_Truth_v005.litematic"
FRAME_IN = POC / "locked_frame.json"
LOCAL_IN = POC / "l0_geometry_local.json"
TRUTH_IN = POC / "truth_v005.json"
MICRO_IN = POC / "micro_v006.json"

OUT_DIR = PROJECT / "outputs" / "l1_micro"
OUT_FILE = OUT_DIR / "Redfield_POC_001_L1_Micro_Alpha_v006.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_L1_Micro_Alpha_v006.manifest.json"
REPORT_OUT = PROJECT / "validation" / "poc001_l1_micro_alpha_v006_validation.json"
HOSTMAP_OUT = POC / "micro_v006_hosts.json"
TEST_STRIP_OUT = OUT_DIR / "Astra_EarthForge_Compatibility_v001.litematic"
TEST_STRIP_REPORT = PROJECT / "validation" / "astra_earthforge_compatibility_v001.json"

CODEC_PATH = ROOT / "pipeline" / "export" / "litematic_codec.py"
ASTRA_PATH = ROOT / "pipeline" / "microblocks" / "astra_microblock_codec.py"

Cell2 = Tuple[int,int]
Cell3 = Tuple[int,int,int]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def point_in_polygon(px,pz,poly):
    inside=False
    j=len(poly)-1
    for i in range(len(poly)):
        xi,zi=poly[i]; xj,zj=poly[j]
        if (zi>pz)!=(zj>pz):
            den=zj-zi or 1e-12
            if px < (xj-xi)*(pz-zi)/den + xi:
                inside=not inside
        j=i
    return inside


def raster_polygon(poly) -> Set[Cell2]:
    import math
    xs=[p[0] for p in poly]; zs=[p[1] for p in poly]
    out=set()
    for x in range(math.floor(min(xs)),math.ceil(max(xs))+1):
        for z in range(math.floor(min(zs)),math.ceil(max(zs))+1):
            if point_in_polygon(x+0.5,z+0.5,poly):
                out.add((x,z))
    return out


def frontage(cells:Set[Cell2],side:str):
    byz={}
    for x,z in cells: byz.setdefault(z,[]).append(x)
    return [(min(xs) if side=="east" else max(xs),z) for z,xs in sorted(byz.items())]


def nearest(target,vals):
    return min(vals,key=lambda v:abs(v-target))


def evenly(vals,count):
    vals=sorted(set(vals))
    if count<=0 or not vals: return []
    return [nearest(vals[0]+(vals[-1]-vals[0])*(i+1)/(count+1),vals) for i in range(count)]


class HostBuilder:
    def __init__(self, blocks, base_blocks, codec, astra, min_bounds):
        self.blocks=blocks
        self.base_blocks=base_blocks
        self.codec=codec
        self.astra=astra
        self.pending=[]  # (schem_coord, volume, metadata)
        self.skipped=[]
        self.min_bounds=min_bounds

    def add(self, coord:Cell3, volume, metadata:dict, replace=True):
        if volume.occupied_count()==0:
            return False
        existing=self.blocks.get(coord)
        if existing is not None and not replace:
            self.skipped.append({"coord":list(coord),"existing":existing,"reason":"occupied","metadata":metadata})
            return False
        self.blocks[coord]=self.astra.HOST_STATE
        self.pending.append((coord,volume,metadata))
        return True


def attach_x(front_x:int,side:str):
    return front_x-1 if side=="east" else front_x+1


def overlay_priority(builder, footprint, entry, pentry, ref_x, ref_z, astra):
    side=entry["side"]
    front=frontage(footprint,side)
    if not front: return
    front_zs=sorted(set(z for _x,z in front))
    fx=min(x for x,_z in front) if side=="east" else max(x for x,_z in front)
    hx=attach_x(fx,side)
    material=pentry["material"]
    height=int(entry["height"])
    bay_count=max(2,int(entry["front"]["bays"]))
    bays=evenly(front_zs,bay_count)
    features=set(pentry["features"])

    def sc(px,py,pz): return (px-ref_x,py,pz-ref_z)

    # Cornice: every block on high priority, every second block on medium.
    step=1 if pentry["level"]=="high" else 2
    if "cornice" in features:
        for i,z in enumerate(front_zs):
            if i%step==0:
                builder.add(sc(hx,height+1,z),astra.thin_cornice(side,material),
                            {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"cornice"})

    if "upper_mullions" in features:
        for z in bays:
            for y in (5,6):
                if y < height:
                    builder.add(sc(hx,y,z),astra.vertical_mullion(side,material),
                                {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"upper_mullion"},
                                replace=False)

    if "mullions" in features:
        for z in bays:
            for y in (1,2):
                builder.add(sc(hx,y,z),astra.vertical_mullion(side,material),
                            {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"mullion"},
                            replace=False)

    if "transoms" in features:
        for z in bays:
            for y in (2,6):
                if y < height:
                    builder.add(sc(hx,y,z),astra.transom(side,material),
                                {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"transom"},
                                replace=False)

    if "pilasters" in features:
        pilaster_zs=evenly(front_zs,max(2,bay_count-1))
        for z in pilaster_zs:
            for y in range(0,height):
                # Skip common awning level to preserve vanilla awnings.
                if y==4: continue
                builder.add(sc(hx,y,z),astra.pilaster(side,material),
                            {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"pilaster"},
                            replace=False)

    if "sign_frame" in features:
        for z in front_zs[::max(1,len(front_zs)//3)]:
            builder.add(sc(hx,3,z),astra.sign_frame(side,material),
                        {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"sign_frame"},
                        replace=False)

    if "entry_surround" in features:
        door_zs=entry["front"].get("door_fracs",[0.5])
        targets=[nearest(front_zs[0]+(front_zs[-1]-front_zs[0])*f,front_zs) for f in door_zs]
        for z in targets:
            for y in range(0,min(height,9)):
                builder.add(sc(hx,y,z),astra.entry_surround(side,material),
                            {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"entry_surround"},
                            replace=False)

    if "center_divider" in features:
        z=nearest((front_zs[0]+front_zs[-1])/2,front_zs)
        for y in range(0,height+2):
            builder.add(sc(hx,y,z),astra.pilaster(side,material,depth=5,width=8),
                        {"osm_id":entry["osm_id"],"addresses":entry["addresses"],"feature":"center_divider"},
                        replace=False)


def add_light_cornices(builder, geom, entries, priority_ids, ref_x, ref_z, astra, every_n):
    for entry in entries:
        oid=int(entry["osm_id"])
        if oid in priority_ids:
            continue
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        front=frontage(fp,entry["side"])
        if not front: continue
        fx=min(x for x,_z in front) if entry["side"]=="east" else max(x for x,_z in front)
        hx=attach_x(fx,entry["side"])
        mat="minecraft:bricks" if entry["materials"]["wall"]=="minecraft:bricks" else "minecraft:stone_bricks"
        for i,(_x,z) in enumerate(front):
            if i%every_n==0:
                builder.add((hx-ref_x,int(entry["height"])+1,z-ref_z),
                            astra.thin_cornice(entry["side"],mat,depth=3,height=3),
                            {"osm_id":oid,"addresses":entry["addresses"],"feature":"light_cornice"})


def make_test_strip(codec,astra):
    blocks={}
    hosts=[]
    patterns=[
        ("cornice",astra.thin_cornice("west","minecraft:bricks")),
        ("mullion",astra.vertical_mullion("west","minecraft:smooth_sandstone")),
        ("transom",astra.transom("west","minecraft:stone_bricks")),
        ("pilaster",astra.pilaster("west","minecraft:bricks")),
        ("mixed",astra.mixed_frame("west","minecraft:smooth_sandstone","minecraft:red_terracotta")),
    ]
    for i,(name,volume) in enumerate(patterns):
        coord=(i*2,0,0)
        blocks[coord]=astra.HOST_STATE
        hosts.append((coord,volume,name))
    bounds=(0,0,0,8,0,0)
    w=codec.NBTWriter()
    payloads=[]
    for coord,volume,name in hosts:
        rel=(coord[0]-bounds[0],coord[1]-bounds[1],coord[2]-bounds[2])
        payloads.append(astra.tile_entity_payload(w,rel,volume))
    info=codec.write_single_region_litematic(
        TEST_STRIP_OUT,blocks,bounds,"ASTRA_EARTHFORGE_COMPAT",
        "Astra EarthForge Compatibility v001",
        "Five direct Astra microblock NBT patterns generated by EarthForge.",
        4903,6,1,tile_entity_payloads=payloads
    )
    back,meta=codec.read_back_block_map(TEST_STRIP_OUT,"ASTRA_EARTHFORGE_COMPAT")
    ok=len(meta["tile_entities"])==5 and back=={k:codec.canonical_state(v) for k,v in blocks.items()}
    TEST_STRIP_REPORT.parent.mkdir(parents=True,exist_ok=True)
    TEST_STRIP_REPORT.write_text(json.dumps({
        "schema_version":1,"status":"valid" if ok else "invalid",
        "file":str(TEST_STRIP_OUT.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],"hosts":5,
        "patterns":[x[0] for x in patterns],
        "read_back_tile_entities":len(meta["tile_entities"])
    },indent=2)+"\n",encoding="utf-8")
    if not ok: raise ValueError("Astra compatibility strip read-back failed")


def self_test(codec,astra):
    v=astra.mixed_frame("west","minecraft:bricks","minecraft:red_terracotta")
    assert v.occupied_count()>0
    v4=v.volume_v4()
    fake={"version":2,"size":len(v4["palette"]),"bits":v4["bits"],"cells":v4["cells"]}
    for i,m in enumerate(v4["palette"]): fake[f"material_{i}"]=m
    decoded=astra.decode_volume_v4(fake)
    assert decoded==v.cells
    print("ASTRA_MICROBLOCK_CODEC_SELF_TEST_PASS",v.occupied_count(),len(v4["palette"]))
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()

    codec=load_module(CODEC_PATH,"earthforge_litematic_codec")
    astra=load_module(ASTRA_PATH,"earthforge_astra_codec")
    if args.self_test:
        return self_test(codec,astra)

    if not BASE_FILE.exists():
        raise FileNotFoundError(f"Validated v005 base missing: {BASE_FILE}")

    frame=load_json(FRAME_IN)
    local=load_json(LOCAL_IN)
    truth=load_json(TRUTH_IN)
    mspec=load_json(MICRO_IN)

    base,base_meta=codec.read_back_block_map(BASE_FILE,"REDFIELD_POC_001_L1_TRUTH_V005")
    blocks=dict(base)

    geom={int(x["osm_id"]):x for x in local["buildings"]}
    entries={int(x["osm_id"]):x for x in truth["entries"]}
    ref=frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])

    # Initial bounds from v005.
    bx,by,bz=base_meta["region_position"]
    bw,bh,bl=base_meta["region_size"]
    min_x,min_y,min_z=bx,by,bz
    max_x,max_y,max_z=bx+bw-1,by+bh-1,bz+bl-1

    builder=HostBuilder(blocks,base,codec,astra,(min_x,min_y,min_z))
    priority_ids={int(x["osm_id"]) for x in mspec["priority"]}

    add_light_cornices(builder,geom,truth["entries"],priority_ids,ref_x,ref_z,astra,
                       int(mspec["global"]["light_cornice_every_n_blocks"]))

    for pentry in mspec["priority"]:
        oid=int(pentry["osm_id"])
        entry=entries[oid]
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        overlay_priority(builder,fp,entry,pentry,ref_x,ref_z,astra)

    if len(builder.pending)>int(mspec["global"]["max_hosts"]):
        raise ValueError(f"Micro host budget exceeded: {len(builder.pending)}")

    # Extend region if needed.
    for (x,y,z),_volume,_meta in builder.pending:
        min_x,min_y,min_z=min(min_x,x),min(min_y,y),min(min_z,z)
        max_x,max_y,max_z=max(max_x,x),max(max_y,y),max(max_z,z)

    writer=codec.NBTWriter()
    tile_payloads=[]
    host_records=[]
    total_cells=0
    for coord,volume,meta in builder.pending:
        rel=(coord[0]-min_x,coord[1]-min_y,coord[2]-min_z)
        tile_payloads.append(astra.tile_entity_payload(writer,rel,volume))
        total_cells+=volume.occupied_count()
        host_records.append({
            "schematic_coord":list(coord),
            "relative_tile_coord":list(rel),
            "occupied_microcells":volume.occupied_count(),
            "materials":volume.materials(),
            **meta
        })

    marker=(0,-1,0)
    marker_block="minecraft:yellow_concrete"
    blocks[marker]=marker_block

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    info=codec.write_single_region_litematic(
        OUT_FILE,blocks,(min_x,min_y,min_z,max_x,max_y,max_z),
        "REDFIELD_POC_001_L1_MICRO_ALPHA_V006",
        "Redfield POC 001 - L1 Micro Alpha v006",
        "v005 normal-block truth base plus direct Astra Microblocks facade overlays. Interiors remain metadata-only.",
        4903,6,1,tile_entity_payloads=tile_payloads
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_POC_001_L1_MICRO_ALPHA_V006")
    normalized={c:codec.canonical_state(s) for c,s in blocks.items()}
    exact=back==normalized
    marker_ok=back.get(marker)==marker_block
    tile_ok=len(meta["tile_entities"])==len(builder.pending)

    # Verify each Astra block entity volume_v4 decodes.
    decoded_cells=0
    astra_ids=0
    for te in meta["tile_entities"]:
        if te.get("id")==astra.BLOCK_ENTITY_ID:
            astra_ids+=1
            decoded=astra.decode_volume_v4(te["volume_v4"])
            decoded_cells+=sum(x is not None for x in decoded)

    if not exact: raise ValueError("v006 block read-back mismatch")
    if not marker_ok: raise ValueError("v006 registration marker failed")
    if not tile_ok or astra_ids!=len(builder.pending): raise ValueError("v006 tile-entity count mismatch")
    if decoded_cells!=total_cells: raise ValueError("v006 microcell read-back mismatch")

    HOSTMAP_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":mspec["export_id"],
        "host_count":len(host_records),
        "occupied_microcells":total_cells,
        "skipped":builder.skipped,
        "hosts":host_records
    },indent=2)+"\n",encoding="utf-8")

    report={
        "schema_version":1,
        "export_id":mspec["export_id"],
        "status":"valid",
        "base_sha256":load_json(PROJECT/"validation"/"poc001_l1_truth_v005_validation.json")["sha256"],
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "non_air_blocks":info["non_air_blocks"],
        "micro_host_blocks":len(builder.pending),
        "micro_occupied_cells":total_cells,
        "micro_materials":sorted({m for _c,v,_meta in builder.pending for m in v.materials()}),
        "skipped_micro_hosts":len(builder.skipped),
        "tile_entities":info["tile_entities"],
        "checks":{
            "base_is_v005":True,
            "exact_block_map":exact,
            "registration_marker":marker_ok,
            "astra_tile_entity_count":tile_ok,
            "astra_volume_v4_decode":decoded_cells==total_cells,
            "micro_host_budget_ok":len(builder.pending)<=int(mspec["global"]["max_hosts"]),
            "interior_blocks_generated":False
        },
        "errors":[]
    }
    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    MANIFEST_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":mspec["export_id"],
        "file":report["file"],"sha256":report["sha256"],
        "region_position":report["region_position"],"region_size":report["region_size"],
        "placement":{
            "instruction":"Stand on existing yellow registration block and set placement origin to player feet.",
            "rotation":0,"mirror":"none","replace_blocks":"ALL"
        },
        "requires_mod":"Astra Microblocks 0.4.0-compatible save contract",
        "compatibility_strip":str(TEST_STRIP_OUT.relative_to(ROOT)).replace("\\","/")
    },indent=2)+"\n",encoding="utf-8")

    make_test_strip(codec,astra)

    print("EarthForge Redfield POC 001 L1 Micro Alpha v006 generated and validated.")
    print(f"  File                 : {report['file']}")
    print(f"  SHA256               : {report['sha256']}")
    print(f"  Region pos           : {report['region_position']}")
    print(f"  Region size          : {report['region_size']}")
    print(f"  Micro host blocks    : {report['micro_host_blocks']}")
    print(f"  Occupied microcells  : {report['micro_occupied_cells']}")
    print(f"  Astra tile entities  : {report['tile_entities']}")
    print(f"  Skipped host attempts: {report['skipped_micro_hosts']}")
    print(f"  Marker               : {list(marker)} {marker_block}")
    print("  Block read-back      : PASS")
    print("  Astra volume decode  : PASS")
    print(f"  Compatibility strip  : {TEST_STRIP_OUT.relative_to(ROOT)}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
