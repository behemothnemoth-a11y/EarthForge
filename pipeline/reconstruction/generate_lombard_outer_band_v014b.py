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
OUT=PROJECT/"outputs"/"outer_band_v014b"
V006=PROJECT/"outputs"/"road_only_v006"/"Lombard_Road_Only_Astra_v006.litematic"
V008=PROJECT/"outputs"/"road_texture_v008"/"Lombard_Road_Texture_Astra_v008.litematic"
V009=PROJECT/"outputs"/"curb_v009"/"Lombard_Curb_Astra_v009.litematic"
V010=PROJECT/"outputs"/"terrace_base_v010"/"Lombard_Terrace_Base_Astra_v010.litematic"
V011=PROJECT/"outputs"/"edge_height_v011"/"Lombard_Edge_Height_Astra_v011.litematic"
V012=PROJECT/"outputs"/"retaining_v012"/"Lombard_Retaining_Astra_v012.litematic"
V014=PROJECT/"outputs"/"outer_band_v014"/"Lombard_Outer_Band_Astra_v014.litematic"

NAME="Lombard_Outer_Band_Astra_v014b"
REGION="LOMBARD_OUTER_BAND_ASTRA_V014B"
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
EDGE_RAISE_MIN_EXCESS_M=0.125
EDGE_RAISE_MAX_EXCESS_M=0.50
EDGE_RAISE_MATERIAL="minecraft:light_gray_concrete"
RETAINING_MIN_EXCESS_M=0.50
RETAINING_FACE="minecraft:light_gray_concrete"
RETAINING_CAP="minecraft:smooth_stone"
RETAINING_CAP_CELLS=2
OUTER_BAND_RADIUS_M=6.5
OUTER_BAND_INNER_RADIUS_M=TERRACE_RADIUS_M
OUTER_BAND_SEAM_M=0.25

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

def build_expanded_terrace_zone(road_poly,road_line):
    row=crooked_row_polygon()
    curb_outer=road_poly.buffer(CURB_BASE_WIDTH_CELLS/MICRO,join_style=1,resolution=16)
    zone=row.intersection(road_poly.buffer(OUTER_BAND_RADIUS_M,join_style=1,resolution=16)).difference(curb_outer)
    zone=zone.difference(endpoint_opening_mask(road_line,halfspan=10.0))
    return zone

def build_outer_band(old_zone,new_zone):
    return new_zone.difference(old_zone)

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

    # v014b boundary cleanup: the current review footprint is NOT physical
    # geometry. Do not turn its perimeter into a wall/cliff. Real retaining
    # faces are generated separately from source/elevation evidence.
    edge_columns=0
    edge_cells=0

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

def rasterize_local_edge_raises(builder:RoadBuilder,curb_base_ring,terrace_zone,road_line,profile,center):
    grid,gm=load_smoothed_ground_grid()
    zero_navd=float(center[0]["elev_navd88_m"])
    prepared=prep(curb_base_ring)
    terrace_check=prep(terrace_zone.buffer(.12))
    minx,minz,maxx,maxz=curb_base_ring.bounds
    gx0=math.floor(minx*MICRO)-1; gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1; gz1=math.ceil(maxz*MICRO)+1
    raised_columns=0
    added_cells=0
    raised_stations=[]
    deferred_stations=[]
    excess_values=[]
    for gz in range(gz0,gz1+1):
        z=(gz+.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+.5)/MICRO
            p=Point(x,z)
            if not prepared.contains(p):
                continue
            station=road_line.project(p)
            centerp=road_line.interpolate(station)
            dx=x-centerp.x; dz=z-centerp.y
            ll=max(1e-9,math.hypot(dx,dz))
            nx=dx/ll; nz=dz/ll
            sample=Point(x+nx*.25,z+nz*.25)
            if not terrace_check.contains(sample):
                continue
            road_e=float(np.interp(station,profile["station_m"],profile["elev_rel_m"]))
            terrace_e=grid_sample(grid,gm,sample.x,sample.y)-zero_navd
            standard_top=road_e+CURB_EXPOSED_HEIGHT_CELLS/MICRO
            excess=terrace_e-standard_top
            if excess>EDGE_RAISE_MAX_EXCESS_M:
                deferred_stations.append(float(station))
                continue
            if excess<EDGE_RAISE_MIN_EXCESS_M:
                continue
            road_top=round(road_e*MICRO)
            target_top=round(terrace_e*MICRO)
            start=road_top+1
            if target_top<=start:
                continue
            for y in range(start,target_top):
                builder.set_micro_local(gx,y,gz,EDGE_RAISE_MATERIAL)
                added_cells+=1
            raised_columns+=1
            raised_stations.append(float(station))
            excess_values.append(float(excess))

    def bands(stations,gap=.9):
        if not stations:
            return []
        s=sorted(set(round(v,2) for v in stations))
        groups=[[s[0]]]
        for v in s[1:]:
            if v-groups[-1][-1]<=gap:
                groups[-1].append(v)
            else:
                groups.append([v])
        return [
            {"station_start_m":g[0],"station_end_m":g[-1],"length_m":round(g[-1]-g[0],2)}
            for g in groups if g[-1]-g[0]>=.5
        ]

    return {
        "raised_columns":raised_columns,
        "added_microcells":added_cells,
        "min_excess_m":EDGE_RAISE_MIN_EXCESS_M,
        "max_excess_m":EDGE_RAISE_MAX_EXCESS_M,
        "mean_applied_excess_m":float(sum(excess_values)/len(excess_values)) if excess_values else 0.0,
        "max_applied_excess_m":max(excess_values) if excess_values else 0.0,
        "raised_station_bands":bands(raised_stations),
        "deferred_retaining_station_bands":bands(deferred_stations),
        "deferred_reason":"terrace exceeds standard curb by >0.50 m; treat as retaining-wall geometry, not taller curb"
    }

def rasterize_retaining_walls(builder:RoadBuilder,curb_base_ring,terrace_zone,road_line,profile,center):
    grid,gm=load_smoothed_ground_grid()
    zero_navd=float(center[0]["elev_navd88_m"])
    prepared=prep(curb_base_ring)
    terrace_check=prep(terrace_zone.buffer(.12))
    minx,minz,maxx,maxz=curb_base_ring.bounds
    gx0=math.floor(minx*MICRO)-1; gx1=math.ceil(maxx*MICRO)+1
    gz0=math.floor(minz*MICRO)-1; gz1=math.ceil(maxz*MICRO)+1
    wall_columns=0
    face_cells=0
    cap_cells=0
    heights=[]
    stations=[]

    for gz in range(gz0,gz1+1):
        z=(gz+.5)/MICRO
        for gx in range(gx0,gx1+1):
            x=(gx+.5)/MICRO
            p=Point(x,z)
            if not prepared.contains(p):
                continue

            station=road_line.project(p)
            centerp=road_line.interpolate(station)
            dx=x-centerp.x; dz=z-centerp.y
            ll=max(1e-9,math.hypot(dx,dz))
            nx=dx/ll; nz=dz/ll
            sample=Point(x+nx*.25,z+nz*.25)
            if not terrace_check.contains(sample):
                continue

            road_e=float(np.interp(station,profile["station_m"],profile["elev_rel_m"]))
            terrace_e=grid_sample(grid,gm,sample.x,sample.y)-zero_navd
            standard_curb_top=road_e+CURB_EXPOSED_HEIGHT_CELLS/MICRO
            excess=terrace_e-standard_curb_top
            if excess<=RETAINING_MIN_EXCESS_M:
                continue

            road_top=round(road_e*MICRO)
            target_top=round(terrace_e*MICRO)
            start=road_top+1
            if target_top-start<=RETAINING_CAP_CELLS:
                continue

            cap_start=max(start,target_top-RETAINING_CAP_CELLS)
            for y in range(start,cap_start):
                builder.set_micro_local(gx,y,gz,RETAINING_FACE)
                face_cells+=1
            for y in range(cap_start,target_top):
                builder.set_micro_local(gx,y,gz,RETAINING_CAP)
                cap_cells+=1

            wall_columns+=1
            heights.append((target_top-start)/MICRO)
            stations.append(float(station))

    def bands(values,gap=.9):
        if not values:
            return []
        s=sorted(set(round(v,2) for v in values))
        groups=[[s[0]]]
        for v in s[1:]:
            if v-groups[-1][-1]<=gap:
                groups[-1].append(v)
            else:
                groups.append([v])
        return [
            {"station_start_m":g[0],"station_end_m":g[-1],"length_m":round(g[-1]-g[0],2)}
            for g in groups if g[-1]-g[0]>=.5
        ]

    return {
        "wall_columns":wall_columns,
        "face_microcells":face_cells,
        "cap_microcells":cap_cells,
        "total_added_microcells":face_cells+cap_cells,
        "min_height_m":min(heights) if heights else 0.0,
        "mean_height_m":float(sum(heights)/len(heights)) if heights else 0.0,
        "max_height_m":max(heights) if heights else 0.0,
        "station_bands":bands(stations),
        "face_material":RETAINING_FACE,
        "cap_material":RETAINING_CAP,
        "source_rule":"build only where smoothed LiDAR terrace exceeds standard curb by >0.50 m"
    }

def compare_v014_boundary_cleanup(builder:RoadBuilder,new_zone):
    _,meta=read_back_block_map(V014,"LOMBARD_OUTER_BAND_ASTRA_V014")
    rp=meta["region_position"]
    old={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        old[pos]=decode_volume_v4(te["volume_v4"])

    new={pos:vol.cells for pos,vol in builder.hosts.items()}
    boundary_check=prep(new_zone.boundary.buffer(.20))
    changed=outside=bad_source=0
    replacements={}
    for pos in set(old)|set(new):
        a_cells=old.get(pos,[None]*4096)
        b_cells=new.get(pos,[None]*4096)
        hx,hy,hz=pos
        for i,(a,b) in enumerate(zip(a_cells,b_cells)):
            if a==b:
                continue
            changed+=1
            lx=i%16; lz=(i//16)%16
            local_x_micro=hx*16+lx+round(REG_LOCAL_X*MICRO)
            local_z_micro=hz*16+lz+round(REG_LOCAL_Z*MICRO)
            x=(local_x_micro+.5)/MICRO; z=(local_z_micro+.5)/MICRO
            if not boundary_check.contains(Point(x,z)):
                outside+=1
            if a!=TERRACE_EDGE:
                bad_source+=1
            key=f"{a}->{b}"
            replacements[key]=replacements.get(key,0)+1
    return outside==0 and bad_source==0,{
        "changed_microcells":changed,
        "changes_outside_review_boundary":outside,
        "changes_not_from_generic_terrace_edge":bad_source,
        "replacement_counts":replacements,
    }

def compare_v012_outer_band_changes(builder:RoadBuilder,old_zone,new_zone):
    _,meta=read_back_block_map(V012,"LOMBARD_RETAINING_ASTRA_V012")
    rp=meta["region_position"]
    old={}
    for te in meta["tile_entities"]:
        if te.get("id")!=BLOCK_ENTITY_ID:
            continue
        pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
        old[pos]=decode_volume_v4(te["volume_v4"])

    # Allow the new 2m band plus a 0.25m seam just inside the former review edge.
    seam=new_zone.difference(old_zone.buffer(-OUTER_BAND_SEAM_M))
    check=prep(seam.buffer(.08))
    new={pos:vol.cells for pos,vol in builder.hosts.items()}
    changed=added=removed=replaced=outside=0
    for pos in set(old)|set(new):
        a_cells=old.get(pos,[None]*4096)
        b_cells=new.get(pos,[None]*4096)
        hx,hy,hz=pos
        for i,(a,b) in enumerate(zip(a_cells,b_cells)):
            if a==b:
                continue
            changed+=1
            if a is None and b is not None: added+=1
            elif a is not None and b is None: removed+=1
            else: replaced+=1
            lx=i%16; lz=(i//16)%16
            local_x_micro=hx*16+lx+round(REG_LOCAL_X*MICRO)
            local_z_micro=hz*16+lz+round(REG_LOCAL_Z*MICRO)
            x=(local_x_micro+.5)/MICRO; z=(local_z_micro+.5)/MICRO
            if not check.contains(Point(x,z)):
                outside+=1
    return outside==0,{
        "changed_microcells":changed,
        "added_microcells":added,
        "removed_microcells":removed,
        "replaced_microcells":replaced,
        "changes_outside_outer_band_or_seam":outside,
    }

def compare_v011_cells(builder:RoadBuilder):
    _,meta=read_back_block_map(V011,"LOMBARD_EDGE_HEIGHT_ASTRA_V011")
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
        "v011_host_count":len(old),
        "missing_v011_hosts":missing_hosts,
        "checked_v011_microcells":checked_cells,
        "mismatched_v011_microcells":mismatched_cells,
    }

def compare_v010_cells(builder:RoadBuilder):
    _,meta=read_back_block_map(V010,"LOMBARD_TERRACE_BASE_ASTRA_V010")
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
        "v010_host_count":len(old),
        "missing_v010_hosts":missing_hosts,
        "checked_v010_microcells":checked_cells,
        "mismatched_v010_microcells":mismatched_cells,
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
    draw.text((20,15),"LOMBARD OUTER BAND v014b / OPEN REVIEW BOUNDARY",font=font(22),fill=(20,20,20))
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
    old_terrace_zone=build_terrace_zone(road_poly,road_line)
    terrace_zone=build_expanded_terrace_zone(road_poly,road_line)
    outer_band=build_outer_band(old_terrace_zone,terrace_zone)
    terrace=rasterize_terrace(builder,terrace_zone,road_line,profile,center)
    edge_raise=rasterize_local_edge_raises(builder,curb["base_ring"],terrace_zone,road_line,profile,center)
    retaining=rasterize_retaining_walls(builder,curb["base_ring"],terrace_zone,road_line,profile,center)
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
        "Lombard outer band v014b. Same controlled 2m outward LiDAR/ROW ground expansion as v014, but generic vertical faces at the temporary review boundary are removed. Real retaining walls remain source-driven.",
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
    v012_band_ok,v012_band_compare=compare_v012_outer_band_changes(builder,old_terrace_zone,terrace_zone)
    v014_cleanup_ok,v014_cleanup_compare=compare_v014_boundary_cleanup(builder,terrace_zone)

    render_previews(center,road_poly,profile,curb["top_ring"],curb["base_ring"],terrace_zone)

    materials=Counter()
    for vol in builder.hosts.values():
        for m in vol.cells:
            if m:
                materials[m]+=1
    allowed_materials={ROAD_BASE,JOINT,CURB_MATERIAL,TERRACE_SURFACE,TERRACE_SUB,TERRACE_EDGE,RETAINING_FACE,RETAINING_CAP,*BRICK_COLORS}
    forbidden=[m for m in materials if m not in allowed_materials]

    report={
        **stats,
        "schema_version":1,
        "project_id":"lombard_sf",
        "review_id":"LOMBARD_OUTER_BAND_V014B",
        "status":"valid" if exact_blocks and exact_cells and v009_locked and v012_band_ok and v014_cleanup_ok and not forbidden else "invalid",
        "scope":"v014 controlled 2m ground band with temporary review-boundary cliff faces removed; no stairs or new feature systems",
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
        "road_curb_lock":{
            "source":"projects/lombard_sf/outputs/curb_v009/Lombard_Curb_Astra_v009.litematic",
            "all_existing_cells_identical":v009_locked,
            **v009_compare,
        },
        "v012_controlled_expansion":{
            "source":"projects/lombard_sf/outputs/retaining_v012/Lombard_Retaining_Astra_v012.litematic",
            "all_changes_confined_to_outer_band_or_seam":v012_band_ok,
            **v012_band_compare,
        },
        "v014_boundary_cleanup":{
            "source":"projects/lombard_sf/outputs/outer_band_v014/Lombard_Outer_Band_Astra_v014.litematic",
            "only_generic_review_edge_faces_changed":v014_cleanup_ok,
            **v014_cleanup_compare,
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
        "edge_height_corrections":{
            "rule":"raise only where smoothed LiDAR terrace sits 0.125-0.50 m above the standard curb; >0.50 m is deferred to the retaining-wall pass",
            "material":EDGE_RAISE_MATERIAL,
            **edge_raise,
        },
        "retaining_walls":{
            **retaining,
        },
        "outer_band":{
            "inner_radius_m":OUTER_BAND_INNER_RADIUS_M,
            "outer_radius_m":OUTER_BAND_RADIUS_M,
            "band_width_m":OUTER_BAND_RADIUS_M-OUTER_BAND_INNER_RADIUS_M,
            "source_geometry":"DataSF crooked-block ROW",
            "elevation_source":"2010 NOAA/USGS class-2 LiDAR 0.5m project grid, same 1.5m smoothing as v012",
            "area_m2":outer_band.area,
            "seam_allowance_m":OUTER_BAND_SEAM_M,
            "new_feature_systems":False,
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
            "retaining_walls":False,
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
            "road_curb_v009_locked":v009_locked,
            "v012_changes_confined_to_outer_band_or_seam":v012_band_ok,
            "v014_boundary_cleanup_only":v014_cleanup_ok,
            "review_status":"OUTER_BAND_V014B_FLYAROUND_REQUIRED",
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
        "# Lombard Outer Band v014b — Boundary Cleanup\n\n"
        "This is the same one-band outward expansion as v014, still returning to accepted v012 and still adding no stairs or other feature systems. "
        "The correction is that the temporary outer review boundary is no longer rendered as a physical concrete cliff. Generic terrace-edge faces at that cutoff are omitted; only real source/elevation-driven retaining walls remain. "
        "The 2m LiDAR/ROW ground band itself is preserved.\n",
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
        "raised_edge_columns":edge_raise["raised_columns"],
        "raised_edge_microcells":edge_raise["added_microcells"],
        "retaining_wall_columns":retaining["wall_columns"],
        "retaining_wall_microcells":retaining["total_added_microcells"],
        "outer_band_area_m2":outer_band.area,
        "v012_changed_microcells":v012_band_compare["changed_microcells"],
        "v014_boundary_cleanup_microcells":v014_cleanup_compare["changed_microcells"],
        "endpoint_drop_m":report["profile"]["generated_endpoint_drop_m"],
        "max_profile_correction_m":report["profile"]["max_abs_smoothing_correction_m"],
        "validation":report["status"],
    },indent=2))
    if report["status"]!="valid":
        raise SystemExit(1)

if __name__=="__main__":
    main()
