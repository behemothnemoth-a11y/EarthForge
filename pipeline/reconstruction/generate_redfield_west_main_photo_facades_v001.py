#!/usr/bin/env python3
"""Verified modern-photo facades 617-627, registered to approved Simply Charming.

Photography is used for measured opening layouts and bounded material samples.
No generated concept geometry is imported. RGB colors are native Astra materials.
"""
from pathlib import Path
import sys, json, hashlib, re, zipfile
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
import generate_redfield_623_simply_charming_photo_v003 as charming
geom=charming.geom
from pipeline.export.litematic_codec import NBTWriter,write_single_region_litematic,read_back_block_map
from pipeline.microblocks.astra_microblock_codec import tile_entity_payload,decode_volume_v4

NAME='Redfield_WestMain_617-627_PhotoFacades_v001'
OUT=ROOT/'projects/redfield_sd/outputs/building_labs/west_main_photo_facades_v001'
REF=ROOT/'projects/redfield_sd/references/private/verified_city_archive'
COLORS=dict(charming.COLORS);MATS=dict(charming.MATS)

def material(name,color):
    state='astra_microblocks:rgb_'+color.lstrip('#').lower()
    existing=next((n for n,s in MATS.items() if s==state),None)
    if existing:return existing
    COLORS[name]=color;MATS[name]=state
    return name

EXTRA={'brick_shadow':'#775441','brick_edge':'#b08060','aged_coping':'#8d8271',
       'stone_sill':'#b2aa90','pale_board':'#a4bac4','board_joint':'#869aa5',
       'board_bare':'#8b8374','gray_board':'#989b92','gray_joint':'#7e827a',
       'marquee_face':'#c9c8b8','marquee_shade':'#8e928a','marquee_rust':'#887766',
       'marquee_light':'#d2d5cb','stucco':'#a7a694','purple':'#514569',
       'silver_frame':'#b5bebc','black_frame':'#414541','stone_base':'#777e7a',
       'red_paint':'#b65c5b','red_joint':'#954d4d','peach_paint':'#d7a27e',
       'peach_joint':'#b68768','window_cover':'#a9a69a','window_blue':'#b5c6c8',
       'timber_post':'#b08c58','brick_ochre':'#b38762','sign_cream':'#e3ddd0',
       'ac_case':'#babcb2','ac_grille':'#666d69','rust_stain':'#716357'}
for n,c in EXTRA.items():assert material(n,c)==n

TILES={};SAMPLE_MANIFEST=[]
def sample(name,file,rect,size,colors):
    path=REF/file
    im=Image.open(path).convert('RGB').crop(rect).resize(size,Image.Resampling.LANCZOS)
    rgb=np.array(im.quantize(colors=colors).convert('RGB'))
    names=np.empty(rgb.shape[:2],object)
    for y in range(rgb.shape[0]):
        for x in range(rgb.shape[1]):
            color='#'+''.join(f'{v:02x}' for v in rgb[y,x])
            names[y,x]=material('sample_'+name+'_'+str(len(MATS)),color)
    TILES[name]=names
    SAMPLE_MANIFEST.append(dict(name=name,file=file,crop=rect,cells=size,colors=colors,
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

sample('617brick','617-619_page_2.png',(273,167,411,199),(46,11),8)
sample('621brick','621_page_2.png',(435,124,612,150),(64,10),8)
sample('625brick','625_page_2.png',(180,322,328,347),(48,9),8)
sample('blueboard','617-619_page_2.png',(268,231,420,265),(51,12),8)
sample('grayboard','621_page_2.png',(299,169,340,281),(15,40),6)
sample('marquee','617-619_page_2.png',(555,402,747,430),(68,10),8)
sample('weatheredboard','625_page_2.png',(542,205,574,303),(12,36),6)
sample('redboard','625_page_2.png',(40,354,127,423),(30,25),6)
sample('peachboard','625_page_2.png',(425,356,591,422),(57,24),6)
sample('carpets_logo','621_page_2.png',(447,337,635,390),(72,20),16)
sample('dakota_logo','625_page_2.png',(143,352,255,414),(39,22),12)
assert len(MATS)<250,len(MATS)

# Widths: photographic estimates anchored to the user's accepted 7-block 623.
# Keep 623 at exactly X=-4 and Z=-3..3; extend neighbours in both directions.
SPANS=[('617-619',0,224),('621',224,432),('623',432,544),('625-627',544,800)]
CFG={'id':'REDFIELD_WEST_MAIN_617_627_PHOTO_V001',
     'coordinates':{'front_boundary_x':-4,'min_z':-19,'width_blocks':50,'cell_resolution':16},
     'dimensions_cells':{'height':224,'depth_min':-16,'depth_max':32},
     'materials':MATS,'preview_colors':COLORS,
     'placement':{'region_bounds':[-5,-1,-19,1,13,30],'origin':[50,-54,14],
                  'rotation':0,'mirror':'none','replace':'ALL',
                  'registration':'Unchanged yellow pad at relative (0,-1,0)'},
     'spans_visual_left_to_right':SPANS,'material_samples':SAMPLE_MANIFEST,
     'scope':'Facades 617-627 only; no interiors, roofs, vehicles or street furniture',
     'confidence':{'opening_counts':'High: visible modern city archive photographs',
                   'dimensions':'Photo-proportional, not survey verified: widths 14/13/7/16 blocks',
                   'hidden_areas':'Truck-obscured bottom of 621 glazing and occluded 625-627 right details inferred locally',
                   'dates':'Archive comparison appearance, not a claim of September 2026 business occupancy',
                   '617_details':'Small antennas, cables and tiny inscriptions omitted below useful resolution',
                   'signs':'Photographed sign color samples; small lettering is resolution limited',
                   '623':'Accepted v003 copied exactly, including its provisional parapet continuation'}}

class Facade:
    def __init__(self,m,left,right,photo_left,photo_right,photo_floor,photo_top,height):
        self.m=m;self.left=left;self.right=right
        self.pl=photo_left;self.pr=photo_right;self.pf=photo_floor;self.pt=photo_top;self.height=height
    def x(self,x):return round(self.left+(x-self.pl)*(self.right-self.left)/(self.pr-self.pl))
    def y(self,y):return round((self.pf-y)*self.height/(self.pf-self.pt))
    def b(self,d0,d1,bottom,top,left,right,mat,feature):
        self.m.box(d0,d1,bottom,top,800-right,800-left,mat,feature)
    def rect(self,rect,mat,feature,d0=0,d1=3):
        l,t,r,b=rect;self.b(d0,d1,self.y(b),self.y(t),self.x(l),self.x(r),mat,feature)
    def surface(self,rect,tile,feature,d0=2,d1=3,stretch=False):
        l,t,r,b=rect;l,r=self.x(l),self.x(r);bt,tp=self.y(b),self.y(t)
        a=TILES[tile]
        for y in range(bt,tp):
            for x in range(l,r):
                iy=round((tp-1-y)*(a.shape[0]-1)/max(1,tp-bt-1)) if stretch else (tp-1-y)%a.shape[0]
                ix=round((x-l)*(a.shape[1]-1)/max(1,r-l-1)) if stretch else (x-l)%a.shape[1]
                self.b(d0,d1,y,y+1,x,x+1,a[iy,ix],feature)
    def wall(self,tile):
        self.b(-16,0,0,self.height,self.left,self.right,'brick_core','normal_masonry_core')
        self.surface((self.pl,self.pt,self.pr,self.pf),tile,'photograph_sampled_brick',0,2)
    def window(self,rect,frame='silver_frame',glass='glass_dark',d=-4,hrail=True):
        l,t,r,b=rect;L,R=self.x(l),self.x(r);B,T=self.y(b),self.y(t)
        self.b(-16,5,B,T,L,R,'air','opening_cut')
        self.b(d,d+1,B,T,L,R,glass,'native_stained_glass')
        for x in [L,R-1]:self.b(d,2,B,T,x,x+1,frame,'thin_frame')
        for y in [B,T-1]:self.b(d,2,y,y+1,L,R,frame,'thin_frame')
        if hrail:self.b(d,1,(B+T)//2,(B+T)//2+1,L,R,frame,'sash_rail')
    def boarded(self,rect,tile,base):
        self.rect(rect,'wood_core','recessed_board_backing',-16,-2)
        self.rect(rect,'air','board_recess',-2,4)
        self.rect(rect,base,'board_field',-2,-1)
        self.surface(rect,tile,'photo_board_paint',-1,0,True)
        l,t,r,b=rect
        for x in range(self.x(l)+4,self.x(r),5):
            self.b(0,1,self.y(b),self.y(t),x,x+1,'board_joint' if tile=='blueboard' else 'gray_joint','board_joint')
    def shop(self,rect,divisions,door_indices=(),frame='silver_frame'):
        l,t,r,b=rect;L,R=self.x(l),self.x(r);B,T=self.y(b),self.y(t)
        self.b(-16,4,B,T,L,R,'air','shop_recess')
        xs=[self.x(x) for x in [l]+list(divisions)+[r]]
        for i,(xl,xr) in enumerate(zip(xs,xs[1:])):
            self.b(-5,-4,B,T,xl,xr,'glass_dark' if i in door_indices else 'glass','shop_glass')
            if i in door_indices:
                self.b(-4,0,B+2,B+3,xl,xr,frame,'door_kick_rail')
                self.b(-5,2,B+(T-B)//2,B+(T-B)//2+3,xr-3,xr-2,'metal','door_handle')
        for x in xs:self.b(-5,1,B,T,x,x+1,frame,'shop_mullion')
        for y in [B,T-1]:self.b(-5,1,y,y+1,L,R,frame,'shop_rail')

def author():
    m=geom.Model(CFG)
    # 617-619: three large boarded upper bays; altered storefront and battered marquee.
    f=Facade(m,0,224,215,845,608,80,196);f.wall('617brick')
    f.rect((215,80,845,88),'aged_coping','617_aged_coping',0,3)
    for rect in [(254,103,434,140),(455,104,630,141),(649,105,824,141)]:
        f.rect(rect,'brick_shadow','617_recessed_parapet_panel',1,2)
        l,t,r,b=rect;f.surface((l+5,t+5,r-5,b-4),'617brick','617_parapet_infill',2,3)
    f.rect((220,143,842,150),'brick_edge','617_narrow_cornice',2,5)
    for x in range(224,840,15):f.rect((x,151,x+8,157),'brick_shadow','617_dentil_recess',2,3)
    for l,r in [(261,428),(460,623),(661,816)]:
        f.boarded((l,227,r,344),'blueboard','pale_board')
        f.rect((l-5,209,r+4,222),'stone_sill','617_upper_lintel',1,4)
        f.rect((l-5,344,r+4,353),'stone_sill','617_upper_sill',1,5)
    for rect in [(286,273,322,332),(369,272,404,332),(525,274,564,334),(722,269,744,339)]:
        f.window(rect)
    f.rect((470,274,503,296),'ac_case','617_air_conditioner_case',1,6)
    f.rect((473,278,500,292),'ac_grille','617_air_conditioner_grille',6,7)
    # Pale altered ground floor, gray tile plinth, asymmetric door/window composition.
    f.rect((218,444,842,605),'stucco','617_ground_infill',0,3)
    f.rect((218,574,842,605),'stone_base','617_stone_plinth',2,4)
    for l,r in [(425,451),(631,663)]:
        f.rect((l,449,r,572),'marquee_rust','617_brown_altered_pilaster',2,4)
    for y in [578,588,599]:
        f.rect((218,y,842,y+2),'marquee_shade','617_plinth_course',4,5)
    f.rect((251,486,293,594),'white','617_solid_door',-1,3)
    f.window((259,495,285,511),frame='white',hrail=False)
    f.rect((285,543,289,548),'metal','617_door_handle',3,5)
    f.window((322,487,413,550),frame='black_frame',hrail=False)
    f.shop((474,491,626,599),[525],door_indices=(0,))
    f.rect((539,569,626,599),'stone_base','617_display_base',-4,2)
    f.shop((670,491,830,598),[749,788],door_indices=(2,))
    # Remaining construction posts are visible in the modern photograph.
    for x in [666,693,721,750,779]:f.rect((x,438,x+6,607),'timber_post','617_exposed_timber_post',8,10)
    # Separate marquee panels follow the irregular shallow plan; no roof behind it.
    for l,r,top,bt,depth in [(220,422,397,444,19),(422,490,402,440,22),(490,544,384,437,27),(544,842,392,440,25)]:
        f.rect((l,top,r,bt),'marquee_shade','617_marquee_support',0,depth)
        f.rect((l+2,top+4,r-2,bt-3),'marquee_face','617_marquee_face',depth,depth+1)
        f.surface((l+2,top+4,r-2,bt-3),'marquee','617_marquee_paint_wear',depth,depth+1,True)
        f.rect((l,top,r,top+3),'silver_frame','617_marquee_top_edge',depth,depth+2)
        f.rect((l,bt-3,r,bt),'marquee_light','617_marquee_lower_edge',depth,depth+2)
    f.rect((247,404,277,422),'black_frame','617_missing_marquee_panel',20,21)
    for x in range(491,543,8):f.rect((x,389,x+2,432),'marquee_light','617_ribbed_centre_panel',28,29)

    # 621: six boarded tall openings, purple sign, pale side-entry surround.
    f=Facade(m,224,432,241,783,520,65,190);f.wall('621brick')
    f.rect((244,67,782,77),'aged_coping','621_coping',1,3)
    f.rect((247,88,782,96),'brick_shadow','621_cornice_shadow',1,3)
    f.rect((247,96,782,101),'brick_edge','621_cornice_edge',2,4)
    for x in range(254,780,24):
        f.rect((x,104,x+12,111),'brick_edge','621_corbel_course',2,4)
        f.rect((x+12,111,x+24,117),'brick_shadow','621_corbel_recess',1,2)
    for l,r in [(295,343),(358,405),(462,510),(524,574),(629,677),(691,738)]:
        f.boarded((l,168,r,286),'grayboard','gray_board')
        f.rect((l-3,287,r+3,292),'silver_frame','621_upper_sill',1,5)
    f.rect((272,300,756,307),'stone_sill','621_continuous_sill_band',1,4)
    f.rect((243,310,350,519),'silver_frame','621_pale_side_entry_surround',0,3)
    f.rect((270,334,322,509),'air','621_side_entry_recess',-16,4)
    f.rect((273,335,321,411),'gray_board','621_side_entry_upper_board',-4,-2)
    f.rect((270,412,318,508),'marquee_shade','621_side_door_leaf',-4,-2)
    for l,r in [(270,274),(318,322)]:f.rect((l,334,r,509),'silver_frame','621_side_entry_frame',-4,1)
    f.rect((270,505,322,509),'silver_frame','621_side_entry_threshold',-4,1)
    f.rect((270,334,322,338),'silver_frame','621_side_entry_head',-4,1)
    f.window((276,416,314,448),hrail=False)
    f.rect((311,461,315,465),'metal','621_side_door_handle',-3,3)
    f.rect((759,310,782,519),'silver_frame','621_right_ground_pier',0,3)
    f.rect((350,335,758,391),'purple','621_purple_sign_band',0,4)
    f.surface((447,337,635,390),'carpets_logo','621_photographed_sign',4,5,True)
    f.rect((350,391,758,395),'silver_frame','621_sign_flashing',0,6)
    f.shop((350,398,754,515),[455,495,554,608,656],door_indices=(2,3))
    f.rect((350,499,454,517),'silver_frame','621_left_display_plinth',-3,1)
    f.rect((657,499,754,517),'silver_frame','621_right_display_plinth_inferred',-3,1)
    # Dark inset transom above the recessed paired entrance.
    f.rect((497,405,605,422),'black_frame','621_entrance_transom',-4,-3)

    # Approved Simply Charming: remap IDs only, no cell, palette-state or placement changes.
    original=charming.author()
    lut=np.array([0]+[m.ids[n] for n in original.names[1:]],np.uint8)
    m.a[:,:208,256:368]=lut[original.a]
    m.operations.append({'feature':'623_exact_approved_v003','source':charming.NAME,'z_blocks':[-3,3]})

    # 625-627: ONE shared upper composition, arched ends and six centre openings.
    f=Facade(m,544,800,18,745,580,56,192);f.wall('625brick')
    f.rect((173,56,593,73),'air','625_627_lower_central_parapet',-16,32)
    f.rect((173,73,593,78),'aged_coping','625_627_central_coping',0,4)
    for l,r in [(18,173),(593,745)]:f.rect((l,56,r,65),'aged_coping','625_627_end_coping',1,4)
    f.rect((18,93,745,102),'stone_sill','625_627_cornice_cap',2,6)
    f.rect((18,105,745,114),'brick_shadow','625_627_cornice_underside',2,4)
    for x in range(23,742,12):f.rect((x,107,x+6,113),'brick_edge','625_627_small_dentils',4,5)
    f.rect((18,145,745,151),'brick_shadow','625_627_string_course',1,3)
    # Raised end pavilions and round parapet tablets visible in the photograph.
    for l,r,c in [(18,173,100),(593,745,665)]:
        f.rect((l,56,r,77),'brick_ochre','625_627_raised_end_panel',0,3)
        for yy in range(f.y(78),f.y(34)+1):
            for xx in range(f.x(c-30),f.x(c+30)+1):
                rr=(xx-f.x(c))**2+(yy-f.y(65))**2
                radius=max(1,round(28*256/727))
                if rr<=radius**2:
                    mat='brick_ochre' if rr>(radius-2)**2 else 'stone_sill'
                    f.b(-16,4,yy,yy+1,xx,xx+1,mat,'625_627_round_parapet_tablet')
    for l,r in [(58,131),(628,702)]:
        # Arch head above a rectangular lower light, with opaque upper infill.
        L,R=f.x(l),f.x(r);cy=f.y(217);rad=(R-L)/2;cx=(L+R)/2
        B=f.y(315)
        f.b(-16,3,B,cy,L,R,'air','arched_end_opening')
        f.b(-5,-4,B,cy,L,R,'window_cover','end_upper_infill')
        for y in range(cy,round(cy+rad)+3):
            for x in range(L-2,R+2):
                rr=(x+.5-cx)**2+(y+.5-cy)**2
                if rr<rad**2:
                    f.b(-16,3,y,y+1,x,x+1,'air','arched_head_cut')
                    f.b(-5,-4,y,y+1,x,x+1,'window_cover','arched_head_infill')
                elif rr<(rad+2)**2:f.b(2,3,y,y+1,x,x+1,'brick_shadow','arched_brick_rim')
        f.window((l,244,r,315),hrail=False)
        f.rect((l-4,315,r+4,322),'stone_sill','end_window_sill',1,5)
    for i,(l,r) in enumerate([(188,230),(251,298),(322,372),(394,442),(466,514),(539,579)]):
        f.rect((l,197,r,314),'air','625_627_rectangular_upper_cut',-16,4)
        f.rect((l,197,r,247),'window_cover','625_627_upper_window_infill',-5,-4)
        if i==5:
            f.boarded((l,197,r,314),'weatheredboard','gray_board')
        else:
            f.window((l,247,r,314),hrail=True)
            f.rect((l+1,249,r-1,259),'window_blue','625_627_pale_blind',-3,-2)
        f.rect((l-5,179,r+5,195),'stone_sill','625_627_flat_lintel',0,3)
        f.rect((l-3,315,r+3,320),'stone_sill','625_627_flat_sill',0,4)
    f.rect((190,294,214,313),'ac_case','625_upper_ac',0,5)
    f.rect((193,298,211,309),'ac_grille','625_upper_ac_grille',5,6)
    f.rect((257,291,294,310),'ac_grille','625_upper_vent',-5,2)
    # Brick quoins at the ends and at the two inset pavilion transitions.
    for x in [20,150,595,722]:
        for y in range(160,322,23):f.rect((x,y,x+20,y+9),'brick_edge','625_627_pavilion_brick_bands',1,3)
    f.rect((18,320,745,327),'stone_sill','625_627_continuous_upper_sill',0,4)
    for l,r,tile,base,joint in [(18,355,'redboard','red_paint','red_joint'),(355,745,'peachboard','peach_paint','peach_joint')]:
        f.rect((l,350,r,576),base,'modern_painted_storefront',0,2)
        f.surface((l,350,r,576),tile,'photo_painted_cladding',2,3)
        for x in range(f.x(l)+5,f.x(r),6):f.b(3,4,0,f.y(350),x,x+1,joint,'fine_vertical_cladding_joint')
    f.surface((143,352,255,414),'dakota_logo','625_photographed_dakota_sign',4,5,True)
    f.shop((47,450,316,567),[106,170,214,251],door_indices=(2,))
    # Angled display returns approximated by the inset frame line at this scale.
    f.rect((47,548,168,568),'red_paint','625_display_panel',-3,2)
    f.rect((215,548,316,568),'red_paint','625_display_panel',-3,2)
    f.shop((356,450,398,575),[],door_indices=(0,))
    f.window((429,458,510,533),frame='sign_cream',hrail=False)
    f.shop((541,450,707,575),[584],door_indices=(0,))
    f.rect((585,548,707,575),'peach_paint','627_display_plinth',-3,2)
    # Thin metal canopy across both shops, with differentiated top, fascia and underside.
    f.rect((18,428,745,436),'marquee_shade','625_627_canopy_underface',0,13)
    f.rect((18,428,745,431),'silver_frame','625_627_canopy_top',0,14)
    f.rect((18,432,745,439),'marquee_face','625_627_canopy_fascia',13,14)
    for x in range(24,738,18):f.rect((x,437,x+7,442),'marquee_shade','625_627_canopy_edge',12,14)
    # Ground thresholds only; no interior floor slab.
    for l,r in [(0,224),(224,432),(544,800)]:
        m.box(-6,4,0,1,800-r,800-l,'stone_base','threshold')
    return m

def front_image(a,m):
    occupied=np.any(a,axis=0);dep=a.shape[0]-1-np.argmax(a[::-1]!=0,axis=0)
    yy,uu=np.indices(dep.shape);ids=a[dep,yy,uu];ids[~occupied]=0
    lut=geom.color_lut(m);rgb=lut[ids].astype(float)
    rgb*=np.where(occupied,.8+.2*dep/a.shape[0],1)[...,None]
    return Image.fromarray(np.uint8(rgb)[::-1,::-1])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    geom.COLORS.clear();geom.COLORS.update(COLORS)
    m=author();blocks,hosts,kinds=geom.split(m);facade=dict(blocks)
    for x in range(-1,2):
        for z in range(-1,2):blocks[(x,-1,z)]='minecraft:stone_bricks'
    blocks[(0,-1,0)]='minecraft:yellow_concrete'
    bounds=CFG['placement']['region_bounds'];writer=NBTWriter()
    tes=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v) for (x,y,z),v in sorted(hosts.items())]
    path=OUT/(NAME+'.litematic')
    stats=write_single_region_litematic(path,blocks,tuple(bounds),CFG['id'],NAME,
        'City archive modern-photo facades 617-627. Approved 623 preserved. Photo-derived dimensions; no roof/interiors.',
        data_version=4903,tile_entity_payloads=tes)
    reread,meta=read_back_block_map(path,CFG['id']);assert blocks==reread
    restored=geom.read_cells({p:s for p,s in reread.items() if p in facade},meta,m)
    assert np.array_equal(restored,m.a)
    original=charming.author();lut=np.array([0]+[m.ids[n] for n in original.names[1:]],np.uint8)
    assert np.array_equal(restored[:,:208,256:368],lut[original.a])
    assert not np.any(restored[:,208:,256:368])
    _,components=label(restored!=0);assert components==1,components
    assert (0,0,0) not in blocks and blocks[(0,-1,0)]=='minecraft:yellow_concrete'
    assert all(x<=-3 for x,y,z in facade)
    with zipfile.ZipFile(Path.home()/'AppData/Roaming/.minecraft/mods/astra-microblocks-0.6.0.jar') as z:
        catalog={e['id'] for e in json.loads(z.read('data/astra_microblocks/materials.json'))}
    used=set(s for v in hosts.values() for s in v.materials())
    assert all(s in catalog or re.fullmatch('astra_microblocks:rgb_[0-9a-f]{6}',s) for s in used)
    # Decode every serialized host independently of authoring IDs; reject invalid palette indices.
    count=0
    for te in meta['tile_entities']:
        v=te['volume_v4'];stride=64//v['bits'];mask=(1<<v['bits'])-1
        for i in range(4096):
            index=(int(v['cells'][i//stride])>>((i%stride)*v['bits']))&mask
            assert index<=v['size']
            count+=bool(index)
    c=Counter(kinds.values());micro=sum(v.occupied_count() for v in hosts.values());assert micro==count
    full=c['full_block']*4096+c['vanilla_slab']*2048
    report={**stats,'facade_counts':dict(c),'pad_blocks':9,'microcells':micro,
            'vanilla_fraction_of_facade_volume':round(full/(full+micro),4),
            'validation':{'exact_readback':True,'independent_palette_check':True,'connected_facade':components,
                          'approved_623_exact_cell_match':True,'registration_preserved':True,
                          'materials_supported':True,'in_game_test':False,'material_count':len(MATS)},
            'confidence':CFG['confidence'],'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2))
    (ROOT/'projects/redfield_sd/poc_001/labs/west_main_photo_facades_v001.json').write_text(json.dumps(CFG,indent=2))
    # Compact operation counts rather than megabytes of repeated one-cell material writes.
    counts=Counter(op['feature'] for op in m.operations)
    (OUT/(NAME+'_features.json')).write_text(json.dumps(counts,indent=2))
    base=front_image(restored,m)
    overview=Image.new('RGB',(2480,890),'#efeee6');d=ImageDraw.Draw(overview)
    d.text((40,25),'REDFIELD / WEST MAIN / VERIFIED PHOTO FACADES 617-627',font=geom.font(32),fill='#243c39')
    d.text((40,73),'50-block photo-proportional frontage | approved Simply Charming unchanged | geometry preview, glass shown as tint',font=geom.font(22),fill='#54605b')
    overview.paste(base.resize((2400,672),Image.Resampling.NEAREST),(40,125))
    for address,l,r in SPANS:
        d.text((40+l*3+8,815),address,font=geom.font(25),fill='#243c39')
    overview.save(OUT/(NAME+'_front.png'))
    for address,l,r in SPANS:
        detail=base.crop((l,0,r,224)).resize(((r-l)*4,896),Image.Resampling.NEAREST)
        im=Image.new('RGB',(detail.width+60,996),'#efeee6');im.paste(detail,(30,70))
        ImageDraw.Draw(im).text((30,20),address+' / photo-based facade',font=geom.font(24),fill='#243c39')
        im.save(OUT/(address+'_detail.png'))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
