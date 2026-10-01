#!/usr/bin/env python3
"""Add block-scale streetscape to the Redfield full-block facade alpha.

Evidence-backed additions:
- Main Street double-yellow center line and angled curb parking marks from
  current city-reference photographs;
- 7th Avenue signalized intersection/crosswalk context from KartaView 2017 +
  OSM traffic-signal crossings;
- 6th and 7th Avenue road surfaces tied to LiDAR ground;
- east/west service alleys from locked OSM alley controls;
- restrained municipal globe lamps along Main from repeated current photos.

This pass deliberately avoids inventing rear doors, utilities, or current
Main/6th signalization that has not been verified.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter, canonical_state, read_back_block_map, write_single_region_litematic
)
from pipeline.microblocks.astra_microblock_codec import (
    BLOCK_ENTITY_ID, HOST_STATE, MicroVolume, cell_index, decode_volume_v4,
    tile_entity_payload
)

PROJECT=ROOT/"projects"/"redfield_sd"
SOURCE=PROJECT/"outputs/full_block_alpha_v001/Redfield_POC_001_FullBlock_FacadeAlpha_v001.litematic"
SOURCE_REGION="REDFIELD_POC001_FULLBLOCK_FACADE_ALPHA_V001"
LIDAR=PROJECT/"downloads/multisource_v001/lidar_spink_2012/redfield_poc001_roi_points.csv"
FRAME=PROJECT/"poc_001/locked_frame.json"
OUT=PROJECT/"outputs/full_block_streetscape_v002"
NAME="Redfield_POC_001_FullBlock_Streetscape_v002"
REGION="REDFIELD_POC001_FULLBLOCK_STREETSCAPE_V002"

REF_X=-78
REF_Z=9
ROAD_BASE="minecraft:gray_concrete"
SIDEWALK_BASE="minecraft:smooth_stone"
ASPHALT="astra_microblocks:rgb_55585a"
ALLEY="astra_microblocks:rgb_70706d"
WHITE="astra_microblocks:rgb_e3e1d7"
YELLOW="astra_microblocks:rgb_e3b72e"
POLE="astra_microblocks:rgb_26292a"
POLE_HILITE="astra_microblocks:rgb_4b4d4c"
GLOBE="astra_microblocks:rgb_d8d0af"
SIGN_GREEN="astra_microblocks:rgb_35634b"
SIGN_WHITE="astra_microblocks:rgb_e6e5dd"
SIGNAL_YELLOW="astra_microblocks:rgb_b78b22"
RED="astra_microblocks:rgb_c64035"
AMBER="astra_microblocks:rgb_d9a12b"
GREEN="astra_microblocks:rgb_398f55"

def floor16(v):
    h=math.floor(v/16);return h,v-h*16

def load_model():
    blocks,meta=read_back_block_map(SOURCE,SOURCE_REGION)
    rp=meta["region_position"];hosts={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            pos=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
            v=MicroVolume()
            v.cells=decode_volume_v4(te["volume_v4"])
            hosts[pos]=v
    return blocks,hosts

def set_micro(blocks,hosts,sx,sy,sz,material):
    hx,lx=floor16(sx);hy,ly=floor16(sy);hz,lz=floor16(sz);pos=(hx,hy,hz)
    if pos in blocks and blocks[pos]!=HOST_STATE:
        existing=blocks[pos]
        v=MicroVolume(existing)
        v.fill_box(0,0,0,16,16,16,existing)
        hosts[pos]=v;blocks[pos]=HOST_STATE
    v=hosts.get(pos)
    if v is None:
        v=MicroVolume("minecraft:stone");hosts[pos]=v;blocks[pos]=HOST_STATE
    v.set(lx,ly,lz,material)

def local_block(x,z):
    return x-REF_X,z-REF_Z

def local_micro(xm,zm):
    return round((xm-REF_X)*16),round((zm-REF_Z)*16)

def load_ground_bins():
    bins=defaultdict(list)
    with LIDAR.open(encoding="utf-8",newline="") as fh:
        for row in csv.DictReader(fh):
            if int(row["class"])!=2:continue
            x=float(row["x_local_m"]);z=float(row["z_local_m"]);e=float(row["elev_m"])
            bins[(round(x),round(z))].append(e)
    med={k:statistics.median(v) for k,v in bins.items()}
    # Same project zero used by the approved MicroGrade.
    road=[]
    for (x,z),e in med.items():
        if -6<=x<=6 and -132<=z<=0:road.append(e)
    base=min(road)
    return med,base

def ground_elev(med,x,z):
    vals=[]
    xi=round(x);zi=round(z)
    for r in (0,1,2,3):
        for dx in range(-r,r+1):
            for dz in range(-r,r+1):
                e=med.get((xi+dx,zi+dz))
                if e is not None:vals.append(e)
        if vals:return statistics.median(vals)
    return None

def height_cells(med,base,x,z):
    e=ground_elev(med,x,z)
    if e is None:return 0
    return max(0,round((e-base)*16))

def surface_column(blocks,hosts,x,z,height,base_block,micro_mat):
    sx,sz=local_block(x,z)
    blocks[(sx,-1,sz)]=base_block
    remaining=int(height);hy=0
    while remaining>0:
        count=min(16,remaining)
        pos=(sx,hy,sz)
        if pos in blocks and blocks[pos]!=HOST_STATE:
            existing=blocks[pos]
            v=MicroVolume(existing)
            v.fill_box(0,0,0,16,16,16,existing)
            hosts[pos]=v;blocks[pos]=HOST_STATE
        v=hosts.get(pos)
        if v is None:
            v=MicroVolume(base_block);hosts[pos]=v;blocks[pos]=HOST_STATE
        v.fill_box(0,0,0,16,count,16,micro_mat)
        remaining-=count;hy+=1

def paint_cell(blocks,hosts,x_micro,z_micro,y_micro,material,thickness=1):
    sx=x_micro-REF_X*16;sz=z_micro-REF_Z*16
    for dx in range(thickness):
        for dz in range(thickness):
            set_micro(blocks,hosts,sx+dx,y_micro,sz+dz,material)

def line_micro(blocks,hosts,x0,z0,x1,z1,y,material,thickness=2):
    steps=max(abs(x1-x0),abs(z1-z0),1)
    for i in range(steps+1):
        x=round(x0+(x1-x0)*i/steps);z=round(z0+(z1-z0)*i/steps)
        paint_cell(blocks,hosts,x,z,y,material,thickness)
def add_cross_streets(blocks,hosts,med,base):
    # Full cross-street carriageways. Main/7th and Main/6th sidewalk crossing
    # extents indicate roughly 20 m road widths.
    for center_z in (0,-132):
        for x in range(-72,73):
            for z in range(center_z-10,center_z+11):
                h=height_cells(med,base,x,z)
                surface_column(blocks,hosts,x,z,h,ROAD_BASE,ASPHALT)
    # Service alleys centered on the locked OSM controls.
    for xc in (-69,68):
        for x in range(xc-2,xc+3):
            for z in range(-122,-12):
                h=height_cells(med,base,x,z)
                surface_column(blocks,hosts,x,z,h,ROAD_BASE,ALLEY)

def road_top_cell(med,base,x,z):
    return height_cells(med,base,x,z)

def add_main_markings(blocks,hosts,med,base):
    # Double yellow centerline: two 2-cell-wide lines separated by 3 cells.
    for z in range(-122*16,1):
        zm=z/16
        y=road_top_cell(med,base,0,zm)
        for xm in (-0.22,0.22):
            x=round(xm*16)
            paint_cell(blocks,hosts,x,z,y,YELLOW,2)
    # Angled parking stall marks, supported by current storefront photos.
    for z0 in range(-116,-16,6):
        for side in (-1,1):
            x_curb=side*9*16
            x_inner=side*4*16
            z_start=z0*16
            z_end=round((z0+2.8)*16)
            midx=(x_curb+x_inner)//2
            midz=(z_start+z_end)//2
            y=road_top_cell(med,base,midx/16,midz/16)
            line_micro(blocks,hosts,x_curb,z_start,x_inner,z_end,y,WHITE,2)

def add_crosswalks_7th(blocks,hosts,med,base):
    # Four ladder-style marked crossings around the signalized 7th intersection.
    # North/south crossings across Main.
    for zc in (-8,8):
        for x in range(-9,10,3):
            y=road_top_cell(med,base,x,zc)
            for xx in range(x*16,(x+2)*16):
                for zz in range((zc-1)*16,(zc+1)*16):
                    paint_cell(blocks,hosts,xx,zz,y,WHITE,1)
    # East/west crossings across 7th.
    for xc in (-8,8):
        for z in range(-9,10,3):
            y=road_top_cell(med,base,xc,z)
            for xx in range((xc-1)*16,(xc+1)*16):
                for zz in range(z*16,(z+2)*16):
                    paint_cell(blocks,hosts,xx,zz,y,WHITE,1)

def cylinder(blocks,hosts,xm,zm,y0,y1,radius_cells,material):
    cx,cz=local_micro(xm,zm)
    for y in range(y0,y1):
        for dx in range(-radius_cells,radius_cells+1):
            for dz in range(-radius_cells,radius_cells+1):
                if dx*dx+dz*dz<=radius_cells*radius_cells:
                    set_micro(blocks,hosts,cx+dx,y,cz+dz,material)

def add_lamp(blocks,hosts,med,base,x,z):
    y0=height_cells(med,base,x,z)+2
    cylinder(blocks,hosts,x,z,y0,y0+62,2,POLE)
    # flared base
    cylinder(blocks,hosts,x,z,y0,y0+8,4,POLE_HILITE)
    cx,cz=local_micro(x,z)
    # globe: small sphere-ish stack
    for dy,r in ((62,3),(64,5),(67,6),(70,5),(73,3)):
        for dx in range(-r,r+1):
            for dz in range(-r,r+1):
                if dx*dx+dz*dz<=r*r:
                    set_micro(blocks,hosts,cx+dx,y0+dy,cz+dz,GLOBE)

def add_main_lamps(blocks,hosts,med,base):
    # Conservative municipal rhythm seen repeatedly in current archive photos.
    z_positions=(-27,-47,-67,-87,-107)
    for z in z_positions:
        add_lamp(blocks,hosts,med,base,-12.4,z)
        add_lamp(blocks,hosts,med,base,12.4,z)

def traffic_head(blocks,hosts,xm,zm,y0,face_axis):
    cx,cz=local_micro(xm,zm)
    # compact yellow housing with vertical R/Y/G lights
    for yy in range(y0,y0+17):
        for a in range(-4,5):
            for b in range(-3,4):
                x=cx+a if face_axis=="z" else cx+b
                z=cz+b if face_axis=="z" else cz+a
                set_micro(blocks,hosts,x,yy,z,SIGNAL_YELLOW)
    for yy,mat in ((y0+13,RED),(y0+8,AMBER),(y0+3,GREEN)):
        for a in range(-2,3):
            for b in range(-1,2):
                x=cx+a if face_axis=="z" else cx+b
                z=cz+b if face_axis=="z" else cz+a
                set_micro(blocks,hosts,x,yy,z,mat)

def add_signal(blocks,hosts,med,base,x,z,toward_x,toward_z):
    y0=height_cells(med,base,x,z)+2
    cylinder(blocks,hosts,x,z,y0,y0+82,3,POLE)
    # line_micro works in project-local micro coordinates.
    cx,cz=round(x*16),round(z*16)
    ex=round((x+toward_x)*16)
    ez=round((z+toward_z)*16)
    line_micro(blocks,hosts,cx,cz,ex,ez,y0+73,POLE,3)
    # signal head near inner end
    hx=x+toward_x*.78; hz=z+toward_z*.78
    traffic_head(blocks,hosts,hx,hz,y0+51,"z" if abs(toward_z)>=abs(toward_x) else "x")
    # green street-name blade near mast root
    bx=round((x+toward_x*.25)*16)-REF_X*16
    bz=round((z+toward_z*.25)*16)-REF_Z*16
    for xx in range(bx-10,bx+11):
        for yy in range(y0+66,y0+71):
            set_micro(blocks,hosts,xx,yy,bz,SIGN_GREEN)
    for xx in range(bx-6,bx+7,4):
        for yy in range(y0+67,y0+70):
            set_micro(blocks,hosts,xx,yy,bz-1,SIGN_WHITE)

def add_7th_signals(blocks,hosts,med,base):
    # Four corner poles just outside the two road edges; KartaView confirms
    # mast-arm traffic signals and a MAIN ST blade at this intersection.
    for x,z,tx,tz in [
        (-12,-12,9,9),(12,-12,-9,9),(-12,12,9,-9),(12,12,-9,-9)
    ]:
        add_signal(blocks,hosts,med,base,x,z,tx,tz)
def make_plan(path):
    W,H=1200,920;im=Image.new("RGB",(W,H),"#efeee7");d=ImageDraw.Draw(im)
    fp=Path("C:/Windows/Fonts/segoeui.ttf");font=lambda n:ImageFont.truetype(str(fp),n)
    d.text((35,25),"REDFIELD / FULL BLOCK STREETSCAPE v002",font=font(28),fill="#243c39")
    d.text((35,65),"Avenues + alleys + Main markings + 7th signals + municipal lamps",font=font(16),fill="#56605d")
    sx=7;ox=W//2;oz=115
    # block
    d.rectangle((ox-10*sx,oz,ox+10*sx,oz+132*sx),fill="#55585a")
    d.rectangle((ox-16*sx,oz,ox-10*sx,oz+132*sx),fill="#bbb8ae")
    d.rectangle((ox+10*sx,oz,ox+16*sx,oz+132*sx),fill="#bbb8ae")
    # cross streets
    for z in (0,132):
        yy=oz+z*sx
        d.rectangle((ox-72*sx,yy-10*sx,ox+72*sx,yy+10*sx),fill="#626462")
    # alleys
    for x in (-69,68):
        xx=ox+x*sx
        d.rectangle((xx-2*sx,oz+10*sx,xx+2*sx,oz+122*sx),fill="#777771")
    # lamps
    for z in (27,47,67,87,107):
        yy=oz+z*sx
        for x in (-12.4,12.4):
            xx=ox+x*sx;d.ellipse((xx-4,yy-4,xx+4,yy+4),fill="#252829")
    # signals
    for x,z in [(-12,12),(12,12),(-12,-12),(12,-12)]:
        xx=ox+x*sx;yy=oz+z*sx;d.rectangle((xx-4,yy-4,xx+4,yy+4),fill="#c79728")
    d.text((35,H-55),"Main/6th remains deliberately unsignalized in this pass because current signalization has not been verified.",font=font(14),fill="#56605d")
    im.save(path)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blocks,hosts=load_model();med,base=load_ground_bins()
    add_cross_streets(blocks,hosts,med,base)
    add_main_markings(blocks,hosts,med,base)
    add_crosswalks_7th(blocks,hosts,med,base)
    add_main_lamps(blocks,hosts,med,base)
    add_7th_signals(blocks,hosts,med,base)
    for pos in hosts:blocks[pos]=HOST_STATE
    xs=[p[0] for p in blocks];ys=[p[1] for p in blocks];zs=[p[2] for p in blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    writer=NBTWriter();tes=[]
    for (x,y,z),v in sorted(hosts.items()):
        tes.append(tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v))
    out=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        out,blocks,bounds,REGION,NAME,
        "Full Redfield 600-block facade alpha plus LiDAR-fitted 6th/7th road surfaces, mapped service alleys, Main markings, 7th signal context and evidence-supported globe lamps.",
        data_version=4903,tile_entity_payloads=tes
    )
    reread,meta=read_back_block_map(out,REGION);expected={p:canonical_state(s) for p,s in blocks.items()};assert reread==expected
    rp=meta["region_position"];decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2]);decoded[p]=decode_volume_v4(te["volume_v4"])
    assert set(decoded)==set(hosts)
    for p,v in hosts.items():assert decoded[p]==v.cells,p
    report={
        **stats,
        "source_full_block_alpha":"projects/redfield_sd/outputs/full_block_alpha_v001/Redfield_POC_001_FullBlock_FacadeAlpha_v001.litematic",
        "astra":{"hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values())},
        "features":{
            "main_double_yellow":True,"angled_parking_marks":True,
            "7th_crosswalks":True,"7th_mast_arm_signals":4,
            "main_globe_lamps":10,"west_alley":True,"east_alley":True,
            "6th_current_signalization_added":False,
        },
        "evidence":{
            "7th_signals":"KartaView sequence 473900 + OSM traffic-signal crossing tags",
            "parking_markings":"repeated current Redfield archive storefront photos",
            "globe_lamps":"repeated current Redfield archive storefront photos; longitudinal positions are inferred municipal rhythm",
            "alleys":"locked OSM/Esri alley controls",
            "cross_street_elevation":"2012 SDGS LiDAR class-2 ground",
        },
        "validation":{"exact_block_readback":True,"exact_astra_readback":True,"registration_marker":reread.get((0,-1,0))=="minecraft:yellow_concrete","in_game_review":False},
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    make_plan(OUT/f"{NAME}_plan.png")
    (OUT/"Build_notes.md").write_text(
        "# Redfield Full Block Streetscape v002\n\n"
        "Extends the full-block facade alpha with the first evidence-backed street system. "
        "Main/7th signals and marked crossing context come from KartaView/OSM; Main/6th is intentionally left without invented signal heads. "
        "Cross streets and alleys are fitted to local LiDAR ground. Main Street receives the current-photo-supported double-yellow and angled parking marks plus a restrained globe-lamp rhythm.\n"
    )
    print(json.dumps({"file":str(out),"sha256":stats["sha256"],"region_size":stats["region_size"],"astra_hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values()),"validation":"PASS"},indent=2))

if __name__=="__main__":main()
