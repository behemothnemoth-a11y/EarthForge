"""Evidence-scoped realism: connected blooms, flush paint, first photo-led group."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape,Point,LineString
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_landscape_v019 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_public_realm_v1 as v
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
from pipeline.terrain.ground_support import interpolate_ground
OUT=v.v.PROJECT/'outputs/realism_v020';NAME='Lombard_Realism_Astra_v020';REGION='LOMBARD_REALISM_V020'
LEAVES=parent.LEAVES;SHRUB=parent.SHRUB;BLOOM=parent.BLOOM
def rgb(s):return 'astra_microblocks:rgb_'+s

def main():
 OUT.mkdir(parents=True,exist_ok=True);source=parent.OUT/f'{parent.NAME}.litematic';blocks,hosts=read(source,parent.REGION)
 original_blocks=blocks.copy();vanilla={p:s for p,s in blocks.items() if p not in hosts};hashes={p:hash((vv.original,tuple(vv.cells))) for p,vv in hosts.items()};backup={};categories={};changes={};bloom_cells=set()
 def get(x,y,z):
  p,i=position(int(x),int(y),int(z));vv=hosts.get(p);return vv.cells[i] if vv else None
 def put(x,y,z,mat,category):
  p,i=position(int(x),int(y),int(z))
  if p in vanilla:return False
  old=hosts[p].cells[i] if p in hosts else None
  if old==mat:return False
  if p not in backup:backup[p]=(hosts[p].original,hosts[p].cells.copy()) if p in hosts else None
  if p not in hosts:hosts[p]=MicroVolume();blocks[p]=HOST_STATE
  hosts[p].cells[i]=mat;categories[(p,i)]=category;changes[category]=changes.get(category,0)+1
  if category=='planting':
   if mat in BLOOM:bloom_cells.add((int(x),int(y),int(z)))
   else:bloom_cells.discard((int(x),int(y),int(z)))
  return True
 cache=np.load(v.OUT/'surface_preview.npz');tops={tuple(map(int,k)):int(t) for k,t in zip(cache['xz'],cache['top'])}
 plan=json.loads((v.OUT/'public_realm_plan.geojson').read_text());layers={f['properties']['layer']:shape(f['geometry']) for f in plan['features'] if f['properties']['layer']!='hedge'};bed=layers['planting_beds']
 print('Rebuilding flower heads as connected round volumes.',flush=True)
 gx,gz=v.raster(bed);allowed=set(zip(map(int,gx),map(int,gz)));botanical=set(SHRUB+BLOOM+[v.HEDGE2]+v.FLOWERS)
 for x,z in allowed:
  base=tops.get((x,z))
  if base is None:continue
  for y in range(base,base+16):
   if get(x,y,z) in botanical:put(x,y,z,None,'planting')
 rng=np.random.default_rng(20020);centers=[];radii=[];heights=[];xmin,zmin,xmax,zmax=bed.bounds
 for _ in range(12000):
  x,z=rng.uniform(xmin,xmax),rng.uniform(zmin,zmax)
  if not bed.contains(Point(x,z)):continue
  if centers and np.min(np.sum((np.array(centers)-[x,z])**2,axis=1))<.74**2:continue
  centers.append([x,z]);radii.append(float(rng.uniform(.58,.78)));heights.append(float(rng.uniform(.40,.62)))
 tree=cKDTree(centers);dist,idx=tree.query(np.c_[(gx+.5)/16,(gz+.5)/16]);leaf_top={}
 for x,z,d,j in zip(gx,gz,dist,idx):
  x,z=int(x),int(z);base=tops.get((x,z))
  if base is None or d>radii[j]:continue
  h=min(11,max(2,round((.10+heights[j]*math.sqrt(max(0,1-(d/radii[j])**2)))*16)))
  leaf_top[(x,z)]=base+h
  for y in range(base,base+h):
   if get(x,y,z) is None:put(x,y,z,SHRUB[(j+x//6+z//6)%len(SHRUB)],'planting')
 # Sparse 0.375-0.5m rounded heads, each a connected 3D ellipsoid,
 # partly embedded into leaves. No per-column random pale tips.
 heads=0;head_centers=[]
 for j,(cx,cz) in enumerate(centers):
  for n in range(2 if j%3 else 3):
   angle=float(rng.uniform(0,2*math.pi));rr=float(rng.uniform(.08,radii[j]*.65));x=round((cx+rr*math.cos(angle))*16);z=round((cz+rr*math.sin(angle))*16)
   if (x,z) not in leaf_top:continue
   r=3 if (j+n)%3 else 4;y=leaf_top[(x,z)]-1
   if any((x-a)**2+(z-c)**2<36 for a,b,c in head_centers[-12:]):continue
   written=0
   for dx in range(-r,r+1):
    for dz in range(-r,r+1):
     key=(x+dx,z+dz);base=tops.get(key)
     if key not in allowed or base is None:continue
     for dy in range(-2,3):
      if (dx*dx+dz*dz)/(r*r)+(dy*dy)/6.25>1:continue
      yy=y+dy
      if base<=yy<base+16 and get(key[0],yy,key[1]) in botanical|{None}:written+=put(key[0],yy,key[1],BLOOM[(j+n)%4],'planting')
   if written:heads+=1;head_centers.append((x,y,z))
 # Terrain clipping can leave tiny colored flecks. Remove only components
 # smaller than eight cells, retaining their underlying leafy support.
 remaining=bloom_cells.copy();tiny_removed=0
 while remaining:
  seed=remaining.pop();component=[seed];queue=[seed]
  while queue:
   x,y,z=queue.pop()
   for q in [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1)]:
    if q in remaining:remaining.remove(q);component.append(q);queue.append(q)
  if len(component)<8:
   for x,y,z in component:put(x,y,z,SHRUB[0],'planting');tiny_removed+=1
 print('Making crossing paint flush; accepted road occupancy stays fixed.',flush=True)
 pavement={v.v.ROAD_BASE,*v.v.BRICK_COLORS,v.v.JOINT,v.v.HYDE_TOP,v.v.HYDE_BASE,v.v.LEAV_TOP,v.v.LEAV_BASE,rgb('686661'),rgb('5d5c59')}
 paint=[]
 for (hx,hy,hz),vv in list(hosts.items()):
  for i,m in enumerate(vv.cells):
   if m!=v.WHITE:continue
   x=hx*16+(i&15)-480;z=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
   if get(x,y-1,z) in pavement and get(x,y+1,z) is None:paint.append((x,y,z))
 for x,y,z in paint:put(x,y,z,None,'paint_overlay_removal');put(x,y-1,z,v.WHITE,'paint_surface_recolor')
 print('Breaking color banding without changing accepted ground heights.',flush=True)
 greens=[rgb('63764a'),rgb('687a4e'),rgb('607348'),rgb('6b7c50')];ground_count=0
 for (x,z),top,mat in zip(cache['xz'],cache['top'],cache['material']):
  x,z,top=int(x),int(z),int(top)
  if mat!=v.GREEN or get(x,top-1,z)!=v.GREEN:continue
  n=math.sin(x*.09+z*.04)+math.sin(z*.13-x*.03)
  ground_count+=put(x,top-1,z,greens[min(3,max(0,int((n+2)*.999)))],'ground_color_only')
 print('Resampling existing outer ground columns from original LiDAR support.',flush=True)
 context_columns={};context_materials={buildings.GROUND,buildings.BASE}
 for (hx,hy,hz),vv in list(hosts.items()):
  for i,m in enumerate(vv.cells):
   if m not in context_materials:continue
   x=hx*16+(i&15)-480;z=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
   context_columns.setdefault((x,z),[]).append(y)
 keys=list(context_columns);raw=np.load(v.v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz');mask=raw['classification']==2
 query=(np.array(keys)+.5)/16
 vals,support=interpolate_ground(np.c_[raw['x'][mask],raw['z'][mask]],raw['elev'][mask],query,max_distance_m=5,max_triangle_edge_m=20)
 zero=float(json.loads(v.v.CENTER.read_text())[0]['elev_navd88_m']);deltas=[];context_written=0
 for (x,z),elev,ok in zip(keys,vals,support['supported']):
  if not ok:continue
  top=round((elev-zero)*16);deltas.append((top-(max(context_columns[(x,z)])+1))/16)
  for y in context_columns[(x,z)]:put(x,y,z,None,'context_ground_resampling')
  for y in range(top-3,top):
   if get(x,y,z) is None:context_written+=put(x,y,z,buildings.GROUND if y==top-1 else buildings.BASE,'context_ground_resampling')
 context_audit={'columns_examined':len(keys),'supported_resampled':int(support['supported'].sum()),'unsupported_preserved':int((~support['supported']).sum()),'old_sampling_m':.25,'new_sampling_m':.0625,'source':'Original class-2 LiDAR TIN; 5m nearest / 20m triangle gates','max_absolute_height_change_m':float(np.max(np.abs(deltas))),'new_scope_or_boundary_walls':False}
 # First connected photo group: 1040's number is visible in reference 021.
 # Neighbor identity is inferred from adjacency, not directly read in image.
 specs=[('201006.0032105','1040 Lombard','blue_framed',rgb('a9cbd6'),rgb('293f48')),
        ('201006.0038369','4 Montclair / neighbor west of 1040','mansard',rgb('c9b788'),rgb('414846'))]
 envelopes=json.loads((buildings.OUT/'building_envelopes.geojson').read_text());byid={f['properties']['id']:f for f in envelopes['features']};zero=float(json.loads(v.v.CENTER.read_text())[0]['elev_navd88_m']);building_audit=[]
 for identity,address,style,body,trim in specs:
  print('Photo group',address,flush=True);f=byid[identity];geom=shape(f['geometry']);prop=f['properties'];floor=round((prop['ground_min_navd88_m']-zero)*16);cap=round((prop['median_first_return_navd88_m']-zero)*16)
  poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,'geoms') else geom;coords=list(poly.exterior.coords)
  # Long southern edge faces Lombard, confirmed against mapped footprint.
  edges=[(np.array(a),np.array(b)) for a,b in zip(coords,coords[1:]) if np.linalg.norm(np.array(b)-a)>3]
  pa,pb=max(edges,key=lambda ab:((ab[0][1]+ab[1][1])/2));pa,pb=sorted([pa,pb],key=lambda q:q[0]);delta=pb-pa;length=np.linalg.norm(delta);uvec=delta/length;normal=np.array([-uvec[1],uvec[0]])
  gx1,gz1=v.raster(geom);wallm=set(buildings.WALLS);roof_start=cap-40
  # Recolor existing neutral walls; opening rhythm only on photo-visible front.
  for x,z in zip(gx1,gz1):
   x,z=int(x),int(z);pt=np.array([(x+.5)/16,(z+.5)/16]);uv=float((pt-pa)@uvec)/length;depth=float((pt-pa)@normal);front=abs(depth)<.24 and 0<=uv<=1
   for y in range(floor,cap):
    old=get(x,y,z)
    if old not in wallm:continue
    mat=body;yy=(y-floor)/16;h=(cap-floor)/16
    if front:
     if style=='blue_framed':
      story=h/4;fy=yy%story
      panel=(uv*3)%1
      if min(panel,1-panel)<.045 or fy<.125:mat=trim
      elif yy<2.4 and .22<uv<.86:mat=rgb('95c7d4') if int(yy*5)%5 else trim
      elif .17<panel<.84 and .65<fy<story-.45:mat=rgb('799da5')
      if yy>h-2.6:mat=trim if min(panel,1-panel)<.05 or fy<.15 else rgb('8cb3ba')
     else:
      if yy<2.65 and .40<uv<.59:mat=rgb('303d39')
      elif 3.9<yy<6.2 or 7.0<yy<9.2:
       fwin=(uv*3)%1
       if .25<fwin<.76:mat=trim if fwin<.30 or fwin>.71 or abs(yy-4)<.15 else rgb('8faaa8')
      if y>=roof_start:continue
    put(x,y,z,mat,'building_group')
  if style=='mansard':
   # Replace the upper neutral envelope with inward-sloping roof surfaces,
   # entirely inside the previous footprint and top elevation. Roof dimensions
   # are provisional photo interpretation; LiDAR peak is not used as a roof.
   for x,z in zip(gx1,gz1):
    x,z=int(x),int(z);p=Point((x+.5)/16,(z+.5)/16);distance=poly.boundary.distance(p);top=min(cap-1,roof_start+round(distance*24))
    for y in range(roof_start,cap):
     if get(x,y,z) in wallm|{body,buildings.ROOF}:put(x,y,z,None,'building_group')
    for y in range(top-1,top+1):
     if get(x,y,z) is None:put(x,y,z,rgb('727b79'),'building_group')
   # Paired dormer impression on the photographed front slope.
   for frac in [.39,.61]:
    for du in np.arange(-.42,.43,.0625):
     pt=pa+uvec*(length*frac+du)-normal*.60;x,z=np.floor(pt*16).astype(int)
     for y in range(roof_start+10,roof_start+28):
      if geom.covers(Point((x+.5)/16,(z+.5)/16)) and get(x,y,z) in {None,rgb('727b79')}:put(x,y,z,trim if abs(du)>.32 or y in [roof_start+10,roof_start+27] else rgb('98b0ac'),'building_group')
  # Entry apron color follows existing supported ground at the visible front;
  # no synthetic terrace level, retaining wall or new property boundary.
  apron=LineString([pa,pb]).buffer(1.25,cap_style=2).difference(geom).difference(layers['pedestrian']).difference(layers['road']);apron_cells=0
  for (x,z),t in tops.items():
   if not apron.covers(Point((x+.5)/16,(z+.5)/16)):continue
   if get(x,t-1,z) in {v.GREEN,*greens}:apron_cells+=put(x,t-1,z,rgb('a39e92'),'entry_apron_color')
  building_audit.append({'id':identity,'address':address,'style':style,'front_edge_xz':[pa.tolist(),pb.tolist()],'photo':'Lombard_Street_(10064415846).jpg','identity_confidence':'visible 1040 garage number' if style=='blue_framed' else 'adjacency match; address association provisional','dimensions':'mapped footprint and existing envelope; subdivisions and roof slopes provisional photo interpretation','entry_apron_recolored_cells':apron_cells,'entry_geometry':'existing ground retained; access levels require closer source evidence'})
 for p in list(hosts):
  if not any(hosts[p].cells):del hosts[p];blocks.pop(p,None)
 print('Auditing accepted v015 road/curb occupancy and changes.',flush=True)
 _,locked=read(v.PARENT,v.PARENT_REGION);_,accepted=read(v.v.V009,'LOMBARD_CURB_ASTRA_V009');road_checked=0;road_missing=0;road_material=0;unexpected=[]
 # Only the v015 accepted pavement/curb cells (not its old terrain) are locked.
 protected_materials=pavement|{v.v.CURB_MATERIAL}
 for p,vol in locked.items():
  for i,m in enumerate(vol.cells):
   if m is None or not (m in v.ASPHALT or (p in accepted and accepted[p].cells[i] is not None)):continue
   road_checked+=1;new=hosts[p].cells[i] if p in hosts else None
   if new is None:road_missing+=1
   if new!=m:
    road_material+=1
    if categories.get((p,i))!='paint_surface_recolor':unexpected.append([p,i,m,new])
 del locked,accepted
 for p,record in backup.items():
  old=record[1] if record else [None]*4096;new=hosts[p].cells if p in hosts else [None]*4096
  for i,(a,b) in enumerate(zip(old,new)):
   if a!=b and (p,i) not in categories:unexpected.append([p,i,a,b])
 assert not unexpected,unexpected[:3]
 xyz=np.array(list(blocks));oldxyz=np.array(list(original_blocks));lo=np.minimum(xyz.min(0),oldxyz.min(0));hi=np.maximum(xyz.max(0),oldxyz.max(0));bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,tuple(p[k]-lo[k] for k in range(3)),vv) for p,vv in sorted(hosts.items())]
 path=OUT/f'{NAME}.litematic';stats=write_single_region_litematic(path,blocks,bounds,REGION,NAME,'Connected bloom clusters, flush crossings, ground color variation and first photo-led two-building group. Accepted road occupancy and public access protected; unsourced context gaps remain.',data_version=v.v.DATA_VERSION,tile_entity_payloads=payload)
 print('Checking exact Litematica and Astra readback.',flush=True);actual,decoded=read(path,REGION)
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==vv.cells and decoded[p].original==vv.original for p,vv in hosts.items()),'untouched_hosts_preserved':all(p in decoded and hash((decoded[p].original,tuple(decoded[p].cells)))==h for p,h in hashes.items() if p not in backup),'vanilla_and_marker_preserved':all(actual.get(p)==s for p,s in vanilla.items()),'accepted_pavement_occupancy_preserved':road_missing==0,'accepted_material_changes_only_flush_paint':not unexpected,'paint_has_no_added_layer':all(get(x,y,z) is None and get(x,y-1,z)==v.WHITE for x,y,z in paint)}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changes':changes,'round_flower_heads':heads,'shrubs':len(centers),'flush_paint_columns':len(paint),'accepted_road_cells_checked':road_checked,'accepted_road_cells_missing':road_missing,'accepted_material_recolors':road_material,'first_building_group':building_audit,'ground_bands':{'finding':'v017 surface quantization on sloped ground; geometry unchanged here','resolution_m':.0625,'action':'non-horizontal low-contrast color variation; larger connected planting masses','unsupported_outer_ground':'No fabricated fill or boundary walls; unresolved v018 support gaps retained.'},'hyde_red_endpoint':{'finding':'Part of accepted v009 footprint; available photos do not establish exact replacement edge at Hyde','action':'Preserved pending a directly registered intersection reference'},'remaining':['unsourced patios and retaining levels','unsupported outer ground gaps','other building facades','exact roof and entry measurements','Hyde red apron material boundary'],'review':'USER_FLYAROUND_REQUIRED'}
 report['outer_ground']=context_audit
 report['tiny_bloom_cells_replaced_with_leaves']=tiny_removed
 report['source_files']=[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [v.v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz',buildings.OUT/'building_envelopes.geojson',v.OUT/'surface_preview.npz']]
 report['photo_sources']={'urls':['https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064415846).jpg','https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064478253).jpg'],'credit':'Andrew Napier','license':'CC BY 2.0','raw_images_embedded':False}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/f'{NAME}_placement.json').write_text((parent.OUT/f'{parent.NAME}_placement.json').read_text());print(json.dumps({'status':report['status'],'changes':changes,'checks':checks},indent=2))
 if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
