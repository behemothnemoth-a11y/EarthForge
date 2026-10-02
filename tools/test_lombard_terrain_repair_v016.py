"""Independent artifact preservation check; requires local Lombard artifacts."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,OUT,PARENT,NAME,REGION
from pipeline.reconstruction import generate_lombard_endpoint_roads_v015 as v

def main():
    old_blocks,old=read(PARENT,v.REGION)
    new_blocks,new=read(OUT/f'{NAME}.litematic',REGION)
    pavement={v.HYDE_TOP,v.HYDE_BASE,v.LEAV_TOP,v.LEAV_BASE,'astra_microblocks:rgb_686661','astra_microblocks:rgb_5d5c59'}
    checked=0;mismatches=0;delta=0
    for pos in old.keys()|new.keys():
        a=old.get(pos);b=new.get(pos)
        for i in range(4096):
            ma=a.cells[i] if a else None;mb=b.cells[i] if b else None
            delta+=ma!=mb
            if ma in pavement:checked+=1;mismatches+=ma!=mb
    vanilla={p:s for p,s in old_blocks.items() if p not in old}
    assert all(new_blocks.get(p)==s for p,s in vanilla.items())
    assert mismatches==0
    report=json.loads((OUT/f'{NAME}_validation.json').read_text())
    assert delta==report['changed_microcells']
    result={'endpoint_pavement_cells_checked':checked,'endpoint_pavement_mismatches':mismatches,
        'changed_microcells_independently_counted':delta,'parent_vanilla_blocks_preserved':len(vanilla),'status':'PASS'}
    (OUT/'independent_preservation_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
