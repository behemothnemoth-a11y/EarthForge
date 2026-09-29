#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

LOCAL_IN = POC / "l0_geometry_local.json"
FRAME_IN = POC / "locked_frame.json"
SPEC_IN = POC / "truth_v005.json"
POLICY_IN = POC / "l1_truth_v005_policy.json"
CODEC_PATH = ROOT / "pipeline" / "export" / "litematic_codec.py"

OUT_DIR = PROJECT / "outputs" / "l1_truth"
OUT_FILE = OUT_DIR / "Redfield_POC_001_L1_Truth_v005.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_L1_Truth_v005.manifest.json"
MODEL_OUT = POC / "l1_truth_v005_model.json"
REPORT_OUT = PROJECT / "validation" / "poc001_l1_truth_v005_validation.json"

Point = Tuple[float,float]
Cell2 = Tuple[int,int]
Cell3 = Tuple[int,int,int]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_codec():
    spec = importlib.util.spec_from_file_location("earthforge_litematic_codec", CODEC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def point_in_polygon(px: float, pz: float, poly: Sequence[Point]) -> bool:
    inside=False
    j=len(poly)-1
    for i in range(len(poly)):
        xi,zi=poly[i]
        xj,zj=poly[j]
        if (zi>pz)!=(zj>pz):
            den=zj-zi
            if abs(den)<1e-12:
                den=1e-12
            if px < (xj-xi)*(pz-zi)/den + xi:
                inside=not inside
        j=i
    return inside


def raster_polygon(poly: Sequence[Point]) -> Set[Cell2]:
    if len(poly)<3:
        return set()
    xs=[p[0] for p in poly]
    zs=[p[1] for p in poly]
    out=set()
    for x in range(math.floor(min(xs)),math.ceil(max(xs))+1):
        for z in range(math.floor(min(zs)),math.ceil(max(zs))+1):
            if point_in_polygon(x+0.5,z+0.5,poly):
                out.add((x,z))
    return out


def distance_point_segment(px,pz,ax,az,bx,bz):
    vx,vz=bx-ax,bz-az
    wx,wz=px-ax,pz-az
    den=vx*vx+vz*vz
    if den<=1e-12:
        return math.hypot(px-ax,pz-az)
    t=max(0.0,min(1.0,(wx*vx+wz*vz)/den))
    cx,cz=ax+t*vx,az+t*vz
    return math.hypot(px-cx,pz-cz)


def raster_line(coords: Sequence[Point], half_width: float, bounds) -> Set[Cell2]:
    if len(coords)<2:
        return set()
    min_x,min_z,max_x,max_z=bounds
    out=set()
    for x in range(math.floor(min_x),math.ceil(max_x)+1):
        for z in range(math.floor(min_z),math.ceil(max_z)+1):
            px,pz=x+0.5,z+0.5
            if min(distance_point_segment(px,pz,*coords[i],*coords[i+1]) for i in range(len(coords)-1)) <= half_width:
                out.add((x,z))
    return out


def boundary(cells: Set[Cell2]) -> Set[Cell2]:
    return {(x,z) for x,z in cells if any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}


def frontage(cells: Set[Cell2], side: str) -> List[Cell2]:
    byz={}
    for x,z in cells:
        byz.setdefault(z,[]).append(x)
    return [(min(xs) if side=="east" else max(xs),z) for z,xs in sorted(byz.items())]


def rearage(cells: Set[Cell2], side: str) -> List[Cell2]:
    byz={}
    for x,z in cells:
        byz.setdefault(z,[]).append(x)
    return [(max(xs) if side=="east" else min(xs),z) for z,xs in sorted(byz.items())]


def edge(cells: Set[Cell2], direction: str) -> List[Cell2]:
    if direction in ("north","south"):
        target=min(z for _x,z in cells) if direction=="north" else max(z for _x,z in cells)
        return sorted([(x,z) for x,z in cells if z==target])
    target=min(x for x,_z in cells) if direction=="west" else max(x for x,_z in cells)
    return sorted([(x,z) for x,z in cells if x==target],key=lambda p:p[1])


def nearest(target: float, vals: List[int]) -> int:
    return min(vals,key=lambda v:abs(v-target))


def positions(vals: List[int], fracs: List[float]) -> List[int]:
    vals=sorted(set(vals))
    if not vals:
        return []
    lo,hi=vals[0],vals[-1]
    return [nearest(lo+(hi-lo)*f,vals) for f in fracs]


def evenly(vals: List[int], count: int) -> List[int]:
    if count<=0:
        return []
    return positions(vals,[(i+1)/(count+1) for i in range(count)])


def setb(blocks: Dict[Cell3,str], x:int,y:int,z:int,state:str):
    blocks[(x,y,z)]=state


def slab(name: str, slab_type="bottom"):
    return f"{name}[type={slab_type},waterlogged=false]"


def stair(name: str, facing: str, half="bottom"):
    return f"{name}[facing={facing},half={half},shape=straight,waterlogged=false]"


def door_pair(name: str, facing: str):
    lower=f"{name}[facing={facing},half=lower,hinge=left,open=false,powered=false]"
    upper=f"{name}[facing={facing},half=upper,hinge=left,open=false,powered=false]"
    return lower,upper


def iron_door_pair(facing: str):
    return door_pair("minecraft:iron_door",facing)


def build_ground(local:dict,frame:dict,policy:dict)->Dict[Cell3,str]:
    pb=frame["plan_bounds_blocks"]
    bounds=(pb["min_x"],pb["min_z"],pb["max_x"],pb["max_z"])
    r=policy["roads"]
    blocks={}

    for feature in local["transport"]:
        role=feature.get("role")
        coords=[tuple(p) for p in feature.get("line_xz_m",[])]
        if len(coords)<2:
            continue
        if role=="main_street":
            width,mat=r["main_half_width_m"],"minecraft:black_concrete"
        elif role=="avenue":
            width,mat=r["avenue_half_width_m"],"minecraft:gray_concrete"
        elif role=="alley":
            width,mat=r["alley_half_width_m"],"minecraft:polished_andesite"
        elif role=="sidewalk":
            width,mat=r["sidewalk_half_width_m"],"minecraft:smooth_stone"
        elif role=="crossing":
            width,mat=r["crossing_half_width_m"],"minecraft:white_concrete"
        else:
            continue
        for x,z in raster_line(coords,float(width),bounds):
            setb(blocks,x,-1,z,mat)

    # Raised curb strip.
    for z in range(-8,-126,-1):
        setb(blocks,-10,0,z,slab("minecraft:smooth_stone_slab","bottom"))
        setb(blocks,10,0,z,slab("minecraft:smooth_stone_slab","bottom"))

    # Angled parking stripes.
    park=policy["parking"]
    if park.get("enabled"):
        spacing=int(park["stall_spacing_z"])
        length=int(park["stall_line_length"])
        for z0 in range(-16,-122,-spacing):
            for i in range(length):
                setb(blocks,-8+i,-1,z0-i,"minecraft:white_concrete")
                setb(blocks,8-i,-1,z0-i,"minecraft:white_concrete")

    setb(blocks,0,-1,0,"minecraft:red_concrete")
    return blocks


def add_streetscape(blocks:Dict[Cell3,str],policy:dict):
    s=policy["streetscape"]
    for x,z in s["lamp_positions"]:
        setb(blocks,x,0,z,"minecraft:polished_blackstone_wall")
        for y in (1,2,3):
            setb(blocks,x,y,z,"minecraft:iron_bars")
        setb(blocks,x,4,z,"minecraft:lantern[hanging=false,waterlogged=false]")

    for x,z in s["bench_positions"]:
        facing="east" if x<0 else "west"
        setb(blocks,x,0,z,stair("minecraft:spruce_stairs",facing))
        setb(blocks,x,0,z+1,stair("minecraft:spruce_stairs",facing))

    for x,z in s["planter_positions"]:
        setb(blocks,x,0,z,"minecraft:composter[level=8]")
        setb(blocks,x,1,z,"minecraft:flowering_azalea_leaves[distance=1,persistent=true,waterlogged=false]")


def material_for_subfacade(entry:dict,t:float,key:str,default:str):
    for sub in entry["front"].get("subfacades",[]):
        lo,hi=sub["range"]
        if lo <= t <= hi and key in sub:
            return sub[key]
    return default


def add_roof_equipment(blocks:Dict[Cell3,str], footprint:Set[Cell2], roof_y:int, program:list):
    xs=sorted(set(x for x,_z in footprint))
    zs=sorted(set(z for _x,z in footprint))
    if len(xs)<4 or len(zs)<4:
        return
    center_x=xs[len(xs)//2]
    center_z=zs[len(zs)//2]

    cursor=0
    for item in program:
        kind=item["type"]
        count=int(item.get("count",1))
        for n in range(count):
            dx=((cursor*3)%max(3,len(xs)//3))-1
            dz=((cursor*5)%max(3,len(zs)//3))-1
            x=nearest(center_x+dx,xs[1:-1] or xs)
            z=nearest(center_z+dz,zs[1:-1] or zs)
            cursor+=1
            if kind=="hvac":
                for ox in (0,1):
                    for oz in (0,1):
                        if (x+ox,z+oz) in footprint:
                            setb(blocks,x+ox,roof_y+1,z+oz,"minecraft:light_gray_concrete")
                setb(blocks,x,roof_y+2,z,"minecraft:iron_bars")
            elif kind=="vent":
                setb(blocks,x,roof_y+1,z,"minecraft:polished_blackstone_wall")
                setb(blocks,x,roof_y+2,z,"minecraft:iron_bars")
            elif kind=="chimney":
                setb(blocks,x,roof_y+1,z,"minecraft:bricks")
                setb(blocks,x,roof_y+2,z,"minecraft:bricks")
            elif kind=="skylight":
                for ox in (0,1):
                    for oz in (0,1):
                        if (x+ox,z+oz) in footprint:
                            setb(blocks,x+ox,roof_y,z+oz,"minecraft:light_blue_stained_glass")
            elif kind=="access":
                for ox in (0,1):
                    for oz in (0,1):
                        if (x+ox,z+oz) in footprint:
                            setb(blocks,x+ox,roof_y+1,z+oz,"minecraft:stone_bricks")
                setb(blocks,x,roof_y+2,z,"minecraft:stone_bricks")


def add_rear_service(blocks:Dict[Cell3,str],footprint:Set[Cell2],entry:dict):
    rear=rearage(footprint,entry["side"])
    if not rear:
        return
    zs=sorted(set(z for _x,z in rear))
    front_side=entry["side"]
    outward="east" if front_side=="east" else "west"
    outward_dx=1 if front_side=="east" else -1
    rprog=entry["rear"]
    door_zs=positions(zs,[(i+1)/(rprog["doors"]+1) for i in range(rprog["doors"])]) if rprog["doors"] else []
    win_zs=positions(zs,[(i+1)/(rprog["windows"]+1) for i in range(rprog["windows"])]) if rprog["windows"] else []
    lower,upper=iron_door_pair(outward)

    for x,z in rear:
        if z in door_zs:
            setb(blocks,x,1,z,lower)
            setb(blocks,x,2,z,upper)
            if rprog.get("canopy"):
                setb(blocks,x+outward_dx,3,z,slab("minecraft:smooth_stone_slab"))
        elif z in win_zs:
            setb(blocks,x,2,z,"minecraft:gray_stained_glass")
        # Rear parapet cap.
        setb(blocks,x,entry["height"],z,slab("minecraft:smooth_stone_slab","top"))


def add_side_windows(blocks,footprint,direction,height,glass,storeys):
    side=edge(footprint,direction)
    if not side:
        return
    axis=[x for x,_z in side] if direction in ("north","south") else [z for _x,z in side]
    vals=sorted(set(axis))
    centers=evenly(vals,3 if len(vals)>10 else 2)
    for x,z in side:
        axis_val=x if direction in ("north","south") else z
        if any(abs(axis_val-c)<=1 for c in centers):
            for y in (1,2):
                if y<height:
                    setb(blocks,x,y,z,glass)
            if storeys>=2:
                for y in (5,6):
                    if y<height:
                        setb(blocks,x,y,z,glass)


def parapet_profile(blocks,front,entry,street_dx,zmin,zmax):
    p=entry["front"]["parapet"]
    style=p["style"]
    mat=p["material"]
    h=entry["height"]
    span=max(1,zmax-zmin)
    mid=(zmin+zmax)/2

    for x,z in front:
        # Base parapet
        setb(blocks,x,h+1,z,mat)

        t=(z-zmin)/span
        if style in ("flat_piers","north_historic") and (int(round(t*entry["front"]["bays"])) % 2 == 0):
            setb(blocks,x,h+2,z,mat)

        elif style=="stepped_center":
            if 0.20<=t<=0.80:
                setb(blocks,x,h+2,z,mat)
            if 0.40<=t<=0.60:
                setb(blocks,x,h+3,z,mat)

        elif style=="historic_crest":
            if 0.16<=t<=0.84:
                setb(blocks,x,h+2,z,entry["materials"]["wall"])
            if 0.42<=t<=0.58:
                setb(blocks,x,h+3,z,mat)

        elif style=="bank_civic":
            if 0.15<=t<=0.85:
                setb(blocks,x,h+2,z,mat)
            if 0.35<=t<=0.65:
                setb(blocks,x,h+3,z,entry["materials"]["wall"])
            if 0.45<=t<=0.55:
                setb(blocks,x,h+4,z,mat)

        elif style=="paired_crest":
            # Each half gets an independent crest.
            local=t if t<0.5 else t-0.5
            if t>=0.5:
                local*=2
            else:
                local*=2
            if 0.12<=local<=0.88:
                setb(blocks,x,h+2,z,mat)
            if 0.38<=local<=0.62:
                setb(blocks,x,h+3,z,entry["materials"]["wall"])
            if 0.46<=local<=0.54:
                setb(blocks,x,h+4,z,mat)

        elif style=="midcentury_band":
            setb(blocks,x,h+1,z,entry["materials"]["secondary"])

        elif style in ("low_modern","modern_low","restaurant_low","office_flat","boutique_low","wide_low"):
            # Keep these deliberately flatter.
            pass

    # Projecting cornice line.
    cornice=slab("minecraft:smooth_stone_slab","top")
    for x,z in front:
        setb(blocks,x+street_dx,h+1,z,cornice)


def build_front(blocks,footprint,entry):
    front=frontage(footprint,entry["side"])
    if not front:
        return
    zs=sorted(set(z for _x,z in front))
    zmin,zmax=zs[0],zs[-1]
    span=max(1,zmax-zmin)
    street_dx=-1 if entry["side"]=="east" else 1
    facing="west" if entry["side"]=="east" else "east"
    m=entry["materials"]
    f=entry["front"]
    h=entry["height"]
    storeys=entry["storeys"]

    doors=set(positions(zs,f["door_fracs"]))
    bay_centers=evenly(zs,f["bays"])
    upper_centers=evenly(zs,f["upper_windows"])
    lower_door,upper_door=door_pair(m["door"],facing)

    for x,z in front:
        t=(z-zmin)/span
        base=material_for_subfacade(entry,t,"base",m["base"])
        trim=material_for_subfacade(entry,t,"trim",m["trim"])
        secondary=material_for_subfacade(entry,t,"secondary",m["secondary"])
        support=any(abs(z-c)<=0 for c in bay_centers)

        setb(blocks,x,0,z,base)

        if z in doors:
            setb(blocks,x,1,z,lower_door)
            setb(blocks,x,2,z,upper_door)
        else:
            for y in (1,2):
                setb(blocks,x,y,z,secondary if support else m["glass"])

        # Transom/sign band is individualized by material.
        if 3<h:
            setb(blocks,x,3,z,trim)

        # Upper windows use explicit centers rather than lower-bay repetition.
        if storeys>=2:
            for y in range(4,h):
                is_window=any(abs(z-c)<=1 for c in upper_centers) and y in (5,6,7)
                if is_window:
                    setb(blocks,x,y,z,m["glass"])
                else:
                    setb(blocks,x,y,z,m["wall"])

            # Stone lintel and sill around each upper group.
            if any(abs(z-c)<=1 for c in upper_centers):
                if 4<h:
                    setb(blocks,x+street_dx,4,z,slab("minecraft:smooth_stone_slab"))
                if 8<h:
                    setb(blocks,x+street_dx,8,z,slab("minecraft:smooth_stone_slab","top"))

    # Awning segments.
    awn=f["awning"]
    if awn.get("material"):
        default_state=slab(awn["material"])
        for x,z in front:
            t=(z-zmin)/span
            for lo,hi in awn["ranges"]:
                if lo<=t<=hi:
                    mat=material_for_subfacade(entry,t,"awning",awn["material"])
                    setb(blocks,x+street_dx,awn["y"],z,slab(mat))
                    break

    parapet_profile(blocks,front,entry,street_dx,zmin,zmax)

    # Special bank portal.
    if f["parapet"]["style"]=="bank_civic":
        center=nearest((zmin+zmax)/2,zs)
        for x,z in front:
            if abs(z-center)<=2:
                for y in range(0,min(h,9)):
                    if abs(z-center)==2:
                        setb(blocks,x,y,z,"minecraft:smooth_sandstone")
                if z==center:
                    setb(blocks,x,0,z,"minecraft:stone_bricks")
                    setb(blocks,x,1,z,lower_door)
                    setb(blocks,x,2,z,upper_door)
        # Broad sandstone horizontal bank course.
        for x,z in front:
            setb(blocks,x,4,z,"minecraft:smooth_sandstone")

    # Paired 625/627 internal visual split at midpoint.
    if f["parapet"]["style"]=="paired_crest":
        mid=nearest((zmin+zmax)/2,zs)
        for x,z in front:
            if abs(z-mid)<=0:
                for y in range(0,h+3):
                    setb(blocks,x,y,z,m["trim"])


def add_internal_divider(blocks,footprint,entry):
    if entry["front"]["parapet"]["style"]!="paired_crest":
        return
    zs=sorted(set(z for _x,z in footprint))
    mid=nearest((zs[0]+zs[-1])/2,zs)
    xs=sorted(set(x for x,z in footprint if z==mid))
    if not xs:
        xs=sorted(set(x for x,_z in footprint))
    for x in xs:
        if (x,mid) in footprint:
            for y in range(0,entry["height"]):
                setb(blocks,x,y,mid,"minecraft:bricks")


def build_primary(blocks,footprint,entry):
    h=entry["height"]
    m=entry["materials"]
    bnd=boundary(footprint)

    # Hollow shell + roof.
    for x,z in footprint:
        setb(blocks,x,-1,z,m["base"])
        setb(blocks,x,h,z,"minecraft:polished_deepslate")
    for x,z in bnd:
        for y in range(h):
            setb(blocks,x,y,z,m["wall"])

    build_front(blocks,footprint,entry)
    add_rear_service(blocks,footprint,entry)
    add_internal_divider(blocks,footprint,entry)

    if entry.get("exposed_side"):
        add_side_windows(blocks,footprint,entry["exposed_side"],h,m["glass"],entry["storeys"])

    add_roof_equipment(blocks,footprint,h,entry["roof"])


def build_rear_addition(blocks,footprint,parent,height):
    wall=parent["materials"]["wall"]
    bnd=boundary(footprint)
    for x,z in footprint:
        setb(blocks,x,-1,z,wall)
        setb(blocks,x,height,z,"minecraft:deepslate_tiles")
    for x,z in bnd:
        for y in range(height):
            setb(blocks,x,y,z,wall)
    # One obvious service door on rear-most edge.
    rear=rearage(footprint,parent["side"])
    if rear:
        zs=sorted(set(z for _x,z in rear))
        dz=nearest((zs[0]+zs[-1])/2,zs)
        facing="east" if parent["side"]=="east" else "west"
        lower,upper=iron_door_pair(facing)
        for x,z in rear:
            if z==dz:
                setb(blocks,x,1,z,lower)
                setb(blocks,x,2,z,upper)
                break


def validate_coverage(local,spec):
    geo={int(x["osm_id"]) for x in local["buildings"]}
    ids={int(x["osm_id"]) for x in spec["entries"]}|{int(x["osm_id"]) for x in spec["secondary"]}
    if ids!=geo:
        raise ValueError(f"Truth spec coverage mismatch missing={sorted(geo-ids)} extra={sorted(ids-geo)}")


def self_test():
    fp={(x,z) for x in range(3,14) for z in range(-14,-2)}
    entry={
        "side":"west","height":10,"storeys":2,
        "materials":{
            "wall":"minecraft:bricks","base":"minecraft:dark_prismarine",
            "trim":"minecraft:smooth_sandstone","glass":"minecraft:black_stained_glass",
            "door":"minecraft:dark_oak_door","secondary":"minecraft:bricks"
        },
        "front":{
            "bays":4,"door_fracs":[0.35],"upper_windows":4,
            "awning":{"material":"minecraft:dark_prismarine_slab","ranges":[[0.05,0.95]],"y":4},
            "parapet":{"style":"north_historic","material":"minecraft:bricks","extra":3},
            "subfacades":[]
        },
        "roof":[{"type":"hvac","count":1},{"type":"chimney","count":1},{"type":"skylight","count":1}],
        "rear":{"doors":1,"windows":2,"canopy":True},
        "exposed_side":"north",
        "visual_confidence":"photo_supported"
    }
    blocks={}
    build_primary(blocks,fp,entry)
    assert any("dark_oak_door[" in s for s in blocks.values())
    assert any("dark_prismarine_slab[" in s for s in blocks.values())
    assert any(s=="minecraft:light_gray_concrete" for s in blocks.values())
    assert any(y>=12 for _x,y,_z in blocks)
    print("L1_TRUTH_SELF_TEST_PASS",len(blocks))
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        return self_test()

    local=load_json(LOCAL_IN)
    frame=load_json(FRAME_IN)
    spec=load_json(SPEC_IN)
    policy=load_json(POLICY_IN)
    codec=load_codec()
    validate_coverage(local,spec)

    geom={int(x["osm_id"]):x for x in local["buildings"]}
    entries={int(x["osm_id"]):x for x in spec["entries"]}
    blocks=build_ground(local,frame,policy)

    model=[]
    for entry in spec["entries"]:
        oid=int(entry["osm_id"])
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        build_primary(blocks,fp,entry)
        model.append({
            "osm_id":oid,
            "addresses":entry["addresses"],
            "name":entry["name"],
            "height":entry["height"],
            "storeys":entry["storeys"],
            "visual_confidence":entry["visual_confidence"],
            "footprint_cells":len(fp),
            "parapet_style":entry["front"]["parapet"]["style"],
            "roof_program":entry["roof"],
            "rear_program":entry["rear"]
        })

    for rear in spec["secondary"]:
        oid=int(rear["osm_id"])
        parent=entries[int(rear["parent_osm_id"])]
        fp=raster_polygon([tuple(p) for p in geom[oid]["polygon_xz_m"]])
        build_rear_addition(blocks,fp,parent,int(rear["height"]))
        model.append({
            "osm_id":oid,"parent_osm_id":rear["parent_osm_id"],
            "profile":"rear_addition","height":rear["height"],
            "visual_confidence":"inferred","footprint_cells":len(fp)
        })

    add_streetscape(blocks,policy)

    ref=frame["future_litematica_registration"]
    ref_x,ref_z=int(ref["player_feet_x"]),int(ref["player_feet_z"])
    schematic={(x-ref_x,y,z-ref_z):state for (x,y,z),state in blocks.items()}
    marker=tuple(policy["registration"]["marker_schematic"])
    marker_block=policy["registration"]["marker_block"]
    schematic[marker]=marker_block

    pb=frame["plan_bounds_blocks"]
    min_x,max_x=int(pb["min_x"])-ref_x,int(pb["max_x"])-ref_x
    min_z,max_z=int(pb["min_z"])-ref_z,int(pb["max_z"])-ref_z
    max_y=max(y for _x,y,_z in schematic)

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    info=codec.write_single_region_litematic(
        OUT_FILE,schematic,(min_x,-1,min_z,max_x,max_y,max_z),
        "REDFIELD_POC_001_L1_TRUTH_V005",
        "Redfield POC 001 - L1 Truth v005",
        "Building-specific normal-block Redfield truth pass. No Microblocks.",
        4903,6,1
    )

    back,meta=codec.read_back_block_map(OUT_FILE,"REDFIELD_POC_001_L1_TRUTH_V005")
    normalized={c:codec.canonical_state(s) for c,s in schematic.items()}
    exact=back==normalized
    marker_ok=back.get(marker)==marker_block
    if not exact:
        missing=set(normalized.items())-set(back.items())
        extra=set(back.items())-set(normalized.items())
        raise ValueError(f"Read-back mismatch missing={len(missing)} extra={len(extra)}")
    if not marker_ok:
        raise ValueError("Registration marker failed")

    confidence={}
    for e in spec["entries"]:
        confidence[e["visual_confidence"]]=confidence.get(e["visual_confidence"],0)+1

    MODEL_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":spec["export_id"],
        "entries":model
    },indent=2)+"\n",encoding="utf-8")

    report={
        "schema_version":1,
        "export_id":spec["export_id"],
        "status":"valid",
        "file":str(OUT_FILE.relative_to(ROOT)).replace("\\","/"),
        "sha256":info["sha256"],
        "region_position":info["region_position"],
        "region_size":info["region_size"],
        "non_air_blocks":info["non_air_blocks"],
        "palette_size":len(info["palette"]),
        "stateful_palette_entries":sum(1 for s in info["palette"] if "[" in s),
        "primary_sites":len(spec["entries"]),
        "secondary_structures":len(spec["secondary"]),
        "visual_confidence_counts":confidence,
        "roof_equipment_items":sum(sum(int(x.get("count",1)) for x in e["roof"]) for e in spec["entries"]),
        "checks":{
            "truth_spec_covers_geometry":True,
            "exact_block_map":exact,
            "registration_marker":marker_ok,
            "microblocks_used":False,
            "building_specific_programs":True,
            "rear_service_architecture":True
        },
        "registration":{
            "marker_position":list(marker),
            "marker_block":marker_block,
            "verified":marker_ok
        },
        "errors":[]
    }
    REPORT_OUT.parent.mkdir(parents=True,exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

    MANIFEST_OUT.write_text(json.dumps({
        "schema_version":1,
        "export_id":spec["export_id"],
        "file":report["file"],
        "sha256":report["sha256"],
        "region_position":report["region_position"],
        "region_size":report["region_size"],
        "placement":{
            "instruction":"Stand on existing yellow registration block and set placement origin to player feet.",
            "rotation":0,"mirror":"none","replace_blocks":"ALL"
        },
        "review_targets":[
            "Does north historic group resemble the 2023 downtown photo?",
            "Does City Hall finally read as a landmark?",
            "Does Leo read as a low corner diner rather than generic storefront?",
            "Are roof silhouettes sufficiently varied?",
            "Do rear/alley elevations feel believable?",
            "Which inferred facades need direct Street View correction next?"
        ]
    },indent=2)+"\n",encoding="utf-8")

    print("EarthForge Redfield POC 001 L1 Truth v005 generated and validated.")
    print(f"  File                : {report['file']}")
    print(f"  SHA256              : {report['sha256']}")
    print(f"  Region pos          : {report['region_position']}")
    print(f"  Region size         : {report['region_size']}")
    print(f"  Non-air blocks      : {report['non_air_blocks']}")
    print(f"  Palette size        : {report['palette_size']}")
    print(f"  Stateful palette    : {report['stateful_palette_entries']}")
    print(f"  Roof detail items   : {report['roof_equipment_items']}")
    print(f"  Photo-supported     : {confidence.get('photo_supported',0)}")
    print(f"  History-supported   : {confidence.get('history_supported',0)}")
    print(f"  Inferred            : {confidence.get('inferred',0)}")
    print(f"  Marker              : {list(marker)} {marker_block}")
    print("  Read-back           : PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
