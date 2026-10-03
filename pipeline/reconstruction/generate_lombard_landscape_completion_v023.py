"""Complete supported Lombard landscape/site connections over accepted v022."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point,shape
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_retaining_finish_v022 as parent
from pipeline.reconstruction import generate_lombard_public_realm_v1 as v
from pipeline.reconstruction import generate_lombard_realism_v020 as realism
from pipeline.reconstruction import generate_lombard_core_isolation_v005 as context
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
OUT=v.v.PROJECT/'outputs/landscape_completion_v023'
NAME='Lombard_Landscape_Completion_Astra_v023';REGION='LOMBARD_LANDSCAPE_COMPLETION_V023'
REF1=v.v.PROJECT/'references/private/wikimedia_commons/022_Lombard_Street_10064478253_.jpg.jpg'
REF2=v.v.PROJECT/'references/private/wikimedia_commons/024_Lombard_Street_5102863893_.jpg.jpg'
REF3=v.v.PROJECT/'references/private/wikimedia_commons/033_Lombard_Street_Cherry_Blossom.jpg.jpg'
GREEN={v.GREEN,realism.rgb('63764a'),realism.rgb('687a4e'),realism.rgb('607348'),realism.rgb('6b7c50')}
SHRUB=realism.SHRUB;BLOOM=realism.BLOOM;LEAVES=realism.LEAVES
BOTANICAL=set(SHRUB+BLOOM+LEAVES+[v.HEDGE,v.HEDGE2,v.LEAF,v.LEAF2])
def xyz(pos,i):
 hx,hy,hz=pos;return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320
def main():
 OUT.mkdir(parents=True,exist_ok=True);source=parent.OUT/f'{parent.NAME}.litematic'
 blocks,hosts=read(source,parent.REGION);vanilla={p:s for p,s in blocks.items() if p not in hosts}
 original={p:(vol.original,vol.cells.copy()) for p,vol in hosts.items()};writes={};tree_sources=set()
 def get(x,y,z):
  p,i=position(int(x),int(y),int(z));q=hosts.get(p);return q.cells[i] if q else None
 def put(x,y,z,mat,why):
  p,i=position(int(x),int(y),int(z))
  if p in vanilla or get(x,y,z) is not None:return False
  if p not in hosts:hosts[p]=MicroVolume('minecraft:bricks');blocks[p]=HOST_STATE
  hosts[p].cells[i]=mat;writes[(p,i)]=why;return True
 plan=json.loads((v.OUT/'public_realm_plan.geojson').read_text())
 def layer(name):
  g=[shape(f['geometry']) for f in plan['features'] if f['properties']['layer']==name]
  return unary_union(g) if g else Point(0,0).buffer(0)
 garden=layer('garden');pedestrian=layer('pedestrian');road=layer('road')
 core_zone=garden.difference(pedestrian.buffer(.18)).difference(road.buffer(.18))
 connector_zone=garden.buffer(2.25).intersection(pedestrian.buffer(3.25)).difference(pedestrian.buffer(.18)).difference(road.buffer(.18))
 allowed=unary_union([core_zone,connector_zone])
 surface={}
 for p,vol in hosts.items():
  for i,m in enumerate(vol.cells):
   if m not in GREEN:continue
   x,y,z=xyz(p,i);surface[(x,z)]=max(surface.get((x,z),-9999),y+1)
 candidate=[];connector_cells=0
 for (x,z),base in surface.items():
  pt=Point((x+.5)/16,(z+.5)/16)
  if not allowed.covers(pt):continue
  if any(get(x,y,z) in BOTANICAL for y in range(base,base+18)):continue
  candidate.append((x,z,base,connector_zone.covers(pt)))
 print('Plain supported green cells selected',len(candidate),flush=True)
 plant_cells=bloom_cells=0
 for x,z,base,is_connector in candidate:
  h=((x*73856093)^(z*19349663))&0xffffffff
  if not is_connector and h%11==0:continue
  height=2+(h%5)
  for y in range(base,base+height):
   plant_cells+=put(x,y,z,SHRUB[(h+y)%len(SHRUB)],'landscape_groundcover')
  if h%17<4:
   bloom_cells+=put(x,base+height,z,BLOOM[(h//17)%len(BLOOM)],'landscape_bloom')
  if is_connector:connector_cells+=1
 # Audit/complete every mapped OSM tree that has supported green ground nearby.
 truth=json.loads(context.TRUTH.read_text());nodes=v.node_sources(truth)
 keys=list(surface);tree= cKDTree(np.array([[(x+.5)/16,(z+.5)/16] for x,z in keys])) if keys else None
 raw=np.load(v.v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz')
 zero=float(json.loads(v.v.CENTER.read_text())[0]['elev_navd88_m'])
 mapped=existing_trees=added_trees=unsupported_trees=0;tree_audit=[]
 for node in nodes:
  if node['tags'].get('natural')!='tree':continue
  mapped+=1;x,z=node['x'],node['z'];dist,idx=tree.query([x,z])
  if dist>1.25:unsupported_trees+=1;tree_audit.append({'osm_id':node['id'],'status':'no_supported_green_base','nearest_m':float(dist)});continue
  gx,gz=keys[int(idx)];base=surface[(gx,gz)]
  present=False
  for dx in range(-4,5):
   for dz in range(-4,5):
    if any(get(gx+dx,base+y,gz+dz)==v.WOOD for y in range(0,28)):
     present=True;break
   if present:break
  if present:existing_trees+=1;tree_audit.append({'osm_id':node['id'],'status':'preserved_existing','nearest_m':float(dist)});continue  # New tree only where the mapped node resolves to supported green context.
  mask=(np.hypot(raw['x']-x,raw['z']-z)<1.8)&(raw['classification']!=2)&(raw['elev']>zero+base/16+2)
  hm=float(np.percentile(raw['elev'][mask],90)-zero-base/16) if mask.sum()>=10 else 5.0
  hm=min(14.,max(3.,hm));radius=1.8;ry=max(1.3,min(3.5,hm*.37));cy=base/16+hm-ry
  trunk_top=round((cy+.3)*16)
  for dx in range(-2,3):
   for dz in range(-2,3):
    if dx*dx+dz*dz<=5:
     for yy in range(base,trunk_top):put(gx+dx,yy,gz+dz,v.WOOD,'mapped_tree_trunk')
  rr=math.ceil(radius*16);yry=math.ceil(ry*16)
  for dx in range(-rr,rr+1):
   for dz in range(-rr,rr+1):
    for dy in range(-yry,yry+1):
     if (dx/(radius*16))**2+(dz/(radius*16))**2+(dy/(ry*16))**2>1:continue
     vx,vz=gx+dx,gz+dz;vy=round(cy*16)+dy
     if pedestrian.covers(Point((vx+.5)/16,(vz+.5)/16)) and vy<base+36:continue
     put(vx,vy,vz,LEAVES[((vx//5)*3+vz//5+vy//4)%len(LEAVES)],'mapped_tree_crown')
  added_trees+=1;tree_sources.add(node['id'])
  tree_audit.append({'osm_id':node['id'],'status':'added_from_mapped_source','height_m':hm,'nearby_non_ground_returns':int(mask.sum()),'nearest_green_m':float(dist)})
 # Parent occupancy is immutable: v023 only adds botanical cells into parent air.
 changed_parent=[];parent_occupied=0
 for p,(orig,cells) in original.items():
  nv=hosts.get(p)
  for i,a in enumerate(cells):
   if a is None:continue
   parent_occupied+=1;b=nv.cells[i] if nv else None
   if b!=a:changed_parent.append([p,i,a,b])
 for p in list(hosts):
  if not any(hosts[p].cells):hosts.pop(p);blocks.pop(p,None)
 # Compact plan/reference sheet for the next flyaround.
 xs=[xyz(p,i)[0] for p,i in writes];zs=[xyz(p,i)[2] for p,i in writes]
 img=Image.new('RGB',(1200,400),'white');d=ImageDraw.Draw(img)
 if xs:
  a,b,c,e=min(xs),max(xs),min(zs),max(zs)
  def pp(x,z):return 35+(x-a)/max(1,b-a)*1130,30+(z-c)/max(1,e-c)*330
  for p,i in writes:
   x,y,z=xyz(p,i);d.point(pp(x,z),fill=(64,108,63))
 map_path=OUT/'Lombard_v023_landscape_scope.png';img.save(map_path)
 sheet=Image.new('RGB',(1600,1080),'#efeee8');sd=ImageDraw.Draw(sheet)
 fp=Path('C:/Windows/Fonts/segoeui.ttf');bp=Path('C:/Windows/Fonts/seguisb.ttf')
 def font(n,b=False):return ImageFont.truetype(str(bp if b and bp.exists() else fp),n) if fp.exists() else None
 sd.text((35,20),'LOMBARD v023 — LANDSCAPE + SITE CONNECTIVITY',fill='#202725',font=font(30,True))
 sd.text((35,62),'Supported green ground only; accepted hardscape/buildings remain frozen.',fill='#58605d',font=font(17))
 cards=[(map_path,'EDIT SCOPE','New botanical additions on existing supported green ground'),
        (REF1,'FULL-BLOCK RHYTHM','Andrew Napier / CC BY 2.0 — dense hedge/flower/tree layering'),
        (REF2,'GARDEN DENSITY','Toi & Moi / CC BY-SA 2.0 — road/planter/tree relationship'),
        (REF3,'UPPER GARDEN EDGE','Cornflower123 / CC0 — landscaping continuity near upper site')]
 for j,(src,title,cap) in enumerate(cards):
  x=35+(j%2)*780;y=105+(j//2)*465;sd.rectangle((x,y,x+750,y+425),outline='#767d79',width=2)
  im=Image.open(src).convert('RGB');fr=ImageOps.contain(im,(725,330));sheet.paste(fr,(x+(750-fr.width)//2,y+38+(330-fr.height)//2))
  sd.text((x+12,y+8),title,fill='#26322f',font=font(18,True));sd.text((x+12,y+388),cap,fill='#404844',font=font(13))
 refsheet=OUT/'Lombard_Landscape_Completion_v023_reference_sheet.jpg';sheet.save(refsheet,quality=92)
 coords=list(blocks);lo=np.min(np.array(coords),axis=0);hi=np.max(np.array(coords),axis=0);bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),vol) for p,vol in sorted(hosts.items())]
 artifact=OUT/f'{NAME}.litematic'
 stats=write_single_region_litematic(artifact,blocks,bounds,REGION,NAME,'Landscape/site-connectivity completion on accepted v022: supported green ground only, mapped-tree audit/completion, no parent occupied-cell edits.',data_version=v.v.DATA_VERSION,tile_entity_payloads=payload)
 actual,decoded=read(artifact,REGION)
 additions_air_only=all(original.get(p,('x',[None]*4096))[1][i] is None for p,i in writes)
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
 'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
 'parent_occupied_cells_preserved':not changed_parent,'additions_only_into_parent_air':additions_air_only,
 'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items()),'mapped_tree_sources_only':all(a['status']!='added_from_mapped_source' or a['osm_id'] in tree_sources for a in tree_audit)}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'candidate_plain_green_columns':len(candidate),'connector_columns_vegetated':connector_cells,'groundcover_cells_added':plant_cells,'bloom_cells_added':bloom_cells,
 'mapped_tree_nodes':mapped,'existing_mapped_trees_preserved':existing_trees,'mapped_trees_added':added_trees,'mapped_trees_without_supported_green_base':unsupported_trees,
 'tree_audit':tree_audit,'changed_parent_occupied_cells':changed_parent[:10],
 'preserved':['v022 road/curb/pavers','sidewalks','stairs/landings/rails','retaining/planter finish','all building envelopes and facade placeholders','registration marker','all pre-existing occupied microcells'],
 'sources':[{'file':'022_Lombard_Street_10064478253_.jpg.jpg','use':'full-block landscape rhythm only'},
 {'file':'024_Lombard_Street_5102863893_.jpg.jpg','use':'garden density/tree massing character only'},
 {'file':'033_Lombard_Street_Cherry_Blossom.jpg.jpg','use':'upper garden edge continuity only'}],
 'review':'USER_MINECRAFT_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
 (OUT/'Build_notes.md').write_text('# Lombard landscape completion v023\n\nAdds botanical mass only above existing supported green surfaces and completes mapped OSM trees where a supported green base exists. Parent occupied cells are immutable.\n')
 print(json.dumps({'file':str(artifact),'status':report['status'],'validation':checks,'candidate_columns':len(candidate),'connector_columns':connector_cells,'plant_cells_added':plant_cells+bloom_cells,'trees':{'mapped':mapped,'preserved':existing_trees,'added':added_trees,'unsupported':unsupported_trees}},indent=2))
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
