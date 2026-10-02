"""Decoded join continuity across the edited boundary, not just export equality."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_road_finish_v021 as g
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
path=g.OUT/f'{g.NAME}.litematic';blocks,hosts=read(path,g.REGION);controls=np.load(g.OUT/'join_surface_controls.npz');palette={g.material(c) for c in json.loads((g.OUT/f'{g.NAME}_validation.json').read_text())['palette']['palette_rgb']};surface=g.OLD_RED|g.ASPHALT|palette|{g.v.WHITE,g.v.STEEL,g.v.BLACK}
def cell(x,y,z):
 p,i=position(x,y,z);v=hosts.get(p);return v.cells[i] if v else None
tops={(int(x),int(z)):int(t) for x,t,z in controls['xyz']};bad=[];maximum=0;neighbors=0;cross_boundary=0;missing=0;red_caps=0
for (x,z),t in tops.items():
 missing+=any(cell(x,y,z) is None for y in range(t-3,t))
 for dx,dz in [(1,0),(0,1),(-1,0),(0,-1)]:
  key=(x+dx,z+dz);nt=tops.get(key)
  if nt is None:
   ys=[y for y in range(t-6,t+7) if cell(key[0],y,key[1]) in surface]
   if not ys:continue
   nt=max(ys)+1;cross_boundary+=1
  neighbors+=1;delta=abs(t-nt);maximum=max(maximum,delta)
  if delta>2:bad.append([x,z,t,key[0],key[1],nt])
for (x,t,z),inside in zip(controls['xyz'],controls['intersection']):
 if inside and cell(int(x),int(t)-1,int(z)) in g.OLD_RED|palette:red_caps+=1
report={'schematic_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'corrected_columns':len(tops),'neighbor_checks':neighbors,'checks_across_edit_boundary':cross_boundary,'max_adjacent_surface_step_m':maximum/16,'steps_above_0_125m':len(bad),'examples':bad[:20],'missing_three_cell_support_columns':missing,'red_cap_surface_columns_remaining':red_caps,'pass':not bad and missing==0 and red_caps==0,'limits':'Local road-surface continuity at corrected joins, including the unedited boundary; not a full-world physics simulation.'}
(g.OUT/'independent_road_join_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if not report['pass']:raise SystemExit(1)
