#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

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
    decode_volume_v4,
    tile_entity_payload,
)

PROJECT=ROOT/"projects"/"lombard_sf"
POC=PROJECT/"poc_001"
CENTER=POC/"l0_crooked_centerline_v001.json"
OUT=PROJECT/"outputs"/"road_only_v006"

NAME="Lombard_Road_Only_Astra_v006"
REGION="LOMBARD_ROAD_ONLY_ASTRA_V006"
DATA_VERSION=4903

# Permanent registration convention inherited from Lombard project.
REG_LOCAL_X=-30.0
REG_LOCAL_Z=-20.0

MARKER="minecraft:yellow_concrete"
PAD="minecraft:polished_andesite"
ROAD_A="astra_microblocks:rgb_9d5041"
ROAD_B="astra_microblocks:rgb_87453a"
MICRO=16
ROAD_THICKNESS_CELLS=3

def font(size:int):
    path=Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path),size) if path.exists() else None

def floor16(v:int):
    host=math.floor(v/16)
    return host,v-host*16

class RoadBuilder:
    """Air-backed Astra builder for road-only truth review."""
    def __init__(self):
        self.blocks={}
        self.hosts={}

    def set_micro_schematic(self,sx:int,sy:int,sz:int,material:str):
        hx,lx=floor16(int(sx))
        hy,ly=floor16(int(sy))
        hz,lz=floor16(int(sz))
        pos=(hx,hy,hz)
        vol=self.hosts.get(pos)
        if vol is None:
            vol=MicroVolume("minecraft:air")
            self.hosts[pos]=vol
            self.blocks[pos]=HOST_STATE
        vol.set(lx,ly,lz,material)

    def set_micro_local(self,x_micro:int,y_micro:int,z_micro:int,material:str):
        sx=x_micro-round(REG_LOCAL_X*MICRO)
        sz=z_micro-round(REG_LOCAL_Z*MICRO)
        self.set_micro_schematic(sx,y_micro,sz,material)

    def road_slab(self,x_micro:int,z_micro:int,top_micro:int,material:str):
        for y in range(top_micro-ROAD_THICKNESS_CELLS,top_micro):
            self.set_micro_local(x_micro,y,z_micro,material)

def variable_road_polygon(road_line:LineString):
    """Retain the v003 reviewed plan logic: narrow straights, modest hairpin flare."""
    coords=list(road_line.coords)
    pieces=[]
    halfwidths=[]
    for i in range(len(coords)-1):
        p0=coords[i]
        p1=coords[i+1]
        j0=max(0,i-2)
        j1=min(len(coords)-1,i+3)
        a=coords[j0]
        b=coords[i]
        c=coords[j1]
        v1=(b[0]-a[0],b[1]-a[1])
        v2=(c[0]-b[0],c[1]-b[1])
        l1=max(1e-6,math.hypot(*v1))
        l2=max(1e-6,math.hypot(*v2))
        dot=max(-1.0,min(1.0,(v1[0]*v2[0]+v1[1]*v2[1])/(l1*l2)))
        turn=math.degrees(math.acos(dot))
        half=2.70+min(0.55,(turn/70.0)*0.55)
        halfwidths.append(half)
        pieces.append(LineString([p0,p1]).buffer(half,cap_style=1,join_style=1,resolution=16))
    poly=unary_union(pieces).buffer(.04,join_style=1).buffer(-.04,join_style=1)
    return poly,halfwidths

def road_material(xm:int,zm:int):
    # Restrained brick variation. No decorative curb/stripe geometry in v006.
    row=math.floor(zm/3)
    col=math.floor((xm+(row&1)*3)/6)
    return ROAD_B if ((row+col)%7==0) else ROAD_A

def build_engineered_profile(center:list[dict]):
    """Smooth LiDAR centerline elevations into a continuous downhill road profile."""
    stations=np.array([float(r["station_2d_m"]) for r in center],dtype=float)
    raw=np.array([float(r["elev_rel_top_m"]) for r in center],dtype=float)

    # Resample densely enough for microblock projection.
    dense_s=np.arange(0.0,stations[-1]+0.125,0.125)
    dense_raw=np.interp(dense_s,stations,raw)

    # About 2m moving-average window removes LiDAR-scale bumps without
    # changing the macro grade or the measured endpoint drop.
    window=17
    pad=window//2
    padded=np.pad(dense_raw,(pad,pad),mode="edge")
    kernel=np.ones(window,dtype=float)/window
    smooth=np.convolve(padded,kernel,mode="valid")

    # Lombard's crooked block is continuously downhill Hyde -> Leavenworth.
    # Remove tiny upward LiDAR wiggles, then re-lock the measured endpoint drop.
    smooth=smooth-smooth[0]
    smooth=np.minimum.accumulate(smooth)
    target_drop=float(raw[-1]-raw[0])
    if abs(smooth[-1])<1e-9:
        raise RuntimeError("engineered profile collapsed")
    smooth*=target_drop/smooth[-1]
    smooth[0]=0.0
    smooth[-1]=target_drop

    raw_dense_rel=dense_raw-dense_raw[0]
    correction=smooth-raw_dense_rel
    return {
        "station_m":dense_s,
        "elev_rel_m":smooth,
        "raw_rel_m":raw_dense_rel,
        "target_drop_m":target_drop,
        "max_abs_smoothing_correction_m":float(np.max(np.abs(correction))),
        "mean_abs_smoothing_correction_m":float(np.mean(np.abs(correction))),
    }

def rasterize_road(builder:RoadBuilder,road_poly,road_line,profile):
    prepared=prep(road_poly)
    minx,minz,maxx,maxz=road_poly.bounds
    gx0=math.floor(minx*MICRO)-1
    gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1
    gz1=math.ceil(maxz*MICRO)+1
    cells=0
    columns=0

    for gz in range(gz0,gz1+1):
        z=(gz+.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+.5)/MICRO
            pt=Point(x,z)
            if not prepared.contains(pt):
                continue
            station=road_line.project(pt)
            elev=float(np.interp(
                station,
                profile["station_m"],
                profile["elev_rel_m"],
            ))
            top_micro=round(elev*MICRO)
            builder.road_slab(gx,gz,top_micro,road_material(gx,gz))
            columns+=1
            cells+=ROAD_THICKNESS_CELLS
    return columns,cells

def add_registration(builder:RoadBuilder):
    # Keep the permanent registration pad outside the review geometry.
    for x in range(-5,6):
        for z in range(-5,6):
            builder.blocks[(x,-1,z)]=PAD
    builder.blocks[(0,-1,0)]=MARKER
    for x in range(1,5):
        builder.blocks[(x,-1,0)]="minecraft:gold_block"
    for z in (-1,1):
        builder.blocks[(4,-1,z)]="minecraft:gold_block"

def render_previews(center,road_poly,profile):
    OUT.mkdir(parents=True,exist_ok=True)

    # Plan view: road only, no contextual geometry.
    minx,minz,maxx,maxz=road_poly.bounds
    scale=8.0
    pad=45
    w=max(900,int((maxx-minx)*scale+pad*2))
    h=max(360,int((maxz-minz)*scale+pad*2))
    im=Image.new("RGB",(w,h),"white")
    draw=ImageDraw.Draw(im)
    def pp(x,z):
        return (pad+(x-minx)*scale,pad+(z-minz)*scale)
    geoms=list(road_poly.geoms) if hasattr(road_poly,"geoms") else [road_poly]
    for geom in geoms:
        if geom.geom_type=="Polygon":
            draw.polygon([pp(x,z) for x,z in geom.exterior.coords],fill=(157,80,65),outline=(45,45,45))
    draw.line([pp(r["x_m"],r["z_m"]) for r in center],fill=(25,25,25),width=2)
    draw.text((20,15),"LOMBARD ROAD ONLY v006 / 1:1 / no context",font=font(22),fill=(20,20,20))
    im.save(OUT/f"{NAME}_plan.png")

    # Longitudinal profile comparison.
    pw,ph=1400,500
    pim=Image.new("RGB",(pw,ph),"white")
    pd=ImageDraw.Draw(pim)
    xs=profile["station_m"]
    raw=profile["raw_rel_m"]
    eng=profile["elev_rel_m"]
    xmin_s,xmax_s=float(xs[0]),float(xs[-1])
    ymin=min(float(raw.min()),float(eng.min()))
    ymax=max(float(raw.max()),float(eng.max()))
    mx,my=70,50
    sx=(pw-2*mx)/(xmax_s-xmin_s)
    sy=(ph-2*my)/(ymax-ymin if ymax!=ymin else 1)
    def profpt(s,e):
        return (mx+(s-xmin_s)*sx,my+(ymax-e)*sy)
    pd.line([profpt(float(s),float(e)) for s,e in zip(xs,raw)],fill=(150,150,150),width=2)
    pd.line([profpt(float(s),float(e)) for s,e in zip(xs,eng)],fill=(40,40,40),width=3)
    pd.text((20,15),"Raw LiDAR centerline vs engineered road profile",font=font(20),fill=(20,20,20))
    pim.save(OUT/f"{NAME}_profile.png")

def main():
    center=json.loads(CENTER.read_text(encoding="utf-8"))
    road_line=LineString([(r["x_m"],r["z_m"]) for r in center])
    road_poly,halfwidths=variable_road_polygon(road_line)
    profile=build_engineered_profile(center)

    builder=RoadBuilder()
    road_columns,road_cells=rasterize_road(builder,road_poly,road_line,profile)
    add_registration(builder)

    for pos in builder.hosts:
        builder.blocks[pos]=HOST_STATE

    xs=[p[0] for p in builder.blocks]
    ys=[p[1] for p in builder.blocks]
    zs=[p[2] for p in builder.blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))

    writer=NBTWriter()
    tile_entities=[]
    for (x,y,z),vol in sorted(builder.hosts.items()):
        rel=(x-bounds[0],y-bounds[1],z-bounds[2])
        tile_entities.append(tile_entity_payload(writer,rel,vol))

    OUT.mkdir(parents=True,exist_ok=True)
    litematic=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        litematic,
        builder.blocks,
        bounds,
        REGION,
        NAME,
        "Lombard road-only truth reset v006. Air-backed Astra brick roadway only, with a smoothed LiDAR-derived downhill profile. No curbs, terrain, stairs, walls, hedges, buildings, or outer context.",
        data_version=DATA_VERSION,
        tile_entity_payloads=tile_entities,
    )

    actual,meta=read_back_block_map(litematic,REGION)
    expected={pos:canonical_state(state) for pos,state in builder.blocks.items()}
    exact_blocks=actual==expected

    rp=meta["region_position"]
    decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        decoded[pos]=decode_volume_v4(te["volume_v4"])
    exact_hosts=set(decoded)==set(builder.hosts)
    exact_cells=exact_hosts and all(decoded[p]==builder.hosts[p].cells for p in builder.hosts)

    render_previews(center,road_poly,profile)

    materials=Counter()
    for vol in builder.hosts.values():
        for m in vol.cells:
            if m:
                materials[m]+=1
    forbidden=[m for m in materials if m not in (ROAD_A,ROAD_B)]

    report={
        **stats,
        "schema_version":1,
        "project_id":"lombard_sf",
        "review_id":"LOMBARD_ROAD_ONLY_V006",
        "status":"valid" if exact_blocks and exact_cells and not forbidden else "invalid",
        "scope":"road only",
        "source_centerline":"projects/lombard_sf/poc_001/l0_crooked_centerline_v001.json",
        "centerline_nodes":len(center),
        "centerline_length_m":road_line.length,
        "road_area_m2":road_poly.area,
        "width_model":{
            "straight_full_width_m":5.40,
            "max_full_width_m":6.50,
            "actual_min_full_width_m":2*min(halfwidths),
            "actual_max_full_width_m":2*max(halfwidths),
            "mean_full_width_m":2*sum(halfwidths)/len(halfwidths),
        },
        "profile":{
            "method":"LiDAR centerline -> 0.125m resample -> ~2m moving average -> monotonic downhill -> endpoint drop relock",
            "source_endpoint_drop_m":float(center[-1]["elev_rel_top_m"]-center[0]["elev_rel_top_m"]),
            "generated_endpoint_drop_m":float(profile["elev_rel_m"][-1]-profile["elev_rel_m"][0]),
            "max_abs_smoothing_correction_m":profile["max_abs_smoothing_correction_m"],
            "mean_abs_smoothing_correction_m":profile["mean_abs_smoothing_correction_m"],
            "monotonic_downhill":bool(np.all(np.diff(profile["elev_rel_m"])<=1e-9)),
        },
        "astra":{
            "air_backed_hosts":True,
            "host_count":len(builder.hosts),
            "road_surface_columns":road_columns,
            "occupied_road_microcells":road_cells,
            "thickness_cells":ROAD_THICKNESS_CELLS,
            "materials":dict(materials),
            "forbidden_materials":forbidden,
        },
        "excluded":{
            "curbs":True,
            "terrain":True,
            "stairs":True,
            "landings":True,
            "retaining_walls":True,
            "hedges":True,
            "buildings":True,
            "cross_streets":True,
            "cable_car_context":True,
        },
        "validation":{
            "exact_block_readback":exact_blocks,
            "exact_astra_host_set":exact_hosts,
            "exact_astra_microcell_readback":exact_cells,
            "registration_marker":actual.get((0,-1,0))==MARKER,
            "review_status":"ROAD_ONLY_V006_FLYAROUND_REQUIRED",
        }
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    (OUT/f"{NAME}_placement.json").write_text(json.dumps({
        "yellow_marker":[0,-1,0],
        "stand_above_marker":True,
        "placement_origin":"player feet",
        "rotation":0,
        "mirror":"none",
        "replace_blocks":"ALL"
    },indent=2)+"\n",encoding="utf-8")
    (OUT/"Build_notes.md").write_text(
        "# Lombard Road Only v006\n\n"
        "Hard reset to the road itself. This artifact contains only the brick roadway plus the permanent registration pad. "
        "All context layers are excluded until the road passes Minecraft flyaround review. "
        "The road plan keeps the detailed 157-node centerline and reviewed variable-width logic; the vertical profile is rebuilt as a smoothed, continuously downhill engineered surface from the LiDAR centerline elevations. "
        "Astra hosts are air-backed so no hidden stone/terrain volume is introduced.\n",
        encoding="utf-8"
    )

    print(json.dumps({
        "file":str(litematic),
        "sha256":stats["sha256"],
        "region_position":stats["region_position"],
        "region_size":stats["region_size"],
        "astra_hosts":len(builder.hosts),
        "road_columns":road_columns,
        "road_microcells":road_cells,
        "endpoint_drop_m":report["profile"]["generated_endpoint_drop_m"],
        "max_profile_correction_m":report["profile"]["max_abs_smoothing_correction_m"],
        "validation":report["status"],
    },indent=2))
    if report["status"]!="valid":
        raise SystemExit(1)

if __name__=="__main__":
    main()
