"""Independent flower connectivity and revision-evidence checks on the export."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_realism_v020 as g
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
def main():
 path=g.OUT/f'{g.NAME}.litematic';blocks,hosts=read(path,g.REGION);bloom=set();shrubs=set(g.SHRUB)
 for (hx,hy,hz),vol in hosts.items():
  for i,m in enumerate(vol.cells):
   if m in g.BLOOM:bloom.add((hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320))
 def get(p):
  q,i=position(*p);v=hosts.get(q);return v.cells[i] if v else None
 neighbors=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)];remaining=bloom.copy();components=[];unsupported=[]
 while remaining:
  first=remaining.pop();queue=[first];size=0;touch=False;lo=list(first);hi=list(first)
  while queue:
   p=queue.pop();size+=1
   for k in range(3):lo[k]=min(lo[k],p[k]);hi[k]=max(hi[k],p[k])
   for d in neighbors:
    n=tuple(p[k]+d[k] for k in range(3))
    if n in remaining:remaining.remove(n);queue.append(n)
    elif not touch and get(n) in shrubs:touch=True
  rec={'cells':size,'span_cells':[hi[k]-lo[k]+1 for k in range(3)],'touches_shrub':touch}
  components.append(rec)
  if not touch:unsupported.append({'start':first,**rec})
 report={'schematic_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bloom_cells':len(bloom),'connected_components':len(components),'components_smaller_than_8_cells':sum(c['cells']<8 for c in components),'unsupported_components':len(unsupported),'unsupported_examples':unsupported[:10],'minimum_component_cells':min(c['cells'] for c in components),'pass':not unsupported,'limits':'Connectivity and structural support only; plant spacing and visual character still require flyaround.'}
 report['pass']=report['pass'] and report['components_smaller_than_8_cells']==0
 (g.OUT/'independent_realism_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if not report['pass']:raise SystemExit(1)
if __name__=='__main__':main()
