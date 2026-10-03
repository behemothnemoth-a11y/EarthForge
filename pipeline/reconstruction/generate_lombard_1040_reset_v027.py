"""Lombard v027: remove 1040 entirely and return the site to source-acquisition state."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from shapely.geometry import Point,shape
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_access_tree_realism_v024 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_realism_v020 as realism
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic

OUT=realm.v.PROJECT/'outputs/house_1040_reset_v027'
NAME='Lombard_1040_Source_Reset_Astra_v027';REGION='LOMBARD_1040_SOURCE_RESET_V027'
BUILDING_ID='201006.0032105'

def xyz(pos,i):
    hx,hy,hz=pos
    return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=parent.OUT/f'{parent.NAME}.litematic'
    blocks,hosts=read(source,parent.REGION)
    vanilla={p:s for p,s in blocks.items() if p not in hosts}
    original={p:(v.original,v.cells.copy()) for p,v in hosts.items()}
    env=json.loads((buildings.OUT/'building_envelopes.geojson').read_text())
    feat=next(f for f in env['features'] if str(f['properties']['id'])==BUILDING_ID)
    geom=shape(feat['geometry'])
    poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,'geoms') else geom
    prop=feat['properties']
    zero=float(json.loads(realm.v.CENTER.read_text())[0]['elev_navd88_m'])
    floor=round((prop['ground_min_navd88_m']-zero)*16)
    cap=round((prop['median_first_return_navd88_m']-zero)*16)
    old1040={*buildings.WALLS,buildings.ROOF,
             realism.rgb('a9cbd6'),realism.rgb('293f48'),
             realism.rgb('95c7d4'),realism.rgb('799da5'),
             realism.rgb('8cb3ba')}
    writes={};removed=0
    target=poly.buffer(.16);minx,minz,maxx,maxz=target.bounds
    candidate_hosts=[]
    for p,v in hosts.items():
        hx,hy,hz=p
        hminx=(hx*16-480)/16;hmaxx=(hx*16-480+15)/16
        hminz=(hz*16-320)/16;hmaxz=(hz*16-320+15)/16
        if hmaxx<minx or hminx>maxx or hmaxz<minz or hminz>maxz:continue
        if hy*16+15<floor-4 or hy*16>cap+4:continue
        candidate_hosts.append((p,v))
    for p,v in candidate_hosts:
        for i,m in enumerate(v.cells.copy()):
            if m not in old1040:continue
            x,y,z=xyz(p,i)
            if floor-4<=y<=cap+4 and target.covers(Point((x+.5)/16,(z+.5)/16)):
                v.cells[i]=None;writes[(p,i)]=(m,None);removed+=1
    for p,_ in candidate_hosts:
        if p in hosts and not any(hosts[p].cells):
            del hosts[p];blocks.pop(p,None)
    remain=[]
    for p,v in candidate_hosts:
        if p not in hosts:continue
        for i,m in enumerate(v.cells):
            if m not in old1040:continue
            x,y,z=xyz(p,i)
            if floor-4<=y<=cap+4 and target.covers(Point((x+.5)/16,(z+.5)/16)):
                remain.append([x,y,z,m])
    escaped=[]
    for p,i in writes:
        x,y,z=xyz(p,i)
        if not target.covers(Point((x+.5)/16,(z+.5)/16)):
            escaped.append([x,y,z])
    outside_ok=True
    for p,_ in candidate_hosts:
        orig,cells=original[p];q=hosts.get(p)
        for i,a in enumerate(cells):
            if (p,i) in writes:continue
            b=q.cells[i] if q is not None else None
            if a!=b:
                outside_ok=False;break
        if not outside_ok:break
    coords=np.array(list(blocks));lo=coords.min(0);hi=coords.max(0)
    bounds=(*lo.tolist(),*hi.tolist());writer=NBTWriter()
    payload=[tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),q)
             for p,q in sorted(hosts.items())]
    artifact=OUT/f'{NAME}.litematic'
    stats=write_single_region_litematic(
        artifact,blocks,bounds,REGION,NAME,
        '1040 Lombard source reset: prior placeholder/interpreted building geometry removed from accepted v024 context. Empty building footprint is intentional reset state, not terrain truth.',
        data_version=realm.v.DATA_VERSION,tile_entity_payloads=payload)
    actual,decoded=read(artifact,REGION)
    checks={
        'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
        'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
        '1040_building_materials_absent':not remain,
        'declared_1040_footprint_only':not escaped,
        'all_parent_cells_outside_declared_removals_preserved':outside_ok,
        'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items())
    }
    report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','validation':checks,
        'parent':'v024 accepted public-realm/access context',
        'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'building_id':BUILDING_ID,'address':'1040 Lombard Street',
        'removed_microcells':removed,'source_footprint_area_m2':poly.area,
        'source_vertical_envelope_cells':[floor,cap],
        'reset_policy':'No replacement terrain, foundation, facade, roof, or house massing is inferred. The cleared footprint is a workflow reset void until the 1040 source-truth package is approved.',
        'preserved':['road and pavers','driveways','sidewalks','stairs and rails','landscaping','trees as v024 context','all neighboring buildings','registration marker'],
        'rejected_as_geometry':['v020 blue facade interpretation','v025 flat facade skeleton','v026 3D front massing interpretation'],
        'next_gate':'1040_SOURCE_TRUTH_REVIEW'}
    (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/f'{NAME}_placement.json').write_text(json.dumps({'placement_origin':'same Lombard player-feet origin','rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
    (OUT/'Build_notes.md').write_text('# 1040 Lombard source reset v027\n\nThe building is intentionally absent. This is not a terrain model and must not be used to infer a hole, slab, foundation, or house shape. Geometry resumes only after the 1040 source-truth gate passes.\n')
    print(json.dumps({'file':str(artifact),'status':report['status'],'removed_microcells':removed,'validation':checks},indent=2))
    if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
