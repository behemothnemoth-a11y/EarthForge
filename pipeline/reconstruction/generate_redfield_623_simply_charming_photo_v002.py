#!/usr/bin/env python3
"""Simply Charming 623: photo-led standalone facade study, no old concept geometry."""
from pathlib import Path
import sys,json,hashlib,re,zipfile
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import label
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
import generate_redfield_621_hybrid_restart_v003 as geom
from pipeline.export.litematic_codec import NBTWriter,write_single_region_litematic,read_back_block_map
from pipeline.microblocks.astra_microblock_codec import tile_entity_payload
NAME='Redfield_623_SimplyCharming_PhotoStudy_v002'
OUT=ROOT/'projects/redfield_sd/outputs/building_labs/623_simply_charming_photo_v002'
COLORS={'brick_core':'#9a6255','mortar':'#978f8e','brick':'#a08d91','brick_alt':'#ad999b','brick_dark':'#927f84','green':'#738774','green_dark':'#6e816f','green_light':'#788b77','charcoal':'#5c5c5d','charcoal_dark':'#585859','charcoal_light':'#616163','stone':'#ac8d73','stone_light':'#c2ab8e','stone_dark':'#816c58','metal':'#c4c8c7','white':'#ebebec','sign_white':'#eef3ef','sign_pink':'#cba5a7','ink':'#474145','glass':'#667f87','glass_dark':'#40514f','wood_core':'#493b30','flag_red':'#9b4c48','flag_blue':'#344963','board_frame':'#ad8455'}
MATS={k:'astra_microblocks:rgb_'+v[1:] for k,v in COLORS.items()}
MATS.update(brick_core='minecraft:bricks',wood_core='minecraft:dark_oak_planks',glass='minecraft:gray_stained_glass',glass_dark='minecraft:black_stained_glass')
CFG={'id':'REDFIELD_623_SIMPLY_CHARMING_PHOTO_V002','coordinates':{'front_boundary_x':-4,'min_z':-3,'width_blocks':7,'cell_resolution':16},'dimensions_cells':{'height':208,'depth_min':-16,'depth_max':32},'materials':MATS,'placement':{'region_bounds':[-5,-1,-3,1,12,3],'origin':'Player feet directly above yellow marker (0,-1,0)','rotation':0,'mirror':'none','mode':'standalone study; not an address-verified in-place strip patch'},'reference':{'primary':'https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2642/623-main-street-simply-charming','supplemental':'https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2640/621-main-street-carpets-plus','appearance':'Modern comparison photos published by city archive; exact capture dates unconfirmed','width':'Provisional 7 blocks; image proportions, not surveyed','top':'Visible upper-left portion from adjacent Carpets Plus photograph; far-right parapet continuation provisional'},'preview_colors':COLORS}


SOURCE_PHOTO=ROOT/'projects/redfield_sd/references/private/verified_city_archive/623_page_2.png'

def prepare_photo_materials():
 # Photograph is read as a numerical color reference for voxel materials.
 # Small material samples and the authentic sign only; no whole-photo facade projection.
 src=Image.open(SOURCE_PHOTO).convert('RGB')
 tiles={}
 for label,rect,size,ncolors in [
   ('masonry',(294,20,367,155),(18,34),20),
   ('boarding',(454,8,608,65),(32,12),10),
   ('charcoal_grain',(327,342,360,486),(8,36),8),
   ('logo',(439,199,580,312),(34,28),48)]:
  im=src.crop(rect).resize(size,Image.Resampling.LANCZOS)
  rgb=np.array(im.quantize(colors=ncolors).convert('RGB'))
  if label=='masonry':
   # Remove the exaggerated lavender tint; retain measured cool-gray/red variation.
   rgb=np.clip(rgb.astype(float)*np.array([.91,.94,.92]),0,255).astype(np.uint8)
  names=np.empty(rgb.shape[:2],dtype=object)
  for yy in range(rgb.shape[0]):
   for xx in range(rgb.shape[1]):
    h=''.join(f'{int(v):02x}' for v in rgb[yy,xx]);state='astra_microblocks:rgb_'+h
    name=next((k for k,v in MATS.items() if v==state),None)
    if name is None:
     name='photo_'+label+'_'+str(len(MATS));MATS[name]=state;COLORS[name]='#'+h
    names[yy,xx]=name
  tiles[label]=(names,rgb)
 assert len(MATS)<250, 'Shared codec uses byte material identifiers'
 CFG['reference']['photo_sha256']=hashlib.sha256(SOURCE_PHOTO.read_bytes()).hexdigest()
 CFG['reference']['texture_method']='Bounded palettes sampled from masonry, boarding, dark wood and original logo; no generated reference imagery.'
 CFG['reference']['glass']='Gray stained glass replaces opaque-bordered clear glass; remaining host-boundary texture contrast requires in-game review.'
 return tiles

PHOTO_TILES=prepare_photo_materials()

def author():
 m=geom.Model(CFG)
 def b(d0,d1,y0,y1,l,r,mat,name):m.box(d0,d1,y0,y1,112-r,112-l,mat,name)
 b(-16,0,0,186,0,112,'brick_core','normal_brick_structure')
 # Flat micro-color masonry samples avoid the previous deep, oversized mortar grooves.
 brick=PHOTO_TILES['masonry'][0]
 for y in range(186):
  for x in range(112):
   mat=brick[(185-y)%brick.shape[0],(x+(y//34)*5)%brick.shape[1]]
   b(0,2,y,y+1,x,x+1,mat,'photo_sampled_masonry')
 # Restrained stepped top visible in the adjacent building photograph.
 b(-16,2,186,190,0,9,'brick_core','parapet_left_raised_end')
 b(-16,2,186,190,103,112,'brick_core','parapet_right_end_provisional')
 b(2,3,186,190,0,9,'brick_dark','parapet_left_finish')
 b(2,3,186,190,103,112,'brick_dark','parapet_right_finish')
 b(0,3,184,186,9,103,'brick_dark','parapet_coping')
 # Narrow cream dentil course, not the earlier invented heavy cornice.
 b(2,4,174,177,0,112,'stone_dark','cornice_recess')
 b(3,5,177,179,0,112,'stone','cornice_cap')
 b(4,5,178,179,0,112,'stone_light','cornice_edge')
 for x in range(3,110,5):
  b(3,5,174,177,x,x+3,'stone','cornice_dentil')
  b(5,6,175,176,x+1,x+2,'stone_dark','dentil_inset')
 # Round six-cell medallions with a shaded rim, matching the visible source details.
 for c in [28,56,84]:
  for y in range(160,168):
   for x in range(c-4,c+4):
    rr=(x+.5-c)**2+(y+.5-164)**2
    if rr<=3.5**2:
     mat='stone_dark' if rr>2.7**2 else ('stone_light' if y>=164 else 'stone')
     b(2,3,y,y+1,x,x+1,mat,'round_inset')
 b(2,4,150,153,15,99,'brick_dark','upper_opening_header')
 # Large green boarded upper opening. Keep side masonry piers.
 b(-16,3,89,150,24,96,'wood_core','upper_boarding_backing')
 b(2,3,89,150,24,96,'green','upper_green_boarding')
 grain=PHOTO_TILES['boarding'][0]
 for y in range(89,150):
  for x in range(24,96):
   mat=grain[round((149-y)*(grain.shape[0]-1)/60),(x-24)%grain.shape[1]]
   b(3,4,y,y+1,x,x+1,mat,'photo_sampled_board_paint')
 for x in range(25,96,5):b(3,4,89,150,x,x+1,'green_dark','flush_board_joint')

 # One small horizontal upper window, two narrow lights flanking a wide centre.
 b(-16,5,95,109,34,79,'air','upper_window_opening')
 b(-3,-2,95,109,34,79,'glass_dark','upper_window_glazing')
 for x in [34,43,69,78]:b(-2,2,95,109,x,x+1,'metal','upper_window_mullion')
 for y in [95,108]:b(-2,2,y,y+1,34,79,'metal','upper_window_rail')
 # Sloping metal awning and small scalloped edge observed over the window.
 for d in range(0,11):
  yy=115-round(d*.35);b(d,d+1,yy,yy+2,32,81,'green_dark','upper_window_awning')
 b(10,11,110,112,32,81,'green','awning_front')
 for x in range(32,81,4):b(10,11,109,110,x,min(81,x+2),'green_dark','awning_scallop')
 for x in [32,79]:b(0,11,109,111,x,x+2,'green_dark','awning_side_return')
 # Stone shelf and four corbels below upper infill.
 b(0,6,87,90,16,101,'stone','upper_stone_shelf')
 b(5,7,89,90,16,101,'stone_light','shelf_edge')
 for x in [20,43,67,90]:
  b(0,4,82,87,x,x+4,'stone','shelf_bracket')
  b(3,5,83,85,x,x+4,'stone_dark','bracket_joint')
 # Modern charcoal fascia and vertical ground-floor cladding.
 b(-16,1,0,52,7,105,'wood_core','shop_structure')
 b(1,3,0,52,7,105,'charcoal','shop_cladding')
 grain=PHOTO_TILES['charcoal_grain'][0]
 for y in range(52):
  for x in range(7,105):
   b(3,4,y,y+1,x,x+1,grain[round((51-y)*(grain.shape[0]-1)/51),(x-7)%grain.shape[1]],'photo_sampled_charcoal_boards')
 b(0,3,54,73,7,105,'charcoal_dark','sign_fascia')
 b(3,4,56,71,9,103,'charcoal','fascia_face')
 for x in [33,66]:b(4,5,56,71,x,x+1,'charcoal_dark','fascia_panel_joint')
 b(0,5,52,54,7,105,'metal','shop_header_flashing')
 # Left solid door with small inset glazing. Fixed facade geometry, no door mechanics.
 b(-16,4,0,36,23,39,'air','left_door_opening')
 b(-3,-1,0,36,23,39,'charcoal_dark','left_door_leaf')
 b(-3,0,17,32,26,36,'air','left_door_glass_cut')
 b(-2,-1,17,32,26,36,'glass_dark','left_door_glazing')
 for x in [23,38]:b(-1,2,0,36,x,x+1,'metal','left_door_frame')
 for y in [0,35]:b(-1,2,y,y+1,23,39,'metal','left_door_frame')
 b(-1,1,5,12,26,36,'charcoal','left_door_lower_panel')
 b(-1,3,16,17,25,27,'metal','left_door_handle')
 # Broad white-framed glazed entrance/display assembly on the right.
 b(-16,4,0,41,52,102,'air','shop_glazing_opening')
 b(-3,-2,1,40,53,101,'glass','shop_glazing')
 for x in [52,67,87,101]:b(-2,2,0,41,x,x+1,'white','shop_glazing_mullion')
 for y in [0,40]:b(-2,2,y,y+1,52,102,'white','shop_glazing_rail')
 b(-2,0,7,9,67,88,'metal','entry_kick_rail')
 b(-2,3,17,21,69,70,'metal','entry_handle')
 # Address mark on the actual entry, deliberately small.
 text(m,'623',75,34,-2,'white',font_size=5)
 # Original photographed logo sampled into a restrained 34x28-cell surface.
 # Pale side tabs and script silhouette replace the heavy substitute font.
 logo,logo_rgb=PHOTO_TILES['logo']
 for yy in range(28):
  for xx in range(34):
   x=40+xx;y=80-yy;rr=(x+.5-57)**2+(y+.5-67)**2
   in_circle=rr<=13.5**2
   in_tab=63<=y<=70 and float(np.mean(logo_rgb[yy,xx]))>155
   if in_circle or in_tab:
    b(4,6,y,y+1,x,x+1,'sign_white','sign_disc_support')
    b(6,7,y,y+1,x,x+1,logo[yy,xx],'photographed_logo_color')
 # Wrap the exposed side edges and parapet top with the same masonry family.
 brick=PHOTO_TILES['masonry'][0]
 for y in range(186):
  for d in range(-16,0):
   mat=brick[(185-y)%brick.shape[0],(d+16)%brick.shape[1]]
   b(d,d+1,y,y+1,0,1,mat,'left_masonry_return_finish')
   b(d,d+1,y,y+1,111,112,mat,'right_masonry_return_finish')
 for l,r in [(0,9),(103,112)]:
  b(-16,3,189,190,l,r,'brick_dark','matched_parapet_top')
  for y in range(186,189):
   for d in range(-16,0):
    b(d,d+1,y,y+1,l,l+1,'brick_dark','matched_parapet_end')
    b(d,d+1,y,y+1,r-1,r,'brick_dark','matched_parapet_end')
 b(-16,0,185,186,9,103,'brick_dark','matched_wall_top')
 # Small mounted flag and framed board visible beside the main entrance.
 b(3,5,20,30,43,50,'board_frame','small_wall_board_frame')
 b(5,6,21,29,44,49,'charcoal_dark','small_wall_board_face')
 b(0,9,44,45,45,46,'metal','flag_bracket')
 for y in range(34,44):
  b(8,9,y,y+1,43,47,'flag_red' if y%2 else 'white','small_flag_stripe')
 b(8,9,39,44,43,45,'flag_blue','small_flag_canton')
 # Thin sill/threshold, no interior floors, roof or invented side buildings.
 b(-6,4,0,1,7,105,'stone_dark','threshold')
 return m


def text(m,value,left,y,d,mat,font_size):
 # Rasterize lettering as block geometry; no photographic textures are embedded.
 font=ImageFont.truetype('C:/Windows/Fonts/ariali.ttf',font_size)
 im=Image.new('L',(48,12));draw=ImageDraw.Draw(im);draw.text((0,-1),value,font=font,fill=255)
 a=np.array(im)
 for yy,xx in zip(*np.where(a>100)):
  x=left+int(xx);gy=y+9-int(yy)
  if 0<=x<112:m.box(d,d+1,gy,gy+1,111-x,112-x,mat,'sign_lettering')


def main():
 OUT.mkdir(parents=True,exist_ok=True);geom.COLORS.clear();geom.COLORS.update(COLORS)
 m=author();blocks,hosts,kinds=geom.split(m);facade=dict(blocks)
 # Independent loading pad outside the facade; standard feet-origin yellow marker.
 for x in range(-1,2):
  for z in range(-1,2):blocks[(x,-1,z)]='minecraft:stone_bricks'
 blocks[(0,-1,0)]='minecraft:yellow_concrete'
 bounds=CFG['placement']['region_bounds'];writer=NBTWriter()
 tes=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v) for (x,y,z),v in sorted(hosts.items())]
 path=OUT/(NAME+'.litematic')
 stats=write_single_region_litematic(path,blocks,tuple(bounds),CFG['id'],NAME,'Photo-led Simply Charming facade. Standalone study with yellow registration pad. Width and hidden parapet extent provisional.',data_version=4903,tile_entity_payloads=tes)
 reread,meta=read_back_block_map(path,CFG['id']);assert blocks==reread
 restored=geom.read_cells({p:s for p,s in reread.items() if p in facade},meta,m);assert np.array_equal(restored,m.a)
 _,n=label(restored!=0);assert n==1,n
 assert blocks[(0,-1,0)]=='minecraft:yellow_concrete';assert (0,0,0) not in blocks
 assert all(x<=-3 for x,y,z in facade),'Facade must not touch loading pad'
 jar=Path.home()/'AppData/Roaming/.minecraft/mods/astra-microblocks-0.6.0.jar'
 with zipfile.ZipFile(jar) as z:catalog={e['id'] for e in json.loads(z.read('data/astra_microblocks/materials.json'))}
 used=set(s for v in hosts.values() for s in v.materials())
 assert all(s in catalog or re.fullmatch('astra_microblocks:rgb_[0-9a-f]{6}',s) for s in used)
 c=Counter(kinds.values());vanilla=c['full_block']*4096+c['vanilla_slab']*2048;micro=sum(v.occupied_count() for v in hosts.values())
 report={**stats,'facade_counts':dict(c),'pad_blocks':9,'vanilla_fraction_of_facade_volume':round(vanilla/(vanilla+micro),4),'microcells':micro,'validation':{'exact_readback':True,'facade_connected_components':n,'materials_supported':True,'marker_at_0_minus1_0':True,'no_runtime_test':True,'palette_material_count':len(MATS),'gray_glass_replaces_clear_glass':True},'confidence':CFG['reference'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (OUT/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2));(OUT/(NAME+'_operations.json')).write_text(json.dumps(m.operations,indent=2))
 (ROOT/'projects/redfield_sd/poc_001/labs/623_simply_charming_photo_v002.json').write_text(json.dumps(CFG,indent=2))
 geom.front_preview(restored,m,kinds,OUT/(NAME+'_front.png'));geom.perspective(restored,m,OUT/(NAME+'_oblique.png'))
 for suffix in ['front','oblique']:
  p=OUT/(NAME+'_'+suffix+'.png');im=Image.open(p);draw=ImageDraw.Draw(im);draw.rectangle((0,0,im.width,100),fill='#efeee6')
  draw.text((42,24),'623 / SIMPLY CHARMING / PHOTO STUDY',font=geom.font(29),fill='#243c39')
  draw.text((42,66),'7-block provisional frontage | real photo basis | glass rendered as solid tint',font=geom.font(18),fill='#54605b')
  im.save(p)
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
