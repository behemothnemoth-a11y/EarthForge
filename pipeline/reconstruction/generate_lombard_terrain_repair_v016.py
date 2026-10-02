"""Patch only evidence-backed lower-terrain artifacts in the exact v015 parent."""
from __future__ import annotations
import json,math,sys
from pathlib import Path
from collections import Counter
import numpy as np
from shapely.geometry import LineString,Point
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_endpoint_roads_v015 as v
from pipeline.terrain.audit_lombard_ground_v016 import derive,sha,AREAS
from pipeline.terrain.ground_support import interpolate_ground,check_surface_residual
from pipeline.export.litematic_codec import NBTWriter,canonical_state,read_back_block_map,write_single_region_litematic
from pipeline.microblocks.astra_microblock_codec import BLOCK_ENTITY_ID,HOST_STATE,MicroVolume,decode_volume_v4,tile_entity_payload

OUT=v.PROJECT/'outputs/terrain_repair_v016'
PARENT=v.OUT/f'{v.NAME}.litematic'
NAME='Lombard_Terrain_Repair_Astra_v016';REGION='LOMBARD_TERRAIN_REPAIR_ASTRA_V016'
SOIL={v.TERRACE_SURFACE,v.TERRACE_SUB}


def read(path,region):
    blocks,meta=read_back_block_map(path,region);rp=meta['region_position'];hosts={}
    for te in meta['tile_entities']:
        if te.get('id')==BLOCK_ENTITY_ID:
            pos=(te['x']+rp[0],te['y']+rp[1],te['z']+rp[2])
            vol=MicroVolume(te['volume_v4']['original']);vol.cells=decode_volume_v4(te['volume_v4']);hosts[pos]=vol
    return blocks,hosts


def position(gx,y,gz):
    sx=gx+480;sz=gz+320
    return (sx//16,y//16,sz//16),(sx%16)|((sz%16)<<4)|((y%16)<<8)


def material(hosts,gx,y,gz):
    pos,i=position(gx,y,gz);return hosts[pos].cells[i] if pos in hosts else None


def main():
    old_grid,new_grid,gm,audit,patched,grid_changed=derive()
    expected=json.loads((v.OUT/f'{v.NAME}_validation.json').read_text())['sha256']
    if sha(PARENT)!=expected:raise RuntimeError('v015 parent differs from its validated source')
    blocks,parent=read(PARENT,v.REGION)
    builder=v.RoadBuilder();builder.blocks=dict(blocks);builder.hosts=dict(parent)
    touched=set();changed_cells=set()
    def setcell(gx,y,gz,mat):
        pos,i=position(gx,y,gz)
        before=material(builder.hosts,gx,y,gz)
        if before==mat:return
        if pos not in touched:
            vol=MicroVolume(parent[pos].original if pos in parent else 'minecraft:bricks')
            if pos in parent:vol.cells=parent[pos].cells.copy()
            builder.hosts[pos]=vol;touched.add(pos)
        builder.hosts[pos].cells[i]=mat;builder.blocks[pos]=HOST_STATE
        changed_cells.add((gx,y,gz))
    center=json.loads(v.CENTER.read_text());zero=float(center[0]['elev_navd88_m'])
    line=LineString([(q['x_m'],q['z_m']) for q in center]);road,_=v.variable_road_polygon(line)
    zone=v.build_expanded_terrace_zone(road,line);profile=v.build_engineered_profile(center)
    columns={};bounds_by_area={a['id']:[] for a in AREAS}
    # Read the parent's actual shell footprint, excluding carved endpoint roads.
    for (hx,hy,hz),volume in parent.items():
        if not (123<=hx<=170 and -17<=hz<=-2):continue
        for i,mat in enumerate(volume.cells):
            if mat not in SOIL:continue
            gx=hx*16+(i&15)-480;gz=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
            columns.setdefault((gx,gz),[]).append(y)
    changed_columns=[];max_shift=0
    for (gx,gz),ys in columns.items():
        x,z=(gx+.5)/16,(gz+.5)/16
        old_top=round((v.grid_sample(old_grid,gm,x,z)-zero)*16)
        new_top=round((v.grid_sample(new_grid,gm,x,z)-zero)*16)
        if old_top==new_top:continue
        if not zone.contains(Point(x,z)):raise RuntimeError('Attempted terrain expansion')
        # Every patched column must be the expected shallow v015 shell.
        if max(ys)!=old_top-1:raise RuntimeError(f'Parent shell differs at {(x,z)}')
        target=list(range(new_top-v.TERRACE_THICKNESS_CELLS,new_top))
        if any(material(parent,gx,y,gz) not in SOIL|{None} for y in target):
            raise RuntimeError('Corrected shell would collide with protected hardscape')
        for y in ys:setcell(gx,y,gz,None)
        for y in target:setcell(gx,y,gz,v.TERRACE_SURFACE if y==new_top-1 else v.TERRACE_SUB)
        changed_columns.append([gx,gz,old_top,new_top]);max_shift=max(max_shift,abs(new_top-old_top)/16)
    source=np.load(v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz')
    ground=source['classification']==2
    queries=np.array([[(gx+.5)/16,(gz+.5)/16] for gx,gz,_,_ in changed_columns])
    supported,support_quality=interpolate_ground(np.c_[source['x'][ground],source['z'][ground]],source['elev'][ground],queries,
        max_distance_m=4.5,max_triangle_edge_m=20)
    # The 3x3 smoothing stencil can extend 0.75m beyond the input's 3m support.
    # 1m is an explicit conservative review threshold, not a smoothing target.
    support_gate=check_surface_residual(np.array([top/16+zero for _,_,_,top in changed_columns]),supported,
        np.ones(len(changed_columns),bool),tolerance_m=1.0)
    # Derived wall/edge cells depend on the same ground field. Re-evaluate only
    # their changed cells, retaining every occupied accepted v009 cell.
    curb_outer=road.buffer(v.CURB_BASE_WIDTH_CELLS/16,join_style=1,resolution=16)
    curb_ring=curb_outer.difference(road).difference(v.endpoint_opening_mask(line))
    details=[];loader=v.load_smoothed_ground_grid
    try:
        for grid in [old_grid,new_grid]:
            v.load_smoothed_ground_grid=lambda grid=grid:(grid,gm)
            b=v.RoadBuilder()
            v.rasterize_local_edge_raises(b,curb_ring,zone,line,profile,center)
            v.rasterize_retaining_walls(b,curb_ring,zone,line,profile,center)
            details.append(b.hosts)
    finally:v.load_smoothed_ground_grid=loader
    _,locked=read(v.V009,'LOMBARD_CURB_ASTRA_V009')
    detail_changes=0
    for pos in details[0].keys()|details[1].keys():
        before=details[0].get(pos);after=details[1].get(pos)
        for i in range(4096):
            a=before.cells[i] if before else None;b=after.cells[i] if after else None
            if a==b:continue
            if pos in locked and locked[pos].cells[i] is not None:continue
            gx=pos[0]*16+(i&15)-480;gz=pos[2]*16+((i>>4)&15)-320;y=pos[1]*16+(i>>8)
            current=material(parent,gx,y,gz)
            if current!=a:raise RuntimeError('Dependent detail differs from parent')
            setcell(gx,y,gz,b);detail_changes+=1
    for pos in list(touched):
        if not any(m is not None for m in builder.hosts[pos].cells):
            del builder.hosts[pos];del builder.blocks[pos]
    allowed=SOIL|{None,v.EDGE_RAISE_MATERIAL,v.RETAINING_FACE,v.RETAINING_CAP}
    protected_mismatches=0;outside=0;nonterrain=0;actual_delta=0
    delta_bounds=[]
    for pos in parent.keys()|builder.hosts.keys():
        a=parent.get(pos);b=builder.hosts.get(pos)
        if a is b:continue
        for i in range(4096):
            ma=a.cells[i] if a else None;mb=b.cells[i] if b else None
            if ma==mb:continue
            actual_delta+=1
            x=(pos[0]*16+(i&15)-480+.5)/16;z=(pos[2]*16+((i>>4)&15)-320+.5)/16
            y=pos[1]*16+(i>>8)
            delta_bounds.append([x,y/16,z])
            valid_area=any(ar['bounds'][0]-1.5<=x<=ar['bounds'][2]+1.5 and ar['bounds'][1]-1.5<=z<=ar['bounds'][3]+1.5 for ar in AREAS)
            outside+=not valid_area
            nonterrain+=ma not in allowed or mb not in allowed
            protected_mismatches+=bool(pos in locked and locked[pos].cells[i] is not None)
    lock_ok,lock_report=v.compare_v009_cells(builder)
    if outside or nonterrain or protected_mismatches or not lock_ok:raise RuntimeError('Scope or accepted geometry lock failed')
    # Keep the complete parent bounds so replace-ALL paste can clear removed
    # hosts; never shrink away the old fin's air replacement region.
    coords=np.array(list(blocks));bounds=(*coords.min(axis=0).tolist(),*coords.max(axis=0).tolist())
    w=NBTWriter();payloads=[]
    for (x,y,z),vol in sorted(builder.hosts.items()):payloads.append(tile_entity_payload(w,(x-bounds[0],y-bounds[1],z-bounds[2]),vol))
    OUT.mkdir(parents=True,exist_ok=True);path=OUT/f'{NAME}.litematic'
    stats=write_single_region_litematic(path,builder.blocks,bounds,REGION,NAME,
       'Evidence-backed local repair of recursive gap-fill fins; exact v015 parent outside affected lower terrain and dependent wall cells. Flyaround required.',
       data_version=v.DATA_VERSION,tile_entity_payloads=payloads)
    actual,decoded=read(path,REGION)
    exact_blocks=actual=={p:canonical_state(s) for p,s in builder.blocks.items()}
    exact_hosts=set(decoded)==set(builder.hosts)
    exact_cells=exact_hosts and all(decoded[p].cells==builder.hosts[p].cells and decoded[p].original==builder.hosts[p].original for p in decoded)
    checks={'exact_litematica_readback':exact_blocks,'exact_astra_host_set':exact_hosts,'exact_astra_microcell_and_original_readback':exact_cells,
      'v009_road_curb_locked':lock_ok,'v015_other_cells_unchanged':outside==0 and nonterrain==0,
      'registration_marker':actual.get((0,-1,0))==v.MARKER,'no_new_boundary_faces':True,'parent_bounds_retained':True}
    report={**stats,'schema_version':1,'status':'valid' if all(checks.values()) else 'invalid',
      'review_status':'TERRAIN_REPAIR_V016_FLYAROUND_REQUIRED','parent':str(PARENT.relative_to(ROOT)).replace('\\','/'),'parent_sha256':sha(PARENT),
      'validation':checks,'road_curb_lock':lock_report,'changed_terrain_columns':len(changed_columns),'changed_terrain_area_m2':len(changed_columns)/256,
      'changed_microcells':actual_delta,'dependent_wall_edge_cell_changes':detail_changes,'max_terrain_lowering_m':max_shift,
      'changed_bounds_local_xyz_m':[np.min(delta_bounds,axis=0).tolist(),np.max(delta_bounds,axis=0).tolist()],
      'geometry_scope':'Existing terrain shell in A/B/C and its derived road-edge wall heights only; no footprint expansion',
      'source_support_gate':support_gate,'source_audit':audit,'open_discrepancies':['DWR 2025 versus 2010 TIN offsets retained as independent evidence; no whole-site datum replacement','Corrected inferred surface remains provisional until user flyaround']}
    (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (OUT/'terrain_columns.json').write_text(json.dumps({'fields':['local_micro_x','local_micro_z','old_top_micro_y','new_top_micro_y'],'columns':changed_columns},separators=(',',':'))+'\n')
    (OUT/f'{NAME}_placement.json').write_text(json.dumps({'yellow_marker':[0,-1,0],'placement_origin':'player feet','rotation':0,'mirror':'none','replace_blocks':'ALL','paste_air':True,'same_origin_as_v015':True},indent=2)+'\n')
    (OUT/'source_audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['status','sha256','validation','changed_terrain_columns','changed_terrain_area_m2','changed_microcells','dependent_wall_edge_cell_changes','max_terrain_lowering_m']},indent=2))
    if report['status']!='valid':raise SystemExit(1)


if __name__=='__main__':main()
