#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"redfield_sd"
POC=PROJECT/"poc_001"
LOCAL=POC/"l0_geometry_local.json"
TRUTH=POC/"truth_v005.json"
MICRO=POC/"micro_v006.json"
INTERIOR=POC/"interior_seed_v001.json"
SOURCES=PROJECT/"source_manifests"/"redfield_poc001_truth_v005.json"
OUT=POC/"build_studio_jobs_v001.json"


def load(p): return json.loads(p.read_text(encoding="utf-8"))


def main():
    local=load(LOCAL); truth=load(TRUTH); micro=load(MICRO); interior=load(INTERIOR)
    geom={int(x["osm_id"]):x for x in local["buildings"]}
    iseed={int(x["osm_id"]):x for x in interior["seeds"]}
    priority={int(x["osm_id"]):x for x in micro["priority"]}

    jobs=[]
    for e in truth["entries"]:
        oid=int(e["osm_id"])
        jobs.append({
            "building_id":f"redfield_sd_osm_{oid}",
            "osm_id":oid,
            "addresses":e["addresses"],
            "name":e["name"],
            "footprint":{
                "local_xz_m":geom[oid]["polygon_xz_m"],
                "source_tags":geom[oid].get("tags",{})
            },
            "facade":{
                "side":e["side"],
                "height_blocks":e["height"],
                "storeys":e["storeys"],
                "program":e["front"],
                "materials":e["materials"]
            },
            "micro_overlay":{
                "enabled":oid in priority,
                "program":priority.get(oid),
                "allowed_uses":["cornice","mullion","transom","pilaster","surround","thin_trim"]
            },
            "interior_program":iseed[oid],
            "confidence":{
                "visual":e["visual_confidence"],
                "footprint":"osm_reviewed",
                "height":"block-scale inferred/history-supported"
            },
            "earthforge_authority":[
                "world_position","orientation","footprint","registration_origin","final_export"
            ]
        })

    OUT.write_text(json.dumps({
        "schema_version":1,
        "job_set":"REDFIELD_POC_001_BUILD_STUDIO_V001",
        "jobs":jobs
    },indent=2)+"\n",encoding="utf-8")
    print("BUILD_STUDIO_JOBS_PASS",len(jobs),"jobs")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
