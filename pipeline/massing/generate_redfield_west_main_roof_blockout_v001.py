#!/usr/bin/env python3
"""Regular-block shells and roofs behind the approved 617-627 facade schematic."""
from pathlib import Path
import sys,json,math,hashlib
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import label

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.export.litematic_codec import NBTWriter,read_back_block_map,write_single_region_litematic
from pipeline.microblocks.astra_microblock_codec import MicroVolume,decode_volume_v4,tile_entity_payload

NAME='Redfield_WestMain_617-627_RegularBlockShells_Roofs_v001'
REGION='REDFIELD_WEST_MAIN_SHELLS_ROOFS_V001'
OUT=ROOT/'projects/redfield_sd/outputs/building_labs/west_main_shells_roofs_v001'
SOURCE=ROOT/'projects/redfield_sd/outputs/building_labs/west_main_photo_facades_v001/Redfield_WestMain_617-627_PhotoFacades_v001.litematic'
FOOTPRINTS=ROOT/'projects/redfield_sd/buildings/poc001_buildings_selected.geojson'
IDS=[1474301419,1474301430,1474301428,1474301456]
PALETTE={'wall':'minecraft:bricks','floor':'minecraft:stone',
         'roof_dark':'minecraft:gray_concrete','roof_light':'minecraft:light_gray_concrete',
         'coping':'minecraft:stone_bricks'}

def inside(x,z,poly):
    hit=False
    for (ax,az),(bx,bz) in zip(poly,poly[1:]+poly[:1]):
        if (az>z)!=(bz>z) and x<(bx-ax)*(z-az)/(bz-az)+ax:hit=not hit
    return hit

def host_volumes(meta):
    px,py,pz=meta['region_position'];result={}
    for te in meta['tile_entities']:
        v=MicroVolume(te['volume_v4'].get('original','minecraft:stone'))
        v.cells=decode_volume_v4(te['volume_v4'])
        result[(te['x']+px,te['y']+py,te['z']+pz)]=v
        assert te.get('astra_orientation',0)==0
    return result

def derive_footprint():
    features=[f for f in json.loads(FOOTPRINTS.read_text())['features'] if f['properties']['osm_id'] in IDS]
    points=[p for f in features for p in f['geometry']['coordinates'][0]]
    north=max(p[1] for p in points);south=min(p[1] for p in points);front=max(p[0] for p in points)
    metres_per_block=(north-south)*111132/50
    mx=111320*math.cos(math.radians((north+south)/2))
    polygons=[]
    for f in features:
        poly=[(-4+(lon-front)*mx/metres_per_block,-19+(north-lat)*50/(north-south)) for lon,lat in f['geometry']['coordinates'][0]]
        polygons.append((f['properties']['osm_id'],poly))
    # Rasterize geographic outer outline to block centers. Front core occupies X=-5.
    mask={};minx=math.floor(min(p[0] for _,poly in polygons for p in poly))
    for x in range(minx,-4):
        for z in range(-19,31):
            for osm,poly in polygons:
                if inside(x+.5,z+.5,poly):mask[(x,z)]=osm;break
    assert all((-5,z) in mask for z in range(-19,31))
    return mask,{'osm_way_ids_used_as_combined_outline':IDS,'metres_per_block_fit':metres_per_block,
        'combined_frontage_metres_approx':50*metres_per_block,'frontage_blocks':50,
        'mapping':'North edge -> Z=-19; south edge -> Z=31; street boundary -> X=-4. Uniform scale in plan.',
        'source_geographic_extent':{'north':north,'south':south,'east':front},
        'source_sha256':hashlib.sha256(FOOTPRINTS.read_bytes()).hexdigest(),
        'warning':'OSM address labels from older EarthForge files are not used. Internal address/roof boundaries remain inferred.',
        'block_depth_range':[min(sum((x,z) in mask for x in range(minx,-4)) for z in range(-19,31)),max(sum((x,z) in mask for x in range(minx,-4)) for z in range(-19,31))]}

def font(size):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)

def previews(blocks,added,mask):
    # Metric block-plan: roofs, original facade strip and unchanged loading pad.
    cell=15;minx=min(x for x,z in mask);maxx=2;left=80;top=160
    w=(maxx-minx+1)*cell+160;h=50*cell+270
    im=Image.new('RGB',(w,h),'#efeee6');d=ImageDraw.Draw(im)
    d.text((40,25),'REDFIELD / REGULAR-BLOCK SHELLS + ROOFS',font=font(28),fill='#243c39')
    d.text((40,70),'Top view: street on right, rear outline on left. Each square is one block.',font=font(17),fill='#54605b')
    for (x,z),osm in mask.items():
        c='#b2b4b2' if osm in [1474301419,1474301456,1474301428] else '#777a78'
        if x==-5:c='#a47665'
        xx=left+(x-minx)*cell;yy=top+(z+19)*cell
        d.rectangle((xx,yy,xx+cell,yy+cell),fill=c,outline='#999e96')
    # Party walls follow accepted facade divisions; not asserted cadastral partitions.
    for z in [-4,3,16]:
        xs=[x for x,zz in mask if zz==z]
        d.line((left+(min(xs)-minx)*cell,top+(z+19)*cell,left+(-4-minx)*cell,top+(z+19)*cell),fill='#87624e',width=3)
    for name,z in [('625-627',-11),('623',0),('621',10),('617-619',24)]:
        d.text((left+(-4-minx)*cell+8,top+(z+19)*cell),name,font=font(15),fill='#243c39')
    for x in range(-1,2):
        for z in range(-1,2):
            xx=left+(x-minx)*cell;yy=top+(z+19)*cell
            d.rectangle((xx,yy,xx+cell,yy+cell),fill='#eac546' if x==z==0 else '#9d9f98',outline='#62655f')
    d.text((40,h-70),'Footprint outline from OSM, checked against Esri overhead imagery; address splits and roof height are provisional.',font=font(16),fill='#54605b')
    im.save(OUT/(NAME+'_roof_plan.png'))
    # Full-block axonometric massing preview; original microblock hosts simplified as cubes.
    color={'minecraft:bricks':(156,103,81),'minecraft:stone':(110,113,111),
           'minecraft:gray_concrete':(102,108,109),'minecraft:light_gray_concrete':(174,178,174),
           'minecraft:stone_bricks':(130,135,128),'minecraft:yellow_concrete':(234,197,70),
           'minecraft:dark_oak_planks':(87,69,50)}
    def project(p):
        x,y,z=p;return (.80*x-.72*z,.30*x+.34*z-.95*y)
    faces=[]
    for (x,y,z),state in blocks.items():
        c=color.get(state,(142,108,93))
        for delta,pts,shade in [((1,0,0),[(x+1,y,z),(x+1,y,z+1),(x+1,y+1,z+1),(x+1,y+1,z)],.82),
                               ((0,1,0),[(x,y+1,z),(x+1,y+1,z),(x+1,y+1,z+1),(x,y+1,z+1)],1),
                               ((0,0,1),[(x,y,z+1),(x+1,y,z+1),(x+1,y+1,z+1),(x,y+1,z+1)],.65)]:
            if (x+delta[0],y+delta[1],z+delta[2]) in blocks:continue
            faces.append((x+z+y*.3,pts,tuple(round(v*shade) for v in c)))
    ps=[project(p) for _,pts,c in faces for p in pts];mn=np.min(ps,axis=0);mx=np.max(ps,axis=0)
    scale=min(1500/(mx[0]-mn[0]),860/(mx[1]-mn[1]))
    im=Image.new('RGB',(1620,1040),'#efeee6');d=ImageDraw.Draw(im)
    d.text((40,25),'REDFIELD / BUILDING VOLUME + ROOF BLOCKOUT',font=font(30),fill='#243c39')
    d.text((40,70),'Regular blocks added behind the approved facades. Facade details simplified in this massing view.',font=font(20),fill='#54605b')
    for _,pts,c in sorted(faces,key=lambda f:f[0]):
        poly=[tuple((np.array(project(p))-mn)*scale+np.array([60,125])) for p in pts]
        d.polygon(poly,fill=c)
    im.save(OUT/(NAME+'_massing.png'))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old,meta=read_back_block_map(SOURCE,'REDFIELD_WEST_MAIN_617_627_PHOTO_V001')
    hosts=host_volumes(meta);blocks=dict(old);added={}
    mask,fit=derive_footprint();roof_y=10
    def put(p,s):
        assert p not in old,'Never overwrite an approved facade or pad block'
        blocks[p]=s;added[p]=s
    for (x,z),osm in mask.items():
        if x>=-5:continue
        put((x,-1,z),PALETTE['floor'])
        perimeter=any((x+dx,z+dz) not in mask for dx,dz in [(1,0),(-1,0),(0,1),(0,-1)])
        partition=z in [-4,3,16]
        if perimeter or partition:
            for y in range(roof_y):put((x,y,z),PALETTE['wall'])
        roof=PALETTE['roof_light'] if osm in [1474301419,1474301456,1474301428] else PALETTE['roof_dark']
        put((x,roof_y,z),roof)
        if perimeter:put((x,roof_y+1,z),PALETTE['coping'])
    assert added and all(s in PALETTE.values() for s in added.values())
    assert all(x<=-6 for x,y,z in added)
    assert all(blocks[p]==s for p,s in old.items())
    bounds=(min(x for x,y,z in blocks),-1,-19,1,13,30)
    writer=NBTWriter()
    tes=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v) for (x,y,z),v in sorted(hosts.items())]
    stats=write_single_region_litematic(OUT/(NAME+'.litematic'),blocks,bounds,REGION,NAME,
        'Approved photo facades retained. All new shells, floors and flat roofs are normal full blocks. Plan fitted to combined mapped footprint; roof height/partitions provisional.',
        data_version=4903,tile_entity_payloads=tes)
    check,newmeta=read_back_block_map(OUT/(NAME+'.litematic'),REGION);assert check==blocks
    newhosts=host_volumes(newmeta);assert set(newhosts)==set(hosts)
    assert all(newhosts[p].cells==hosts[p].cells for p in hosts)
    # Verify both occupied and air positions in the entire original schematic region.
    ox,oy,oz=meta['region_position'];sx,sy,sz=meta['region_size']
    for x in range(ox,ox+sx):
        for y in range(oy,oy+sy):
            for z in range(oz,oz+sz):assert old.get((x,y,z))==check.get((x,y,z))
    assert all((x,roof_y,z) in check for x,z in mask if x<=-6)
    # Added roofs must remain connected, not isolated plates.
    grid=np.zeros((bounds[3]-bounds[0]+1,15,50),bool)
    for x,y,z in check:
        if x<=-3:grid[x-bounds[0],y+1,z+19]=True
    _,components=label(grid);assert components==1,components
    # A clear hollow sample behind every frontage (at least one full-height column).
    hollow={}
    for name,z0,z1 in [('617-619',17,31),('621',4,17),('623',-3,4),('625-627',-19,-3)]:
        candidates=[(x,z) for x,z in mask if x<=-7 and z0<=z<z1 and all((x,y,z) not in check for y in range(roof_y))]
        assert candidates,name;hollow[name]=len(candidates)
    report={**stats,'new_regular_blocks':len(added),'new_material_counts':dict(Counter(added.values())),
            'retained_astra_hosts':len(hosts),'new_astra_hosts':0,'roof_deck_y':roof_y,
            'validation':{'exact_readback':True,'all_original_cells_and_air_preserved':True,
                          'all_original_host_cells_preserved':True,'new_blocks_full_vanilla_only':True,
                          'continuous_roof_coverage':True,'building_connected_components':components,
                          'hollow_interior_columns':hollow,'in_game_test':False},
            'footprint_fit':fit,'source_schematic_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'confidence':{'outer_plan':'Mapped combined outline, visually checked against overhead imagery; not surveyed.',
                          'roof_shape':'Flat block decks represent low-slope roofs. Falls, drainage and roof equipment not resolved.',
                          'roof_height':'Relative deck Y=10 chosen below the existing front parapets; not measured eave elevations.',
                          'partitions':'Follow accepted facade boundaries; internal legal/structural boundaries unverified.'}}
    (OUT/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2))
    previews(check,added,mask)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
