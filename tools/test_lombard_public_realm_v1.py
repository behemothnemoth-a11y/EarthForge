"""Independent decoded-volume checks for the assembled Lombard public corridor."""
import sys,json,hashlib,math
from shapely.geometry import LineString
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction.generate_lombard_public_realm_v1 import OUT,NAME,REGION,WALK,WALKJOINT,BRICK,STEP,LEAF,LEAF2
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.reconstruction.generate_lombard_stairs_v013 import load_core_stairs

def main():
    global OUT,NAME,REGION
    data_out=OUT;data_name=NAME
    if '--landscape' in sys.argv:
        from pipeline.reconstruction.generate_lombard_landscape_v019 import OUT as out,NAME as name,REGION as region
        OUT,NAME,REGION=out,name,region
    elif '--blockout' in sys.argv:
        from pipeline.reconstruction.generate_lombard_neighborhood_v018 import OUT as out,NAME as name,REGION as region
        OUT,NAME,REGION=out,name,region
    artifact=OUT/f'{NAME}.litematic';blocks,hosts=read(artifact,REGION)
    foliage_materials={LEAF,LEAF2}
    if '--landscape' in sys.argv:
        from pipeline.reconstruction.generate_lombard_landscape_v019 import LEAVES,SHRUB
        foliage_materials.update(LEAVES+SHRUB)
    cache=np.load(data_out/'surface_preview.npz');tops={tuple(k):int(t) for k,t in zip(cache['xz'],cache['top'])}
    def cell(x,y,z):
        p,i=position(x,y,z);v=hosts.get(p);return v.cells[i] if v else None
    pedestrian=np.isin(cache['material'],[WALK,WALKJOINT,BRICK,STEP]);missing=[];foliage=[];checked=0
    for key,t in zip(cache['xz'][pedestrian],cache['top'][pedestrian]):
        x,z=map(int,key);t=int(t);checked+=1
        if cell(x,t-1,z) is None:missing.append([x,t-1,z])
        for y in range(t,t+36):
            if cell(x,y,z) in foliage_materials:foliage.append([x,y,z])
    stairs=[];obstacles=[]
    for feature in json.loads((data_out/f'{data_name}_validation.json').read_text())['features']:
        if feature['type']!='stairs':continue
        s={'line':LineString(feature['modeled_line_xz_m']),'osm_id':feature['osm_id']}
        count=0;absent=0
        for d in np.arange(.2,s['line'].length-.2,.125):
            p=s['line'].interpolate(d);x,z=math.floor(p.x*16),math.floor(p.y*16);t=tops.get((x,z));count+=1
            if t is None:absent+=1;continue
            for y in range(t+3,t+30):
                m=cell(x,y,z)
                if m is not None:obstacles.append({'stair':s.get('id',s.get('osm_id')),'xyz':[x,y,z],'material':m});break
        stairs.append({'osm_id':s.get('id',s.get('osm_id')),'samples':count,'unsupported_samples':absent})
    report={'schematic_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'pedestrian_columns_checked':checked,'missing_pedestrian_surface_cells':len(missing),'foliage_below_2_25m_over_pedestrian_surfaces':len(foliage),'stair_centerline_checks':stairs,'stair_centerline_obstacle_samples':len(obstacles),'examples':{'missing':missing[:10],'foliage':foliage[:10],'obstacles':obstacles[:10]},'limits':'Checks modeled pedestrian surfaces and 0.125m stair centerline samples; does not replace an in-game walking or collision test.'}
    report['pass']=not missing and not foliage and not obstacles and all(s['unsupported_samples']==0 for s in stairs)
    (OUT/'independent_pedestrian_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['pass']:raise SystemExit(1)
if __name__=='__main__':main()
