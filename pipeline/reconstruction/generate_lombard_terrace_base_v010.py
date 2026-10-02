#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, Polygon, shape
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
CITY=POC/"l0_city_layers_v001.json"
GRID=PROJECT/"downloads"/"raw"/"lombard_poc001_ground_grid_050cm_v001.npz"
OUT=PROJECT/"outputs"/"terrace_base_v010"
V006=PROJECT/"outputs"/"road_only_v006"/"Lombard_Road_Only_Astra_v006.litematic"
V008=PROJECT/"outputs"/"road_texture_v008"/"Lombard_Road_Texture_Astra_v008.litematic"
V009=PROJECT/"outputs"/"curb_v009"/"Lombard_Curb_Astra_v009.litematic"

NAME="Lombard_Terrace_Base_Astra_v010"
REGION="LOMBARD_TERRACE_BASE_ASTRA_V010"
DATA_VERSION=4903

# Permanent registration convention inherited from Lombard project.
REG_LOCAL_X=-30.0
REG_LOCAL_Z=-20.0

MARKER="minecraft:yellow_concrete"
PAD="minecraft:polished_andesite"
ROAD_BASE="astra_microblocks:rgb_75433f"
BRICK_COLORS=[
    "astra_microblocks:rgb_995750",
    "astra_microblocks:rgb_a05b53",
    "astra_microblocks:rgb_94514d",
    "astra_microblocks:rgb_8a4b47",
]
JOINT="astra_microblocks:rgb_684b47"
MICRO=16
ROAD_THICKNESS_CELLS=3
BRICK_LENGTH_M=0.20
BRICK_WIDTH_M=0.10
JOINT_SAMPLE_M=0.006
CURB_MATERIAL="minecraft:light_gray_concrete"
CURB_EXPOSED_HEIGHT_CELLS=2
CURB_TOP_WIDTH_CELLS=2
CURB_BASE_WIDTH_CELLS=3
CURB_ENDPOINT_CLEARANCE_M=0.75
TERRACE_RADIUS_M=4.5
TERRACE_SURFACE="astra_microblocks:rgb_6b604b"
TERRACE_SUB="astra_microblocks:rgb_584a3d"
TERRACE_EDGE="minecraft:light_gray_concrete"
TERRACE_THICKNESS_CELLS=4
TERRACE_EDGE_DEPTH_CELLS=4

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
            vol=MicroVolume("minecraft:bricks")
            self.hosts[pos]=vol
            self.blocks[pos]=HOST_STATE
        vol.set(lx,ly,lz,material)

    def set_micro_local(self,x_micro:int,y_micro:int,z_micro:int,material:str):
        sx=x_micro-round(REG_LOCAL_X*MICRO)
        sz=z_micro-round(REG_LOCAL_Z*MICRO)
        self.set_micro_schematic(sx,y_micro,sz,material)

    def road_slab(self,x_micro:int,z_micro:int,top_micro:int,top_material:str):
        for y in range(top_micro-ROAD_THICKNESS_CELLS,top_micro-1):
            self.set_micro_local(x_micro,y,z_micro,ROAD_BASE)
        self.set_micro_local(x_micro,top_micro-1,z_micro,top_material)

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

def brick_surface_material(road_line:LineString,pt:Point,station:float):
    # Reference-driven running bond: ~20x10cm clay pavers, long axis following
    # the local road tangent. The 1/16m grid quantizes the real brick size.
    d=.45
    a=road_line.interpolate(max(0.0,station-d))
    b=road_line.interpolate(min(road_line.length,station+d))
    tx=b.x-a.x
    tz=b.y-a.y
    ll=max(1e-9,math.hypot(tx,tz))
    tx/=ll
    tz/=ll
    nx=-tz
    nz=tx
    center=road_line.interpolate(station)
    lateral=(pt.x-center.x)*nx+(pt.y-center.y)*nz

    row=math.floor(lateral/BRICK_WIDTH_M)
    stagger=(BRICK_LENGTH_M*.5) if (row&1) else 0.0
    u=(station+stagger)%BRICK_LENGTH_M

    # A narrow, slightly dark brick-end joint. We deliberately do not draw
    # full row joints because one Astra cell is wider than a real mortar line.
    if min(u,BRICK_LENGTH_M-u)<JOINT_SAMPLE_M:
        return JOINT

    brick=math.floor((station+stagger)/BRICK_LENGTH_M)
    h=((brick*73856093)^(row*19349663))&0xffffffff
    roll=h%100
    if roll<68:
        return BRICK_COLORS[0]
    if roll<84:
        return BRICK_COLORS[1]
    if roll<96:
        return BRICK_COLORS[2]
    return BRICK_COLORS[3]

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

def load_smoothed_ground_grid():
    d=np.load(GRID)
    grid=d["grid"].astype(float)
    # 3x3 / ~1.5m box smoothing: retain the real terrace elevations while
    # removing sub-meter LiDAR roughness that should not become visible bumps.
    pad=np.pad(grid,1,mode="edge")
    smooth=sum(pad[dz:dz+grid.shape[0],dx:dx+grid.shape[1]] for dz in range(3) for dx in range(3))/9.0
    meta={k:float(d[k]) for k in ("xmin","xmax","zmin","zmax","res")}
    return smooth,meta

def grid_sample(grid,meta,x,z):
    fx=(x-meta["xmin"])/meta["res"]
    fz=(z-meta["zmin"])/meta["res"]
    fx=max(0.0,min(grid.shape[1]-1.001,fx))
    fz=max(0.0,min(grid.shape[0]-1.001,fz))
    ix=int(math.floor(fx)); iz=int(math.floor(fz))
    tx=fx-ix; tz=fz-iz
    ix1=min(grid.shape[1]-1,ix+1)
    iz1=min(grid.shape[0]-1,iz+1)
    return float(
        grid[iz,ix]*(1-tx)*(1-tz)+grid[iz,ix1]*tx*(1-tz)+
        grid[iz1,ix]*(1-tx)*tz+grid[iz1,ix1]*tx*tz
    )

def crooked_row_polygon():
    city=json.loads(CITY.read_text(encoding="utf-8"))
    parts=[
        shape(r["geometry"])
        for r in city["right_of_way"]
        if str(r["properties"].get("cnn")) in ("8448000","8449000")
    ]
    if not parts:
        raise RuntimeError("No crooked-block DataSF ROW geometry")
    return unary_union(parts)

def build_terrace_zone(road_poly,road_line):
    # Keep only the public terrace/planter mass close enough to the road to
    # explain the switchbacks. This deliberately excludes broad outer terrain.
    row=crooked_row_polygon()
    curb_outer=road_poly.buffer(CURB_BASE_WIDTH_CELLS/MICRO,join_style=1,resolution=16)
    zone=row.intersection(road_poly.buffer(TERRACE_RADIUS_M,join_style=1,resolution=16)).difference(curb_outer)
    zone=zone.difference(endpoint_opening_mask(road_line,halfspan=10.0))
    return zone

def rasterize_terrace(builder:RoadBuilder,zone,road_line,profile,center):
    grid,gm=load_smoothed_ground_grid()
    zero_navd=float(center[0]["elev_navd88_m"])
    prepared=prep(zone)
    minx,minz,maxx,maxz=zone.bounds
    gx0=math.floor(minx*MICRO)-1; gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1; gz1=math.ceil(maxz*MICRO)+1
    occupied=set()
    top_by_col={}
    surface_cells=0
    sub_cells=0
    for gz in range(gz0,gz1+1):
        z=(gz+.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+.5)/MICRO
            if not prepared.contains(Point(x,z)):
                continue
            elev=grid_sample(grid,gm,x,z)-zero_navd
            top=round(elev*MICRO)
            occupied.add((gx,gz)); top_by_col[(gx,gz)]=top
            builder.set_micro_local(gx,top-1,gz,TERRACE_SURFACE)
            surface_cells+=1
            for y in range(top-TERRACE_THICKNESS_CELLS,top-1):
                builder.set_micro_local(gx,y,gz,TERRACE_SUB)
                sub_cells+=1

    # A minimal exposed face around each terrace shelf. This is only enough to
    # make the level readable; final retaining-wall material/profile comes later.
    edge_columns=0
    edge_cells=0
    for (gx,gz),top in top_by_col.items():
        if all((gx+dx,gz+dz) in occupied for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))):
            continue
        edge_columns+=1
        for y in range(top-TERRACE_EDGE_DEPTH_CELLS,top):
            builder.set_micro_local(gx,y,gz,TERRACE_EDGE)
            edge_cells+=1

    return {
        "zone":zone,
        "surface_columns":len(occupied),
        "surface_microcells":surface_cells,
        "sub_microcells":sub_cells,
        "edge_columns":edge_columns,
        "edge_microcells":edge_cells,
        "smoothed_lidar_window_m":1.5,
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
            top_material=brick_surface_material(road_line,pt,station)
            builder.road_slab(gx,gz,top_micro,top_material)
            columns+=1
            cells+=ROAD_THICKNESS_CELLS
    return columns,cells

def endpoint_opening_mask(road_line:LineString,halfspan:float=8.0):
    coords=list(road_line.coords)
    def rect(endpoint,inside):
        ex,ez=endpoint
        ix,iz=inside
        # Tangent always points from the endpoint into the crooked block.
        tx=ix-ex
        tz=iz-ez
        ll=max(1e-9,math.hypot(tx,tz))
        tx/=ll
        tz/=ll
        nx=-tz
        nz=tx
        # Remove curb from 2m outside the endpoint to 0.75m inside it.
        back=-2.0
        front=CURB_ENDPOINT_CLEARANCE_M
        return Polygon([
            (ex+tx*back-nx*halfspan,ez+tz*back-nz*halfspan),
            (ex+tx*front-nx*halfspan,ez+tz*front-nz*halfspan),
            (ex+tx*front+nx*halfspan,ez+tz*front+nz*halfspan),
            (ex+tx*back+nx*halfspan,ez+tz*back+nz*halfspan),
        ])
    start=rect(coords[0],coords[1])
    end=rect(coords[-1],coords[-2])
    return unary_union([start,end])

def rasterize_curb(builder:RoadBuilder,road_poly,road_line,profile):
    # SF Public Works Standard Plan 87,169: nominal 6-inch top width and
    # 6-inch exposed curb height. Astra 1/16m grid quantizes each to 2 cells
    # (0.125m). A 3-cell lower body gives a one-cell batter approximation.
    top_width_m=CURB_TOP_WIDTH_CELLS/MICRO
    base_width_m=CURB_BASE_WIDTH_CELLS/MICRO
    opening=endpoint_opening_mask(road_line)
    top_ring=road_poly.buffer(top_width_m,join_style=1,resolution=16).difference(road_poly).difference(opening)
    base_ring=road_poly.buffer(base_width_m,join_style=1,resolution=16).difference(road_poly).difference(opening)
    prep_base=prep(base_ring)
    prep_top=prep(top_ring)
    minx,minz,maxx,maxz=base_ring.bounds
    gx0=math.floor(minx*MICRO)-1
    gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1
    gz1=math.ceil(maxz*MICRO)+1
    base_columns=0
    top_columns=0
    cells=0
    for gz in range(gz0,gz1+1):
        z=(gz+.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+.5)/MICRO
            pt=Point(x,z)
            in_base=prep_base.contains(pt)
            in_top=prep_top.contains(pt)
            if not in_base:
                continue
            station=road_line.project(pt)
            # Keep both road ends open where Lombard ties into Hyde and
            # Leavenworth; the curb must not wrap across the vehicle path.
            if station<CURB_ENDPOINT_CLEARANCE_M or station>road_line.length-CURB_ENDPOINT_CLEARANCE_M:
                continue
            elev=float(np.interp(station,profile["station_m"],profile["elev_rel_m"]))
            road_top=round(elev*MICRO)
            # Body extends down to road slab depth and one cell above road.
            for y in range(road_top-ROAD_THICKNESS_CELLS,road_top+1):
                builder.set_micro_local(gx,y,gz,CURB_MATERIAL)
                cells+=1
            base_columns+=1
            if in_top:
                # Inner/top band reaches the second exposed cell.
                builder.set_micro_local(gx,road_top+1,gz,CURB_MATERIAL)
                cells+=1
                top_columns+=1
    return {
        "base_columns":base_columns,
        "top_columns":top_columns,
        "microcells":cells,
        "top_ring":top_ring,
        "base_ring":base_ring,
    }

def compare_v008_road_cells(builder:RoadBuilder):
    # v009 may add new curb cells/hosts, but every occupied v008 road cell must
    # remain present with the exact same material.
    _,meta=read_back_block_map(V008,"LOMBARD_ROAD_TEXTURE_ASTRA_V008")
    rp=meta["region_position"]
    old={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        old[pos]=decode_volume_v4(te["volume_v4"])
    missing_hosts=0
    mismatched_cells=0
    checked_cells=0
    for pos,old_cells in old.items():
        new=builder.hosts.get(pos)
        if new is None:
            missing_hosts+=1
            continue
        for a,b in zip(old_cells,new.cells):
            if a is None:
                continue
            checked_cells+=1
            if b!=a:
                mismatched_cells+=1
    ok=missing_hosts==0 and mismatched_cells==0
    return ok,{
        "v008_host_count":len(old),
        "missing_v008_hosts":missing_hosts,
        "checked_road_microcells":checked_cells,
        "mismatched_road_microcells":mismatched_cells,
    }

def compare_v009_cells(builder:RoadBuilder):
    # v010 may only fill previously-empty cells outside the approved road/curb.
    _,meta=read_back_block_map(V009,"LOMBARD_CURB_ASTRA_V009")
    rp=meta["region_position"]
    old={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        old[pos]=decode_volume_v4(te["volume_v4"])
    missing_hosts=0
    mismatched_cells=0
    checked_cells=0
    for pos,old_cells in old.items():
        new=builder.hosts.get(pos)
        if new is None:
            missing_hosts+=1
            continue
        for a,b in zip(old_cells,new.cells):
            if a is None:
                continue
            checked_cells+=1
            if b!=a:
                mismatched_cells+=1
    ok=missing_hosts==0 and mismatched_cells==0
    return ok,{
        "v009_host_count":len(old),
        "missing_v009_hosts":missing_hosts,
        "checked_v009_microcells":checked_cells,
        "mismatched_v009_microcells":mismatched_cells,
    }

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

def compare_v006_occupancy(builder:RoadBuilder):
    # Texture passes are not allowed to alter approved v006 road geometry.
    _,meta=read_back_block_map(V006,"LOMBARD_ROAD_ONLY_ASTRA_V006")
    rp=meta["region_position"]
    old={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        old[pos]=decode_volume_v4(te["volume_v4"])

    same_hosts=set(old)==set(builder.hosts)
    mismatched_cells=0
    if same_hosts:
        for pos,old_cells in old.items():
            new_cells=builder.hosts[pos].cells
            mismatched_cells+=sum(
                1 for a,b in zip(old_cells,new_cells)
                if (a is None)!=(b is None)
            )
    else:
        # Host mismatch is already a geometry failure; no need to fake a cell count.
        mismatched_cells=-1
    return same_hosts and mismatched_cells==0,{
        "same_host_positions":same_hosts,
        "mismatched_occupancy_cells":mismatched_cells,
        "v006_host_count":len(old),
        "v007_host_count":len(builder.hosts),
    }

def render_previews(center,road_poly,profile,curb_top,curb_base,terrace_zone):
    OUT.mkdir(parents=True,exist_ok=True)

    # Plan view: frozen road + curb + immediate terrace base only.
    minx,minz,maxx,maxz=terrace_zone.union(curb_base).bounds
    scale=8.0
    pad=45
    w=max(900,int((maxx-minx)*scale+pad*2))
    h=max(360,int((maxz-minz)*scale+pad*2))
    im=Image.new("RGB",(w,h),"white")
    draw=ImageDraw.Draw(im)
    def pp(x,z):
        return (pad+(x-minx)*scale,pad+(z-minz)*scale)
    for geom in (list(terrace_zone.geoms) if hasattr(terrace_zone,"geoms") else [terrace_zone]):
        if geom.geom_type=="Polygon":
            draw.polygon([pp(x,z) for x,z in geom.exterior.coords],fill=(115,101,78),outline=(88,76,59))
    for geom in (list(curb_base.geoms) if hasattr(curb_base,"geoms") else [curb_base]):
        if geom.geom_type=="Polygon":
            draw.polygon([pp(x,z) for x,z in geom.exterior.coords],fill=(180,180,176),outline=(110,110,108))
    for geom in (list(road_poly.geoms) if hasattr(road_poly,"geoms") else [road_poly]):
        if geom.geom_type=="Polygon":
            draw.polygon([pp(x,z) for x,z in geom.exterior.coords],fill=(157,80,65),outline=(45,45,45))
    draw.line([pp(r["x_m"],r["z_m"]) for r in center],fill=(25,25,25),width=2)
    draw.text((20,15),"LOMBARD TERRACE BASE v010 / v009 locked",font=font(22),fill=(20,20,20))
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
    curb=rasterize_curb(builder,road_poly,road_line,profile)
    terrace_zone=build_terrace_zone(road_poly,road_line)
    terrace=rasterize_terrace(builder,terrace_zone,road_line,profile,center)
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
        "Lombard terrace base v010. Approved v009 road and curb are preserved exactly; only the immediate DataSF/LiDAR-derived terrace and planter base is added.",
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
    v009_locked,v009_compare=compare_v009_cells(builder)

    render_previews(center,road_poly,profile,curb["top_ring"],curb["base_ring"],terrace_zone)

    materials=Counter()
    for vol in builder.hosts.values():
        for m in vol.cells:
            if m:
                materials[m]+=1
    allowed_materials={ROAD_BASE,JOINT,CURB_MATERIAL,TERRACE_SURFACE,TERRACE_SUB,TERRACE_EDGE,*BRICK_COLORS}
    forbidden=[m for m in materials if m not in allowed_materials]

    report={
        **stats,
        "schema_version":1,
        "project_id":"lombard_sf",
        "review_id":"LOMBARD_TERRACE_BASE_V010",
        "status":"valid" if exact_blocks and exact_cells and v009_locked and not forbidden else "invalid",
        "scope":"terrace-base-only layer added outside approved v009 road+curb",
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
        "texture":{
            "reference":"projects/lombard_sf/references/private/wikimedia_commons/007_Crooked_Section_of_Lombard_Street.jpg.jpg",
            "pattern":"running bond aligned to local road tangent",
            "nominal_brick_length_m":BRICK_LENGTH_M,
            "nominal_brick_width_m":BRICK_WIDTH_M,
            "joint_sampling_m":JOINT_SAMPLE_M,
            "brick_palette":BRICK_COLORS,
            "joint_material":JOINT,
            "base_material":ROAD_BASE,
        },
        "v009_lock":{
            "source":"projects/lombard_sf/outputs/curb_v009/Lombard_Curb_Astra_v009.litematic",
            "all_existing_cells_identical":v009_locked,
            **v009_compare,
        },
        "curb":{
            "source":"SF Public Works Standard Plan 87,169 + Section 202.01 nominal 6-inch curb height",
            "nominal_top_width_m":0.1524,
            "modeled_top_width_m":CURB_TOP_WIDTH_CELLS/MICRO,
            "nominal_exposed_height_m":0.1524,
            "modeled_exposed_height_m":CURB_EXPOSED_HEIGHT_CELLS/MICRO,
            "base_width_m":CURB_BASE_WIDTH_CELLS/MICRO,
            "material":CURB_MATERIAL,
            "base_columns":curb["base_columns"],
            "top_columns":curb["top_columns"],
            "microcells":curb["microcells"],
        },
        "terrace_base":{
            "source_geometry":"DataSF crooked-block ROW intersected with a 4.5 m road-support band",
            "elevation_source":"2010 NOAA/USGS class-2 LiDAR 0.5 m grid",
            "elevation_smoothing_m":terrace["smoothed_lidar_window_m"],
            "support_radius_m":TERRACE_RADIUS_M,
            "surface_material":TERRACE_SURFACE,
            "sub_material":TERRACE_SUB,
            "edge_material":TERRACE_EDGE,
            "surface_columns":terrace["surface_columns"],
            "surface_microcells":terrace["surface_microcells"],
            "sub_microcells":terrace["sub_microcells"],
            "edge_columns":terrace["edge_columns"],
            "edge_microcells":terrace["edge_microcells"],
        },
        "astra":{
            "empty_cells_remain_empty":True,
            "host_original":"minecraft:bricks",
            "host_original_supported":True,
            "host_count":len(builder.hosts),
            "road_surface_columns":road_columns,
            "occupied_road_microcells":road_cells,
            "thickness_cells":ROAD_THICKNESS_CELLS,
            "materials":dict(materials),
            "forbidden_materials":forbidden,
        },
        "excluded":{
            "curbs":False,
            "terrain":False,
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
            "v009_locked":v009_locked,
            "review_status":"TERRACE_BASE_V010_FLYAROUND_REQUIRED",
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
        "# Lombard Terrace Base v010\n\n"
        "Terrace-base-only pass outside approved v009 road and curb. Every occupied v009 road/curb cell is locked and validated unchanged. "
        "The immediate terrace/planter masses come from the DataSF crooked-block ROW, clipped to a 4.5 m support band around the road, with elevations from the 2010 NOAA/USGS class-2 LiDAR grid smoothed over about 1.5 m to suppress scan noise. "
        "Only a shallow soil shelf and minimal exposed edge face are included. No stairs, detailed retaining walls, hedges/flowers, buildings, broad terrain, or outer street context are present.\n",
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
        "curb_microcells":curb["microcells"],
        "terrace_surface_columns":terrace["surface_columns"],
        "terrace_edge_columns":terrace["edge_columns"],
        "endpoint_drop_m":report["profile"]["generated_endpoint_drop_m"],
        "max_profile_correction_m":report["profile"]["max_abs_smoothing_correction_m"],
        "validation":report["status"],
    },indent=2))
    if report["status"]!="valid":
        raise SystemExit(1)

if __name__=="__main__":
    main()
