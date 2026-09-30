#!/usr/bin/env python3
"""Reference-led facade-only 617-627 streetscape; preserves approved 621 v003."""
from pathlib import Path
import sys,json,copy,hashlib,re,zipfile
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
import generate_redfield_621_hybrid_restart_v003 as base
from pipeline.export.litematic_codec import NBTWriter,write_single_region_litematic,read_back_block_map
from pipeline.microblocks.astra_microblock_codec import tile_entity_payload
NAME='Redfield_WestMain_617-627_HybridFacades_v001'
OUT=ROOT/'projects/redfield_sd/outputs/building_labs/west_main_hybrid_facades_v001'
CONFIG=ROOT/'projects/redfield_sd/poc_001/labs/west_main_hybrid_facades_v001.json'


def ornament(m,center,y,half=5):
    b=m.box
    b(0,4,y-half-2,y+half+3,center-half-2,center+half+3,'trim','ornament_tablet')
    b(4,5,y-half,y+half+1,center-half,center+half+1,'stone_shadow','ornament_recess')
    m.ring(center,y,half-2,half,5,7,'stone_edge','ornament_ring')
    b(5,7,y-1,y+2,center-1,center+2,'bronze','ornament_boss')


def window(m,c,y0,y1,pediment=True,half=10):
    b=m.box;l=c-half;r=c+half
    b(-32,1,y0,y1,l,r,'air','upper_opening')
    b(-6,-5,y0,y1,l,r,'glass_smoke','upper_glass')
    for u in [l,r-1,c]:b(-5,-3,y0,y1,u,u+1,'frame','window_frame')
    for y in [y0,y0+(y1-y0)//2,y1-2]:b(-5,-3,y,y+2,l,r,'frame','window_rail')
    for u in [l-4,r]:
        b(0,5,y0-2,y1+2,u,u+4,'trim','stone_jamb')
        b(5,6,y0,y1,u,u+1,'stone_shadow','reed_groove')
        b(5,7,y0,y1,u+2,u+3,'stone_edge','reed_edge')
        for y in [y0+3,y1-5]:b(5,7,y,y+2,u+1,u+3,'bronze','jamb_rosette')
    b(-6,8,y0-3,y0,l-5,r+5,'trim','sill')
    b(7,8,y0-3,y0-2,l-5,r+5,'stone_shadow','sill_shadow')
    b(7,9,y0-1,y0,l-5,r+5,'stone_edge','sill_bead')
    b(0,7,y1,y1+6,l-5,r+5,'stone_mid','lintel')
    b(6,7,y1+1,y1+3,l-3,r+3,'stone_shadow','lintel_panel')
    b(7,8,y1+5,y1+6,l-5,r+5,'stone_edge','lintel_bead')
    if pediment:
        for a,z in [(l-5,c),(c,r+5)]:
            ya=y1+7 if a<c else y1+14;yz=y1+14 if a<c else y1+7
            m.line(a,ya,z,yz,0,7,'trim','pediment',1)
            m.line(a,ya,z,yz,7,8,'stone_edge','pediment_bead',0)
        b(0,8,y1+6,y1+8,l-5,r+5,'stone_shadow','pediment_base')
        b(7,8,y1+7,y1+8,l-5,r+5,'stone_edge','pediment_base_bead')
        b(0,5,y1+6,y1+12,c-1,c+2,'bronze','pediment_boss')


def lamp(m,u):
    b=m.box
    # Attached bracket and decorative miniature lantern; host is not a light source.
    b(0,3,49,64,u-2,u+3,'frame','lamp_backplate')
    b(1,15,55,57,u,u+2,'bronze','lamp_arm')
    b(12,14,49,56,u,u+2,'frame','lamp_chain')
    b(9,17,41,49,u-3,u+5,'glass_amber','lamp_glass')
    b(10,16,42,48,u-2,u+4,'lamp_warm','lamp_core')
    for d in [9,16]:
        for v in [u-3,u+4]:b(d,d+1,41,49,v,v+1,'bronze','lamp_cage')
    for y in [40,49]:b(8,18,y,y+1,u-4,u+6,'frame','lamp_cap')


def shop(m,s0,s1,paint,light,shadow,door=True):
    b=m.box;mid=(s0+s1)//2
    # Three-bay storefront with a recessed, framed central portal.
    b(-2,1,2,80,s0,s1,paint,'painted_shop_face')
    dl,dr=mid-10,mid+10
    bays=[(s0+9,dl-6),(dr+6,s1-9)]
    for l,r in bays:
        b(-32,1,12,59,l,r,'air','shop_opening')
        b(-6,-5,13,47,l,r,'glass_clear','shop_glass')
        b(-6,-5,49,59,l,r,'glass_amber','shop_transom_glass')
        for u in [l,r-2]:b(-5,-3,12,59,u,u+2,shadow,'shop_frame')
        for y in [12,47,58]:b(-5,-3,y,y+2,l,r,shadow,'shop_rail')
        for u in range(l+5,r-1,6):b(-5,-3,49,59,u,u+1,'bronze','shop_transom_lead')
        b(-6,5,10,13,l,r,'stone_mid','shop_sill')
        b(0,3,2,10,l,r,shadow,'stall_panel')
        b(3,4,3,9,l+1,r-1,light,'stall_border')
        b(4,5,4,8,l+2,r-2,paint,'stall_inset')
        b(5,6,4,5,l+3,r-3,'bronze','stall_pinstripe')
    b(-48,1,0,59,dl,dr,'air','entry_opening')
    # Deliberately open centre; wood/glass sidelights evoke reference doorway.
    for u in [dl,dr-2]:b(-8,2,0,59,u,u+2,'wood','door_jamb')
    b(-8,-6,43,45,dl,dr,'wood','door_header')
    b(-9,-8,45,59,dl,dr,'glass_amber','entry_transom_glass')
    for y in [45,51,57]:b(-8,-6,y,y+1,dl,dr,'bronze','entry_transom_rail')
    for u in range(dl+3,dr,5):b(-8,-6,45,59,u,u+1,'wood','entry_transom_bar')
    # Narrow fixed door leaves on each side retain 16-cell central walking space.
    for l,r in [(dl,dl+2),(dr-2,dr)]:b(-8,-5,0,43,l,r,'wood','entry_side_leaf')
    for u in [s0+2,dl-5,dr+2,s1-6]:
        b(0,5,2,63,u,u+4,paint,'shop_post')
        b(5,6,8,56,u+1,u+2,light,'shop_post_edge')
        b(0,7,0,6,u-2,u+6,'base','shop_post_base')
        b(0,7,58,64,u-2,u+6,'trim','shop_post_cap')
    b(0,7,62,65,s0,s1,shadow,'shop_canopy_shadow')
    b(0,9,65,67,s0,s1,light,'shop_canopy_edge')
    b(0,6,77,80,s0,s1,'stone_mid','shop_header')
    b(5,7,79,80,s0,s1,'stone_edge','shop_header_edge')
    for l,r in [(s0+6,mid-3),(mid+3,s1-6)]:
        b(0,3,68,76,l,r,shadow,'sign_recess')
        b(3,4,69,75,l+1,r-1,light,'sign_border')
        b(4,5,70,74,l+2,r-2,paint,'sign_panel')
        b(5,6,70,71,l+3,r-3,'bronze','sign_pinstripe')
    for l,r in bays:lamp(m,(l+r)//2)
    return (dl+2,dr-2)


def author(cfg,spec):
    if spec['address']=='621':
        old=json.loads(base.CFG_PATH.read_text());old['materials']=cfg['materials'];old['dimensions_cells']['height']=224
        return base.author(old),[(54,74)]
    c=copy.deepcopy(cfg);c['coordinates'].update(min_z=spec['z0'],width_blocks=spec['width'])
    m=base.Model(c);b=m.box;w=m.width;h=spec['height'];paint,light,shadow=spec['paint']
    b(-32,0,0,h,0,w,'brick','masonry_core')
    b(-32,0,0,16,0,w,'base','plinth_core')
    b(-32,0,16,80,0,w,'wood','storefront_core')
    # Shallow edge returns, maximum three blocks behind the front.
    for l,r in [(0,8),(w-8,w)]:b(-48,-32,0,80,l,r,'brick','shallow_return')
    entries=[]
    divisions=[(0,w)] if spec['address']!='623' else [(0,w//2),(w//2,w)]
    for l,r in divisions:entries.append(shop(m,l,r,paint,light,shadow))
    if spec['address']=='617-619':
        # The low, deliberately restrained brown storefront at the left of reference.
        b(0,5,79,82,0,w,'stone_shadow','low_cornice_shadow')
        b(0,7,82,85,0,w,'stone_mid','low_cornice')
        b(0,8,85,87,0,w,'stone_edge','low_cornice_cap')
        for u in [0,w-8]:
            b(0,4,0,h+5,u,u+8,'base','low_end_pier')
            b(-32,6,h+3,h+6,u,u+8,'stone_mid','low_pier_cap')
        b(-32,4,h-3,h,0,w,'stone_mid','low_parapet_cap')
        for u in range(8,w-8,12):b(3,4,h-3,h,u,u+1,'stone_shadow','cap_joint')
        return m,entries
    y0=88;y1=150 if spec['address']=='623' else 145
    centers=spec['window_centers']
    for i,cx in enumerate(centers):window(m,cx,y0,y1,spec['address']!='625' or i==1,12 if spec['address']=='623' else 10)
    corn=174 if spec['address']=='623' else 168
    b(0,6,corn-7,corn-4,0,w,'stone_mid','cornice_lower_string')
    b(5,7,corn-5,corn-4,0,w,'stone_edge','cornice_lower_edge')
    for u in range(5,w-4,10):
        b(0,5,corn-4,corn+5,u,u+4,shadow,'bracket_shadow')
        b(4,9,corn,corn+6,u,u+4,'trim','cornice_bracket')
        b(8,9,corn+1,corn+5,u+1,u+3,'stone_shadow','bracket_inset')
    for ya,yb,d,mat in [(5,7,7,'stone_shadow'),(7,9,10,'stone_mid'),(9,10,12,'stone_edge'),(10,12,14,'stone_mid'),(12,13,15,'stone_edge')]:
        b(0,d,corn+ya,corn+yb,0,w,mat,'cornice_course')
    # Broad stepped central parapets, heights and tablets vary by building.
    c0=w//2
    for inset,raiseby in [(0,0),(14,4),(26,8),(36,12)]:
        l=max(8,c0-w//3+inset);r=min(w-8,c0+w//3-inset)
        if l<r:
            b(-32,0,h,h+raiseby,l,r,'brick','parapet_step')
            b(-32,4,h+raiseby-2,h+raiseby,l,r,'stone_mid','parapet_step_coping')
            b(3,4,h+raiseby-1,h+raiseby,l,r,'stone_edge','parapet_coping_edge')
    b(-32,3,h-2,h,0,w,'stone_mid','parapet_base_coping')
    ornament(m,c0,h+2,4 if spec['address']=='625' else 5)
    # Edge piers carry the facade divisions, as in the reference.
    for u in [0,w-6]:
        b(0,6,0,80,u,u+6,'trim','end_shop_pier')
        b(5,7,8,75,u+2,u+4,'stone_mid','end_pier_reed')
        b(0,7,77,h+4,u,u+6,'stone_mid','end_upper_pier')
        for y in range(80,h,8):b(6,7,y,y+1,u,u+6,'stone_shadow','pier_masonry_joint')
        b(-32,8,h+3,h+6,u,u+6,'stone_edge','pier_cap')
        ornament(m,u+3,h-5,2)
    if spec['address'] in ['625','627']:
        for cfin in [3,w-3]:
            for y,wide in [(h+6,4),(h+8,2),(h+10,3),(h+12,1)]:
                b(-5,2,y,y+2,max(0,cfin-wide),min(w,cfin+wide),'stone_mid','corner_finial')
    if spec['address']=='623':
        for u in [48,96,144,192]:
            b(0,5,79,corn,u-2,u+2,'stone_mid','interbay_pilaster')
            for y in range(83,corn,10):b(5,6,y,y+1,u-2,u+2,'stone_shadow','pilaster_joint')
    return m,entries


def preview(a,m,path,map_kinds=None):
    occupied=np.any(a,axis=0);dep=a.shape[0]-1-np.argmax(a[::-1]!=0,axis=0)
    yy,uu=np.indices(dep.shape);ids=a[dep,yy,uu];ids[~occupied]=0
    lut=base.color_lut(m);rgb=lut[ids].astype(float)
    rgb*=np.where(occupied,0.77+0.23*dep/a.shape[0],1)[...,None]
    width=m.width*3;height=a.shape[1]*3
    im=Image.new('RGB',(width+100,height+155),'#efeee6');d=ImageDraw.Draw(im)
    d.text((40,18),'REDFIELD / WEST MAIN 617-627 / HYBRID FACADES',font=base.font(29),fill='#243c39')
    d.text((40,60),'Saved geometry | glazed storefronts | concept reference | glass shown as solid tint',font=base.font(19),fill='#54605b')
    im.paste(Image.fromarray(np.uint8(rgb)[::-1,::-1]).resize((width,height),Image.Resampling.NEAREST),(50,100))
    for spec in reversed(m.cfg['buildings']):
        x=50+(m.width-(spec['z0']+130)*16-spec['width']*8)*3
        d.text((x-35,height+112),spec['address'],font=base.font(22),fill='#243c39')
    im.save(path)


def main():
    cfg=json.loads(CONFIG.read_text());base.COLORS.update(cfg['preview_colors'])
    total=base.Model(cfg);parts=[];entrances=[]
    for spec in cfg['buildings']:
        m,entry=author(cfg,spec);off=(spec['z0']+130)*16
        total.a[:,:,off:off+m.width]=m.a
        for l,r in entry:entrances.append((off+l,off+r))
        parts.append((spec,m))
    blocks,hosts,kinds=base.split(total);bounds=cfg['placement']['region_bounds'];OUT.mkdir(parents=True,exist_ok=True)
    writer=NBTWriter();entities=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v) for (x,y,z),v in sorted(hosts.items())]
    target=OUT/(NAME+'.litematic')
    stats=write_single_region_litematic(target,blocks,tuple(bounds),cfg['id'],NAME,'Reference-led facade-only hybrid strip. Same Redfield registration. Astra 0.6.0 RGB and glass.',data_version=4903,tile_entity_payloads=entities)
    reread,meta=read_back_block_map(target,cfg['id']);assert blocks==reread
    rebuilt=base.read_cells(reread,meta,total);assert np.array_equal(rebuilt,total.a)
    _,components=label(rebuilt!=0);assert components==1,components
    for l,r in entrances:assert not np.any(rebuilt[:,0:40,l:r]),(l,r)
    assert all(59<=x<=65 and -130<=z<=-85 for x,y,z in blocks)
    # Compare the accepted 621 cell-for-cell, not merely by appearance.
    oldcfg=json.loads(base.CFG_PATH.read_text());accepted=base.author(oldcfg)
    off=(-99+130)*16
    assert np.array_equal(rebuilt[:,:208,off:off+128],accepted.a)
    assert not np.any(rebuilt[:,208:,off:off+128])
    # Check all material descriptors against installed mod, then independently unpack palettes.
    jar=Path.home()/'AppData/Roaming/.minecraft/mods/astra-microblocks-0.6.0.jar'
    with zipfile.ZipFile(jar) as z:catalog={x['id'] for x in json.loads(z.read('data/astra_microblocks/materials.json'))}
    materials=Counter()
    for t in meta['tile_entities']:
        v=t['volume_v4'];palette=[None]+[v['material_'+str(i)] for i in range(v['size'])]
        assert all(s in catalog or re.fullmatch(r'astra_microblocks:rgb_[0-9a-f]{6}',s) for s in palette[1:])
        stride=64//v['bits'];mask=(1<<v['bits'])-1
        for i in range(4096):
            idx=(int(v['cells'][i//stride])>>((i%stride)*v['bits']))&mask
            assert idx<len(palette)
            if palette[idx]:materials[palette[idx]]+=1
    counts=Counter(kinds.values());vol=counts['full_block']*4096+counts['vanilla_slab']*2048
    cells=sum(v.occupied_count() for v in hosts.values())
    report={**stats,'counts':dict(counts),'astra_microcells':cells,'vanilla_volume_share':round(vol/(vol+cells),4),
       'validation':{'exact_geometry_and_material_readback':True,'connected_components':components,'all_entrances_clear':True,'accepted_621_v003_unchanged':True,'materials_checked_against_installed_astra_060':True,'runtime_test':'not performed'},
       'materials':dict(materials),'buildings':cfg['buildings'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2))
    (OUT/(NAME+'_operations.json')).write_text(json.dumps({spec['address']:m.operations for spec,m in parts},indent=2))
    preview(rebuilt,total,OUT/(NAME+'_front.png'))
    for spec,m in parts:
        # Individual previews retain exact saved geometry, local framing only.
        off=(spec['z0']+130)*16
        a=rebuilt[:,:,off:off+m.width]
        base.perspective(a,m,OUT/(spec['address']+'_detail.png'))
        image=Image.open(OUT/(spec['address']+'_detail.png'));draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,1240,99),fill='#efeee6')
        draw.text((42,24),spec['address']+' / FACADE DETAIL',font=base.font(31),fill='#243c39')
        draw.text((42,69),'Saved geometry; glass shown as solid tint. No roof or interior.',font=base.font(18),fill='#54605b')
        image.save(OUT/(spec['address']+'_detail.png'))
    print(json.dumps({k:v for k,v in report.items() if k not in ['materials','buildings']},indent=2))

if __name__=='__main__':main()
