"""Source-footprint neighborhood blockout around immutable Lombard v017."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from shapely.geometry import shape,Point
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_public_realm_v1 as prior
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read
from pipeline.terrain.ground_support import interpolate_ground
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
from pipeline.microblocks.astra_microblock_codec import tile_entity_payload
OUT=prior.v.PROJECT/'outputs/neighborhood_blockout_v018'
NAME='Lombard_Neighborhood_Blockout_Astra_v018';REGION='LOMBARD_NEIGHBORHOOD_BLOCKOUT_V018'
WALLS=['astra_microblocks:rgb_c8c4b9','astra_microblocks:rgb_b8b4aa','astra_microblocks:rgb_d3cbb9','astra_microblocks:rgb_bfc3bd']
ROOF='astra_microblocks:rgb_777b79';GROUND='astra_microblocks:rgb_85816b';BASE='astra_microblocks:rgb_777563'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 parent_path=prior.OUT/f'{prior.NAME}.litematic';blocks,parent=read(parent_path,prior.REGION)
 builder=prior.Builder({p:s for p,s in blocks.items() if p not in parent},parent)
 city_path=prior.v.CITY;city=json.loads(city_path.read_text());truth_path=prior.context.BUILDINGS;truth=json.loads(truth_path.read_text());ids={b['sf16_bldgid'] for b in truth['buildings']};by_id={b['sf16_bldgid']:b for b in truth['buildings']}
 plan=json.loads((prior.OUT/'public_realm_plan.geojson').read_text());layers={f['properties']['layer']:shape(f['geometry']) for f in plan['features'] if f['properties']['layer']!='hedge'}
 core=layers['scope'];protected=unary_union([layers['road'],layers['pedestrian']]).buffer(.25)
 selected=[b for b in city['buildings'] if b['properties']['sf16_bldgid'] in ids or shape(b['geometry']).distance(core)<=8]
 all_buildings=unary_union([shape(b['geometry']) for b in city['buildings']])
 selected_geom=unary_union([shape(b['geometry']) for b in selected])
 # The 3m halo is a context sampling extent, never a property boundary or wall.
 context=selected_geom.buffer(3,join_style=2).difference(all_buildings).difference(core)
 raw_path=prior.v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz';raw=np.load(raw_path);mask=raw['classification']==2;points=np.c_[raw['x'][mask],raw['z'][mask]];elev=raw['elev'][mask]
 zero=float(json.loads(prior.v.CENTER.read_text())[0]['elev_navd88_m'])
 print('Selected',len(selected),'city footprint components. Sampling context ground.',flush=True)
 # Quarter-meter samples, four-microcell wide structural shells. Unsupported
 # exterior cells stay absent with explicit QA; no recursive gap filling.
 xmin,zmin,xmax,zmax=context.bounds;xx,zz=np.meshgrid(np.arange(math.floor(xmin*4),math.ceil(xmax*4)),np.arange(math.floor(zmin*4),math.ceil(zmax*4)))
 from shapely import contains_xy
 keep=contains_xy(context,(xx+.5)/4,(zz+.5)/4);qx,qz=xx[keep],zz[keep]
 vals,support=interpolate_ground(points,elev,np.c_[(qx+.5)/4,(qz+.5)/4],max_distance_m=5,max_triangle_edge_m=20)
 ground_count=0
 for x,z,h,ok in zip(qx,qz,vals,support['supported']):
  if not ok:continue
  y=round((h-zero)*16)
  for dx in range(4):
   for dz in range(4):
    gx,gz=int(x*4+dx),int(z*4+dz)
    if not context.covers(Point((gx+.5)/16,(gz+.5)/16)):continue
    for yy in range(y-3,y):builder.set_micro_local(gx,yy,gz,GROUND if yy==y-1 else BASE)
    ground_count+=1
 audit=[];out_features=[]
 for n,b in enumerate(selected):
  prop=b['properties'];identity=prop['sf16_bldgid'];source=shape(b['geometry']);geom=source.difference(protected);removed=source.area-geom.area
  base=float(prop['gnd_min_m']);roof=float(prop['median_1st_m']);height=float(prop['hgt_median_m']);peak=float(prop['peak_1st_m'])
  if not all(math.isfinite(v) for v in [base,roof,height]) or roof<=base:raise ValueError('Invalid source building height '+identity)
  floor=round((base-zero)*16);cap=round((roof-zero)*16);wall=geom.difference(geom.buffer(-.1875,join_style=2))
  before=builder.skipped;gx,gz=prior.raster(wall)
  for x,z in zip(gx,gz):
   for y in range(floor,cap):builder.set_micro_local(x,y,z,WALLS[n%len(WALLS)])
  gx,gz=prior.raster(geom)
  for x,z in zip(gx,gz):
   for y in range(cap-2,cap):builder.set_micro_local(x,y,z,ROOF)
  rec=by_id.get(identity,{})
  audit.append({'id':identity,'address':rec.get('address'),'street':rec.get('street'),'source_footprint_area_m2':source.area,'modeled_footprint_area_m2':geom.area,'public_clearance_clip_m2':removed,'ground_min_navd88_m':base,'median_first_return_navd88_m':roof,'source_median_height_m':height,'source_peak_navd88_m':peak,'source_height_std_m':float(prop['hgt_stdcm'])/100,'skipped_parent_overlap_writes':builder.skipped-before,'interpretation':'Flat height-envelope cap, not inferred roof shape; neutral palette does not assert facade colors. First-return statistics may include vegetation.'})
  out_features.append({'type':'Feature','properties':audit[-1],'geometry':geom.__geo_interface__})
  print('Building',n+1,'/',len(selected),identity,flush=True)
 # Registration/pad vanilla blocks are immutable too. Remove any new host
 # occupying those positions before serialization.
 for pos,state in blocks.items():
  if pos not in parent:
   builder.hosts.pop(pos,None);builder.blocks[pos]=state
 builder.prune_empty_hosts();coords=np.array(list(builder.blocks));old=np.array(list(blocks));lo=np.minimum(coords.min(0),old.min(0));hi=np.maximum(coords.max(0),old.max(0));bounds=(*lo.tolist(),*hi.tolist())
 writer=NBTWriter();payload=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),vol) for (x,y,z),vol in sorted(builder.hosts.items())]
 path=OUT/f'{NAME}.litematic';stats=write_single_region_litematic(path,builder.blocks,bounds,REGION,NAME,'Neutral city-footprint building envelopes and original-ground context around preserved v017; roof forms and exterior architectural details unverified.',data_version=prior.v.DATA_VERSION,tile_entity_payloads=payload)
 print('Exported; exact readback and full parent preservation audit.',flush=True)
 actual,decoded=read(path,REGION);checked=mismatches=0
 for pos,vol in parent.items():
  new=decoded.get(pos)
  for i,m in enumerate(vol.cells):
   if m is not None:checked+=1;mismatches+=new is None or new.cells[i]!=m
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in builder.blocks.items()},'exact_astra':set(decoded)==set(builder.hosts) and all(decoded[p].cells==v.cells and decoded[p].original==v.original for p,v in builder.hosts.items()),'all_parent_occupied_microcells_preserved':mismatches==0,'parent_vanilla_preserved':all(actual.get(p)==s for p,s in blocks.items() if p not in parent),'marker':actual.get((0,-1,0))==prior.v.MARKER}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_microcells_checked':checked,'parent_microcell_mismatches':mismatches,'buildings':audit,'context':{'selection':'Existing 29-component frontage selection plus city footprints within 8m of the v017 scope','ground_halo_m':3,'halo_is_property_boundary':False,'new_context_ground_columns':ground_count,'sample_count':len(vals),'unsupported_samples_not_filled':int((~support['supported']).sum()),'max_nearest_supported_ground_m':float(support['nearest_ground_m'][support['supported']].max()),'vertical_scope_boundary_faces':0},'sources':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [parent_path,city_path,truth_path,raw_path]],'not_generated':['photoreal textures','windows and facade ornament','unverified patios, awnings, entrances or garages','roof pitch inferred from height statistics','property fences based on arbitrary sampling extent'],'review':'NEIGHBORHOOD_BLOCKOUT_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'building_envelopes.geojson').write_text(json.dumps({'type':'FeatureCollection','features':out_features})+'\n');(OUT/f'{NAME}_placement.json').write_text((prior.OUT/f'{prior.NAME}_placement.json').read_text())
 print(json.dumps({'status':report['status'],'buildings':len(audit),'checks':checks,'preserved_cells':checked,'unsupported_context_samples':report['context']['unsupported_samples_not_filled'],'hosts':len(decoded)},indent=2))
 if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
