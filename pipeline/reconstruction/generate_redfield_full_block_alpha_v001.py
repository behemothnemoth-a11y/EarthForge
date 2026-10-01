#!/usr/bin/env python3
"""Redfield Main 600 block full-block alpha.

Purpose:
- carry the approved LiDAR MicroGrade through the entire block;
- preserve the v002 native/photo-proportional 617-627 west frontage;
- author native current-photo facades for the remaining west/east buildings;
- use the mapped outer footprints + LiDAR roof bands for building massing;
- keep raw licensed/reference imagery private.

This is a block-scale review candidate, not final facade detailing.
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
    decode_volume_v4,
    tile_entity_payload,
)
from pipeline.reconstruction.facade_module_compiler import (
    FacadeCanvas,
    FacadePlacement,
)
from pipeline.reconstruction import generate_redfield_west_main_trueframe_v002 as westv2
from pipeline.terrain import generate_redfield_poc001_micrograde_v001 as micrograde

PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"
AUTHORITY = POC / "full_block_facade_authority_v001.json"
GEOM = POC / "l0_geometry_local.json"
LIDAR = (
    PROJECT
    / "downloads/multisource_v001/lidar_spink_2012/"
      "redfield_poc001_roi_points.csv"
)
OUT = PROJECT / "outputs" / "full_block_alpha_v001"
NAME = "Redfield_POC_001_FullBlock_FacadeAlpha_v001"
REGION = "REDFIELD_POC001_FULLBLOCK_FACADE_ALPHA_V001"

SIDE_WALL = "minecraft:bricks"
ROOF = "minecraft:gray_concrete"
ROOF_EDGE = "minecraft:light_gray_concrete"

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def rgb(value: str) -> str:
    if value.startswith("astra_microblocks:"):
        return value
    if value.startswith("rgb_"):
        return "astra_microblocks:" + value
    if value.startswith("#"):
        return "astra_microblocks:rgb_" + value[1:].lower()
    return value

def palette(item: dict, key: str, fallback: str = "rgb_888888") -> str:
    return rgb(item.get("palette", {}).get(key, fallback))

def load_lidar():
    out=[]
    with LIDAR.open(encoding="utf-8",newline="") as fh:
        for row in csv.DictReader(fh):
            out.append((
                float(row["x_local_m"]),
                float(row["z_local_m"]),
                float(row["elev_m"]),
                int(row["class"]),
            ))
    return out

def polygon_bounds(poly):
    xs=[p[0] for p in poly]; zs=[p[1] for p in poly]
    return min(xs),max(xs),min(zs),max(zs)

def inside(x,z,poly):
    hit=False
    j=len(poly)-1
    for i,(xi,zi) in enumerate(poly):
        xj,zj=poly[j]
        if ((zi>z)!=(zj>z)) and (x < (xj-xi)*(z-zi)/(zj-zi+1e-300)+xi):
            hit=not hit
        j=i
    return hit

def union_inside(x,z,polys):
    return any(inside(x,z,p) for p in polys)

def union_bounds(polys):
    b=[polygon_bounds(p) for p in polys]
    return min(x[0] for x in b),max(x[1] for x in b),min(x[2] for x in b),max(x[3] for x in b)

def raster_union(polys):
    xmin,xmax,zmin,zmax=union_bounds(polys)
    out=set()
    for x in range(math.floor(xmin),math.ceil(xmax)):
        for z in range(math.floor(zmin),math.ceil(zmax)):
            if union_inside(x+.5,z+.5,polys): out.add((x,z))
    return out

def authority_frontage(items):
    out={}
    for item in items:
        out[item["id"]]={
            "z_north_m":min(item["z0_m"],item["z1_m"]),
            "z_south_m":max(item["z0_m"],item["z1_m"]),
            "z0_micro":round(min(item["z0_m"],item["z1_m"])*16),
            "z1_micro":round(max(item["z0_m"],item["z1_m"])*16),
            "front_x_m":item["front_x_m"],
            "front_x_micro":round(item["front_x_m"]*16),
        }
    return out

def zone_for_z(z,items):
    candidates=[]
    for item in items:
        lo=min(item["z0_m"],item["z1_m"]); hi=max(item["z0_m"],item["z1_m"])
        if lo <= z <= hi: return item
        candidates.append((abs(z-(lo+hi)/2),item))
    return min(candidates,key=lambda t:t[0])[1]

def facade_base_cells(row_cells,item):
    lo=math.floor(min(item["z0_m"],item["z1_m"]))
    hi=math.ceil(max(item["z0_m"],item["z1_m"]))
    vals=[]
    for z in range(lo,hi+1):
        zz=max(micrograde.LOCAL_Z_MIN,min(micrograde.LOCAL_Z_MAX,z))
        vals.append(row_cells[zz]+2)
    return round(statistics.median(vals))

def build_roof_profiles(items, side_polys, lidar, smooth_ground, base_elev):
    profiles={}; audit={}
    xmin,xmax,_,_=union_bounds(side_polys)
    for item in items:
        zmin=min(item["z0_m"],item["z1_m"]); zmax=max(item["z0_m"],item["z1_m"])
        raw={}; support={}
        for x in range(math.floor(xmin),math.ceil(xmax)):
            vals=[]
            for px,pz,elev,cls in lidar:
                if cls!=1 or not (x<=px<x+1) or not (zmin<=pz<=zmax):
                    continue
                if not union_inside(px,pz,side_polys): continue
                iz=max(micrograde.LOCAL_Z_MIN,min(micrograde.LOCAL_Z_MAX,round(pz)))
                g=smooth_ground[iz]; h=elev-g
                if 2.0<=h<=15.0: vals.append(elev)
            if vals:
                hist=Counter(round(v*4)/4 for v in vals); mode,count=hist.most_common(1)[0]
                raw[x]=mode; support[x]=(len(vals),count)
        if not raw:
            # Evidence-sparing fallback: use facade height slightly below parapet.
            zc=round((zmin+zmax)/2)
            g=smooth_ground[max(micrograde.LOCAL_Z_MIN,min(micrograde.LOCAL_Z_MAX,zc))]
            fallback=g+max(3.0,item["facade_height_m"]-.5)
            raw={x:fallback for x in range(math.floor(xmin),math.ceil(xmax))}
        known=sorted(raw); filled={}
        for x in range(math.floor(xmin),math.ceil(xmax)):
            filled[x]=raw[x] if x in raw else raw[min(known,key=lambda k:abs(k-x))]
        smooth={}
        for x in sorted(filled):
            smooth[x]=statistics.median([filled[k] for k in filled if abs(k-x)<=1])
        profiles[item["id"]]={x:round((e-base_elev)*16) for x,e in smooth.items()}
        audit[item["id"]]={
            "z_range_m":[zmin,zmax],
            "raw_mode_count":len(raw),
            "roof_height_blocks":{
                str(x):round(profiles[item["id"]][x]/16,3) for x in sorted(profiles[item["id"]])
            },
            "source":"2012 SDGS LiDAR modal first returns; fallback only where a zone lacks returns"
        }
    return profiles,audit
def build_side_shell(
    blocks,hosts,items,polys,roof_profiles,ref_x,ref_z,set_micro
):
    footprint=raster_union(polys)
    regular=0
    for x,z in sorted(footprint):
        item=zone_for_z(z+.5,items)
        front=item["front_x_m"]
        # Keep a 2 m facade reserve. Streetward direction depends on side.
        if item["side"]=="west" and x>math.floor(front)-2: continue
        if item["side"]=="east" and x<math.ceil(front)+2: continue
        perimeter=any((x+dx,z+dz) not in footprint for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))
        prof=roof_profiles[item["id"]]
        roof_top=prof.get(x,prof[min(prof,key=lambda k:abs(k-x))])
        sx=x-ref_x; sz=z-ref_z
        if perimeter:
            host_y=max(0,math.floor((roof_top-1)/16))
            for y in range(host_y):
                pos=(sx,y,sz)
                if pos not in blocks:
                    blocks[pos]=SIDE_WALL; regular+=1
            sy0=host_y*16
            for lx in range(16):
                for lz in range(16):
                    for yy in range(sy0,roof_top):
                        set_micro(sx*16+lx,yy,sz*16+lz,SIDE_WALL)
        # 2-cell roof membrane
        for lx in range(16):
            for lz in range(16):
                for yy in range(max(0,roof_top-2),roof_top):
                    set_micro(sx*16+lx,yy,sz*16+lz,ROOF)
    return footprint,regular

def placement_for(item,base_cells,ref_x,ref_z):
    south=max(item["z0_m"],item["z1_m"])
    north=min(item["z0_m"],item["z1_m"])
    return FacadePlacement(
        side=item["side"],
        front_x_micro=round(item["front_x_m"]*16),
        south_z_micro=round(south*16),
        north_z_micro=round(north*16),
        base_y_micro=base_cells,
        ref_x_block=ref_x,
        ref_z_block=ref_z,
    )

def make_canvas(item,row_cells,ref_x,ref_z,set_micro):
    return FacadeCanvas(
        placement_for(item,facade_base_cells(row_cells,item),ref_x,ref_z),
        round(item["facade_height_m"]*16),
        set_micro,
    )

def brick_texture(c,mat,shade):
    c.wall(mat,3)
    # restrained micro courses, not noisy per-cell texture
    for y in range(5,c.height,6):
        for u in range(c.width):
            c.cell(u,y,2,shade)

def author_gabled_office(c,item):
    body=palette(item,"body"); trim=palette(item,"trim"); dark=palette(item,"dark"); glass=palette(item,"glass")
    c.rect(0,1,0,4.15,-2,1,body); c.horizontal_seams(.2,4.1,5,trim,2)
    c.gable(4.15,item["facade_height_m"],body,trim)
    c.door(.44,.57,2.5,trim,dark,glass,-7)
    for a,b in [(.13,.22),(.25,.34),(.36,.43),(.60,.67),(.70,.79),(.82,.91)]:
        c.window(a,b,1.0,2.35,glass,dark,-5,2,False)
    for a,b,y0,y1 in [(.15,.20,3.15,3.55),(.28,.34,3.35,3.85),(.37,.43,3.45,4.0),(.61,.67,3.45,4.0),(.73,.79,3.35,3.85),(.84,.89,3.15,3.55)]:
        c.window(a,b,y0,y1,glass,dark,-4,1,False)
    c.window(.43,.57,4.05,4.42,glass,dark,-4,1,False)

def author_wide_mansard(c,item):
    brick=palette(item,"brick"); roof=palette(item,"roof"); trim=palette(item,"trim"); glass=palette(item,"glass")
    brick_texture(c,brick,trim)
    c.awning(0,1,4.45,18,20,roof,trim)
    c.rect(0,1,4.5,5.2,0,3,brick)
    bays=[(.10,.29),(.31,.39),(.41,.59),(.62,.70),(.72,.91)]
    for i,(a,b) in enumerate(bays):
        if i in (1,3): c.door(a,b,2.55,roof,trim,glass,-6)
        else: c.window(a,b,.75,2.65,glass,trim,-5,2,False,True)

def author_two_story_pastry(c,item):
    upper=palette(item,"upper"); lower=palette(item,"lower"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(upper,3)
    c.window(.22,.39,4.45,5.75,glass,trim,-5,2,True,True)
    c.rect(.61,.77,4.35,5.75,-3,1,rgb("rgb_b28e83"))
    c.rect(0,1,0,3.45,-2,1,lower)
    c.awning(.04,.96,3.35,14,8,trim,rgb("rgb_c4b28f"))
    for a,b in [(.12,.29),(.31,.46),(.48,.64),(.66,.82)]:
        c.window(a,b,.45,2.7,glass,trim,-5,2,True,True)
    c.door(.82,.91,2.6,lower,trim,glass,-6)

def author_midcentury(c,item):
    upper=palette(item,"upper"); awn=palette(item,"awning"); base=palette(item,"base"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(upper,3); c.vertical_seams(0,1,3.2,5.2,10,rgb("rgb_a6a6a0"),2)
    c.awning(.02,.98,3.15,13,10,awn,trim)
    c.rect(0,1,0,.65,-2,1,base)
    c.window(.08,.43,.7,2.55,glass,trim,-5,2,False,True)
    c.door(.45,.55,2.65,trim,trim,glass,-6)
    c.window(.57,.92,.7,2.55,glass,trim,-5,2,False,True)
    for uf in (.2,.4,.6,.8):
        u=c.U(uf); y=c.Y(4.45)
        c.line(u,y,u-3,y-8,2,4,rgb("rgb_25282a"),1)

def author_two_story_black(c,item):
    brick=palette(item,"brick"); roof=palette(item,"roof"); lower=palette(item,"lower"); trim=palette(item,"trim"); glass=palette(item,"glass")
    brick_texture(c,brick,rgb("rgb_7f3e32"))
    for a,b in [(.24,.40),(.58,.74)]:
        c.rect(a,b,4.65,6.15,-3,1,rgb("rgb_a17e70"))
    c.awning(0,1,4.05,10,16,roof,roof)
    c.rect(.20,.80,.45,2.25,-2,1,lower)
    c.door(.07,.17,2.45,roof,trim,glass,-6)
    c.door(.83,.93,2.45,roof,trim,glass,-6)
    c.rect(.25,.75,.65,2.05,1,3,rgb("rgb_9c6b58"))

def author_historic_stonebase(c,item):
    brick=palette(item,"brick"); cream=palette(item,"cream"); stone=palette(item,"stone"); trim=palette(item,"trim"); glass=palette(item,"glass")
    brick_texture(c,brick,rgb("rgb_794737"))
    cols=[(.18,.31),(.34,.47),(.55,.68),(.71,.84)]
    mural=[rgb("rgb_53a5b6"),rgb("rgb_d65b72"),rgb("rgb_e7c84d"),rgb("rgb_4d85af")]
    for i,(a,b) in enumerate(cols):
        c.rect(a,b,5.1,7.0,-4,1,mural[i])
        c.rect(a-.01,b+.01,7.05,7.25,0,4,trim)
    c.rect(0,1,2.75,4.1,0,3,cream)
    c.rect(0,1,0,2.75,-2,1,stone)
    c.door(.43,.55,2.7,rgb("rgb_1f2425"),trim,glass,-7)
    for a,b in [(.08,.18),(.26,.35),(.62,.71),(.80,.90)]:
        c.window(a,b,.55,2.35,glass,trim,-4,2,False)
def author_corner_restaurant(c,item):
    body=palette(item,"body"); tower=palette(item,"tower"); sign=palette(item,"sign"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(body,3)
    c.rect(.03,.68,3.05,4.45,0,3,sign)
    c.window(.18,.38,.65,2.55,glass,trim,-5,2,False,True)
    c.window(.42,.62,.65,2.55,glass,trim,-5,2,False,True)
    c.rect(.70,.94,0,6.5,-3,2,tower)
    c.vertical_seams(.70,.94,0,6.5,7,rgb("rgb_552522"),2)
    c.window(.75,.84,1.35,2.15,glass,trim,-5,2,False)
    c.window(.86,.93,1.35,2.15,glass,trim,-5,2,False)

def author_full_awning(c,item):
    body=palette(item,"body"); awn=palette(item,"awning"); base=palette(item,"base"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(body,3); c.rect(0,1,0,.5,-2,1,base)
    c.awning(0,1,4.0,18,22,awn,trim)
    for a,b in [(.10,.28),(.32,.52),(.58,.73),(.76,.91)]:
        if a==.58: c.door(a,b,2.55,body,trim,glass,-6)
        else: c.window(a,b,.65,2.5,glass,trim,-5,2,False)

def author_metal_infill(c,item):
    body=palette(item,"body"); brick=palette(item,"brick"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(body,3); c.horizontal_seams(.2,7.1,4,rgb("rgb_63727a"),2)
    c.rect(0,1,7.1,8.1,-2,1,brick)
    for u in range(0,c.width,9):
        for y in range(c.Y(7.35),c.Y(7.7)):
            c.cell(u,y,2,rgb("rgb_5e382f"))
    c.window(.17,.36,4.85,5.35,glass,trim,-5,2,False)
    c.window(.55,.78,4.55,6.0,glass,trim,-5,2,False,True)
    c.window(.08,.27,.65,2.55,glass,trim,-5,2,False)
    c.door(.43,.55,2.65,body,trim,glass,-6)
    c.window(.58,.88,.65,2.55,glass,trim,-5,2,False,True)

def author_brick_orange(c,item):
    brick=palette(item,"brick"); body=palette(item,"body"); trim=palette(item,"trim"); glass=palette(item,"glass")
    brick_texture(c,brick,rgb("rgb_573c35"))
    # notched parapet
    for uf in (.04,.34,.68,.94):
        c.rect(uf-.025,uf+.025,5.75,6.0,0,4,trim)
    c.rect(.08,.92,4.35,4.55,0,5,trim)
    c.rect(.07,.93,0,3.55,-2,1,body); c.horizontal_seams(.1,3.5,7,rgb("rgb_8d5429"),2)
    c.window(.12,.35,.65,2.45,glass,trim,-5,2,False)
    c.door(.45,.55,2.55,rgb("rgb_4c382e"),trim,glass,-6)
    c.window(.65,.88,.65,2.45,glass,trim,-5,2,False)

def author_terrys_group(c,item616,item614):
    brick=palette(item616,"brick"); accent=palette(item616,"accent"); body=palette(item616,"body"); stone=palette(item616,"stone"); roof=palette(item616,"roof"); trim=palette(item616,"trim"); glass=palette(item616,"glass")
    split=.50
    # low combined lower facade
    c.rect(0,1,0,4.0,-2,1,body); c.rect(0,1,0,1.6,-2,2,stone)
    c.awning(0,1,2.65,12,8,roof,trim)
    # tall 616 left/north pavilion (photo-left)
    c.rect(0,split,4.0,8.5,-3,1,brick)
    c.rect(.03,split-.03,6.4,7.85,0,3,accent)
    c.rect(.08,split-.08,7.0,7.35,2,5,rgb("rgb_4e2929"))
    # parapet crown
    c.rect(.04,split-.04,8.15,8.5,0,4,trim)
    # ground openings
    c.window(.05,.23,.45,2.35,glass,trim,-5,2,False)
    c.door(.25,.34,2.45,body,trim,glass,-6)
    c.window(.36,.48,.45,2.35,glass,trim,-5,2,False)
    c.door(.57,.65,2.35,body,trim,glass,-6)
    c.window(.68,.94,.45,2.25,glass,trim,-5,2,False,True)
    # Terry's sign field across low 614 half
    c.rect(split,.98,2.75,4.65,0,3,body)

def author_low_mansard(c,item):
    body=palette(item,"body"); roof=palette(item,"roof"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.rect(0,1,0,3.0,-2,1,body); c.vertical_seams(0,1,0,3,8,rgb("rgb_244a50"),2)
    c.awning(0,1,4.0,11,12,roof,roof)
    c.rect(.05,.42,4.05,4.65,0,2,trim)
    c.window(.05,.25,.55,2.55,glass,trim,-5,2,False)
    c.window(.28,.50,.55,2.55,glass,trim,-5,2,False)
    c.window(.52,.75,.55,2.55,glass,trim,-5,2,False)
    c.window(.77,.95,.55,2.55,glass,trim,-5,2,False)

def author_low_white(c,item):
    body=palette(item,"body"); parapet=palette(item,"parapet"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.rect(0,1,0,3.3,-2,1,body); c.vertical_seams(0,1,0,3.3,9,rgb("rgb_bab8b2"),2)
    c.rect(.02,.98,3.25,4.6,-3,1,parapet)
    c.rect(0,1,3.0,3.18,0,9,trim)
    c.window(.10,.37,.65,2.55,glass,trim,-5,2,False)
    c.door(.45,.55,2.65,body,trim,glass,-6)
    c.window(.63,.90,.65,2.55,glass,trim,-5,2,False)

def author_sign_box(c,item):
    body=palette(item,"body"); trim=palette(item,"trim"); sign=palette(item,"sign"); glass=palette(item,"glass")
    c.wall(body,3); c.horizontal_seams(.1,5.3,6,rgb("rgb_4f514e"),2)
    c.rect(.03,.97,5.2,5.6,0,8,trim)
    # large sign field
    c.rect(.12,.88,3.1,5.0,2,4,body)
    # simplified ALLEY CUTS lettering blocks rather than raster text
    for uf in (.22,.34,.46,.58,.70):
        c.rect(uf,uf+.035,4.15,4.65,4,6,sign)
    c.window(.10,.34,.55,2.35,glass,trim,-5,2,False)
    c.door(.43,.57,2.65,body,trim,glass,-6)
    c.window(.66,.90,.55,2.35,glass,trim,-5,2,False)

def author_city_hall(c,item):
    brick=palette(item,"brick"); stone=palette(item,"stone"); dark=palette(item,"dark"); trim=palette(item,"trim"); glass=palette(item,"glass")
    c.wall(brick,4); c.rect(0,1,0,.75,0,4,stone)
    # heavy classical cornice/parapet
    c.rect(.02,.98,7.65,7.9,0,7,trim); c.rect(.06,.94,7.95,8.25,0,5,trim); c.rect(.10,.90,8.35,8.75,0,3,brick)
    # central recessed portal
    c.clear(.31,.70,.8,7.35,-28,8); c.rect(.33,.68,2.85,7.25,-10,-5,dark)
    c.door(.41,.59,2.85,dark,trim,glass,-9)
    c.round_column(.36,.85,6.85,4,stone,4); c.round_column(.65,.85,6.85,4,stone,4)
    c.rect(.32,.69,6.75,7.05,0,10,stone)
    c.window(.08,.20,1.2,2.8,glass,trim,-5,2,False)
    c.window(.80,.92,1.2,2.8,glass,trim,-5,2,False)

AUTHOR={
    "gabled_office":author_gabled_office,
    "wide_mansard_storefront":author_wide_mansard,
    "two_story_pastry":author_two_story_pastry,
    "midcentury_awning":author_midcentury,
    "two_story_black_mansard":author_two_story_black,
    "historic_stonebase":author_historic_stonebase,
    "corner_restaurant_tower":author_corner_restaurant,
    "one_story_full_awning":author_full_awning,
    "two_story_metal_infill":author_metal_infill,
    "brick_parapet_orange":author_brick_orange,
    "low_mansard_office":author_low_mansard,
    "low_white_storefront":author_low_white,
    "modern_sign_box":author_sign_box,
    "neoclassical_city_hall":author_city_hall,
}
def make_overview(items,path):
    W,H=1800,980
    im=Image.new("RGB",(W,H),"#efeee7"); d=ImageDraw.Draw(im)
    fp=Path("C:/Windows/Fonts/segoeui.ttf")
    font=lambda n:ImageFont.truetype(str(fp),n)
    d.text((40,25),"REDFIELD / MAIN 600 BLOCK / FACADE ALPHA v001",font=font(30),fill="#243c39")
    d.text((40,70),"Native current-photo facade modules + LiDAR/MicroGrade block frame",font=font(17),fill="#56605d")
    z_s=-13;z_n=-122;x0=80;x1=1720;scale=(x1-x0)/(z_s-z_n)
    zx=lambda z:x0+(z_s-z)*scale
    for side,y in [("west",230),("east",590)]:
        d.text((40,y-50),side.upper()+" SIDE",font=font(21),fill="#243c39")
        for item in sorted([i for i in items if i["side"]==side],key=lambda i:max(i["z0_m"],i["z1_m"]),reverse=True):
            south=max(item["z0_m"],item["z1_m"]); north=min(item["z0_m"],item["z1_m"])
            a,b=zx(south),zx(north)
            col=(148,93,79) if side=="west" else (109,130,103)
            d.rectangle((a,y,b,y+round(item["facade_height_m"]*18)),fill=col,outline="#3c403d",width=2)
            if b-a>45:d.text((a+4,y+5),item["id"],font=font(14),fill="white")
    d.text((40,915),"This preview is mass/proportion only; the Litematic contains the authored microcell windows, doors, awnings, columns and roof bands.",font=font(15),fill="#56605d")
    im.save(path)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    authority=read_json(AUTHORITY); items=authority["facades"]
    geom=read_json(GEOM); byid={b["osm_id"]:b for b in geom["buildings"]}
    (
        frame,raw_ground,smooth_ground,row_cells,base_elev,
        blocks,hosts,_,_
    )=micrograde.build_surface()
    ref=frame["future_litematica_registration"]; ref_x=int(ref["player_feet_x"]); ref_z=int(ref["player_feet_z"])
    lidar=load_lidar()

    def set_micro(sx,sy,sz,material):
        # Reuse the v002 collision-safe writer.
        westv2.set_micro(blocks,hosts,sx,sy,sz,material)

    # Side massing + LiDAR roofs.
    roof_audit={}; shell_blocks=0
    side_profiles={}
    for side in ("west","east"):
        side_items=[i for i in items if i["side"]==side]
        side_polys=[byid[i["osm_id"]]["polygon_xz_m"] for i in side_items]
        profiles,audit=build_roof_profiles(side_items,side_polys,lidar,smooth_ground,base_elev)
        side_profiles[side]=profiles; roof_audit.update(audit)
        _,regular=build_side_shell(blocks,hosts,side_items,side_polys,profiles,ref_x,ref_z,set_micro)
        shell_blocks+=regular

    # Preserve the accepted/v002 north-west photo facades exactly at the corrected widths.
    north_items=[i for i in items if i["id"] in ("617-619","621","623","625-627")]
    north_front=authority_frontage(north_items)
    src_blocks,src_decoded,_=westv2.source_tiles()
    westv2.transform_facades(
        blocks,hosts,src_blocks,src_decoded,north_front,row_cells,ref_x,ref_z
    )

    authored=[]
    # Native remaining facades.
    for item in items:
        if item["style"]=="accepted_v002": continue
        if item["id"] in ("614","616"): continue
        c=make_canvas(item,row_cells,ref_x,ref_z,set_micro)
        AUTHOR[item["style"]](c,item)
        authored.append(item["id"])

    # Terry's is one shared visual composition spanning 616 + 614.
    i614=next(i for i in items if i["id"]=="614"); i616=next(i for i in items if i["id"]=="616")
    terry={
        **i616,
        "id":"614-616",
        "z0_m":min(i614["z0_m"],i616["z0_m"]),
        "z1_m":max(i614["z1_m"],i616["z1_m"]),
        "front_x_m":min(i614["front_x_m"],i616["front_x_m"]),
        "facade_height_m":8.5,
    }
    tc=make_canvas(terry,row_cells,ref_x,ref_z,set_micro)
    author_terrys_group(tc,i616,i614); authored.extend(["614","616"])

    for pos in hosts: blocks[pos]=HOST_STATE
    xs=[p[0] for p in blocks];ys=[p[1] for p in blocks];zs=[p[2] for p in blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    writer=NBTWriter(); tes=[]
    for (x,y,z),vol in sorted(hosts.items()):
        tes.append(tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),vol))
    out=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        out,blocks,bounds,REGION,NAME,
        "Redfield Main/6th-to-Main/7th block alpha: LiDAR MicroGrade, mapped union shells/roofs, accepted 617-627 v002 facade method, and native current-photo facade modules for remaining storefronts.",
        data_version=4903,tile_entity_payloads=tes,
    )
    reread,meta=read_back_block_map(out,REGION)
    expected={p:canonical_state(s) for p,s in blocks.items()}
    assert reread==expected
    pos=meta["region_position"];decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+pos[0],te["y"]+pos[1],te["z"]+pos[2])
            decoded[p]=decode_volume_v4(te["volume_v4"])
    assert set(decoded)==set(hosts)
    for p,v in hosts.items(): assert decoded[p]==v.cells,p
    assert reread.get((0,-1,0))=="minecraft:yellow_concrete"

    report={
        **stats,
        "astra_min_version":"0.7.0",
        "authority":"projects/redfield_sd/poc_001/full_block_facade_authority_v001.json",
        "authored_native_facades":authored,
        "preserved_v002_facades":["617-619","621","623","625-627"],
        "shell_full_blocks":shell_blocks,
        "astra":{"hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values())},
        "roof_audit":roof_audit,
        "validation":{
            "exact_block_readback":True,
            "exact_astra_readback":True,
            "registration_marker":True,
            "micrograde_carried_forward":True,
            "raw_reference_images_embedded":False,
            "in_game_review":False,
        },
        "confidence":{
            "outer_geometry":"high relative to locked EarthForge mapped frame",
            "west_617_627":"high relative to accepted v002 proof pipeline",
            "remaining_facade_module_geometry":"medium; authored from current Redfield 21 Feet photos and requires in-game refinement",
            "east_internal_frontage":"medium-high; current photos/history override demonstrably wrong per-address OSM partitions",
            "side_rear_detail":"low-medium; outer mass/roof only until direct alley/oblique evidence is acquired",
        }
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    make_overview(items,OUT/f"{NAME}_overview.png")
    (OUT/"Build_notes.md").write_text(
        "# Redfield Full Block Facade Alpha v001\n\n"
        "First block-scale candidate using the v002 true-frame method. The four accepted 617-627 facades are preserved through the same photo-proportional transform; every other frontage is authored natively from current Redfield 21 Feet reference photos.\n\n"
        "East-side per-address OSM widths are not trusted where photographs/history contradict them. The block keeps the mapped outer frame while internal facade zones use the facade authority registry.\n\n"
        "This candidate includes the LiDAR MicroGrade, building outer shells, LiDAR roof bands and front facades. Rear openings, utilities and fine streetscape are later passes.\n"
    )
    print(json.dumps({
        "file":str(out),"sha256":stats["sha256"],"region_size":stats["region_size"],
        "facades":len(items),"native":len(authored),"astra_hosts":len(hosts),
        "occupied_microcells":sum(v.occupied_count() for v in hosts.values()),
        "shell_blocks":shell_blocks,"validation":"PASS"
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
