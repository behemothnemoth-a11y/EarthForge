"""Non-photoreal, reference-led landscape form pass over Lombard v018."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape,Point
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_public_realm_v1 as v
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as parent
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
OUT=v.v.PROJECT/'outputs/landscape_realism_v019';NAME='Lombard_Landscape_Realism_Astra_v019';REGION='LOMBARD_LANDSCAPE_REALISM_V019'
LEAVES=['astra_microblocks:rgb_365b36','astra_microblocks:rgb_40613a','astra_microblocks:rgb_4c6b40','astra_microblocks:rgb_587343']
SHRUB=['astra_microblocks:rgb_41653b','astra_microblocks:rgb_4b703d','astra_microblocks:rgb_587944']
BLOOM=['astra_microblocks:rgb_c6b8c7','astra_microblocks:rgb_b58fa7','astra_microblocks:rgb_d8d4c2','astra_microblocks:rgb_b6b7d0']
def main():
 OUT.mkdir(parents=True,exist_ok=True);path=parent.OUT/f'{parent.NAME}.litematic';blocks,hosts=read(path,parent.REGION);original_blocks=blocks.copy();vanilla={p:s for p,s in blocks.items() if p not in hosts};backup={};original_hash={p:hash((vv.original,tuple(vv.cells))) for p,vv in hosts.items()}
 def setcell(x,y,z,mat):
  pos,i=position(x,y,z)
  if pos in vanilla:return False
  if pos not in backup:backup[pos]=(hosts[pos].original,hosts[pos].cells.copy()) if pos in hosts else None
  if pos not in hosts:hosts[pos]=MicroVolume('minecraft:bricks');blocks[pos]=HOST_STATE
  hosts[pos].cells[i]=mat;return True
 cache=np.load(v.OUT/'surface_preview.npz');tops={tuple(map(int,k)):int(t) for k,t in zip(cache['xz'],cache['top'])}
 plan=json.loads((v.OUT/'public_realm_plan.geojson').read_text());bed=shape(next(f['geometry'] for f in plan['features'] if f['properties']['layer']=='planting_beds'))
 # Only the original illustrative bed plants may be removed, never substrate,
 # mapped hedge borders, paths, hardscape or building envelopes.
 gx,gz=v.raster(bed);removed=0;allowed_bed=set()
 print('Replacing flat bed patches with rounded clustered shrubs.',flush=True)
 for x,z in zip(gx,gz):
  x,z=int(x),int(z);base=tops.get((x,z))
  if base is None:continue
  allowed_bed.add((x,z))
  for y in range(base,base+8):
   p,i=position(x,y,z);vv=hosts.get(p)
   if vv and vv.cells[i] in {v.HEDGE2,*v.FLOWERS}:setcell(x,y,z,None);removed+=1
 rng=np.random.default_rng(19019);centers=[];radii=[];heights=[];xmin,zmin,xmax,zmax=bed.bounds
 for _ in range(12000):
  x,z=rng.uniform(xmin,xmax),rng.uniform(zmin,zmax)
  if not bed.contains(Point(x,z)):continue
  if centers and np.min(np.sum((np.array(centers)-[x,z])**2,axis=1))<.62**2:continue
  centers.append([x,z]);radii.append(float(rng.uniform(.46,.68)));heights.append(float(rng.uniform(.42,.78)))
 tree=cKDTree(centers);dist,idx=tree.query(np.c_[(gx+.5)/16,(gz+.5)/16]);added=0
 for x,z,d,i in zip(gx,gz,dist,idx):
  x,z=int(x),int(z);base=tops.get((x,z));radius=radii[i]
  if base is None or (x,z) not in allowed_bed or d>radius:continue
  texture=math.sin(x*.51+z*.17)+math.sin(z*.43-x*.11)
  h=max(2,round((.10+heights[i]*math.sqrt(max(0,1-(d/radius)**2)))*16+texture*.5))
  flower_hash=((x//2)*73856093)^((z//2)*19349663)^(int(i)*83492791)
  bloom=flower_hash%13<4 and d<radius*.94
  h=min(h,14)
  for y in range(base,base+h+(2 if bloom else 0)):
   pos,k=position(x,y,z);existing=hosts.get(pos);old=existing.cells[k] if existing else None
   if old is not None:continue
   m=BLOOM[(i+flower_hash//13)%len(BLOOM)] if bloom and y>=base+h-1 else SHRUB[(x//3+z//3+y//3+i)%len(SHRUB)]
   added+=setcell(x,y,z,m)
 # Preserve mapped tree locations and trunks. Slightly break the outer blocky
 # crown surfaces and vary leaf masses within the original crown envelope.
 recolored=thinned=0;leafset={v.LEAF,v.LEAF2}
 print('Refining existing crown edges; trunks and clearance remain fixed.',flush=True)
 for pos,vol in list(hosts.items()):
  hx,hy,hz=pos
  for i,m in enumerate(vol.cells):
   if m not in leafset:continue
   x=hx*16+(i&15)-480;z=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
   # Classify original crown boundary against an immutable per-host snapshot.
   def oldcell(a,b,c):
    pp,ii=position(a,b,c)
    if pp in backup:
     q=backup[pp];return q[1][ii] if q else None
    q=hosts.get(pp);return q.cells[ii] if q else None
   boundary=any(oldcell(x+dx,y+dy,z+dz) not in leafset for dx,dy,dz in [(2,0,0),(-2,0,0),(0,2,0),(0,-2,0),(0,0,2),(0,0,-2)])
   noise=math.sin(x*.71+y*.31)+math.sin(z*.57-y*.41)
   if boundary and noise>1.23:setcell(x,y,z,None);thinned+=1
   else:setcell(x,y,z,LEAVES[((x//5)*3+z//5+y//4)%len(LEAVES)]);recolored+=1
 empty=[p for p,vv in hosts.items() if not any(m is not None for m in vv.cells)]
 for p in empty:del hosts[p];del blocks[p]
 # Changed original cells must be botanical materials; additions must stay in
 # mapped beds above their original surface, within the declared 1m envelope.
 protected=0;unexpected=[];changed=0
 for pos,record in backup.items():
  old=record[1] if record else [None]*4096;new=hosts[pos].cells if pos in hosts else [None]*4096;hx,hy,hz=pos
  for i,(a,b) in enumerate(zip(old,new)):
   if a==b:continue
   changed+=1;x=hx*16+(i&15)-480;z=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
   permitted=(a in leafset) or ((x,z) in allowed_bed and tops[(x,z)]<=y<tops[(x,z)]+16 and a in {None,v.HEDGE2,*v.FLOWERS})
   if not permitted:unexpected.append([x,y,z,a,b])
 if unexpected:raise RuntimeError('Change escaped botanical scope '+str(unexpected[:3]))
 coords=np.array(list(blocks));old=np.array(list(original_blocks));lo=np.minimum(coords.min(0),old.min(0));hi=np.maximum(coords.max(0),old.max(0));bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
 payload=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),vol) for (x,y,z),vol in sorted(hosts.items())]
 artifact=OUT/f'{NAME}.litematic';stats=write_single_region_litematic(artifact,blocks,bounds,REGION,NAME,'Rounded shrub and flower clusters plus refined existing tree crowns; simple colors, no photo textures; v018 buildings and hardscape preserved.',data_version=v.v.DATA_VERSION,tile_entity_payloads=payload)
 print('Exported; checking exact readback and non-landscape preservation.',flush=True)
 actual,decoded=read(artifact,REGION)
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==vol.cells and decoded[p].original==vol.original for p,vol in hosts.items()),'unchanged_hosts_preserved':all(p in decoded and hash((decoded[p].original,tuple(decoded[p].cells)))==h for p,h in original_hash.items() if p not in backup),'only_approved_botanical_cells_changed':not unexpected,'vanilla_and_marker_preserved':all(actual.get(p)==s for p,s in vanilla.items())}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'removed_flat_plant_cells':removed,'shrub_cluster_count':len(centers),'plant_cells_added':added,'crown_cells_recolored':recolored,'outer_crown_cells_thinned':thinned,'changed_microcells':changed,'preserved':['all building masses','road and curbs','stairs paths rails and crossings','ground surfaces','mapped hedge borders','tree trunks and locations','registration'],'reference':{'url':'https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064478253).jpg','credit':'Andrew Napier','license':'CC BY 2.0','interpretation':'Rounded flowering shrub masses inside clipped hedge beds; crowns with varied green masses. Individual plant positions, sizes, season and colors are illustrative, not surveyed.'},'not_addressed':['building architectural detail and real roof forms','unsupported outer terrain gaps','raised paint overlays','site retaining/entrance connections'],'review':'LANDSCAPE_REALISM_V019_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/f'{NAME}_placement.json').write_text((parent.OUT/f'{parent.NAME}_placement.json').read_text());print(json.dumps(report,indent=2))
 if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
