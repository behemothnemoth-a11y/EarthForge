#!/usr/bin/env python3
"""Reproducible hybrid 621 facade, authored independently of prior schematics.

Run from any directory: python this_file.py [--output-dir PATH]
Dependencies: numpy, Pillow, scipy. All geometry uses a continuous 1/16 grid.
Whole homogeneous cubes are exported as vanilla blocks, never Astra hosts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.export.litematic_codec import (NBTWriter, write_single_region_litematic,
    read_back_block_map)
from pipeline.microblocks.astra_microblock_codec import (MicroVolume, HOST_STATE,
    tile_entity_payload, decode_volume_v4)

CFG_PATH = ROOT / 'projects/redfield_sd/poc_001/labs/621_hybrid_restart_v001.json'
NAME = 'Redfield_621_HybridRestart_v001'
COLORS = {'brick': '#a35b46', 'trim': '#d8c39a', 'green': '#28564b',
          'green_inset': '#627154', 'frame': '#343635', 'wood': '#71533b',
          'base': '#8c918c', 'floor': '#a37d51', 'metal': '#d9b34a'}


class Model:
    def __init__(self, cfg):
        self.cfg = cfg
        dim = cfg['dimensions_cells']
        self.d0, self.d1 = dim['depth_min'], dim['depth_max']
        self.width = cfg['coordinates']['width_blocks'] * 16
        self.a = np.zeros((self.d1-self.d0, dim['height'], self.width), dtype=np.uint8)
        self.names = ['air'] + list(cfg['materials'])
        self.ids = {s: i for i, s in enumerate(self.names)}
        self.operations = []

    def box(self, d0, d1, y0, y1, u0, u1, mat, feature):
        box = (max(d0, self.d0), min(d1, self.d1), max(y0, 0),
               min(y1, self.a.shape[1]), max(u0, 0), min(u1, self.width))
        d0, d1, y0, y1, u0, u1 = map(int, box)
        if d1 <= d0 or y1 <= y0 or u1 <= u0:
            return
        self.a[d0-self.d0:d1-self.d0, y0:y1, u0:u1] = self.ids[mat]
        self.operations.append({'feature': feature, 'box': list(box), 'material': mat})

    def line(self, u0, y0, u1, y1, d0, d1, mat, feature, thickness=2):
        steps = max(abs(u1-u0), abs(y1-y0), 1)
        for i in range(steps+1):
            u = round(u0+(u1-u0)*i/steps)
            y = round(y0+(y1-y0)*i/steps)
            self.box(d0,d1,y-thickness,y+thickness+1,u-thickness,u+thickness+1,mat,feature)

    def ring(self, uc, yc, r0, r1, d0, d1, mat, feature):
        for y in range(yc-r1,yc+r1+1):
            for u in range(uc-r1,uc+r1+1):
                if r0*r0 <= (u-uc)**2+(y-yc)**2 <= r1*r1:
                    self.box(d0,d1,y,y+1,u,u+1,mat,feature)


def author(cfg):
    m = Model(cfg)
    b = m.box
    # Primary wall: two solid blocks thick, aligned to the host grid.
    b(-32,0,0,192,0,128,'brick','masonry_core')
    b(-32,0,0,16,0,128,'base','masonry_plinth')
    b(-32,0,16,64,0,128,'green','storefront_structure')
    b(-32,0,64,80,0,128,'green','structural_sign_band')
    # Open display wells and central walk-through entry, no glass.
    for u0,u1 in [(16,48),(80,112)]:
        b(-32,1,12,59,u0,u1,'air','display_opening')
        b(-32,-29,12,59,u0,u0+2,'wood','display_reveal')
        b(-32,-29,12,59,u1-2,u1,'wood','display_reveal')
        b(-32,0,11,13,u0,u1,'trim','display_sill')
        # Thin rear frames supported by the sill and header.
        for u in [u0,u1-2]: b(-27,-25,13,59,u,u+2,'frame','display_frame')
        b(-27,-25,46,48,u0,u1,'frame','display_transom')
    b(-48,1,0,59,54,74,'air','walk_through_entry')
    # Shallow structural returns and floor strips, not a full building extrusion.
    b(-48,-32,0,96,0,16,'brick','east_return')
    b(-48,-32,0,96,112,128,'brick','west_return')
    b(-48,-32,0,8,16,54,'floor','display_floor')
    b(-48,-32,0,8,74,112,'floor','display_floor')
    b(-48,-32,80,88,0,128,'floor','upper_floor_strip')
    # Three tall upper openings; host-aligned widths preserve normal masonry piers.
    for win in cfg['upper_windows']:
        l,r = win['u0'],win['u1']; c=(l+r)//2
        b(-32,1,88,145,l,r,'air','upper_window_opening')
        for u in [l,l+15]: b(-24,-22,88,145,u,u+1,'frame','upper_window_frame')
        b(-24,-22,116,118,l,r,'frame','upper_window_crossbar')
        b(-24,-22,88,145,c,c+1,'frame','upper_window_mullion')
        b(-24,-22,88,90,l,r,'frame','upper_window_frame')
        b(-24,-22,143,145,l,r,'frame','upper_window_frame')
        # Recess-facing stone liners connect frames to the brick.
        b(-25,3,87,89,l,r,'trim','window_reveal_sill')
        for u in [l-3,r]:
            b(0,5,87,146,u,u+3,'trim','window_jamb')
            b(5,7,89,144,u+1,u+2,'trim','jamb_fluting')
        b(0,8,85,89,l-5,r+5,'trim','projecting_sill')
        b(0,6,144,149,l-5,r+5,'trim','window_lintel')
        m.line(l-5,150,c,157,0,8,'trim','pediment',1)
        m.line(c,157,r+5,150,0,8,'trim','pediment',1)
        b(0,8,148,151,l-5,r+5,'trim','pediment_base')
        b(0,5,147,152,c-2,c+2,'trim','keystone')
    # Storefront posts, recessed panels and connective frame details.
    for l,r in [(3,10),(48,54),(74,80),(118,125)]:
        b(0,5,2,64,l,r,'green','storefront_pilaster')
        b(5,7,7,57,l+2,r-2,'trim','pilaster_inlay')
        b(0,8,0,5,l-2,r+2,'base','pilaster_base')
        b(0,8,57,64,l-2,r+2,'trim','pilaster_capital')
    for l,r in [(16,48),(80,112)]:
        b(0,3,2,10,l,r,'green','stallriser')
        b(3,4,4,8,l+3,r-3,'trim','stallriser_border')
        b(4,5,5,7,l+4,r-4,'green_inset','stallriser_inset')
    # Door jambs and transom; walk-through centre remains empty.
    for u in [52,74]: b(-30,2,0,59,u,u+2,'wood','entry_jamb')
    b(-30,-28,48,50,54,74,'wood','entry_transom')
    for u in [57,62,67,72]: b(-30,-28,50,59,u,u+1,'wood','entry_transom_grid')
    for y in [54,58]: b(-30,-28,y,y+1,54,74,'wood','entry_transom_grid')
    # Full-block sign band with thin layered borders and three inset panels.
    b(0,6,64,67,0,128,'trim','sign_band_lower_moulding')
    b(0,5,77,80,0,128,'trim','sign_band_upper_moulding')
    for l,r in [(9,43),(47,81),(85,119)]:
        b(0,3,68,76,l,r,'green_inset','sign_panel')
        b(3,4,69,75,l+1,r-1,'green','sign_panel_border')
    # Connected sloping awning. Its back meets the solid structural sign band.
    for d in range(0,23):
        y = 65-round(d*0.28)
        b(d,d+1,y,y+2,8,120,'green','sloped_awning')
    b(21,24,58,61,8,120,'trim','awning_front_edge')
    for u in range(10,119,6): b(21,24,56,59,u,u+3,'trim','awning_scallop')
    for u in [10,49,77,116]:
        for d in range(0,23):
            y=53+round(d*0.27)
            b(d,d+1,y,y+2,u,u+2,'green','awning_brace')
    # Strong masonry lintel, bracketed cornice, fine edge profile.
    b(0,6,160,164,0,128,'trim','cornice_lower_string')
    for u in range(4,125,10):
        b(0,5,164,174,u,u+4,'green','cornice_bracket')
        b(5,9,169,175,u,u+4,'trim','cornice_bracket_tip')
    for y0,y1,d in [(174,177,9),(177,180,13),(180,182,16)]:
        b(0,d,y0,y1,0,128,'trim','cornice_profile')
    # Raised centre and corner parapet masses are whole-brick volumes.
    b(-32,0,192,200,0,16,'brick','parapet_end_piers')
    b(-32,0,192,200,112,128,'brick','parapet_end_piers')
    b(-32,0,192,200,40,88,'brick','parapet_centre_step')
    b(-32,0,200,208,48,80,'brick','parapet_centre_step')
    for l,r,y in [(0,16,200),(16,40,192),(40,48,200),(48,80,208),(80,88,200),(88,112,192),(112,128,200)]:
        b(-32,3,y-3,y,l,r,'trim','parapet_coping')
    for c in [8,120]:
        b(0,3,184,196,c-5,c+5,'trim','corner_medallion_base')
        b(3,4,186,194,c-4,c+4,'green','corner_medallion_field')
        m.ring(c,190,2,3,4,6,'trim','corner_rosette')
    b(0,3,189,203,58,70,'trim','crest_base')
    m.ring(64,196,3,5,3,6,'trim','central_rosette')
    b(3,5,194,199,62,67,'green','central_rosette_centre')
    # Keep the clear entry envelope authoritative over decorative post bases.
    b(-48,8,0,40,54,74,'air','entry_clearance_final')
    return m


SLABS = {'minecraft:bricks': 'minecraft:brick_slab',
         'minecraft:smooth_sandstone': 'minecraft:smooth_sandstone_slab',
         'minecraft:dark_prismarine': 'minecraft:dark_prismarine_slab',
         'minecraft:stone_bricks': 'minecraft:stone_brick_slab',
         'minecraft:spruce_planks': 'minecraft:spruce_slab',
         'minecraft:polished_blackstone': 'minecraft:polished_blackstone_slab',
         'minecraft:dark_oak_planks': 'minecraft:dark_oak_slab'}


def split(m):
    blocks, hosts, kinds = {}, {}, {}
    c = m.cfg['coordinates']
    for di in range(0,m.a.shape[0],16):
        for yi in range(0,m.a.shape[1],16):
            for ui in range(0,m.width,16):
                a = m.a[di:di+16,yi:yi+16,ui:ui+16]
                vals = np.unique(a)
                if len(vals)==1 and vals[0]==0: continue
                xyz=(c['front_boundary_x']+(di+m.d0)//16,yi//16,c['min_z']+ui//16)
                state=None;kind='microblock'
                if len(vals)==1:
                    state=m.cfg['materials'][m.names[int(vals[0])]];kind='full_block'
                elif len(vals)==2 and vals[0]==0:
                    mat=m.cfg['materials'][m.names[int(vals[1])]]
                    if mat in SLABS:
                        for half,section,empty in [('bottom',a[:,:8,:],a[:,8:,:]),('top',a[:,8:,:],a[:,:8,:])]:
                            if np.all(section==vals[1]) and not np.any(empty):
                                state=SLABS[mat]+'[type='+half+',waterlogged=false]';kind='vanilla_slab'
                if state is None:
                    v=MicroVolume()
                    lut=[None]+[m.cfg['materials'][n] for n in m.names[1:]]
                    v.cells=[lut[int(x)] for x in a.transpose(1,2,0).ravel()]
                    hosts[xyz]=v;state=HOST_STATE
                blocks[xyz]=state;kinds[xyz]=kind
    return blocks,hosts,kinds


def read_cells(blocks,meta,m):
    a=np.zeros_like(m.a)
    reverse={v:m.ids[k] for k,v in m.cfg['materials'].items()}
    pos=meta['region_position']
    tes={(t['x']+pos[0],t['y']+pos[1],t['z']+pos[2]):t for t in meta['tile_entities']}
    for (x,y,z),state in blocks.items():
        di=(x-m.cfg['coordinates']['front_boundary_x'])*16-m.d0
        yi=y*16;ui=(z-m.cfg['coordinates']['min_z'])*16
        if state==HOST_STATE:
            cells=decode_volume_v4(tes[(x,y,z)]['volume_v4'])
            vol=np.array([0 if s is None else reverse[s] for s in cells],dtype=np.uint8).reshape(16,16,16).transpose(2,0,1)
        elif state in reverse: vol=np.full((16,16,16),reverse[state],np.uint8)
        else:
            basic=state.split('[')[0];mat=next(k for k,v in SLABS.items() if v==basic)
            vol=np.zeros((16,16,16),np.uint8)
            vol[:,8:,:] = reverse[mat] if 'type=top' in state else 0
            if 'type=bottom' in state:vol[:,:8,:]=reverse[mat]
        a[di:di+16,yi:yi+16,ui:ui+16]=vol
    return a


def font(size):
    for p in ['C:/Windows/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()


def color_lut(m):
    return np.array([(239,238,230)]+[tuple(bytes.fromhex(COLORS[n][1:])) for n in m.names[1:]],dtype=np.uint8)


def front_preview(a,m,kinds,path):
    occupied=np.any(a,axis=0)
    dep=a.shape[0]-1-np.argmax(a[::-1]!=0,axis=0)
    yy,uu=np.indices(dep.shape);ids=a[dep,yy,uu];ids[~occupied]=0
    lut=color_lut(m)
    rgb=lut[ids].astype(float)
    shade=np.clip(0.72+0.28*dep/a.shape[0],0.65,1)
    rgb*=np.where(occupied,shade,1)[...,None]
    actual=Image.fromarray(np.uint8(rgb)[::-1,::-1]).resize((512,832),Image.Resampling.NEAREST)
    maprgb=np.full((*dep.shape,3),(239,238,230),np.uint8)
    kindcolors={'full_block':(51,121,177),'vanilla_slab':(61,164,159),'microblock':(207,139,49)}
    for y,u in zip(*np.where(occupied)):
        x=m.cfg['coordinates']['front_boundary_x']+(int(dep[y,u])+m.d0)//16
        z=m.cfg['coordinates']['min_z']+u//16
        maprgb[y,u]=kindcolors[kinds[(x,y//16,z)]]
    overlay=Image.fromarray(maprgb[::-1,::-1]).resize((512,832),Image.Resampling.NEAREST)
    im=Image.new('RGB',(1260,1050),'#efeee6');d=ImageDraw.Draw(im)
    d.text((45,24),'621 / HYBRID RESTART',font=font(32),fill='#243c39')
    d.text((45,68),'Actual exported geometry | 8-block frontage | no glass | concept-based facade',font=font(18),fill='#54605b')
    im.paste(actual,(60,135));im.paste(overlay,(680,135))
    d.text((60,104),'MATERIAL + DEPTH',font=font(18),fill='#243c39')
    d.text((680,104),'BLOCK TYPE AT VISIBLE SURFACE',font=font(18),fill='#243c39')
    for i,(name,col) in enumerate(kindcolors.items()):
        x=70+i*400;d.rectangle((x,994,x+20,1014),fill=col)
        d.text((x+30,991),name.replace('_',' ').title(),font=font(19),fill='#243c39')
    im.save(path)


def rectangles(a):
    """Greedy rectangular patches of equal nonzero material IDs."""
    a=a.copy();h,w=a.shape
    for y in range(h):
        x=0
        while x<w:
            v=int(a[y,x])
            if not v:x+=1;continue
            right=x+1
            while right<w and a[y,right]==v:right+=1
            bottom=y+1
            while bottom<h and np.all(a[bottom,x:right]==v):bottom+=1
            a[y:bottom,x:right]=0
            yield x,y,right,bottom,v
            x=right


def perspective(a,m,path):
    # Exact exposed surfaces, merged only across equal material coplanar cells.
    faces=[];lut=color_lut(m)
    for axis in range(3):
        v=np.moveaxis(a,axis,0)
        for i in range(len(v)):
            nxt=v[i+1] if i+1<len(v) else np.zeros_like(v[i])
            surface=np.where((v[i]!=0)&(nxt==0),v[i],0)
            for x0,y0,x1,y1,mat in rectangles(surface):
                # axis0: remaining y,u; axis1: d,u; axis2: d,y
                pts=[]
                for xx,yy in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
                    p=[yy,xx];p.insert(axis,i+1)
                    pts.append(tuple(p))
                depth=sum(p[0]+0.34*p[2]+0.26*p[1] for p in pts)/4
                faces.append((depth,axis,mat,pts))
    def project(p):
        dd,y,u=p
        return (-u+0.34*dd, -y+0.12*u+0.26*dd)
    allp=[project(p) for _,_,_,pts in faces for p in pts]
    mn=np.min(allp,axis=0);mx=np.max(allp,axis=0)
    scale=min(1050/(mx[0]-mn[0]),920/(mx[1]-mn[1]))
    im=Image.new('RGB',(1240,1140),'#efeee6');draw=ImageDraw.Draw(im)
    draw.text((42,24),'621 / DEPTH AND STRUCTURE',font=font(31),fill='#243c39')
    draw.text((42,69),'Geometry preview from the saved .litematic; material colors are illustrative.',font=font(18),fill='#54605b')
    for _,axis,mat,pts in sorted(faces):
        col=tuple((lut[mat]*[0.83,1.0,0.67][axis]).astype(int))
        poly=[tuple((np.array(project(p))-mn)*scale+np.array([88,125])) for p in pts]
        draw.polygon(poly,fill=col,outline=col)
        # Cover subpixel cracks between coplanar patches after screen rounding.
        draw.line(poly+[poly[0]],fill=col,width=2)
    draw.text((42,1088),'Full masonry core + fine projecting details. Shallow facade study; rear remains open.',font=font(19),fill='#243c39')
    im.save(path)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args()
    out=args.output_dir or ROOT/'projects/redfield_sd/outputs/building_labs/621_hybrid_restart_v001'
    out.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(CFG_PATH.read_text());m=author(cfg)
    blocks,hosts,kinds=split(m)
    bounds=cfg['placement']['region_bounds'];writer=NBTWriter()
    entities=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v)
              for (x,y,z),v in sorted(hosts.items())]
    target=out/(NAME+'.litematic')
    stats=write_single_region_litematic(target,blocks,tuple(bounds),cfg['id'],NAME,
        '621 hybrid restart: full masonry with Astra detail. Concept-based facade only. Same Redfield origin.',
        data_version=4903,tile_entity_payloads=entities)
    reread,meta=read_back_block_map(target,cfg['id'])
    assert reread==blocks,'Block state read-back failed'
    rebuilt=read_cells(reread,meta,m)
    assert np.array_equal(rebuilt,m.a),'Microcell/material/coordinate equivalence failed'
    assert len(meta['tile_entities'])==len(hosts)
    # Collision-level comparison in one common grid checks mixed-type seams.
    _,ncomponents=label(rebuilt!=0)
    assert ncomponents==1, f'Detached geometry: {ncomponents} components'
    assert all(not (v.occupied_count()==4096 and len(v.materials())==1) for v in hosts.values())
    # Clear 1.25-block entry across complete depth, 2.5 blocks tall.
    assert not np.any(rebuilt[:,0:40,54:74]),'Entry obstructed'
    assert all(-99<=p[2]<=-92 for p in blocks),'Neighbor footprint changed'
    assert not any('glass' in x for x in stats['palette'])
    c=Counter(kinds.values());equiv={k:0 for k in c}
    for p,k in kinds.items():equiv[k]+=hosts[p].occupied_count() if k=='microblock' else (2048 if k=='vanilla_slab' else 4096)
    report={**stats,'id':cfg['id'],'counts':dict(c),'occupied_cell_equivalents_by_type':equiv,
      'vanilla_share_of_occupied_volume':round((equiv.get('full_block',0)+equiv.get('vanilla_slab',0))/sum(equiv.values()),4),
      'astra_microcells':sum(v.occupied_count() for v in hosts.values()),
      'validation':{'block_readback':True,'exact_material_and_geometry_readback':True,'connected_components':ncomponents,
        'unnecessary_homogeneous_full_cube_hosts':0,'clear_entry_width_blocks':1.25,'clear_entry_height_blocks':2.5,
        'neighbor_slots_untouched':True,'glass':False,'roof':False,'full_building_body':False,'in_game_validation':'not performed'},
      'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'config_sha256':hashlib.sha256(CFG_PATH.read_bytes()).hexdigest()}
    (out/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2))
    (out/(NAME+'_operations.json')).write_text(json.dumps(m.operations,indent=2))
    front_preview(rebuilt,m,kinds,out/(NAME+'_front.png'))
    perspective(rebuilt,m,out/(NAME+'_oblique.png'))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
