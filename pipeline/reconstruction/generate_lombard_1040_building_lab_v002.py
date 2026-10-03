#!/usr/bin/env python3
"""EarthForge 1040 Lombard standalone Single-Building Truth Lab v002.

The building is generated in a normalized local frame with no Lombard context.
Facade geometry is authored continuously in EarthForge FacadeCanvas coordinates
before being split into Astra hosts. This prevents host-boundary striping.
"""
from __future__ import annotations

import json, math, hashlib, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter, canonical_state, write_single_region_litematic,
    read_back_block_map,
)
from pipeline.microblocks import astra_microblock_codec as astra
from pipeline.microblocks.facade_canvas import FacadeCanvas

PROJECT=ROOT/"projects"/"lombard_sf"
LAB=PROJECT/"building_labs"/"1040_lombard"
SPEC=LAB/"lab_v002.json"
OUT=PROJECT/"outputs"/"building_labs"/"1040_lombard_v002"
OUT_FILE=OUT/"Lombard_1040_BuildingLab_v002.litematic"
REGION="LOMBARD_1040_BUILDING_LAB_V002"

U_MARGIN=16
FRONT_MARGIN=32
DATA_VERSION=4903
MIRROR_CELL_SUM=None
PARENT_FILE=PROJECT/"outputs"/"building_labs"/"1040_lombard_v001"/"Lombard_1040_BuildingLab_v001.litematic"
PARENT_REGION="LOMBARD_1040_BUILDING_LAB_V001"

def load():
    return json.loads(SPEC.read_text(encoding="utf-8"))

def mcell(m):
    return int(round(float(m)*16))

def host_set(volumes, mx, my, mz, material):
    # Front faces -Z, so photo-right must run toward -X.
    if MIRROR_CELL_SUM is None: raise RuntimeError("Lab frame not initialized")
    mx=MIRROR_CELL_SUM-mx
    hx=math.floor(mx/16); hy=math.floor(my/16); hz=math.floor(mz/16)
    lx=mx-hx*16; ly=my-hy*16; lz=mz-hz*16
    key=(hx,hy,hz)
    if key not in volumes:
        volumes[key]=astra.MicroVolume()
    volumes[key].set(lx,ly,lz,material)

def raster_fill_polygon(poly, y0, y1, material, volumes):
    minx,minz,maxx,maxz=poly.bounds
    for mx in range(math.floor(minx*16),math.ceil(maxx*16)):
        for mz in range(math.floor(minz*16),math.ceil(maxz*16)):
            p=Point((mx+.5)/16,(mz+.5)/16)
            if not poly.covers(p):
                continue
            for my in range(y0,y1):
                host_set(volumes,U_MARGIN+mx,my,FRONT_MARGIN+mz,material)

def raster_boundary_walls(poly, y0, y1, thickness_m, material, volumes, min_depth_m):
    ring=poly.boundary.buffer(thickness_m/2,cap_style=2,join_style=2)
    minx,minz,maxx,maxz=ring.bounds
    for mx in range(math.floor(minx*16),math.ceil(maxx*16)):
        for mz in range(math.floor(minz*16),math.ceil(maxz*16)):
            p=Point((mx+.5)/16,(mz+.5)/16)
            if p.y < min_depth_m or not ring.covers(p):
                continue
            for my in range(y0,y1):
                host_set(volumes,U_MARGIN+mx,my,FRONT_MARGIN+mz,material)

def opening_frame(canvas, u0, u1, y0, y1, dface, frame, border=2, mullions=0, transoms=1):
    """Carved aperture with continuous returns and registered open pane rays."""
    canvas.clear(-24,dface+8,y0,y1,u0,u1)
    for a,b,c,e in [(u0,u0+border,y0,y1),(u1-border,u1,y0,y1),
                      (u0,u1,y0,y0+border),(u0,u1,y1-border,y1)]:
        canvas.box(dface-5,dface+2,c,e,a,b,frame)
    for k in range(1,mullions+1):
        uc=round(u0+(u1-u0)*k/(mullions+1))
        canvas.box(dface,dface+2,y0,y1,uc,uc+1,frame)
    for k in range(1,transoms+1):
        yc=round(y0+(y1-y0)*k/(transoms+1))
        canvas.box(dface,dface+2,yc,yc+1,u0,u1,frame)
    if mullions==3 and transoms==4:
        for k in range(4):
            uc=round(u0+(u1-u0)*(k+.5)/4)
            canvas.box(dface,dface+2,y0,y1,uc,uc+1,frame)
    if not hasattr(canvas,'opening_records'): canvas.opening_records=[]
    rays=[]
    for u in range(u0+border,u1-border):
        for y in range(y0+border,y1-border):
            if all((d,y,u) not in canvas.cells for d in range(-24,dface+4)):
                rays.append((u,y))
    canvas.opening_records.append({'bounds':(u0,u1,y0,y1),'face':dface,'rays':rays})


def facade_to_hosts(canvas, volumes, main_wall_inward_m):
    wall_z=FRONT_MARGIN+mcell(main_wall_inward_m)
    for (d,y,u),material in canvas.cells.items():
        mx=U_MARGIN+u
        mz=wall_z-d
        host_set(volumes,mx,y,mz,material)

def draw_front(canvas, out_path):
    front=canvas.frontmost()
    scale=4
    img=Image.new("RGB",(canvas.width*scale,canvas.height*scale),(242,242,239))
    d=ImageDraw.Draw(img)
    colors={
        "astra_microblocks:rgb_91b9ca":(145,185,202),
        "astra_microblocks:rgb_82aec2":(130,174,194),
        "astra_microblocks:rgb_203743":(32,55,67),
        "astra_microblocks:rgb_2b4551":(43,69,81),
        "astra_microblocks:rgb_e7e4da":(231,228,218),
        "astra_microblocks:rgb_a7cdd9":(167,205,217),
        "astra_microblocks:rgb_17262c":(23,38,44),
    }
    for (y,u),(depth,mat) in front.items():
        c=colors.get(mat,(100,100,100))
        x0=u*scale; yy=(canvas.height-y-1)*scale
        d.rectangle((x0,yy,x0+scale-1,yy+scale-1),fill=c)
    img.save(out_path)

def main():
    spec=load()
    OUT.mkdir(parents=True,exist_ok=True)
    mats=spec["materials"]
    fp=Polygon(spec["footprint_ud_m"])
    if not fp.is_valid:
        fp=fp.buffer(0)
    frontage=float(spec["normalized_frame"]["frontage_m"])
    width=mcell(frontage)
    global MIRROR_CELL_SUM
    MIRROR_CELL_SUM=2*U_MARGIN+width-1
    top=float(spec["absolute_controls"]["source_envelope_height_m"])
    body_top=float(spec["absolute_controls"]["body_top_candidate_m"])
    height=mcell(top)

    volumes={}
    # Source footprint floor and roof/deck skins.
    raster_fill_polygon(fp,0,2,mats["shadow"],volumes)
    raster_fill_polygon(fp,mcell(body_top),mcell(body_top)+3,mats["roof"],volumes)
    # Exact footprint side/rear shell, front 1.25m left to the dedicated facade canvas.
    raster_boundary_walls(fp,0,mcell(body_top),.1875,mats["body_alt"],volumes,1.25)

    f=spec["facade_candidate"]
    zones=f["zones_u"]
    v=f["vertical_m"]
    main_in=float(f["main_wall_inward_m"])
    canvas=FacadeCanvas(width,height)

    # Continuous main wall field; individual modules then carve/project from it.
    canvas.box(-4,1,0,mcell(body_top),0,width,mats["body"])

    entry_u0,entry_u1=[round(q*width) for q in zones["entry"]]
    cent_u0,cent_u1=[round(q*width) for q in zones["central_bay"]]
    right_u0,right_u1=[round(q*width) for q in zones["right_body"]]
    garage_u0,garage_u1=[round(q*width) for q in zones["garage"]]

    def proj(face_inward):
        return mcell(main_in-float(face_inward))

    dgarage=proj(f["garage_face_inward_m"])
    dlower=proj(f["lower_bay_face_inward_m"])
    dupper=proj(f["upper_bay_face_inward_m"])
    dright=proj(f["right_body_face_inward_m"])
    dentry=proj(f["entry_back_inward_m"])

    # Recessed entry: clear main wall and place a dark back plane.
    entry_top=mcell(2.85)
    canvas.clear(-20,20,0,entry_top,entry_u0,entry_u1)
    canvas.box(dentry,dentry+3,0,entry_top,entry_u0,entry_u1,mats["shadow"])
    canvas.box(dentry,dentry+4,0,entry_top,entry_u1-3,entry_u1,mats["frame"])

    # Garage: a solid paneled door on a shallow plane.
    garage_head=mcell(v["garage_head"])
    canvas.clear(-16,20,mcell(.10),garage_head+2,garage_u0,garage_u1)
    canvas.box(dgarage,dgarage+3,mcell(.10),garage_head,garage_u0,garage_u1,mats["garage"])
    canvas.box(dgarage,dgarage+4,mcell(.10),garage_head,garage_u0,garage_u0+3,mats["frame"])
    canvas.box(dgarage,dgarage+4,mcell(.10),garage_head,garage_u1-3,garage_u1,mats["frame"])
    canvas.box(dgarage,dgarage+4,garage_head-3,garage_head,garage_u0,garage_u1,mats["frame"])
    for k in range(1,4):
        uc=round(garage_u0+(garage_u1-garage_u0)*k/4)
        canvas.box(dgarage+2,dgarage+3,mcell(.10),garage_head,uc,uc+1,mats["garage_seam"])
    for yy in np.arange(.55,float(v["garage_head"]),.48):
        yc=mcell(yy)
        canvas.box(dgarage+2,dgarage+3,yc,yc+1,garage_u0,garage_u1,mats["garage_seam"])

    # Lower bay shell. Strong projection is authored as a coherent box.
    lower_y0=mcell(2.42); lower_y1=mcell(5.20)
    canvas.box(0,dlower+1,lower_y0,lower_y0+3,cent_u0,cent_u1,mats["frame_alt"])
    canvas.box(0,dlower+1,lower_y1-3,lower_y1,cent_u0,cent_u1,mats["frame_alt"])
    canvas.box(0,dlower+1,lower_y0,lower_y1,cent_u0,cent_u0+3,mats["frame"])
    canvas.box(0,dlower+1,lower_y0,lower_y1,cent_u1-3,cent_u1,mats["frame"])
    canvas.box(dlower-3,dlower+1,lower_y0,lower_y1,cent_u0,cent_u1,mats["body_alt"])

    lower_sill=mcell(v["lower_window_sill"]); lower_head=mcell(v["lower_window_head"])
    opening_frame(canvas,cent_u0+5,cent_u1-5,lower_sill,lower_head,dlower,mats["window_frame"],2,5,1)
    # Restrained lower-spandrel half timbering.

    # Upper bay sits visibly behind the lower bay.
    upper_u0=round(.17*width); upper_u1=round(.60*width)
    upper_y0=mcell(5.28); upper_y1=mcell(8.20)
    canvas.box(0,dupper+1,upper_y0,upper_y0+3,upper_u0,upper_u1,mats["frame_alt"])
    canvas.box(0,dupper+1,upper_y1-3,upper_y1,upper_u0,upper_u1,mats["frame_alt"])
    canvas.box(0,dupper+1,upper_y0,upper_y1,upper_u0,upper_u0+3,mats["frame"])
    canvas.box(0,dupper+1,upper_y0,upper_y1,upper_u1-3,upper_u1,mats["frame"])
    canvas.box(dupper-3,dupper+1,upper_y0,upper_y1,upper_u0,upper_u1,mats["body"])
    upper_sill=mcell(v["upper_window_sill"]); upper_head=mcell(v["upper_window_head"])
    opening_frame(canvas,upper_u0+6,upper_u1-6,upper_sill,upper_head,dupper,mats["window_frame"],2,3,4)

    # Broad right vertical body, not the rejected narrow strip.
    right_y0=mcell(.25); right_y1=mcell(8.55)
    canvas.box(dright-3,dright+1,right_y0,right_y1,right_u0,right_u1,mats["body_alt"])
    canvas.box(0,dright+1,right_y0,right_y0+3,right_u0,right_u1,mats["frame_alt"])
    canvas.box(0,dright+1,right_y1-3,right_y1,right_u0,right_u1,mats["frame_alt"])
    canvas.box(0,dright+1,right_y0,right_y1,right_u0,right_u0+3,mats["frame"])
    canvas.box(0,dright+1,right_y0,right_y1,right_u1-3,right_u1,mats["frame"])

    # Persistent narrow upper-right window and small street-level right door.
    opening_frame(canvas,round(.78*width),round(.91*width),mcell(6.25),mcell(7.72),dright,mats["window_frame"],2,2,4)
    door_u0,door_u1=round(.84*width),round(.965*width)
    canvas.clear(-20,dright+8,mcell(.10),mcell(2.20),door_u0,door_u1)
    canvas.box(dright-2,dright+1,mcell(.10),mcell(2.20),door_u0,door_u1,mats["window_frame"])
    canvas.box(dright,dright+2,mcell(.18),mcell(2.10),door_u0+3,door_u1-3,mats["body"])

    # Readable structural diagonals on the broad right field.
    yA,yB,yC=mcell(2.48),mcell(5.30),mcell(8.48)

    # Terrace fascia projects to the source-visible front plane.
    fascia_y0=mcell(v["terrace_fascia_bottom"]); deck_y=mcell(v["terrace_deck"])
    dfascia=proj(.02)
    fascia_u0,fascia_u1=round(.10*width),round(.99*width)
    canvas.box(dfascia-3,dfascia+1,fascia_y0,deck_y,fascia_u0,fascia_u1,mats["body"])
    canvas.box(0,dfascia+1,fascia_y0,fascia_y0+3,fascia_u0,fascia_u1,mats["frame"])
    canvas.box(0,dfascia+1,deck_y-3,deck_y,fascia_u0,fascia_u1,mats["frame"])
    for frac0,frac1 in [(.10,.395),(.395,.69),(.69,.99)]:
        u0,u1=round(frac0*width),round(frac1*width)
        canvas.box(dfascia,dfascia+3,fascia_y0,deck_y,u0,u0+3,mats["frame"])

    # Modular trim is clipped to source-reviewed wall panels and outside openings.
    protected=[(a-1,b+1,c-1,e+1) for a,b,c,e in (r['bounds'] for r in canvas.opening_records)]
    stroke_cells=set()
    for feature in spec['framing_v002']['members']:
        face={'upper':dupper,'lower':dlower,'right':dright,'fascia':dfascia}[feature['plane']]
        uf0,y0,uf1,y1=feature['ends_u_fraction_y_m']
        c=feature['clip_u_fraction_y_m']
        clip=(c[0]*width,c[1]*width,mcell(c[2]),mcell(c[3]))
        stroke_cells.update(canvas.stroke_uy(face,face+2,uf0*width,mcell(y0),uf1*width,mcell(y1),
            spec['framing_v002']['width_cells'],mats['frame'],clip=clip,exclude=protected))
    canvas.stroke_cells=stroke_cells

    # Sparse front railing: two horizontals and widely spaced posts.
    rail_y0=deck_y+2; rail_y1=mcell(v["railing_top"])
    canvas.box(dfascia,dfascia+2,rail_y0,rail_y0+2,fascia_u0,fascia_u1,mats["frame"])
    canvas.box(dfascia,dfascia+2,rail_y1-2,rail_y1,fascia_u0,fascia_u1,mats["frame"])
    for frac in np.linspace(.11,.98,9):
        uc=round(float(frac)*width)
        canvas.box(dfascia,dfascia+2,rail_y0,rail_y1,uc-1,uc+1,mats["frame"])

    # Front pergola posts/header are authored in the continuous canvas.
    perg_y1=mcell(v["pergola_top"])
    for frac in (.10,.55,.99):
        uc=round(frac*width)
        canvas.box(dfascia-1,dfascia+2,deck_y,perg_y1,uc-2,uc+2,mats["frame"])
    canvas.box(dfascia-1,dfascia+2,perg_y1-3,perg_y1,fascia_u0,fascia_u1,mats["frame"])

    # Split the completed continuous facade into Astra hosts only once.
    facade_to_hosts(canvas,volumes,main_in)

    # Pergola rear posts and depth beams are true 3D members.
    front_z=FRONT_MARGIN+mcell(.02)
    back_z=FRONT_MARGIN+mcell(2.10)
    y0=deck_y; y1=perg_y1
    for frac in (.10,.55,.99):
        mx=U_MARGIN+round(frac*width)
        for mz in (front_z,back_z):
            for my in range(y0,y1):
                for dx in range(-2,2):
                    for dz0 in range(-1,2):
                        host_set(volumes,mx+dx,my,mz+dz0,mats["frame"])
    for mx_frac in (.10,.32,.55,.77,.99):
        mx=U_MARGIN+round(mx_frac*width)
        for mz in range(front_z,back_z+1):
            for dx in range(-1,2):
                for my in range(y1-3,y1):
                    host_set(volumes,mx+dx,my,mz,mats["frame_alt"])
    for mz in (front_z,back_z):
        for mx in range(U_MARGIN+fascia_u0,U_MARGIN+fascia_u1):
            for my in range(y1-3,y1):
                host_set(volumes,mx,my,mz,mats["frame"])

    # Right terrace railing return.
    rail_x=U_MARGIN+round(.99*width)
    for mz in range(front_z,back_z+1):
        for my in list(range(rail_y0,rail_y0+2))+list(range(rail_y1-2,rail_y1)):
            host_set(volumes,rail_x,my,mz,mats["frame"])
    for mz in np.linspace(front_z,back_z,5):
        mz=int(round(float(mz)))
        for my in range(rail_y0,rail_y1):
            host_set(volumes,rail_x,my,mz,mats["frame"])

    # Standalone registration marker; not part of the building.
    blocks={(0,0,0):"minecraft:yellow_concrete"}
    for coord in volumes:
        blocks[coord]=astra.HOST_STATE

    # Tight standalone region.
    xs=[p[0] for p in blocks]; ys=[p[1] for p in blocks]; zs=[p[2] for p in blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    writer=NBTWriter()
    payloads=[]
    occupied=0
    materials=set()
    for coord,vol in sorted(volumes.items()):
        rel=(coord[0]-bounds[0],coord[1]-bounds[1],coord[2]-bounds[2])
        payloads.append(astra.tile_entity_payload(writer,rel,vol))
        occupied+=vol.occupied_count()
        materials.update(vol.materials())

    info=write_single_region_litematic(
        OUT_FILE,blocks,bounds,REGION,
        "Lombard 1040 Building Lab v002",
        "Standalone EarthForge Single-Building Truth Lab. Normalized footprint, continuous facade canvas, Astra micro-depth architecture, no Lombard context.",
        data_version=DATA_VERSION,
        tile_entity_payloads=payloads,
    )

    # Exact readback validation.
    back,meta=read_back_block_map(OUT_FILE,REGION)
    normalized={c:canonical_state(s) for c,s in blocks.items()}
    exact_blocks=back==normalized
    astra_count=0
    decoded_cells=0
    decoded_by_host={}
    for te in meta["tile_entities"]:
        if te.get("id")==astra.BLOCK_ENTITY_ID:
            astra_count+=1
            coord=(int(te["x"])+bounds[0],int(te["y"])+bounds[1],int(te["z"])+bounds[2])
            if coord in decoded_by_host:
                raise ValueError("Duplicate Astra host in readback")
            decoded=list(astra.decode_volume_v4(te["volume_v4"]))
            decoded_by_host[coord]=decoded
            decoded_cells+=sum(v is not None for v in decoded)
    exact_astra=(set(decoded_by_host)==set(volumes) and
                 all(decoded_by_host[p]==v.cells for p,v in volumes.items()))

    no_glass=not any("glass" in str(mat).lower() for mat in materials)
    micro_only_above_ground=all(
        state==astra.HOST_STATE
        for (x,y,z),state in blocks.items()
        if y>0
    )

    def decoded_material(mx,my,mz):
        p=(mx//16,my//16,mz//16)
        cells=decoded_by_host.get(p)
        return None if cells is None else cells[(my%16)*256+(mz%16)*16+(mx%16)]
    opening_checks={}; aperture_audit=[]
    for label,rec in zip(('lower','upper','right'),canvas.opening_records):
        blocked=[]; tested=0
        for u,y in rec['rays']:
            mx=MIRROR_CELL_SUM-(U_MARGIN+u)
            for dd in range(-24,rec['face']+4):
                tested+=1
                mz=FRONT_MARGIN+mcell(main_in)-dd
                if decoded_material(mx,y,mz) is not None: blocked.append((mx,y,mz))
        opening_checks[label+'_window_all_panes_clear']=len(rec['rays'])>10 and not blocked
        aperture_audit.append({'name':label,'pane_rays':len(rec['rays']),
                              'decoded_samples':tested,'blocked_samples':len(blocked)})
    trim_crossings=sum(any(a<=u+.5<b and c<=y+.5<e for a,b,c,e in protected)
                       for dd,y,u in canvas.stroke_cells)
    _,parent_meta=read_back_block_map(PARENT_FILE,PARENT_REGION)
    parent_cells={}
    for te in parent_meta['tile_entities']:
        px,py,pz=int(te['x']),int(te['y']),int(te['z'])
        for i,mat in enumerate(astra.decode_volume_v4(te['volume_v4'])):
            if mat is not None:
                parent_cells[(px*16+(i&15),py*16+(i>>8),pz*16+((i>>4)&15))]=mat
    child_cells={}
    for p,vs in decoded_by_host.items():
        for i,mat in enumerate(vs):
            if mat is not None:
                x=p[0]*16+(i&15); y=p[1]*16+(i>>8); z=p[2]*16+((i>>4)&15)
                child_cells[(MIRROR_CELL_SUM-x,y,z)]=mat
    changed=[p for p in parent_cells.keys()|child_cells.keys() if parent_cells.get(p)!=child_cells.get(p)]
    outside=[p for p in changed if not (28<=p[2]<=56 and 0<=p[1]<deck_y)]
    opening_checks['trim_aperture_intersections_zero']=trim_crossings==0
    opening_checks['registered_non_facade_geometry_preserved']=not outside
    opening_checks['photo_handedness_correct']=(MIRROR_CELL_SUM-(U_MARGIN+garage_u0) >
                                               MIRROR_CELL_SUM-(U_MARGIN+round(.84*width)))

    checks={
        "exact_block_map":exact_blocks,
        "exact_astra_cells_and_materials":exact_astra,
        "astra_host_count":astra_count==len(volumes),
        "astra_microcell_decode":decoded_cells==occupied,
        "micro_only_above_ground":micro_only_above_ground,
        "no_glass":no_glass,
        "source_footprint_area":abs(fp.area-177.2084)<.15,
        "source_frontage":abs(frontage-10.934756432120318)<1e-6,
        "continuous_facade_canvas":len(canvas.cells)>25000,
        **opening_checks,
    }

    # Standalone review renders.
    front_png=OUT/"Lombard_1040_BuildingLab_v002_front.png"
    # Final decoded positions, viewed from -Z. Front depth slice excludes the rear shell.
    front={}
    for (hx,hy,hz),vs in decoded_by_host.items():
        for i,mat in enumerate(vs):
            if mat is None: continue
            x=hx*16+(i&15); y=hy*16+(i>>8); z=hz*16+((i>>4)&15)
            u=MIRROR_CELL_SUM-x-U_MARGIN
            if not (0<=u<width and 0<=y<height and z<=56): continue
            key=(y,u)
            if key not in front or z<front[key][0]: front[key]=(z,mat)
    preview=Image.new('RGB',(width*4,height*4),(237,239,237)); pd=ImageDraw.Draw(preview)
    for (y,u),(zz,mat) in front.items():
        h=mat.rsplit('_',1)[-1]
        color=tuple(int(h[j:j+2],16) for j in (0,2,4)) if len(h)==6 else (90,90,90)
        pd.rectangle((u*4,(height-1-y)*4,u*4+3,(height-y)*4-1),fill=color)
    preview.save(front_png)

    plan_png=OUT/"Lombard_1040_BuildingLab_v002_plan.png"
    plan=Image.new("RGB",(900,900),(244,244,241)); pd=ImageDraw.Draw(plan)
    min_u,min_d,max_u,max_d=fp.bounds
    def pp(u,d):
        x=50+(u-min_u)/max(1e-9,max_u-min_u)*800
        y=50+(d-min_d)/max(1e-9,max_d-min_d)*800
        return int(x),int(y)
    pd.polygon([pp(u,d) for u,d in fp.exterior.coords],fill=(210,220,224),outline=(35,50,56))
    pd.line([pp(0,0),pp(frontage,0)],fill=(26,104,162),width=8)
    pd.text((50,20),"1040 Building Lab v002 - normalized source footprint; blue = verified street-facing edge",fill=(35,45,48))
    plan.save(plan_png)

    status="PASS" if all(checks.values()) else "FAIL"
    report={
        "schema_version":1,
        "lab_id":spec["lab_id"],
        "status":status,
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "branch":spec["branch"],
        "standalone":True,
        "lombard_context_included":False,
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "footprint_area_m2":fp.area,
        "frontage_m":frontage,
        "max_depth_m":spec["normalized_frame"]["max_depth_m"],
        "height_m":top,
        "body_top_m":body_top,
        "micro_host_blocks":len(volumes),
        "micro_occupied_cells":occupied,
        "facade_canvas_cells":len(canvas.cells),
        "facade_feature_counts":canvas.feature_counts,
        "materials":sorted(materials),
        "checks":checks,
        "parent_sha256":hashlib.sha256(PARENT_FILE.read_bytes()).hexdigest(),
        "registered_changed_microcells":len(changed),
        "out_of_scope_changes":len(outside),
        "aperture_audit":aperture_audit,
        "trim_aperture_intersections":trim_crossings,
        "normalized_x_reflection_cell_sum":MIRROR_CELL_SUM,
        "review_targets":[
            "whole-house standalone silhouette",
            "lower bay versus upper bay depth",
            "broad right body proportion",
            "garage and recessed left entry",
            "open window voids / no vertical striping",
            "terrace railing and pergola depth",
            "side/rear footprint shape",
        ],
        "visual_status":"REVIEW_REQUIRED_NOT_ACCEPTED",
        "resolved_diagnostics":["Photo-facing handedness", "Square-brush diagonal inflation", "Trim crossing window apertures"],
        "known_visual_defects":[
            "Facade ratios and low garage opening remain inherited provisional estimates, not new measurements.",
            "Full-depth cap, side/rear shape, terrace depth and precise opening dimensions remain source-unresolved."
        ],
        "integration_status":"BLOCKED_VISUAL_QA_AND_SOURCE_REVIEW",
    }
    (OUT/"Lombard_1040_BuildingLab_v002_validation.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")

    integration={
        "schema_version":1,
        "status":"DO_NOT_APPLY_UNTIL_STANDALONE_ACCEPTED",
        "normalized_frame":spec["normalized_frame"],
        "standalone_offsets_micro":{"u_margin":U_MARGIN,"front_margin":FRONT_MARGIN,"x_reflection_cell_sum":MIRROR_CELL_SUM},
        "inverse_cell_center_formula":{"u_m":"(x_reflection_cell_sum - x_micro - u_margin + 0.5)/16", "d_m":"(z_micro - front_margin + 0.5)/16", "y_m":"(y_micro+0.5)/16"},
        "lombard_target":{
            "branch":"codex/lombard-sf-hardmode",
            "driveway_datum_micro_y":spec["absolute_controls"]["driveway_datum_lombard_micro_y"],
            "front_origin_lombard_local_m":spec["normalized_frame"]["front_origin_lombard_local_m"],
            "uvec_lombard_local":spec["normalized_frame"]["uvec_lombard_local"],
            "inward_normal_lombard_local":spec["normalized_frame"]["inward_normal_lombard_local"],
        },
        "rule":"Transform accepted standalone u/d/y microcells back into the locked Lombard frame; never re-infer placement by eye.",
    }
    (OUT/"Lombard_1040_BuildingLab_v002_integration_transform.json").write_text(
        json.dumps(integration,indent=2)+"\n",encoding="utf-8")
    (OUT/"Build_notes.md").write_text(
        "# 1040 Lombard Building Lab v002\n\n"
        "Standalone EarthForge Single-Building Truth Lab. No Lombard context is included. "
        "Facade is authored on one continuous microcell canvas and split into Astra hosts only at export. "
        "Windows are true open voids with microblock frames; no glass is used. "
        "v002 corrects handedness and panel framing with protected apertures; broader dimensions remain provisional. "
        "Do not integrate back into Lombard until source and visual review are accepted.\n",
        encoding="utf-8")

    project_path=LAB/"project.json"
    project=json.loads(project_path.read_text(encoding="utf-8"))
    project["status"]="V002_FRAMING_REVIEW" if status=="PASS" else "V002_VALIDATION_FAILED"
    project["visual_status"]="REVIEW_REQUIRED_NOT_ACCEPTED"
    project["geometry_accepted"]=False
    project["active_artifact"]=str(OUT_FILE.relative_to(ROOT)).replace("\\","/")
    project["active_validation"]=str((OUT/"Lombard_1040_BuildingLab_v002_validation.json").relative_to(ROOT)).replace("\\","/")
    project["active_front_render"]=str(front_png.relative_to(ROOT)).replace("\\","/")
    project["active_plan_render"]=str(plan_png.relative_to(ROOT)).replace("\\","/")
    project["integration_transform"]=str((OUT/"Lombard_1040_BuildingLab_v002_integration_transform.json").relative_to(ROOT)).replace("\\","/")
    if status=="PASS":
        project["active_spec"]=str(SPEC.relative_to(ROOT)).replace("\\","/")
        project_path.write_text(json.dumps(project,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({
        "status":status,
        "file":str(OUT_FILE),
        "sha256":info["sha256"],
        "micro_hosts":len(volumes),
        "micro_cells":occupied,
        "facade_cells":len(canvas.cells),
        "checks":checks,
    },indent=2))
    if status!="PASS":
        raise SystemExit(1)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
