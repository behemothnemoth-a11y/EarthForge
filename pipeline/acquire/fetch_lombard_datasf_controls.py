#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "lombard_sf"
RAW = PROJECT / "references" / "raw" / "datasf_streets_active_lombard_hyde_leavenworth.json"
DERIVED = PROJECT / "roads" / "datasf_street_controls_v001.geojson"
MANIFEST = PROJECT / "source_manifests" / "datasf_streets_controls_v001.json"

DATASET = "3psu-pn9h"
BASE = f"https://data.sfgov.org/resource/{DATASET}.json"

def fetch() -> list[dict]:
    params = {
        "$select": "cnn,street,st_type,f_st,t_st,f_node_cnn,t_node_cnn,oneway,line,data_as_of",
        "$where": "active=true AND street in('LOMBARD','HYDE','LEAVENWORTH')",
        "$limit": "5000",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)

def coords(rec: dict):
    geom = rec.get("line") or {}
    return geom.get("coordinates") or []

def bbox_hit(points, west=-122.4210, south=37.8008, east=-122.4170, north=37.8032):
    for lon, lat in points:
        if west <= lon <= east and south <= lat <= north:
            return True
    return False

def main():
    records = fetch()
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    selected = [r for r in records if bbox_hit(coords(r))]
    features = []
    for r in selected:
        features.append({
            "type": "Feature",
            "properties": {k: r.get(k) for k in ("cnn","street","st_type","f_st","t_st","f_node_cnn","t_node_cnn","oneway","data_as_of")},
            "geometry": r.get("line"),
        })
    fc = {"type":"FeatureCollection","name":"datasf_street_controls_v001","features":features}
    DERIVED.parent.mkdir(parents=True, exist_ok=True)
    DERIVED.write_text(json.dumps(fc, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version":1,
        "source_id":"datasf_streets_active_retired_3psu-pn9h",
        "dataset_id":DATASET,
        "dataset_url":"https://data.sfgov.org/Geographic-Locations-and-Boundaries/Streets-Active-and-Retired/3psu-pn9h",
        "query_streets":["LOMBARD","HYDE","LEAVENWORTH"],
        "query_active":True,
        "selection_bbox_wgs84":[-122.4210,37.8008,-122.4170,37.8032],
        "raw_record_count":len(records),
        "selected_record_count":len(selected),
        "derived_geojson":str(DERIVED.relative_to(ROOT)).replace("\\","/"),
        "raw_local_file":str(RAW.relative_to(ROOT)).replace("\\","/"),
        "raw_git_ignored":True,
        "purpose":"Authoritative city street centerline controls for Lombard/Hyde/Leavenworth intersection lock.",
        "confidence":"high for city-maintained street centerline control; not a cadastral/survey replacement",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"selected":len(selected),"streets":sorted({r.get("street") for r in selected}),"records":selected}, indent=2))

if __name__ == "__main__":
    main()
