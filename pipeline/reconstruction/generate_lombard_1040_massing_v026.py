"""Lombard v026: 1040 front 3D massing reset after rejected flat v025."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from shapely.geometry import Point,LineString,shape
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_access_tree_realism_v024 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction import generate_lombard_realism_v020 as realism
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic

OUT=realm.v.PROJECT/'outputs/house_1040_massing_v026'
NAME='Lombard_1040_3D_Front_Massing_Astra_v026';REGION='LOMBARD_1040_3D_FRONT_V026'
BUILDING_ID='201006.0032105'
REF=realm.v.PROJECT/'references/private/wikimedia_commons/021_Lombard_Street_10064415846_.jpg.jpg'
BLUE='astra_microblocks:rgb_82aec2';BLUE2='astra_microblocks:rgb_91b9ca'
NAVY='astra_microblocks:rgb_203743';NAVY2='astra_microblocks:rgb_2b4551'
WHITE='astra_microblocks:rgb_e5e2d7';GLASS='astra_microblocks:rgb_a3c1c7'
GARAGE='astra_microblocks:rgb_a2cedd';GARAGE_SHADOW='astra_microblocks:rgb_78a6b5'
DARK='astra_microblocks:rgb_16262c'
def xyz(pos,i):
 hx,hy,hz=pos
 return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 source=parent.OUT/f'{parent.NAME}.litematic'
 blocks,hosts=read(source,parent.REGION);vanilla={p:s for p,s in blocks.items() if p not in hosts}
 original={p:(q.original,q.cells.copy()) for p,q in hosts.items()}
 env=json.loads((buildings.OUT/'building_envelopes.geojson').read_text())
 feat=next(f for f in env['features'] if str(f['properties']['id'])==BUILDING_ID)
 geom=shape(feat['geometry']);poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,'geoms') else geom
 center=json.loads(realm.v.CENTER.read_text());road=LineString([(q['x_m'],q['z_m']) for q in center])
 coords=list(poly.exterior.coords);edges=[]
 for a,b in zip(coords,coords[1:]):
  seg=LineString([a,b])
  if seg.length>5:edges.append((seg.distance(road),seg.length,np.array(a,float),np.array(b,float)))
 _,_,pa,pb=min(edges,key=lambda q:q[0])
 if pa[0]>pb[0]:pa,pb=pb,pa
 vec=pb-pa;width=float(np.linalg.norm(vec));uvec=vec/width
 normal=np.array([-uvec[1],uvec[0]])
 if np.dot(np.array([poly.centroid.x,poly.centroid.y])-(pa+pb)/2,normal)<0:normal=-normal

 # Street datum from accepted v024 driveway immediately outside the garage.
 drive_y=[]
 for hp,hv in hosts.items():
  for ii,mm in enumerate(hv.cells):
   if mm not in {parent.DRIVE,parent.DRIVE_JOINT}:continue
   xx,yy,zz=xyz(hp,ii);pt=np.array([(xx+.5)/16,(zz+.5)/16]);r=pt-pa
   u=float(np.dot(r,uvec))/width;d=float(np.dot(r,normal))
   if .20<=u<=.67 and -2.2<=d<=-.35:drive_y.append(yy)
 if len(drive_y)<20:raise RuntimeError('1040 front datum lacks driveway support')
 floor=int(round(float(np.median(drive_y))))+1
 prop=feat['properties'];zero=float(center[0]['elev_navd88_m'])
 source_cap=round((prop['median_first_return_navd88_m']-zero)*16)
 total_h=(source_cap-floor)/16
 deck_h=9.20;rail_top=10.45;pergola_top=min(total_h-.18,12.35)
 if pergola_top<11.5:raise RuntimeError('1040 height envelope too short for observed terrace/pergola')
 print('1040 width',width,'drive floor',floor,'source total height',total_h,'pergola',pergola_top,flush=True)

 writes={};changes={}
 def get(x,y,z):
  p,i=position(int(x),int(y),int(z));q=hosts.get(p);return q.cells[i] if q else None
 def put(x,y,z,mat,why):
  p,i=position(int(x),int(y),int(z))
  if p in vanilla:return False
  old=hosts[p].cells[i] if p in hosts else None
  if old==mat:return False
  if p not in hosts:hosts[p]=MicroVolume('minecraft:bricks');blocks[p]=HOST_STATE
  hosts[p].cells[i]=mat;writes[(p,i)]=(old,mat,why);changes[why]=changes.get(why,0)+1
  return True
 # Remove only prior building-envelope/v020 facade materials in the front 4m.
 old_build=set(buildings.WALLS)|{buildings.ROOF,realism.rgb('a9cbd6'),realism.rgb('293f48'),
  realism.rgb('95c7d4'),realism.rgb('799da5'),realism.rgb('8cb3ba')}
 cleared=0
 for hp,hv in list(hosts.items()):
  hx,hy,hz=hp
  # Fast host-level rejection.
  cx=(hx*16-480+8)/16;cz=(hz*16-320+8)/16
  r=np.array([cx,cz])-pa;um=float(np.dot(r,uvec));dd=float(np.dot(r,normal))
  if um<-1.5 or um>width+1.5 or dd<-1.5 or dd>5.2:continue
  for ii,mm in enumerate(hv.cells.copy()):
   if mm not in old_build:continue
   x,y,z=xyz(hp,ii);pt=np.array([(x+.5)/16,(z+.5)/16]);rr=pt-pa
   u=float(np.dot(rr,uvec))/width;d=float(np.dot(rr,normal));yy=(y-floor)/16
   if -.01<=u<=1.01 and -.05<=d<=4.1 and -.25<=yy<=total_h+.5 and poly.buffer(.03).covers(Point(*pt)):
    put(x,y,z,None,'remove_old_1040_front');cleared+=1

 # Model surfaces on the 1/16m grid. d=0 is the source footprint front edge,
 # positive d runs inward. The main wall is recessed; bays advance to the edge.
 x0,z0,x1,z1=poly.bounds
 gx0=math.floor((x0-.2)*16);gx1=math.ceil((x1+.2)*16)
 gz0=math.floor((z0-.2)*16);gz1=math.ceil((z1+.2)*16)
 columns=[]
 for x in range(gx0,gx1):
  for z in range(gz0,gz1):
   pt=np.array([(x+.5)/16,(z+.5)/16]);rr=pt-pa
   um=float(np.dot(rr,uvec));d=float(np.dot(rr,normal));u=um/width
   if -.02<=u<=1.02 and -.08<=d<=4.1 and poly.buffer(.03).covers(Point(*pt)):
    columns.append((x,z,u,d,um))
 def near(v,t,tol=.075):return abs(v-t)<=tol
 def span(v,a,b):return a<=v<=b

 # helpers return facade face material; glazing/mullions are deliberately discrete.
 def big_window(u,yy,u0,u1,y0,y1,cols=5,rows=2):
  if not (u0<=u<=u1 and y0<=yy<=y1):return None
  ux=(u-u0)/(u1-u0);vy=(yy-y0)/(y1-y0)
  border=min(ux,1-ux,vy,1-vy)<.035
  mull=any(abs(ux-k/cols)<.012 for k in range(1,cols)) or any(abs(vy-k/rows)<.016 for k in range(1,rows))
  return WHITE if border or mull else GLASS
 def narrow_window(u,yy,u0,u1,y0,y1):
  return big_window(u,yy,u0,u1,y0,y1,cols=2,rows=3)
 # Vertical facade/return surfaces.
 for x,z,u,d,um in columns:
  # Recessed main wall behind the two central bays.
  if .15<=u<=.94 and near(d,.55):
   for y in range(floor+3,floor+round(9.20*16)):
    yy=(y-floor)/16
    put(x,y,z,BLUE if ((x//6+z//6+y//8)&1)==0 else BLUE2,'recessed_main_wall')

  # Left entry is clearly recessed from the garage/bays in photographs.
  if .015<=u<=.17 and near(d,1.15):
   for y in range(floor+3,floor+round(2.95*16)):
    put(x,y,z,DARK,'recessed_entry_back')
  if near(u,.17,.008) and .52<=d<=1.18:
   for y in range(floor+3,floor+round(3.0*16)):put(x,y,z,NAVY,'entry_side_return')

  # Garage: shallow front plane, not a giant glass panel.
  if .20<=u<=.67 and near(d,.20):
   for y in range(floor+3,floor+round(2.42*16)):
    yy=(y-floor)/16
    edge=min(u-.20,.67-u)*width<.10 or yy<.10 or 2.42-yy<.10
    seam=abs(((yy-.15)%0.48)-.24)<.035
    vpanel=abs((((u-.20)*width)%1.10)-.55)<.035
    mat=NAVY if edge else GARAGE_SHADOW if seam or vpanel else GARAGE
    put(x,y,z,mat,'garage_plane')

  # Lower projecting bay, level directly over garage.
  if .18<=u<=.69 and near(d,.03):
   for y in range(floor+round(2.55*16),floor+round(5.32*16)):
    yy=(y-floor)/16
    win=big_window(u,yy,.205,.665,3.02,4.92,cols=5,rows=2)
    if win:mat=win
    else:
     timber=(abs(yy-2.62)<.08 or abs(yy-5.23)<.08 or
             min(abs(u-.18),abs(u-.69))*width<.09)
     panel_diag=(yy<3.0 and abs((((u-.18)*width)+(yy-2.55)*.85)%2.2-1.1)<.075)
     mat=NAVY if timber or panel_diag else BLUE
    put(x,y,z,mat,'lower_bay_face')
  if (near(u,.18,.008) or near(u,.69,.008)) and .03<=d<=.56:
   for y in range(floor+round(2.55*16),floor+round(5.32*16)):put(x,y,z,NAVY if y%8<2 else BLUE,'lower_bay_return')

  # Upper projecting bay: slightly narrower, same shallow box logic.
  if .22<=u<=.69 and near(d,.00):
   for y in range(floor+round(5.38*16),floor+round(8.18*16)):
    yy=(y-floor)/16
    win=big_window(u,yy,.245,.665,5.88,7.72,cols=5,rows=2)
    if win:mat=win
    else:
     timber=(abs(yy-5.44)<.08 or abs(yy-8.08)<.08 or min(abs(u-.22),abs(u-.69))*width<.09)
     mat=NAVY if timber else BLUE2
    put(x,y,z,mat,'upper_bay_face')
  if (near(u,.22,.008) or near(u,.69,.008)) and .0<=d<=.58:
   for y in range(floor+round(5.38*16),floor+round(8.18*16)):put(x,y,z,NAVY if y%8<2 else BLUE2,'upper_bay_return')

  # Narrow right-hand vertical bay/tower, deliberately separate from main window bay.
  if .735<=u<=.94 and near(d,.13):
   for y in range(floor+round(.35*16),floor+round(8.22*16)):
    yy=(y-floor)/16
    win=narrow_window(u,yy,.765,.91,3.10,4.82) or narrow_window(u,yy,.765,.91,5.90,7.62)
    if win:mat=win
    else:
     timber=(min(abs(u-.735),abs(u-.94))*width<.09 or any(abs(yy-q)<.075 for q in [2.55,5.35,8.15]))
     diag=(win is None and 2.7<yy<8.0 and abs((((u-.735)*width)+(yy-2.7)*.55)%2.05-1.025)<.065)
     mat=NAVY if timber or diag else BLUE
    put(x,y,z,mat,'right_vertical_bay')
  # Front side returns make the building read as a volume instead of a cardboard face.
  if (near(u,.015,.008) or near(u,.94,.008)) and .13<=d<=2.25:
   for y in range(floor+3,floor+round(9.15*16)):
    yy=(y-floor)/16
    mat=NAVY if any(abs(yy-q)<.075 for q in [2.55,5.35,8.15]) else BLUE2
    put(x,y,z,mat,'front_side_return')

  # Horizontal bay slabs/soffits.
  for yy0,u0,u1,d0,d1 in [(2.55,.18,.69,.03,.56),(5.32,.18,.69,.03,.56),(5.38,.22,.69,.0,.58),(8.18,.22,.69,.0,.58)]:
   if span(u,u0,u1) and span(d,d0,d1):
    y=floor+round(yy0*16)
    put(x,y,z,NAVY,'bay_slab')

  # Solid timbered frieze directly below the open terrace.
  if .15<=u<=.96 and near(d,.02):
   for y in range(floor+round(8.22*16),floor+round(9.18*16)):
    yy=(y-floor)/16
    border=any(abs(yy-q)<.075 for q in [8.25,9.12]) or min(abs(u-.15),abs(u-.96))*width<.09
    cross=abs((((u-.15)*width)+(yy-8.22)*1.15)%2.3-1.15)<.065 or abs((((u-.15)*width)-(yy-8.22)*1.15)%2.3-1.15)<.065
    put(x,y,z,NAVY if border or cross else BLUE2,'terrace_fascia')

  # Terrace deck is a shallow horizontal platform extending back ~2m.
  if .15<=u<=.96 and 0<=d<=2.05:
   y=floor+round(deck_h*16)
   put(x,y,z,NAVY2,'terrace_deck')

 # Sparse open railing + true 3D pergola.
 rail_y0=floor+round((deck_h+.08)*16);rail_y1=floor+round(rail_top*16)
 perg_y0=floor+round(deck_h*16);perg_y1=floor+round(pergola_top*16)
 for x,z,u,d,um in columns:
  # front railing: horizontals plus narrow posts, no solid infill.
  if .15<=u<=.96 and near(d,.01):
   post=abs(((um-.15*width)%0.70)-.35)<.055
   for y in range(rail_y0,rail_y1+1):
    yy=(y-floor)/16
    horiz=any(abs(yy-q)<.055 for q in [deck_h+.10,deck_h+.62,rail_top-.05])
    if post or horiz:put(x,y,z,NAVY,'open_front_railing')
  # right side railing return.
  if near(u,.96,.008) and 0<=d<=2.0:
   post=abs((d%0.70)-.35)<.055
   for y in range(rail_y0,rail_y1+1):
    yy=(y-floor)/16
    if post or any(abs(yy-q)<.055 for q in [deck_h+.10,deck_h+.62,rail_top-.05]):put(x,y,z,NAVY,'open_side_railing')
  # pergola corner/front/back posts.
  post_u=any(abs(u-q)*width<.07 for q in [.15,.56,.96])
  post_d=near(d,.02,.075) or near(d,2.0,.075)
  if post_u and post_d:
   for y in range(perg_y0,perg_y1+1):put(x,y,z,NAVY,'pergola_post')
  # front/back top headers.
  if .15<=u<=.96 and (near(d,.02,.075) or near(d,2.0,.075)):
   for y in range(perg_y1-2,perg_y1+1):put(x,y,z,NAVY,'pergola_header')
  # depth beams at five positions.
  if 0<=d<=2.05 and any(abs(u-q)*width<.065 for q in [.15,.35,.56,.76,.96]):
   for y in range(perg_y1-2,perg_y1+1):put(x,y,z,NAVY2,'pergola_depth_beam')
 for p in list(hosts):
  if not any(hosts[p].cells):hosts.pop(p);blocks.pop(p,None)

 # Scope validation: every changed cell must be inside source 1040 front 4.1m band.
 escaped=[];public_overlap=[]
 public_mats={parent.DRIVE,parent.DRIVE_JOINT,realm.WALK,realm.WALKJOINT,realm.STEP,realm.BRICK}
 for (p,i),(old,new,why) in writes.items():
  x,y,z=xyz(p,i);pt=np.array([(x+.5)/16,(z+.5)/16]);rr=pt-pa
  u=float(np.dot(rr,uvec))/width;d=float(np.dot(rr,normal));yy=(y-floor)/16
  if not (-.03<=u<=1.03 and -.10<=d<=4.15 and -.3<=yy<=total_h+.6 and poly.buffer(.04).covers(Point(*pt))):
   escaped.append([x,y,z,why,u,d,yy])
  if old in public_mats:public_overlap.append([x,y,z,why,old,new])
 if escaped or public_overlap:raise RuntimeError(str({'scope':escaped[:3],'public':public_overlap[:3]}))

 # Reference diagram from actual modeled depth bands.
 plan=Image.new('RGB',(1000,480),'white');pd=ImageDraw.Draw(plan)
 def sx(u):return 60+u*860
 def sd(d):return 410-d/2.5*300
 pd.rectangle((60,80,920,410),outline='#888',width=2)
 pd.line((sx(.15),sd(.55),sx(.94),sd(.55)),fill='#87aebf',width=5)
 pd.line((sx(.18),sd(.03),sx(.69),sd(.03)),fill='#294550',width=7)
 pd.line((sx(.22),sd(0),sx(.69),sd(0)),fill='#203743',width=7)
 pd.line((sx(.735),sd(.13),sx(.94),sd(.13)),fill='#426878',width=7)
 pd.line((sx(.015),sd(1.15),sx(.17),sd(1.15)),fill='#16262c',width=7)
 pd.text((60,25),'1040 v026 plan/depth logic: bays forward, wall/entry recessed, terrace 2m deep',fill='#243338')
 plan_path=OUT/'Lombard_1040_v026_depth_diagram.png';plan.save(plan_path)

 # Simple elevation diagram emphasizing two living bays + open terrace, not three flat glass storeys.
 elev=Image.new('RGB',(900,700),'#e8eff1');ed=ImageDraw.Draw(elev)
 def ex(u):return 55+u*790
 def ey(m):return 655-m/max(total_h,12.5)*600
 ed.rectangle((ex(.15),ey(9.18),ex(.96),ey(.15)),fill=(130,174,194),outline=(32,55,67),width=4)
 ed.rectangle((ex(.20),ey(2.42),ex(.67),ey(.18)),fill=(162,206,221),outline=(32,55,67),width=4)
 for u0,u1,y0,y1 in [(.205,.665,3.02,4.92),(.245,.665,5.88,7.72),(.765,.91,3.10,4.82),(.765,.91,5.90,7.62)]:
  ed.rectangle((ex(u0),ey(y1),ex(u1),ey(y0)),fill=(163,193,199),outline=(229,226,215),width=5)
 ed.rectangle((ex(.15),ey(9.18),ex(.96),ey(8.22)),outline=(32,55,67),width=4)
 # open railing/pergola
 for q in np.arange(.15,.97,.08):ed.line((ex(q),ey(10.45),ex(q),ey(9.25)),fill=(32,55,67),width=2)
 ed.line((ex(.15),ey(10.45),ex(.96),ey(10.45)),fill=(32,55,67),width=4)
 ed.line((ex(.15),ey(pergola_top),ex(.96),ey(pergola_top)),fill=(32,55,67),width=6)
 for q in [.15,.56,.96]:ed.line((ex(q),ey(pergola_top),ex(q),ey(9.18)),fill=(32,55,67),width=4)
 ed.text((55,18),'v026: two projecting living bays + narrow right bay + genuinely open terrace/pergola',fill='#243338')
 elev_path=OUT/'Lombard_1040_v026_elevation_intent.png';elev.save(elev_path)

 # Review sheet uses committed street overview; dedicated 2009/2019 URLs are in manifest/docs.
 sheet=Image.new('RGB',(1600,1080),'#efeee8');s=ImageDraw.Draw(sheet)
 fp=Path('C:/Windows/Fonts/segoeui.ttf');bp=Path('C:/Windows/Fonts/seguisb.ttf')
 def font(n,b=False):
  p=bp if b and bp.exists() else fp
  return ImageFont.truetype(str(p),n) if p.exists() else None
 s.text((35,20),'1040 LOMBARD v026 — 3D FRONT MASSING RESET',fill='#202725',font=font(30,True))
 s.text((35,62),'v025 flat facade rejected. Review bays, recesses and open terrace before fine detailing.',fill='#58605d',font=font(16))
 cards=[(REF,'STREET IDENTITY','Andrew Napier / CC BY 2.0 — overall 1040 relationship'),
        (plan_path,'DEPTH LOGIC','Main wall recessed; projecting bays and 2m terrace create real volume'),
        (elev_path,'MASSING INTENT','Two living bays, narrow right bay, garage, open railing/pergola')]
 for j,(src,title,captext) in enumerate(cards):
  x=35+(j%2)*780;y=105+(j//2)*465;s.rectangle((x,y,x+750,y+425),outline='#767d79',width=2)
  im=Image.open(src).convert('RGB');fr=ImageOps.contain(im,(725,330));sheet.paste(fr,(x+(750-fr.width)//2,y+38+(330-fr.height)//2))
  s.text((x+12,y+8),title,fill='#26322f',font=font(18,True));s.text((x+12,y+388),captext,fill='#404844',font=font(13))
 x,y=815,570;s.rectangle((x,y,x+750,y+425),outline='#767d79',width=2)
 s.text((x+12,y+8),'DEDICATED SOURCE CHECKS',fill='#26322f',font=font(18,True))
 lines=['June 2009 — Sławek Zawadzki / CC BY-SA 3.0','August 2013 — dronepicr / CC BY 2.0','July 2019 — Pom\' / CC BY-SA 2.0',
        'All show the same structural hierarchy: projecting bays + narrow right bay + open terrace/pergola.']
 for k,t in enumerate(lines):s.text((x+25,y+80+k*55),t,fill='#404844',font=font(16))
 sheet_path=OUT/'Lombard_1040_3D_Massing_v026_reference_sheet.jpg';sheet.save(sheet_path,quality=92)
 coords=np.array(list(blocks));lo=coords.min(0);hi=coords.max(0);bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),q) for p,q in sorted(hosts.items())]
 artifact=OUT/f'{NAME}.litematic'
 stats=write_single_region_litematic(artifact,blocks,bounds,REGION,NAME,
  '1040 Lombard 3D front massing reset from v024: recessed wall/entry, two projecting bays, narrow right bay, garage and open terrace/pergola. v025 flat facade rejected.',
  data_version=realm.v.DATA_VERSION,tile_entity_payloads=payload)
 actual,decoded=read(artifact,REGION)
 touched={p for p,i in writes};outside_ok=True
 for p,(orig,cells) in original.items():
  q=decoded.get(p)
  if q is None:
   # Pruning a now-empty host is valid only when every previously occupied
   # cell in that host was explicitly changed by the declared 1040 reset.
   if any(a is not None and (p,i) not in writes for i,a in enumerate(cells)):
    outside_ok=False;break
   continue
  if p not in touched:
   if q.original!=orig or q.cells!=cells:outside_ok=False;break
  else:
   for i,a in enumerate(cells):
    if (p,i) not in writes and q.cells[i]!=a:outside_ok=False;break
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
  'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
  'declared_1040_front_scope_only':not escaped,'public_realm_cells_untouched':not public_overlap,
  'all_parent_cells_outside_declared_edits_preserved':outside_ok,'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items()),
  'source_front_width_10_93m':10.7<width<11.2,'driveway_datum_supported':len(drive_y)>=20}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,
  'parent':'v024 (v025 rejected)','parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'building_id':BUILDING_ID,'address':'1040 Lombard Street',
  'front_width_m':width,'driveway_datum_samples':len(drive_y),'source_total_height_m':total_h,'terrace_deck_m':deck_h,'railing_top_m':rail_top,'pergola_top_m':pergola_top,
  'changed_microcells':len(writes),'changes':changes,
  'source_interpretation':{'June 2009':'projecting central bays, recessed entry, narrow right bay, open roof terrace/pergola',
   'August 2013':'same hierarchy plus facade framing and garage relationship','July 2019':'clear terrace/pergola depth and asymmetric bay composition'},
  'deferred':['fine timber pattern','decorative metal railing loops','bougainvillea and facade vegetation','full side/rear architecture','interiors','final roof/rear massing'],
  'review':'USER_MINECRAFT_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
 (OUT/'Build_notes.md').write_text('# 1040 Lombard 3D front massing v026\n\nv025 is rejected as a flat facade. v026 restarts from v024 and models the source-visible front as actual volumes: recessed base wall, two projecting bays, narrow right bay, and open terrace/pergola.\n')
 print(json.dumps({'file':str(artifact),'status':report['status'],'width_m':width,'height_m':total_h,'changed_microcells':len(writes),'changes':changes,'validation':checks},indent=2))
 if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
