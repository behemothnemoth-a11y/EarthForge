"""Lombard v025: source-led street-facing facade skeleton for 1040 Lombard."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from shapely.geometry import Point,LineString,shape
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_access_tree_realism_v024 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic

OUT=realm.v.PROJECT/'outputs/house_1040_facade_v025'
NAME='Lombard_1040_Facade_Skeleton_Astra_v025';REGION='LOMBARD_1040_FACADE_V025'
BUILDING_ID='201006.0032105'
REF=realm.v.PROJECT/'references/private/wikimedia_commons/021_Lombard_Street_10064415846_.jpg.jpg'
BODY=['astra_microblocks:rgb_a8cbd7','astra_microblocks:rgb_b2d1db']
TRIM='astra_microblocks:rgb_263e4a';FRAME='astra_microblocks:rgb_e6e3d8'
GLASS='astra_microblocks:rgb_91b1b8';GARAGE='astra_microblocks:rgb_9bc8d7'
GARAGE_LINE='astra_microblocks:rgb_6f96a2';ENTRY='astra_microblocks:rgb_182a31'
RAIL='astra_microblocks:rgb_202b2e'
def xyz(pos,i):
 hx,hy,hz=pos
 return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320

WINDOWS=[
 (.18,.62,2.85,5.05,6,3),(.72,.89,2.95,4.95,2,3),
 (.18,.52,5.65,7.75,4,2),(.72,.87,5.65,7.75,2,2),
 (.18,.52,8.25,10.10,4,2),(.72,.87,8.25,10.10,2,2)
]

def window_material(u,yy,width):
 for u0,u1,y0,y1,cols,rows in WINDOWS:
  if not (u0<=u<=u1 and y0<=yy<=y1):continue
  w=(u1-u0)*width; ux=(u-u0)/(u1-u0)*w; vy=yy-y0
  border=min(ux,w-ux,vy,y1-yy)<.085
  vm=any(abs(ux-w*k/cols)<.045 for k in range(1,cols))
  hm=any(abs(vy-(y1-y0)*k/rows)<.045 for k in range(1,rows))
  return FRAME if border or vm or hm else GLASS
 return None

def facade_material(u,yy,width,height,x,y,z):
 wm=window_material(u,yy,width)
 if wm:return ('window',wm)
 if .20<=u<=.67 and .18<=yy<=2.58:
  border=min((u-.20)*width,(.67-u)*width,yy-.18,2.58-yy)<.10
  panel=(abs((yy-.18)%0.46)<.045 or abs(((u-.20)*width)%1.12)<.045)
  return ('garage',TRIM if border else GARAGE_LINE if panel else GARAGE)
 if .035<=u<=.155 and .20<=yy<=2.78:return ('entry',ENTRY)
 if yy>=10.98:
  rail=(yy<11.10 or yy>height-.13 or abs(((u*width)%0.55)-.275)<.055)
  return ('rail',RAIL if rail else None)
 horiz=any(abs(yy-q)<.095 for q in [2.68,5.28,7.98,10.28,10.92])
 vert=any(abs(u-q)*width<.095 for q in [.03,.16,.66,.70,.92,.97])
 diag=(abs(((u*width+yy*.88)%2.45)-1.225)<.075 or
       abs(((u*width-yy*.74)%2.65)-1.325)<.07)
 if horiz or vert or diag:return ('wall',TRIM)
 return ('wall',BODY[((x//5)+(z//5)+(y//6))&1])
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 source=parent.OUT/f'{parent.NAME}.litematic'
 blocks,hosts=read(source,parent.REGION);vanilla={p:s for p,s in blocks.items() if p not in hosts}
 original={p:(v.original,v.cells.copy()) for p,v in hosts.items()}
 env=json.loads((buildings.OUT/'building_envelopes.geojson').read_text())
 feat=next(f for f in env['features'] if str(f['properties']['id'])==BUILDING_ID)
 geom=shape(feat['geometry']);poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,'geoms') else geom
 center=json.loads(realm.v.CENTER.read_text());road=LineString([(q['x_m'],q['z_m']) for q in center])
 edges=[]
 coords=list(poly.exterior.coords)
 for a,b in zip(coords,coords[1:]):
  seg=LineString([a,b])
  if seg.length>5:edges.append((seg.distance(road),seg.length,np.array(a,float),np.array(b,float)))
 _,_,pa,pb=min(edges,key=lambda q:q[0])
 if pa[0]>pb[0]:pa,pb=pb,pa
 d=pb-pa;width=float(np.linalg.norm(d));uvec=d/width
 normal=np.array([-uvec[1],uvec[0]])
 if np.dot(np.array([poly.centroid.x,poly.centroid.y])-((pa+pb)/2),normal)<0:normal=-normal
 prop=feat['properties'];zero=float(center[0]['elev_navd88_m'])
 # Anchor the garage/front facade to the accepted v024 driveway immediately
 # outside the source footprint, not to the minimum ground anywhere under the
 # deep sloping parcel. This prevents a false extra storey at the street face.
 drive_y=[]
 for hp,hv in hosts.items():
  for ii,mm in enumerate(hv.cells):
   if mm not in {parent.DRIVE,parent.DRIVE_JOINT}:continue
   xx,yy0,zz=xyz(hp,ii);pt0=np.array([(xx+.5)/16,(zz+.5)/16]);rr=pt0-pa
   uu=float(np.dot(rr,uvec))/width;dd=float(np.dot(rr,normal))
   if .20<=uu<=.67 and -2.2<=dd<=-.35:drive_y.append(yy0)
 if len(drive_y)<20:raise RuntimeError('1040 front datum lacks accepted driveway support')
 floor=int(round(float(np.median(drive_y))))+1
 cap=round((prop['median_first_return_navd88_m']-zero)*16)
 height=(cap-floor)/16
 print('1040 front width',width,'height envelope',height,'floor/cap',floor,cap,'drive samples',len(drive_y),flush=True)
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
 # Rebuild only the first 0.50 m of the source-identified road-facing facade.
 minx,minz,maxx,maxz=poly.bounds
 for x in range(math.floor((minx-.2)*16),math.ceil((maxx+.2)*16)):
  for z in range(math.floor((minz-.2)*16),math.ceil((maxz+.2)*16)):
   pt=np.array([(x+.5)/16,(z+.5)/16]);rel=pt-pa
   u_m=float(np.dot(rel,uvec));depth=float(np.dot(rel,normal));u=u_m/width
   if not (0<=u<=1 and 0<=depth<=.50):continue
   if not poly.buffer(.01).covers(Point(*pt)):continue
   for y in range(floor,cap):
    yy=(y-floor)/16;kind,mat=facade_material(u,yy,width,height,x,y,z)
    if kind=='window':
     if depth<=.12:put(x,y,z,mat,'window_frame_or_glass')
     elif depth<=.46:put(x,y,z,None,'window_recess')
    elif kind=='entry':
     if depth<.30:put(x,y,z,None,'entry_recess')
     elif depth<=.43:put(x,y,z,ENTRY,'entry_back')
    elif kind=='rail':
     if depth<=.48:put(x,y,z,mat,'top_terrace_rail' if mat else 'top_terrace_open')
    elif depth<=.20:
     put(x,y,z,mat,'garage' if kind=='garage' else 'blue_panel_and_timber')

 # QA: every edit must stay inside 1040, within the front half-metre and height envelope.
 escaped=[]
 for (p,i),(old,new,why) in writes.items():
  x,y,z=xyz(p,i);pt=np.array([(x+.5)/16,(z+.5)/16]);rel=pt-pa
  u=float(np.dot(rel,uvec))/width;depth=float(np.dot(rel,normal))
  if not (-.002<=u<=1.002 and -.002<=depth<=.505 and floor<=y<cap and poly.buffer(.02).covers(Point(*pt))):
   escaped.append([x,y,z,why,u,depth])
 if escaped:raise RuntimeError('1040 facade edit escaped declared scope '+str(escaped[:3]))

 # Reference plan and facade intent diagram.
 plan=Image.new('RGB',(760,360),'white');pd=ImageDraw.Draw(plan)
 bx=poly.bounds;rx=[q['x_m'] for q in center];rz=[q['z_m'] for q in center]
 x0=min(bx[0],min(rx))-3;x1=max(bx[2],max(rx))+3;z0=min(bx[1],min(rz))-3;z1=max(bx[3],max(rz))+3
 def pp(x,z):return (30+(x-x0)/(x1-x0)*700,25+(z-z0)/(z1-z0)*305)
 pd.line([pp(*q) for q in road.coords],fill=(151,83,73),width=5)
 pd.polygon([pp(*q) for q in poly.exterior.coords],outline=(84,84,84),fill=(220,222,218))
 pd.line([pp(*pa),pp(*pb)],fill=(33,91,126),width=8)
 pd.text((30,332),'Blue = source-identified 1040 street facade (~10.93 m)',fill=(30,45,55))
 plan_path=OUT/'Lombard_1040_v025_plan.png';plan.save(plan_path)
 elev=Image.new('RGB',(900,650),'#dfeaf0');ed=ImageDraw.Draw(elev)
 def ex(u):return 45+u*810
 def ey(m):return 615-m/max(height,12.1)*565
 ed.rectangle((45,50,855,615),fill=(171,205,216),outline=(38,62,74),width=5)
 for u0,u1,y0,y1,cols,rows in WINDOWS:
  ed.rectangle((ex(u0),ey(y1),ex(u1),ey(y0)),fill=(145,177,184),outline=(234,232,222),width=5)
  for k in range(1,cols):ed.line((ex(u0+(u1-u0)*k/cols),ey(y1),ex(u0+(u1-u0)*k/cols),ey(y0)),fill=(234,232,222),width=2)
  for k in range(1,rows):ed.line((ex(u0),ey(y0+(y1-y0)*k/rows),ex(u1),ey(y0+(y1-y0)*k/rows)),fill=(234,232,222),width=2)
 ed.rectangle((ex(.20),ey(2.58),ex(.67),ey(.18)),fill=(155,200,215),outline=(38,62,74),width=5)
 ed.rectangle((ex(.035),ey(2.78),ex(.155),ey(.20)),fill=(24,42,49),outline=(38,62,74),width=4)
 for q in [2.68,5.28,7.98,10.28,10.92]:ed.line((45,ey(q),855,ey(q)),fill=(38,62,74),width=5)
 for q in [.03,.16,.66,.70,.92,.97]:ed.line((ex(q),ey(10.92),ex(q),615),fill=(38,62,74),width=4)
 ed.text((45,18),'v025 facade identity intent — photo-proportioned openings, not survey dimensions',fill=(30,45,55))
 elev_path=OUT/'Lombard_1040_v025_elevation_intent.png';elev.save(elev_path)

 ref=Image.open(REF).convert('RGB')
 crop=ref.crop((int(ref.width*.64),int(ref.height*.03),ref.width,int(ref.height*.94)))
 sheet=Image.new('RGB',(1600,1080),'#efeee8');sd=ImageDraw.Draw(sheet)
 fp=Path('C:/Windows/Fonts/segoeui.ttf');bp=Path('C:/Windows/Fonts/seguisb.ttf')
 def font(n,b=False):
  p=bp if b and bp.exists() else fp
  return ImageFont.truetype(str(p),n) if p.exists() else None
 sd.text((35,20),'1040 LOMBARD v025 — STREET FACADE SKELETON',fill='#202725',font=font(30,True))
 sd.text((35,62),'Identity/opening rhythm only. Roof, rear, interiors and neighboring houses remain frozen.',fill='#58605d',font=font(16))
 cards=[(plan_path,'PLAN / FRONT EDGE','DataSF footprint + road; blue edge is the only architectural edit'),
        (REF,'STREET OVERVIEW','Andrew Napier / CC BY 2.0 — 1040 identity and overall facade relationship'),
        (crop,'FACADE CROP','Light-blue infill, dark framing, discrete windows, garage and open top terrace'),
        (elev_path,'MODELED SLICE','Photo-proportioned facade skeleton; depth/roof refinement comes later')]
 for j,(src,title,captext) in enumerate(cards):
  x=35+(j%2)*780;y=105+(j//2)*465;sd.rectangle((x,y,x+750,y+425),outline='#767d79',width=2)
  im=src if isinstance(src,Image.Image) else Image.open(src).convert('RGB')
  fr=ImageOps.contain(im,(725,330));sheet.paste(fr,(x+(750-fr.width)//2,y+38+(330-fr.height)//2))
  sd.text((x+12,y+8),title,fill='#26322f',font=font(18,True));sd.text((x+12,y+388),captext,fill='#404844',font=font(13))
 sheet_path=OUT/'Lombard_1040_Facade_v025_reference_sheet.jpg';sheet.save(sheet_path,quality=92)
 coords=np.array(list(blocks));lo=coords.min(0);hi=coords.max(0);bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),vol) for p,vol in sorted(hosts.items())]
 artifact=OUT/f'{NAME}.litematic'
 stats=write_single_region_litematic(artifact,blocks,bounds,REGION,NAME,
  'Source-led 1040 Lombard street facade skeleton: discrete openings, light-blue panels, dark framing, garage and open top terrace. No roof/rear/interior work.',
  data_version=realm.v.DATA_VERSION,tile_entity_payloads=payload)
 actual,decoded=read(artifact,REGION);touched={p for p,i in writes}
 outside_ok=True
 for p,(orig,cells) in original.items():
  q=decoded.get(p)
  if q is None:outside_ok=False;break
  if p not in touched:
   if q.original!=orig or q.cells!=cells:outside_ok=False;break
  else:
   for i,a in enumerate(cells):
    if (p,i) not in writes and q.cells[i]!=a:outside_ok=False;break
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
  'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
  'declared_1040_front_scope_only':not escaped,'all_parent_cells_outside_declared_edits_preserved':outside_ok,
  'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items()),'source_front_width_10_93m':10.7<width<11.2}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,
  'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'building_id':BUILDING_ID,'address':'1040 Lombard Street',
  'front_edge_m':width,'envelope_height_m':height,'changed_microcells':len(writes),'changes':changes,
  'source_basis':{'footprint':'DataSF building footprint 201006.0032105 + OSM address match 1040 Lombard Street',
   'street_photo':'Wikimedia Commons Lombard Street (10064415846), Andrew Napier, CC BY 2.0',
   'interpretation':'Opening and timber proportions are photo-proportioned; not measured facade survey dimensions.'},
  'explicitly_deferred':['bay/projection depth verification','roof/pergola geometry','side and rear facades','interior','bougainvillea facade vegetation'],
  'review':'USER_MINECRAFT_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
 (OUT/'Build_notes.md').write_text('# 1040 Lombard facade skeleton v025\n\nFirst architecture slice after public-realm work. Rebuilds only the road-facing half-metre of the source-identified 1040 footprint. The old v020 glass-grid interpretation is not reused as truth.\n')
 print(json.dumps({'file':str(artifact),'status':report['status'],'front_width_m':width,'height_m':height,'changed_microcells':len(writes),'changes':changes,'validation':checks},indent=2))
 if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
