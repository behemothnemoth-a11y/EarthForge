#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
RAW=PROJECT/"references"/"raw"/"datasf_lombard_width_sources_v001.json"
ROW_OUT=PROJECT/"roads"/"datasf_row_lombard_v001.geojson"
META_OUT=PROJECT/"source_manifests"/"datasf_lombard_width_sources_v001.json"
CNNS=(8448000,8449000)

def get(dataset, params):
    url=f"https://data.sfgov.org/resource/{dataset}.json?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=60) as r:
        return json.load(r),url

def main():
    row,row_url=get("h8n7-e4ns",{"$select":"cnn,cnntext,shape_area,shape_leng,distance,the_geom","$where":"cnn in (8448000,8449000)","$limit":"50"})
    sw,sw_url=get("4g86-grxu",{"$select":"cnn,street,st_type,width_min,width_reco,sidewalk_f,side,shape,data_as_of","$where":"cnn in ('8448000','8449000')","$limit":"50"})
    RAW.parent.mkdir(parents=True,exist_ok=True)
    RAW.write_text(json.dumps({"row":row,"sidewalk":sw},indent=2)+"\n",encoding="utf-8")
    features=[{"type":"Feature","properties":{k:r.get(k) for k in ("cnn","cnntext","shape_area","shape_leng","distance")},"geometry":r["the_geom"]} for r in row]
    ROW_OUT.parent.mkdir(parents=True,exist_ok=True)
    ROW_OUT.write_text(json.dumps({"type":"FeatureCollection","name":"datasf_row_lombard_v001","features":features},indent=2)+"\n",encoding="utf-8")
    actual={r["cnn"]:{"actual_sidewalk_width_ft":float(r["sidewalk_f"]),"side":r["side"],"minimum_ft":float(r["width_min"]),"recommended_ft":float(r["width_reco"]),"data_as_of":r.get("data_as_of")} for r in sw}
    meta={"schema_version":1,"project_id":"lombard_sf","row_source":{"dataset":"h8n7-e4ns","url":row_url,"note":"2014 ROW analysis; not engineering survey accuracy"},"sidewalk_source":{"dataset":"4g86-grxu","url":sw_url,"field_definition":"SIDEWALK_F is actual sidewalk width in feet; negative means variable, most zero means unknown"},"segments":actual,"derived_row_geojson":str(ROW_OUT.relative_to(ROOT)).replace("\\","/"),"raw_local_file":str(RAW.relative_to(ROOT)).replace("\\","/"),"raw_git_ignored":True}
    META_OUT.write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(meta,indent=2))
if __name__=="__main__": main()
