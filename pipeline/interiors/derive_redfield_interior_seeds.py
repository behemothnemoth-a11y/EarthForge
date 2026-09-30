#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"redfield_sd"
POC=PROJECT/"poc_001"
LOCAL=POC/"l0_geometry_local.json"
TRUTH=POC/"truth_v005.json"
PROGRAM=POC/"interior_program_v001.json"
OUT=POC/"interior_seed_v001.json"
REPORT=PROJECT/"validation"/"poc001_interior_readiness_v001.json"


def load(p): return json.loads(p.read_text(encoding="utf-8"))


def main():
    local=load(LOCAL); truth=load(TRUTH); prog=load(PROGRAM)
    geom={int(x["osm_id"]):x for x in local["buildings"]}
    truth_by={int(x["osm_id"]):x for x in truth["entries"]}
    seeds=[]

    for p in prog["programs"]:
        oid=int(p["osm_id"]); e=truth_by[oid]
        poly=e_poly=geom[oid]["polygon_xz_m"]
        xs=[x for x,z in poly]; zs=[z for x,z in poly]
        minx,maxx,minz,maxz=min(xs),max(xs),min(zs),max(zs)
        frac=float(p["ground_floor"]["front_depth_fraction"])
        side=e["side"]

        if side=="east":
            split=minx+(maxx-minx)*frac
            front_box=[minx,minz,split,maxz]
            rear_box=[split,minz,maxx,maxz]
            stair_x=maxx-2
        else:
            split=maxx-(maxx-minx)*frac
            front_box=[split,minz,maxx,maxz]
            rear_box=[minx,minz,split,maxz]
            stair_x=minx+2

        stair_z=minz+2
        floor_height=max(4, round(e["height"]/max(1,e["storeys"])))

        seeds.append({
            "osm_id":oid,
            "addresses":p["addresses"],
            "category":p["category"],
            "facade_side":side,
            "footprint_local_bounds":[round(minx,3),round(minz,3),round(maxx,3),round(maxz,3)],
            "floor_height_blocks":floor_height,
            "storeys":e["storeys"],
            "ground_floor_zones":{
                "front":{"label":p["ground_floor"]["front_zone"],"box":[round(v,3) for v in front_box]},
                "rear":{"label":p["ground_floor"]["rear_zone"],"box":[round(v,3) for v in rear_box]}
            },
            "stair_seed":{"x":round(stair_x,3),"z":round(stair_z,3),"strategy":p["vertical_circulation"]},
            "upper_floor":p["upper_floor"],
            "generate_blocks_now":False,
            "confidence":p["interior_confidence"]
        })

    OUT.write_text(json.dumps({
        "schema_version":1,
        "seed_id":"REDFIELD_POC_001_INTERIOR_SEED_V001",
        "status":"planning_only",
        "seeds":seeds
    },indent=2)+"\n",encoding="utf-8")

    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({
        "schema_version":1,
        "status":"ready_for_review",
        "building_programs":len(seeds),
        "blocks_generated":0,
        "all_primary_buildings_covered":len(seeds)==len(truth["entries"]),
        "next_gate":"Exterior building pipeline approval before I2 block interior generation"
    },indent=2)+"\n",encoding="utf-8")

    print("INTERIOR_SEEDS_PASS",len(seeds),"programs; 0 blocks generated")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
