"""Material-only finish for Lombard retaining/planter edges after v021."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from shapely.geometry import Point,LineString,shape
from shapely.ops import unary_union
from shapely.prepared import prep
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_road_finish_v021 as parent
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
road=parent.road;v=parent.v
OUT=road.PROJECT/'outputs/retaining_finish_v022'
NAME='Lombard_Retaining_Planter_Finish_Astra_v022';REGION='LOMBARD_RETAINING_FINISH_V022'
REF1=road.PROJECT/'references/private/wikimedia_commons/033_Lombard_Street_Cherry_Blossom.jpg.jpg'
REF2=road.PROJECT/'references/private/wikimedia_commons/049_Lombard_Street-Coit_Tower-San_Francisco-2.jpg.jpg'
def mat(rgb):return 'astra_microblocks:rgb_'+''.join(f'{max(0,min(255,int(x))):02x}' for x in rgb)
def ref_palette():
 im=Image.open(REF1).convert('RGB');a=np.array(im);h,w=a.shape[:2];crop=a[int(h*.52):int(h*.96),int(w*.10):int(w*.92)]
 flat=crop.reshape(-1,3).astype(float);spread=flat.max(1)-flat.min(1);mean=flat.mean(1)
 sample=flat[(spread<24)&(mean>95)&(mean<205)]
 base=np.round(np.percentile(sample,[30,48,66,82],axis=0)).astype(int)
 caps=np.clip(base+np.array([18,18,16]),0,255)
 return base,caps,{'file':str(REF1.relative_to(ROOT)),'sha256':hashlib.sha256(REF1.read_bytes()).hexdigest(),
 'page':'https://commons.wikimedia.org/wiki/File:Lombard_Street_Cherry_Blossom.jpg','artist':'Cornflower123','license':'CC0',
 'interpretation':'Low retaining/planter concrete color family and lighter top coping only; photograph illumination is not calibrated albedo.'}
def main():
 OUT.mkdir(parents=True,exist_ok=True);source=parent.OUT/f'{parent.NAME}.litematic'
 print('Loading v021.',flush=True);blocks,hosts=read(source,parent.REGION);vanilla={p:s for p,s in blocks.items() if p not in hosts}
 original={p:(vol.original,vol.cells.copy()) for p,vol in hosts.items()};backup={};writes={};changes={}
 center=json.loads(road.CENTER.read_text());line=LineString([(q['x_m'],q['z_m']) for q in center]);roadpoly,_=road.variable_road_polygon(line)
 profile=road.build_engineered_profile(center)
 curb_ring=roadpoly.buffer(road.CURB_BASE_WIDTH_CELLS/16,join_style=1,resolution=16).difference(roadpoly).difference(road.endpoint_opening_mask(line))
 scope=curb_ring;ring=prep(curb_ring)
 face,caps,evidence=ref_palette();face_m=[mat(c) for c in face];cap_m=[mat(c) for c in caps]
 _,accepted_pre=read(road.V009,'LOMBARD_CURB_ASTRA_V009')
 target_face=road.CURB_MATERIAL;target_cap='minecraft:smooth_stone';changed_columns=set();candidate_columns={}
 def put(pos,i,m,why):
  old=hosts[pos].cells[i]
  if old==m:return
  if pos not in backup:backup[pos]=(hosts[pos].original,hosts[pos].cells.copy())
  hosts[pos].cells[i]=m;writes[(pos,i)]=(old,m,why);changes[why]=changes.get(why,0)+1
 # Collect only source-bounded retaining/planter material above the accepted curb.
 for (hx,hy,hz),vol in list(hosts.items()):
  for i,m in enumerate(vol.cells):
   if m not in {target_face,target_cap}:continue
   gx=hx*16+(i&15)-480;gz=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
   pt=Point((gx+.5)/16,(gz+.5)/16)
   if not ring.covers(pt):continue
   station=line.project(pt);road_top=round(float(np.interp(station,profile['station_m'],profile['elev_rel_m']))*16)
   av=accepted_pre.get((hx,hy,hz))
   if av is not None and av.cells[i] is not None:continue
   if y<=road_top+1:continue
   candidate_columns.setdefault((gx,gz),[]).append((y,(hx,hy,hz),i,m))
 # Detail only the visible top/coping band: no wholesale wall-face recolor.
 for (gx,gz),items in candidate_columns.items():
  items.sort(key=lambda q:q[0]);top=items[-1][0]
  touched=False
  for y,pos,i,m in items:
   depth=top-y
   if depth==0:
    idx=((gx*19349663)^(gz*83492791))&1
    put(pos,i,cap_m[idx],'retaining_coping_finish');touched=True
   elif depth<=2 and m==target_face:
    roll=((gx*73856093)^(gz*19349663)^(y*83492791))&0xffffffff
    idx=0 if roll%100<58 else 1 if roll%100<82 else 2 if roll%100<96 else 3
    put(pos,i,face_m[idx],'retaining_upper_face_finish');touched=True
  if touched:changed_columns.add((gx,gz))
 print('Changed cells',len(writes),'columns',len(changed_columns),flush=True)
 # hard gates: material-only, central scope only, and no further edits to the
 # current v021 values at any cell belonging to accepted v009 road/curb.
 occupancy_changes=0;unexpected=[]
 for (p,i),(old,new,why) in writes.items():
  if (old is None)!=(new is None):occupancy_changes+=1
  hx,hy,hz=p;gx=hx*16+(i&15)-480;gz=hz*16+((i>>4)&15)-320
  if not scope.buffer(.01).covers(Point((gx+.5)/16,(gz+.5)/16)):unexpected.append([gx,hy*16+(i>>8),gz,why])
 accepted=accepted_pre;road_checked=road_mismatch=0;protected_write_overlap=0
 for p,vol in accepted.items():
  nv=hosts.get(p);parent_snapshot=original.get(p)
  for i,m in enumerate(vol.cells):
   if m is None:continue
   road_checked+=1
   # Compare v022 to the current v021 parent state, including inherited
   # absence from the declared v021 endpoint-cap repair.
   parent_value=parent_snapshot[1][i] if parent_snapshot is not None else None
   new_value=nv.cells[i] if nv is not None else None
   if new_value!=parent_value:road_mismatch+=1
   if (p,i) in writes:protected_write_overlap+=1
 # plan map
 xs=[x for x,z in changed_columns];zs=[z for x,z in changed_columns]
 img=Image.new('RGB',(1200,380),'white');d=ImageDraw.Draw(img)
 minx,maxx=(min(xs),max(xs)) if xs else (0,1);minz,maxz=(min(zs),max(zs)) if zs else (0,1)
 def pp(x,z):return (40+(x-minx)/(max(1,maxx-minx))*1120,30+(z-minz)/(max(1,maxz-minz))*300)
 for x,z in changed_columns:
  px,pz=pp(x,z);d.point((px,pz),fill=(125,124,119))
 d.line([pp(q['x_m']*16,q['z_m']*16) for q in center],fill=(142,66,56),width=3)
 map_path=OUT/'Lombard_V022_Retaining_Edge_Map.png';img.save(map_path)
 # reference sheet
 W,H=1600,1080;sheet=Image.new('RGB',(W,H),'#efeee8');sd=ImageDraw.Draw(sheet)
 fontp=Path('C:/Windows/Fonts/segoeui.ttf');boldp=Path('C:/Windows/Fonts/seguisb.ttf')
 def font(sz,b=False):
  p=boldp if b and boldp.exists() else fontp
  return ImageFont.truetype(str(p),sz) if p.exists() else None
 sd.text((35,22),'LOMBARD v022 — RETAINING / PLANTER EDGE FINISH',fill='#202725',font=font(30,True))
 sd.text((35,64),'Material-only detail. No geometry, road, planting or building changes.',fill='#58605d',font=font(17))
 items=[(map_path,'EDIT SCOPE','Gray = existing retaining/planter cells only'),
 (REF1,'LOW WALL REFERENCE','Cornflower123 / CC0 — face + coping character'),
 (REF2,'HAIRPIN EDGE REFERENCE','Yair-haklai / CC BY-SA 4.0 — curved edge read')]
 positions=[(35,105),(815,105),(35,565)]
 for (src,title,caption),(x,y) in zip(items,positions):
  im=Image.open(src).convert('RGB');frame=ImageOps.contain(im,(750,340));bx=x+(750-frame.width)//2;by=y+35+(340-frame.height)//2
  sheet.paste(frame,(bx,by));sd.rectangle((x,y,x+750,y+420),outline='#767d79',width=2);sd.text((x+12,y+8),title,fill='#26322f',font=font(18,True));sd.text((x+12,y+382),caption,fill='#404844',font=font(14))
 # palette panel
 x,y=815,565;sd.rectangle((x,y,x+750,y+420),outline='#767d79',width=2);sd.text((x+12,y+8),'PHOTO-SAMPLED CONCRETE FAMILY',fill='#26322f',font=font(18,True))
 sw=face.tolist()+caps[:2].tolist()
 for j,c in enumerate(sw):
  xx=x+35+(j%3)*220;yy=y+70+(j//3)*120;sd.rectangle((xx,yy,xx+170,yy+70),fill=tuple(c),outline='#555');sd.text((xx,yy+78),str(c),fill='#404844',font=font(13))
 sheet_path=OUT/'Lombard_Retaining_Finish_v022_reference_sheet.jpg';sheet.save(sheet_path,quality=92)
 # export
 writer=NBTWriter();coords=list(blocks);bounds=(min(p[0] for p in coords),min(p[1] for p in coords),min(p[2] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords),max(p[2] for p in coords))
 payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),vol) for p,vol in sorted(hosts.items())]
 path=OUT/f'{NAME}.litematic';stats=write_single_region_litematic(path,blocks,bounds,REGION,NAME,'Material-only retaining/planter concrete finish on v021. No occupancy or building changes.',data_version=road.DATA_VERSION,tile_entity_payloads=payload)
 actual,decoded=read(path,REGION);checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==vol.cells and decoded[p].original==vol.original for p,vol in hosts.items()),'material_only':occupancy_changes==0,'scope_only':not unexpected,'v021_values_on_v009_cells_preserved':road_mismatch==0 and protected_write_overlap==0,'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items())}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changed_microcells':len(writes),'changed_columns':len(changed_columns),'changes':changes,'road_cells_checked':road_checked,'road_mismatches_vs_v021_parent':road_mismatch,'protected_v009_write_overlap':protected_write_overlap,'reference':evidence,'palette':{'face':face.tolist(),'cap':caps[:2].tolist()},'preserved':['all occupancy','v021 parent values at every accepted v009 road/curb cell','sidewalks','stairs and rails','planting','buildings','registration'],'review':'USER_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
 (OUT/'Build_notes.md').write_text('# Lombard retaining/planter finish v022\n\nMaterial-only surface refinement of source-bounded retaining/planter edges. No geometry, road, landscape or building changes.\n')
 print(json.dumps({'file':str(path),'status':report['status'],'changed_microcells':len(writes),'changed_columns':len(changed_columns),'validation':checks},indent=2))
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
