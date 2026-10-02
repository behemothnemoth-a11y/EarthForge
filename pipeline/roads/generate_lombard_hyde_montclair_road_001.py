#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import transform as shp_transform
from shapely.prepared import prep

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipeline.export.litematic_codec import NBTWriter, canonical_state, read_back_block_map, write_single_region_litematic
from pipeline.microblocks.astra_microblock_codec import HOST_STATE, MicroVolume, decode_volume_v4, tile_entity_payload

PROJECT=ROOT/"projects"/"lombard_sf"
ROW_FILE=PROJECT/"roads"/"datasf_row_lombard_v001.geojson"
STREET_FILE=PROJECT/"roads"/"datasf_street_controls_v001.geojson"
WIDTH_FILE=PROJECT/"source_manifests"/"datasf_lombard_width_sources_v001.json"
OUTDIR=PROJECT/"outputs"/"slices"/"hyde_montclair_road_001"
OUT=OUTDIR/"Lombard_Hyde_to_Montclair_Road_Astra_v001.litematic"
VAL=PROJECT/"validation"/"lombard_hyde_montclair_road_astra_v001.json"
SLICE=PROJECT/"slices"/"hyde_montclair_road_001"
CNN="8449000"; OFFSET_X=48; OFFSET_Z=48; MICRO=16
ROAD_MATERIAL="astra_microblocks:rgb_c64035"
MARKER="minecraft:yellow_concrete"; SLAB_Y=(14,15)

def read_json(p): return json.loads(p.read_text(encoding="utf-8"))

def source_geometry():
    row=read_json(ROW_FILE)
    rf=next(f for f in row["features"] if str(f["properties"]["cnn"])==CNN)
    streets=read_json(STREET_FILE)
    sf=next(f for f in streets["features"] if str(f["properties"]["cnn"])==CNN)
    width=read_json(WIDTH_FILE)["segments"][CNN]
    tr=Transformer.from_crs(4326,7131,always_xy=True)
    row_m=shp_transform(tr.transform,shape(rf["geometry"]))
    center_m=shp_transform(tr.transform,shape(sf["geometry"]))
    h_e,h_n=tr.transform(-122.419613973,37.801994863)
    sidewalk_m=float(width["actual_sidewalk_width_ft"])*0.3048
    road_m=row_m.buffer(-sidewalk_m,join_style=1)
    if road_m.is_empty: raise RuntimeError("ROW inset produced empty road body")
    def local(x,y,z=None): return (x-h_e,-(y-h_n))
    return shp_transform(local,road_m),shp_transform(local,center_m),width

def rasterize(poly):
    prepared=prep(poly)
    minx,minz,maxx,maxz=poly.bounds
    gx0=math.floor(minx*MICRO)-1; gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1; gz1=math.ceil(maxz*MICRO)+1
    hosts={}; occupied=0
    for gz in range(gz0,gz1+1):
        z=(gz+0.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+0.5)/MICRO
            if not prepared.contains(Point(x,z)): continue
            ax=gx+OFFSET_X*MICRO; az=gz+OFFSET_Z*MICRO
            hx=math.floor(ax/MICRO); hz=math.floor(az/MICRO)
            cx=ax-hx*MICRO; cz=az-hz*MICRO
            key=(hx,-1,hz)
            vol=hosts.get(key)
            if vol is None:
                vol=MicroVolume("minecraft:bricks"); hosts[key]=vol
            for cy in SLAB_Y: vol.set(cx,cy,cz,ROAD_MATERIAL)
            occupied+=len(SLAB_Y)
    return hosts,occupied

def preview(poly,center,path):
    minx,minz,maxx,maxz=poly.bounds
    scale=10; pad=30
    w=max(300,int((maxx-minx)*scale+2*pad)); h=max(220,int((maxz-minz)*scale+2*pad))
    im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im)
    def pp(x,z): return (pad+(x-minx)*scale,pad+(z-minz)*scale)
    d.polygon([pp(x,z) for x,z in poly.exterior.coords],fill=(198,64,53),outline=(70,70,70))
    d.line([pp(x,z) for x,z in center.coords],fill=(35,35,35),width=2)
    d.text((10,8),"Lombard Hyde to Montclair - DataSF road-body candidate - 1:1 metric",fill=(0,0,0))
    path.parent.mkdir(parents=True,exist_ok=True); im.save(path)

def main():
    road,center,width=source_geometry()
    hosts,occupied=rasterize(road)
    blocks={(0,-1,0):MARKER}
    for pos in hosts:
        blocks[pos]=HOST_STATE

    xs=[p[0] for p in blocks]; zs=[p[2] for p in blocks]
    bounds=(min(xs),-1,min(zs),max(xs),-1,max(zs))
    writer=NBTWriter(); tes=[]
    for (x,y,z),vol in sorted(hosts.items()):
        rel=(x-bounds[0],y-bounds[1],z-bounds[2])
        tes.append(tile_entity_payload(writer,rel,vol))

    OUTDIR.mkdir(parents=True,exist_ok=True)
    stats=write_single_region_litematic(
        OUT,blocks,bounds,
        "lombard_hyde_montclair_road_001",
        "Lombard Hyde to Montclair Road Astra v001",
        "Stress-build road slice. DataSF ROW polygon inset by actual 15 ft sidewalk width. Flat plan-geometry review only.",
        data_version=4903,
        tile_entity_payloads=tes,
    )

    actual,meta=read_back_block_map(OUT,"lombard_hyde_montclair_road_001")
    expected={pos:canonical_state(state) for pos,state in blocks.items()}
    exact_blocks=actual==expected

    decoded={}
    px,py,pz=meta["region_position"]
    for te in meta["tile_entities"]:
        if te.get("id")!="astra_microblocks:test_host":
            continue
        pos=(te["x"]+px,te["y"]+py,te["z"]+pz)
        decoded[pos]=decode_volume_v4(te["volume_v4"])

    exact_hosts=set(decoded)==set(hosts)
    exact_cells=exact_hosts and all(decoded[pos]==hosts[pos].cells for pos in hosts)

    SLICE.mkdir(parents=True,exist_ok=True)
    preview(road,center,SLICE/"road_preview.png")

    derivation={
        "schema_version":1,
        "slice_id":"LOMBARD_HYDE_MONTCLAIR_ROAD_001",
        "cnn":CNN,
        "scope":"Hyde Street node to Montclair Terrace node, complete CNN 8449000",
        "working_crs":"EPSG:7131",
        "minecraft_scale":"1 block = 1 meter; Astra cells = 1/16 meter",
        "derivation":"DataSF ROW polygon h8n7-e4ns inset uniformly by DataSF SIDEWALK_F actual sidewalk width for CNN 8449000",
        "actual_sidewalk_width_ft":width["actual_sidewalk_width_ft"],
        "actual_sidewalk_width_m":float(width["actual_sidewalk_width_ft"])*0.3048,
        "source_limitations":[
            "ROW source is a 2014 analysis and explicitly not engineering survey accuracy.",
            "SIDEWALK_F source reports 15 ft, Both.",
            "This is a source-backed road-body candidate for Minecraft review, not final curb truth."
        ],
        "road_candidate_area_m2":road.area,
        "centerline_length_m":center.length,
        "local_bounds_m":list(road.bounds),
        "terrain_included":False,
        "curb_detail_included":False,
        "landscape_included":False
    }
    (SLICE/"derivation.json").write_text(json.dumps(derivation,indent=2)+"\n",encoding="utf-8")

    report={
        **stats,
        "schema_version":1,
        "slice_id":derivation["slice_id"],
        "status":"valid" if exact_blocks and exact_cells else "invalid",
        "astra_min_version":"0.7.0",
        "astra_hosts":len(hosts),
        "occupied_microcells":occupied,
        "exact_block_readback":exact_blocks,
        "exact_astra_host_set":exact_hosts,
        "exact_astra_microcell_readback":exact_cells,
        "registration_marker":actual.get((0,-1,0))==MARKER,
        "review_gate":"USER_MINECRAFT_FLYAROUND_REQUIRED",
        "review_focus":[
            "road footprint width",
            "switchback spacing",
            "curve shape",
            "1:1 player-scale feel",
            "whether this slice is large enough for productive review"
        ],
        "derivation_file":str((SLICE/"derivation.json").relative_to(ROOT)).replace("\\","/")
    }
    VAL.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if report["status"]!="valid":
        raise SystemExit(1)

if __name__=="__main__":
    main()
