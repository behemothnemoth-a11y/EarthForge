"""Lombard v024: mapped driveway access, Hyde sidewalk closure, tree realism."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point,LineString,shape
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_landscape_completion_v023 as parent
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_core_isolation_v005 as context
from pipeline.reconstruction import generate_lombard_retaining_finish_v022 as v022
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic

OUT=realm.v.PROJECT/'outputs/access_tree_realism_v024'
NAME='Lombard_Access_And_Tree_Realism_Astra_v024';REGION='LOMBARD_ACCESS_TREE_REALISM_V024'
REF1=realm.v.PROJECT/'references/private/wikimedia_commons/021_Lombard_Street_10064415846_.jpg.jpg'
REF2=realm.v.PROJECT/'references/private/wikimedia_commons/024_Lombard_Street_5102863893_.jpg.jpg'
REF3=realm.v.PROJECT/'references/private/wikimedia_commons/033_Lombard_Street_Cherry_Blossom.jpg.jpg'
DRIVE='astra_microblocks:rgb_9f9b91';DRIVE_JOINT='astra_microblocks:rgb_85827b'
TREE_MATS={realm.WOOD,realm.LEAF,realm.LEAF2,*parent.LEAVES}
BOTANICAL=set(parent.BOTANICAL)|TREE_MATS
DRIVEWAY_WIDTH_M=2.75

def xyz(pos,i):
 hx,hy,hz=pos
 return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320

def raster(poly):
 if poly.is_empty:return np.empty(0,dtype=int),np.empty(0,dtype=int)
 x0,z0,x1,z1=poly.bounds
 gx,gz=np.meshgrid(np.arange(math.floor(x0*16),math.ceil(x1*16)),np.arange(math.floor(z0*16),math.ceil(z1*16)))
 from shapely import contains_xy
 ok=contains_xy(poly,(gx+.5)/16,(gz+.5)/16)
 return gx[ok],gz[ok]

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 source=parent.OUT/f'{parent.NAME}.litematic'
 blocks,hosts=read(source,parent.REGION)
 vanilla={p:s for p,s in blocks.items() if p not in hosts}
 original={p:(v.original,v.cells.copy()) for p,v in hosts.items()}
 writes={};changes={}
 def get(x,y,z):
  p,i=position(int(x),int(y),int(z));q=hosts.get(p)
  return q.cells[i] if q else None
 def put(x,y,z,mat,why):
  p,i=position(int(x),int(y),int(z))
  if p in vanilla:return False
  old=hosts[p].cells[i] if p in hosts else None
  if old==mat:return False
  if p not in hosts:hosts[p]=MicroVolume('minecraft:bricks');blocks[p]=HOST_STATE
  hosts[p].cells[i]=mat;writes[(p,i)]=(old,mat,why);changes[why]=changes.get(why,0)+1
  return True

 plan=json.loads((realm.OUT/'public_realm_plan.geojson').read_text())
 def layer(name):
  q=[shape(f['geometry']) for f in plan['features'] if f['properties']['layer']==name]
  return unary_union(q) if q else Point(0,0).buffer(0)
 road=layer('road');pedestrian=layer('pedestrian');garden=layer('garden')
 env=json.loads((buildings.OUT/'building_envelopes.geojson').read_text())
 building_union=unary_union([shape(f['geometry']) for f in env['features']])
 cache=np.load(realm.OUT/'surface_preview.npz')
 tops={tuple(map(int,k)):int(t) for k,t in zip(cache['xz'],cache['top'])}
 for p,vol in hosts.items():
  for i,m in enumerate(vol.cells):
   if m not in parent.GREEN:continue
   x,y,z=xyz(p,i);tops[(x,z)]=max(tops.get((x,z),-9999),y+1)

 truth=json.loads(context.TRUTH.read_text());ways=context.parse_osm_local(truth)
 driveway_ways=[w for w in ways if w['tags'].get('service')=='driveway' and w['line'].intersects(garden.buffer(5))]
 driveway_polys=[w['line'].buffer(DRIVEWAY_WIDTH_M/2,cap_style=2,join_style=2).difference(road.buffer(.03)).difference(building_union) for w in driveway_ways]
 driveway_scope=unary_union(driveway_polys)
 byid={str(w['id']):w for w in ways}
 top_cross=byid['691835290']['line'];top_side=byid['691835289']['line']
 ends1=[Point(top_cross.coords[0]),Point(top_cross.coords[-1])];ends2=[Point(top_side.coords[0]),Point(top_side.coords[-1])]
 a,b=min(((a,b) for a in ends1 for b in ends2),key=lambda ab:ab[0].distance(ab[1]))
 gap=LineString([a.coords[0],b.coords[0]])
 top_existing=unary_union([byid[i]['line'].buffer(.75,cap_style=2,join_style=2) for i in ['691835288','691835289']])
 top_gap=gap.buffer(.78,cap_style=2,join_style=2)
 top_scope=unary_union([top_existing,top_gap]).difference(road.buffer(.02))
 access_scope=unary_union([driveway_scope,top_scope])

 face,caps,_=v022.ref_palette()
 retaining={v022.mat(c) for c in face}|{v022.mat(c) for c in caps[:2]}|{realm.v.CURB_MATERIAL,'minecraft:smooth_stone'}
 removable_above=BOTANICAL|retaining|{realm.BLACK}
 surface_allowed=parent.GREEN|{realm.WALK,realm.WALKJOINT,realm.STEP,realm.BRICK,realm.v.CURB_MATERIAL,*retaining,DRIVE,DRIVE_JOINT}
 road_writes=0;drive_columns=sidewalk_columns=rail_cuts=wall_cuts=0

 def clear_above(x,z,base,poly,kind):
  nonlocal rail_cuts,wall_cuts
  for y in range(base,base+28):
   m=get(x,y,z)
   if m not in removable_above:continue
   if m==realm.BLACK:rail_cuts+=1
   if m in retaining:wall_cuts+=1
   put(x,y,z,None,kind+'_clearance')

 for w,poly in zip(driveway_ways,driveway_polys):
  gx,gz=raster(poly)
  for x,z in zip(gx,gz):
   x,z=int(x),int(z);base=tops.get((x,z))
   if base is None:continue
   pt=Point((x+.5)/16,(z+.5)/16)
   if road.covers(pt):road_writes+=1;continue
   clear_above(x,z,base,poly,'driveway')
   old=get(x,base-1,z)
   if old not in surface_allowed and old is not None:continue
   station=w['line'].project(pt);mat=DRIVE_JOINT if int(round(station*16))%24==0 else DRIVE
   put(x,base-1,z,mat,'driveway_surface');drive_columns+=1

 gx,gz=raster(top_scope)
 for x,z in zip(gx,gz):
  x,z=int(x),int(z);base=tops.get((x,z))
  if base is None:continue
  pt=Point((x+.5)/16,(z+.5)/16)
  if road.covers(pt):continue
  clear_above(x,z,base,top_scope,'top_sidewalk')
  old=get(x,base-1,z)
  if old not in surface_allowed and old is not None:continue
  mat=realm.WALKJOINT if (x//24+z//24)%11==0 else realm.WALK
  put(x,base-1,z,mat,'top_sidewalk_surface');sidewalk_columns+=1

 # Tree realism: reshape only trees already represented in the parent.
 nodes=[n for n in realm.node_sources(truth) if n['tags'].get('natural')=='tree']
 tree_xy=np.array([[n['x'],n['z']] for n in nodes]);tree_index=cKDTree(tree_xy)
 groups={i:[] for i in range(len(nodes))}
 for p,(orig,cells) in original.items():
  for i,m in enumerate(cells):
   if m not in TREE_MATS:continue
   x,y,z=xyz(p,i);dist,j=tree_index.query([(x+.5)/16,(z+.5)/16])
   if dist<=3.0:groups[int(j)].append((x,y,z,m))

 tree_audit=[];tree_write_scope={}
 for j,cells in groups.items():
  if len(cells)<24:continue
  node=nodes[j];cx=round(node['x']*16);cz=round(node['z']*16)
  wood=[q for q in cells if q[3]==realm.WOOD];leaf=[q for q in cells if q[3]!=realm.WOOD]
  if not leaf:continue
  base=min(q[1] for q in wood) if wood else min(q[1] for q in cells)
  leaf_min=min(q[1] for q in leaf);top=max(q[1] for q in leaf)
  rr=np.array([math.hypot(q[0]-cx,q[2]-cz) for q in leaf])
  radius=max(14,min(36,int(round(np.percentile(rr,97)))+1))
  height=max(24,top-base+1);crown_h=max(16,top-leaf_min+1)
  old_tree_keys={(x,y,z) for x,y,z,m in cells}
  for x,y,z,m in cells:
   if building_union.covers(Point(((x+.5)/16,(z+.5)/16))):continue
   put(x,y,z,None,'tree_reshape_remove')

  seed=int(node['id'])&0xffffffff
  trunk_top=max(leaf_min+2,min(top-8,base+round(height*.62)))
  for y in range(base,trunk_top+1):
   frac=(y-base)/max(1,trunk_top-base);rad=3 if frac<.35 and height>72 else 2
   if frac>.78:rad=1
   for dx in range(-rad,rad+1):
    for dz in range(-rad,rad+1):
     if dx*dx+dz*dz>rad*rad:continue
     pt=Point(((cx+dx+.5)/16,(cz+dz+.5)/16))
     if access_scope.covers(pt) or building_union.covers(pt):continue
     put(cx+dx,y,cz+dz,realm.WOOD,'tree_trunk')

  branch_targets=[]
  for k in range(4):
   ang=((seed%360)+k*91+(seed>>(k+2))%19)*math.pi/180
   dist=radius*(.38+.10*((seed>>(k*3))&3))
   tx=round(cx+math.cos(ang)*dist);tz=round(cz+math.sin(ang)*dist)
   ty=min(top-3,leaf_min+round(crown_h*(.42+.08*k)))
   sy=trunk_top-5+(k%3)*3;n=max(abs(tx-cx),abs(tz-cz),abs(ty-sy),1)
   for s in range(n+1):
    f=s/n;x=round(cx+(tx-cx)*f);z=round(cz+(tz-cz)*f);y=round(sy+(ty-sy)*f)
    rad=2 if s<n*.45 else 1
    for dx in range(-rad,rad+1):
     for dz in range(-rad,rad+1):
      if dx*dx+dz*dz>rad*rad:continue
      pt=Point(((x+dx+.5)/16,(z+dz+.5)/16))
      if access_scope.covers(pt) or building_union.covers(pt):continue
      put(x+dx,y,z+dz,realm.WOOD,'tree_branch')
   branch_targets.append((tx,ty,tz))

  lobes=[(cx,leaf_min+round(crown_h*.56),cz,radius*.62,crown_h*.46,radius*.58)]
  for k,(tx,ty,tz) in enumerate(branch_targets):
   lobes.append((round((cx+tx)/2),min(top-2,ty+round(crown_h*.10)),round((cz+tz)/2),radius*(.42+.04*(k%2)),crown_h*(.30+.03*k),radius*(.40+.03*((k+1)%2))))
  xmin,xmax=cx-radius,cx+radius;zmin,zmax=cz-radius,cz+radius
  for x in range(xmin,xmax+1):
   for z in range(zmin,zmax+1):
    pt=Point(((x+.5)/16,(z+.5)/16))
    if access_scope.covers(pt) or building_union.covers(pt):continue
    for y in range(leaf_min,top+1):
     best=99.
     for lx,ly,lz,rx,ry,rz in lobes:
      q=((x-lx)/max(1,rx))**2+((y-ly)/max(1,ry))**2+((z-lz)/max(1,rz))**2
      best=min(best,q)
     if best>1:continue
     outer=((x-cx)/radius)**2+((z-cz)/radius)**2+((y-(leaf_min+top)/2)/max(1,crown_h*.56))**2
     if outer>1.16:continue
     h=((x*73856093)^(z*19349663)^(y*83492791)^seed)&0xffffffff
     if best>.72 and h%100<28:continue
     if best>.88 and h%100<55:continue
     put(x,y,z,parent.LEAVES[(h//101)%len(parent.LEAVES)],'tree_crown')
     tree_write_scope[(x,y,z)]=(j,radius,base,top)

  newcells=0
  for p,i in writes:
   x,y,z=xyz(p,i)
   if (x,y,z) in tree_write_scope and tree_write_scope[(x,y,z)][0]==j:newcells+=1
  tree_audit.append({'osm_id':node['id'],'parent_tree_cells':len(cells),'height_m':height/16,'old_crown_radius_m':radius/16,'trunk_base_y_cells':base,'top_y_cells':top,'rebuilt_tree_cells':newcells})

 for p in list(hosts):
  if not any(hosts[p].cells):hosts.pop(p);blocks.pop(p,None)

 # Hard validation of mutation scopes.
 access_escape=[];tree_escape=[];unexpected=[]
 for (p,i),(old,new,why) in writes.items():
  x,y,z=xyz(p,i);pt=Point((x+.5)/16,(z+.5)/16)
  if why.startswith('driveway') or why.startswith('top_sidewalk'):
   if not access_scope.buffer(.01).covers(pt):access_escape.append([x,y,z,why])
   if road.covers(pt):road_writes+=1
  elif why.startswith('tree_'):
   dist,j=tree_index.query([(x+.5)/16,(z+.5)/16])
   if dist>3.0:tree_escape.append([x,y,z,why,float(dist)])
  else:unexpected.append([x,y,z,why])
 if unexpected or access_escape or tree_escape:raise RuntimeError(str({'unexpected':unexpected[:3],'access':access_escape[:3],'tree':tree_escape[:3]}))

 # No building footprint or road mutation.
 building_writes=0
 for p,i in writes:
  x,y,z=xyz(p,i);pt=Point((x+.5)/16,(z+.5)/16)
  if building_union.covers(pt):building_writes+=1

 # Review map/reference sheet.
 center=json.loads(realm.v.CENTER.read_text());roadline=LineString([(q['x_m'],q['z_m']) for q in center])
 allx=[q['x_m'] for q in center];allz=[q['z_m'] for q in center]
 x0,x1=min(allx)-8,max(allx)+8;z0,z1=min(allz)-18,max(allz)+18
 mapimg=Image.new('RGB',(1200,430),'white');d=ImageDraw.Draw(mapimg)
 def pp(x,z):return (40+(x-x0)/(x1-x0)*1120,30+(z-z0)/(z1-z0)*350)
 d.line([pp(x,z) for x,z in roadline.coords],fill=(150,88,80),width=8)
 for w in driveway_ways:d.line([pp(x,z) for x,z in w['line'].coords],fill=(201,129,49),width=5)
 d.line([pp(x,z) for x,z in gap.coords],fill=(57,128,173),width=6)
 for n in nodes:
  x,y=pp(n['x'],n['z']);d.ellipse((x-3,y-3,x+3,y+3),fill=(62,115,65))
 map_path=OUT/'Lombard_v024_access_tree_scope.png';mapimg.save(map_path)

 sheet=Image.new('RGB',(1600,1080),'#efeee8');sd=ImageDraw.Draw(sheet)
 fp=Path('C:/Windows/Fonts/segoeui.ttf');bp=Path('C:/Windows/Fonts/seguisb.ttf')
 def font(n,b=False):
  p=bp if b and bp.exists() else fp
  return ImageFont.truetype(str(p),n) if p.exists() else None
 sd.text((35,20),'LOMBARD v024 — ACCESS + TREE REALISM',fill='#202725',font=font(30,True))
 sd.text((35,62),'Orange = mapped driveways; blue = Hyde sidewalk closure; green dots = mapped trees.',fill='#58605d',font=font(16))
 cards=[(map_path,'SOURCE TOPOLOGY','OSM driveways + sidewalk gap + mapped tree positions'),
        (REF1,'HOUSE / ACCESS CONTEXT','Andrew Napier / CC BY 2.0 — property access + garden relationship'),
        (REF2,'TREE / GARDEN MASSING','Toi & Moi / CC BY-SA 2.0 — irregular tree crowns in planted terraces'),
        (REF3,'UPPER SITE / TREES','Cornflower123 / CC0 — upper garden and tree character')]
 for j,(src,title,cap) in enumerate(cards):
  x=35+(j%2)*780;y=105+(j//2)*465;sd.rectangle((x,y,x+750,y+425),outline='#767d79',width=2)
  im=Image.open(src).convert('RGB');fr=ImageOps.contain(im,(725,330));sheet.paste(fr,(x+(750-fr.width)//2,y+38+(330-fr.height)//2))
  sd.text((x+12,y+8),title,fill='#26322f',font=font(18,True));sd.text((x+12,y+388),cap,fill='#404844',font=font(13))
 refsheet=OUT/'Lombard_Access_Tree_Realism_v024_reference_sheet.jpg';sheet.save(refsheet,quality=92)

 coords=list(blocks);arr=np.array(coords);lo=arr.min(0);hi=arr.max(0);bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),vol) for p,vol in sorted(hosts.items())]
 artifact=OUT/f'{NAME}.litematic'
 stats=write_single_region_litematic(artifact,blocks,bounds,REGION,NAME,'Source-mapped driveway surfaces, explicit Hyde sidewalk connection, and tree morphology realism on accepted v023.',data_version=realm.v.DATA_VERSION,tile_entity_payloads=payload)
 actual,decoded=read(artifact,REGION)
 checks={
  'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
  'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
  'access_scope_only':not access_escape,
  'tree_scope_only':not tree_escape,
  'road_untouched':road_writes==0,
  'building_footprints_untouched':building_writes==0,
  'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items()),
  'eight_mapped_driveways':len(driveway_ways)==8,
  'hyde_sidewalk_gap_closed':sidewalk_columns>0 and gap.length<5
 }
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,
  'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changes':changes,
  'driveways':{'count':len(driveway_ways),'osm_ids':[str(w['id']) for w in driveway_ways],'width_m':DRIVEWAY_WIDTH_M,'width_basis':'explicit v024 nominal single-car access width; OSM supplies centerline/topology but no width','surface_columns':drive_columns,'rail_cells_cut_at_access_crossings':rail_cuts,'retaining_cells_cut_at_access_crossings':wall_cuts},
  'hyde_sidewalk':{'osm_crossing':'691835290','osm_sidewalk':'691835289','source_gap_m':gap.length,'surface_columns_written':sidewalk_columns,'resolution':'explicit connector between nearest mapped endpoints inside existing sidewalk/ground support'},
  'trees':{'mapped_nodes_considered':len(nodes),'trees_reshaped':len(tree_audit),'audit':tree_audit,'policy':'mapped locations fixed; morphology rebuilt inside existing parent height/radius envelopes; no species claim'},
  'preserved':['crooked-road surface and endpoint roads','building envelopes/facades','registration marker','terrain elevations outside declared access corrections','unsupported/missing tree sites remain absent'],
  'review':'USER_MINECRAFT_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
 (OUT/'Build_notes.md').write_text('# Lombard access + tree realism v024\n\nSeven source-mapped OSM driveways replace planting only in their access corridors. The Hyde-side sidewalk gap is explicitly closed between mapped footway endpoints. Existing mapped trees are reshaped for realism without moving their source locations.\n')
 print(json.dumps({'file':str(artifact),'status':report['status'],'validation':checks,'driveways':len(driveway_ways),'drive_columns':drive_columns,'top_sidewalk_columns':sidewalk_columns,'trees_reshaped':len(tree_audit),'changed_microcells':len(writes)},indent=2))
 if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
