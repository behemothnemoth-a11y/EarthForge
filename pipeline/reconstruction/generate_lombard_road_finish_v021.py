"""Fix inferred rounded endpoint caps; reference-sampled, antialiased paver color."""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Point,LineString
from shapely import points,line_locate_point,line_interpolate_point,contains_xy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_realism_v020 as parent
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
v=parent.v;road=v.v
OUT=road.PROJECT/'outputs/road_finish_v021';NAME='Lombard_Road_Joins_And_Pavers_Astra_v021';REGION='LOMBARD_ROAD_FINISH_V021'
OLD_RED=set(road.BRICK_COLORS+[road.ROAD_BASE,road.JOINT]);ASPHALT=v.ASPHALT
PHOTO=road.PROJECT/'references/private/wikimedia_commons/007_Crooked_Section_of_Lombard_Street.jpg.jpg'
def material(rgb):return 'astra_microblocks:rgb_'+''.join(f'{int(x):02x}' for x in rgb)

def reference_palette():
 im=Image.open(PHOTO).convert('RGB');mask=Image.new('L',im.size);polygon=[(130,850),(490,760),(900,860),(1100,935),(100,935)];ImageDraw.Draw(mask).polygon(polygon,fill=255)
 samples=np.array(im)[np.array(mask)>0].astype(float);samples=samples[(samples[:,0]>samples[:,1]*1.12)&(samples[:,0]-samples[:,2]>15)]
 brick=np.round(np.percentile(samples,[20,30,45,60,75,85],axis=0));mortar=np.array([115,109,103]);palette=np.unique(np.round(np.array([c*(1-f)+mortar*f for c in brick for f in [0,.10,.20,.30,.40]])).astype(np.uint8),axis=0)
 return brick,palette,{'file':str(PHOTO.relative_to(ROOT)),'sha256':hashlib.sha256(PHOTO.read_bytes()).hexdigest(),'page':'https://commons.wikimedia.org/wiki/File:Crooked_Section_of_Lombard_Street.jpg','artist':'Cornflower123','license':'CC0','photo_date':'2024-02-16','sample_polygon_pixels':polygon,'brick_rgb_percentiles':brick.tolist(),'mortar_rgb_interpretation':mortar.tolist(),'palette_rgb':palette.tolist(),'limits':'Photo illumination is not calibrated material albedo; mortar shade and 20x10cm dimensions remain provisional. No baked shadows, photograph projection or new resource pack.'}

def paver_materials(keys,line):
 brick,palette,evidence=reference_palette();xz=(np.array(keys)+.5)/16;pt=points(xz[:,0],xz[:,1]);s=line_locate_point(line,pt);cp=line_interpolate_point(line,s)
 from shapely import get_x,get_y
 a=line_interpolate_point(line,np.maximum(0,s-.45));b=line_interpolate_point(line,np.minimum(line.length,s+.45));tx=get_x(b)-get_x(a);tz=get_y(b)-get_y(a);length=np.maximum(1e-6,np.hypot(tx,tz));tx/=length;tz/=length;nx=-tz;nz=tx;lat=(xz[:,0]-get_x(cp))*nx+(xz[:,1]-get_y(cp))*nz
 color=np.zeros((len(keys),3),float);mortar=np.array(evidence['mortar_rgb_interpretation'])
 # Area-sample both brick boundaries. A 6mm joint must not turn into a
 # fully dark 62.5mm cell; that aliasing made the old road look striped.
 for dx in [-.375,-.125,.125,.375]:
  for dz in [-.375,-.125,.125,.375]:
   u=s+(dx*tx+dz*tz)/16;vv=lat+(dx*nx+dz*nz)/16;row=np.floor(vv/.10).astype(np.int64);stagger=(row&1)*.10;col=np.floor((u+stagger)/.20).astype(np.int64)
   h=((col*73856093)^(row*19349663))&0xffffffff;rgb=brick[h%len(brick)];along=(u+stagger)%.20;across=vv%.10;joint=(np.minimum(along,.20-along)<.003)|(np.minimum(across,.10-across)<.003)
   color+=np.where(joint[:,None],mortar,rgb)/16
 chosen=np.empty(len(keys),np.int16)
 for start in range(0,len(keys),20000):
  c=color[start:start+20000];chosen[start:start+len(c)]=np.argmin(((c[:,None,:]-palette[None,:,:])**2).sum(2),axis=1)
 return [material(c) for c in palette],chosen,evidence

def main():
 OUT.mkdir(parents=True,exist_ok=True);source=parent.OUT/f'{parent.NAME}.litematic';print('Loading v020.',flush=True);blocks,hosts=read(source,parent.REGION);original_blocks=blocks.copy();vanilla={p:s for p,s in blocks.items() if p not in hosts};hashes={p:hash((vol.original,tuple(vol.cells))) for p,vol in hosts.items()};backup={};writes={};changes={}
 def get(x,y,z):
  p,i=position(int(x),int(y),int(z));vol=hosts.get(p);return vol.cells[i] if vol else None
 def put(x,y,z,m,why):
  p,i=position(int(x),int(y),int(z))
  if p in vanilla:raise RuntimeError('Road correction reached registration/full block')
  old=hosts[p].cells[i] if p in hosts else None
  if old==m:return
  if p not in backup:backup[p]=(hosts[p].original,hosts[p].cells.copy()) if p in hosts else None
  if p not in hosts:hosts[p]=MicroVolume();blocks[p]=HOST_STATE
  hosts[p].cells[i]=m;writes[(p,i)]=why;changes[why]=changes.get(why,0)+1
 red={};asphalt={};extra={};scan=OLD_RED|ASPHALT|{road.CURB_MATERIAL,v.WHITE,v.STEEL,v.BLACK}
 for (hx,hy,hz),vol in hosts.items():
  for i,m in enumerate(vol.cells):
   if m not in scan:continue
   key=(hx*16+(i&15)-480,hz*16+((i>>4)&15)-320);y=hy*16+(i>>8)
   if m in OLD_RED:red.setdefault(key,[]).append(y)
   elif m in ASPHALT:asphalt.setdefault(key,[]).append(y)
   else:extra.setdefault(key,[]).append((y,m))
 print('Recovering accepted cross-street surfaces and classifying overlaps.',flush=True)
 center=json.loads(road.CENTER.read_text());line=LineString([(p['x_m'],p['z_m']) for p in center]);roadpoly,_=road.variable_road_polygon(line);join_keys=set();intersection_keys=set();audits=[];expected=[]
 specs=[('Hyde',['7144000','7145000'],road.HYDE_PAVEMENT_WIDTH_M,road.HYDE_TOP,road.HYDE_BASE),('Leavenworth',['8268000','8269000'],road.LEAVENWORTH_PAVEMENT_WIDTH_M,road.LEAV_TOP,road.LEAV_BASE)]
 for name,cnns,width,topmat,basemat in specs:
  cross,_=road.combined_intersection_line(*cnns);poly=cross.buffer(width/2,cap_style=2,join_style=2);scope=poly.buffer(2,join_style=2).intersection(roadpoly.buffer(.20));candidates=[]
  for key,ys in asphalt.items():
   pt=Point((key[0]+.5)/16,(key[1]+.5)/16)
   if not poly.covers(pt):continue
   t=max(ys)+1
   if get(key[0],t,key[1])==v.WHITE:t+=1
   candidates.append([key[0],key[1],t])
  data=np.array(candidates);st=line_locate_point(cross,points((data[:,0]+.5)/16,(data[:,1]+.5)/16));bins=np.rint(st*8).astype(int);unique=np.unique(bins);elev=np.array([np.median(data[bins==j,2]) for j in unique]);stations=unique/8
  selected=[key for key in red if scope.covers(Point((key[0]+.5)/16,(key[1]+.5)/16))];inside=0;paint_count=0;rail_count=0;removed_curbs=0;max_delta=0.;bounds=[]
  # Include obsolete cap-curb columns inside the intersection but not outside
  # its pavement; genuine roadside curbs and pedestrian landings stay fixed.
  for key,items in extra.items():
   if key in red:continue
   if any(m==road.CURB_MATERIAL for y,m in items) and poly.covers(Point((key[0]+.5)/16,(key[1]+.5)/16)) and roadpoly.buffer(.20).covers(Point((key[0]+.5)/16,(key[1]+.5)/16)):selected.append(key)
   elif name=='Hyde' and key in asphalt and poly.covers(Point((key[0]+.5)/16,(key[1]+.5)/16)):
    pavement_top=max(asphalt[key])+1
    if any(m in {v.STEEL,v.BLACK} and abs(y-pavement_top)<=1 for y,m in items):selected.append(key)
  for x,z in selected:
   pt=Point((x+.5)/16,(z+.5)/16);is_cross=poly.covers(pt);distance=poly.distance(pt);target=float(np.interp(cross.project(pt),stations,elev));oldtop=max(red.get((x,z),asphalt.get((x,z),[round(target)-1])))+1
   if is_cross:newtop=round(target);inside+=1;intersection_keys.add((x,z))
   else:
    w=max(0.,1-distance/2);w=w*w*(3-2*w);newtop=round(oldtop*(1-w)+target*w)
   max_delta=max(max_delta,abs(newtop-oldtop)/16);join_keys.add((x,z));old_ys=red.get((x,z),[])+asphalt.get((x,z),[]);features=[];oldsurface=max(oldtop,max(asphalt.get((x,z),[oldtop-1]))+1)
   for y,m in extra.get((x,z),[]):
    if m==road.CURB_MATERIAL and is_cross and abs(y-oldtop)<=6:old_ys.append(y);removed_curbs+=1
    elif m in {v.WHITE,v.STEEL,v.BLACK} and min(abs(y-oldtop),abs(y-oldsurface))<=2:old_ys.append(y);features.append(m)
   for y in old_ys:put(x,y,z,None,'endpoint_geometry')
   if is_cross:
    mat=road.asphalt_top(topmat,x,z);base=basemat
   else:mat=road.BRICK_COLORS[0];base=road.ROAD_BASE
   if v.WHITE in features:mat=v.WHITE;paint_count+=1
   if v.STEEL in features:mat=v.STEEL;rail_count+=1
   elif v.BLACK in features:mat=v.BLACK;rail_count+=1
   for y in range(newtop-3,newtop):
    existing=get(x,y,z)
    if existing is not None and existing not in scan:raise RuntimeError(f'Road blend hits non-road material {(x,y,z,existing)}')
    put(x,y,z,mat if y==newtop-1 else base,'endpoint_geometry')
   expected.append([x,z,newtop,mat,is_cross]);bounds.append([x/16,z/16])
  audits.append({'name':name,'city_cnns':cnns,'pavement_width_m':width,'classification':'reconstruction artifact: circular road cap protected through later endpoint-road assembly','corrected_columns':len(selected),'intersection_columns':inside,'transition_max_length_m':2,'max_height_change_m':max_delta,'obsolete_curb_cells_removed':removed_curbs,'crossing_columns_redraped':paint_count,'track_columns_embedded':rail_count,'profile_source':'median original v020 asphalt surface per 0.125m cross-street station, interpolated only within existing 50m street','profile_station_m':stations.tolist(),'profile_top_cells':elev.tolist(),'scope_polygon':scope.__geo_interface__,'additional_track_scope':'Existing Hyde rail/slot columns over asphalt only; embed throughout the 50m segment to avoid a new step at the repaired cap.' if name=='Hyde' else None})
  print(name,{k:audits[-1][k] for k in ['corrected_columns','intersection_columns','max_height_change_m','obsolete_curb_cells_removed']},flush=True)
 print('Recoloring red pavers with area-sampled narrow joints.',flush=True)
 texture_keys=[key for key in red if key not in intersection_keys];palette,ids,photo=paver_materials(texture_keys,line);textured=0;texture_scope=set()
 for (x,z),idx in zip(texture_keys,ids):
  # Re-evaluate top after entrance grade repair. Preserve white paint.
  candidates=red[(x,z)];ys=range(min(candidates)-32,max(candidates)+33) if (x,z) in join_keys else candidates
  yy=[y for y in ys if get(x,y,z) in OLD_RED]
  if not yy:continue
  y=max(yy)
  if get(x,y+1,z) is not None:continue
  # Recolor the full existing red slab in this column so exposed grade risers
  # do not retain the old dark base color as artificial transverse stripes.
  for yy0 in yy:
   put(x,yy0,z,palette[int(idx)],'paver_color_only');texture_scope.add((x,yy0,z))
  textured+=1
 for p in list(hosts):
  if not any(hosts[p].cells):del hosts[p];blocks.pop(p,None)
 unexpected=[];occupancy_changes=0;material_changes=0
 for p,record in backup.items():
  old=record[1] if record else [None]*4096;new=hosts[p].cells if p in hosts else [None]*4096;hx,hy,hz=p
  for i,(a,b) in enumerate(zip(old,new)):
   if a==b:continue
   x=hx*16+(i&15)-480;z=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8);geometry=(a is None)!=(b is None);occupancy_changes+=geometry;material_changes+=not geometry
   if geometry and (x,z) not in join_keys:unexpected.append([x,y,z,a,b])
   if (x,z) not in join_keys and ((x,y,z) not in texture_scope or a not in OLD_RED or b not in palette):unexpected.append([x,y,z,a,b])
 assert not unexpected,unexpected[:3]
 # Independent expected top colors after texture stage are used for readback.
 for row in expected:
  x,z,t,m,inside=row;row[3]=get(x,t-1,z)
 np.savez_compressed(OUT/'join_surface_controls.npz',xyz=np.array([[r[0],r[2],r[1]] for r in expected],int),intersection=np.array([r[4] for r in expected],bool))
 coords=np.array(list(blocks));oldcoords=np.array(list(original_blocks));lo=np.minimum(coords.min(0),oldcoords.min(0));hi=np.maximum(coords.max(0),oldcoords.max(0));bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter();payload=[tile_entity_payload(writer,tuple(p[k]-lo[k] for k in range(3)),vol) for p,vol in sorted(hosts.items())];path=OUT/f'{NAME}.litematic'
 stats=write_single_region_litematic(path,blocks,bounds,REGION,NAME,'Repair inherited round road caps at Hyde/Leavenworth; blend short approach joins; reference-sampled paver colors and antialiased narrow joints. Blue facade remains rejected provisional work.',data_version=road.DATA_VERSION,tile_entity_payloads=payload)
 print('Exported; checking exact readback and change boundaries.',flush=True);actual,decoded=read(path,REGION)
 def decodedcell(x,y,z):
  p,i=position(x,y,z);vv=decoded.get(p);return vv.cells[i] if vv else None
 checks={'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==vol.cells and decoded[p].original==vol.original for p,vol in hosts.items()),'untouched_hosts_preserved':all(p in decoded and hash((decoded[p].original,tuple(decoded[p].cells)))==h for p,h in hashes.items() if p not in backup),'vanilla_and_registration_preserved':all(actual.get(p)==s for p,s in vanilla.items()),'geometry_changes_only_in_declared_joins':not unexpected,'road_surface_controls':all(decodedcell(x,t-1,z)==m and decodedcell(x,t,z) is None for x,z,t,m,c in expected),'three_cell_slabs':all(all(decodedcell(x,y,z) is not None for y in range(t-3,t)) for x,z,t,m,c in expected),'no_red_caps_remaining':all(decodedcell(x,t-1,z) not in OLD_RED|set(palette) for x,z,t,m,c in expected if c)}
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'joins':audits,'paver_surface_columns':textured,'palette':photo,'changes':changes,'changed_occupancy_cells':occupancy_changes,'changed_material_cells':material_changes,'preserved':['crooked road geometry outside the declared 2m endpoint blend strips','curbs outside intersection cap footprints','landscape and ground','all buildings','pedestrian stairs and rails','registration'],'blue_building_review':'Rejected facade interpretation: oversized regular glass grid; actual solid blue panels, discrete white-framed openings, bay projections and upper enclosure need a separate source-led rebuild. No further propagation; unchanged in road-focused v021.','sources':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [road.CITY,road.CENTER,road.PROJECT/'references/private/esri/lombard_poc001_world_imagery.jpg',road.PROJECT/'references/private/wikimedia_commons/022_Lombard_Street_10064478253_.jpg.jpg']],'limits':['Paving colors sampled under photographic illumination, not calibrated albedo','1/16m RGB microcells cannot reproduce millimetre texture or physically based roughness','City-width road edge is the geometric join authority; imagery corroborates asphalt intersections, not surveyed millimetre boundaries'],'review':'USER_FLYAROUND_REQUIRED'}
 (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/f'{NAME}_placement.json').write_text((parent.OUT/f'{parent.NAME}_placement.json').read_text());print(json.dumps({'status':report['status'],'checks':checks,'textured_columns':textured,'changes':changes},indent=2))
 if not all(checks.values()):raise SystemExit(1)
if __name__=='__main__':main()
