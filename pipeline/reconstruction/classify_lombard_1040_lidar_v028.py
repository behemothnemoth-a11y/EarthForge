"""Classify 1040 Lombard non-ground LiDAR by local surface roughness.

This is an observational B0/B1 aid only. "Planar candidate" does not mean roof,
and "rough candidate" does not prove vegetation. No Minecraft geometry is made.
"""
from __future__ import annotations
import json, math
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from shapely import contains_xy
from shapely.geometry import shape

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
OUT=PROJECT/"outputs"/"house_1040_source_truth_v027"
RAW=PROJECT/"downloads/raw/lombard_poc001_lidar_roi_v001.npz"
BUILDING_ID="201006.0032105"
CELL_M=0.35
NEIGHBOR_M=0.95

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if not RAW.exists():raise SystemExit("Canonical Lombard LiDAR ROI is not materialized")
    buildings=json.loads((PROJECT/"poc_001/l2_building_source_truth_v002.json").read_text())
    rec=next(b for b in buildings["buildings"] if b["sf16_bldgid"]==BUILDING_ID)
    geom=shape(rec["geometry_local"]);poly=max(geom.geoms,key=lambda g:g.area) if hasattr(geom,"geoms") else geom
    raw=np.load(RAW)
    inside=contains_xy(poly.buffer(.15),raw["x"],raw["z"])
    nonground=inside&(raw["classification"]!=2)
    x=raw["x"][nonground].astype(float);z=raw["z"][nonground].astype(float);e=raw["elev"][nonground].astype(float)
    if len(e)<100:raise SystemExit(f"Too few non-ground returns inside 1040 scope: {len(e)}")

    ix=np.floor(x/CELL_M).astype(int);iz=np.floor(z/CELL_M).astype(int)
    groups=defaultdict(list)
    for n,key in enumerate(zip(ix,iz)):groups[key].append(n)
    cells=[]
    for (gx,gz),idx in groups.items():
        vals=e[idx]
        cells.append({
            "gx":int(gx),"gz":int(gz),"x_m":float((gx+.5)*CELL_M),"z_m":float((gz+.5)*CELL_M),
            "count":len(idx),"median_elev_m":float(np.median(vals)),
            "vertical_span_m":float(np.percentile(vals,95)-np.percentile(vals,5))
        })
    centers=np.array([[c["x_m"],c["z_m"]] for c in cells],float)
    heights=np.array([c["median_elev_m"] for c in cells],float)
    tree=cKDTree(centers)
    labels={"planar_candidate":0,"rough_candidate":0,"uncertain":0,"insufficient_support":0}
    planar_elev=[]
    for i,c in enumerate(cells):
        ids=tree.query_ball_point(centers[i],NEIGHBOR_M)
        if len(ids)<6:
            label="insufficient_support";rms=None
        else:
            p=centers[ids];h=heights[ids]
            A=np.c_[p[:,0]-centers[i,0],p[:,1]-centers[i,1],np.ones(len(ids))]
            coef,*_=np.linalg.lstsq(A,h,rcond=None)
            resid=h-A@coef;rms=float(np.sqrt(np.mean(resid*resid)))
            span=c["vertical_span_m"]
            interior=poly.buffer(-.45).covers(shape({"type":"Point","coordinates":[c["x_m"],c["z_m"]]})) if not poly.buffer(-.45).is_empty else True
            if rms<=.15 and span<=.35 and interior:
                label="planar_candidate";planar_elev.append(c["median_elev_m"])
            elif rms>=.32 or span>=.70:
                label="rough_candidate"
            else:label="uncertain"
        c["local_plane_rms_m"]=rms;c["label"]=label;labels[label]+=1

    modes=[]
    if planar_elev:
        vals=np.array(planar_elev)
        lo=math.floor(vals.min()*4)/4;hi=math.ceil(vals.max()*4)/4
        edges=np.arange(lo,hi+.26,.25);hist,_=np.histogram(vals,edges)
        for k in np.argsort(hist)[::-1][:8]:
            if hist[k]==0:continue
            modes.append({"bin_min_navd88_m":float(edges[k]),"bin_max_navd88_m":float(edges[k+1]),"cell_count":int(hist[k])})

    report={
        "schema_version":1,"building_id":BUILDING_ID,
        "method":{"cell_m":CELL_M,"neighbor_radius_m":NEIGHBOR_M,
                  "planar_rule":"local plane RMS <= 0.15 m, within-cell p95-p05 span <= 0.35 m, and >=0.45 m inside footprint",
                  "rough_rule":"local plane RMS >= 0.32 m OR within-cell p95-p05 span >= 0.70 m",
                  "warning":"Heuristic observational classification only. Planar candidate is not automatically roof/building; rough candidate is not automatically vegetation."},
        "non_ground_returns_in_scope":int(len(e)),"cell_count":len(cells),"label_counts":labels,
        "planar_candidate_fraction":float(labels["planar_candidate"]/max(1,len(cells))),
        "candidate_surface_elevation_modes":modes,
        "cells":cells
    }
    (OUT/"Lombard_1040_LiDAR_Surface_Classification_v028.json").write_text(json.dumps(report,indent=2)+"\n")

    minx,minz,maxx,maxz=poly.bounds;W=1000;H=1000
    def pxy(xx,zz):return (int(30+(xx-minx)/max(1e-9,maxx-minx)*(W-60)),int(30+(zz-minz)/max(1e-9,maxz-minz)*(H-60)))
    im=Image.new("RGB",(W,H),"white");d=ImageDraw.Draw(im)
    colors={"planar_candidate":(55,115,165),"rough_candidate":(151,92,65),"uncertain":(155,155,145),"insufficient_support":(215,215,210)}
    for c in cells:
        px,py=pxy(c["x_m"],c["z_m"]);r=3
        d.rectangle((px-r,py-r,px+r,py+r),fill=colors[c["label"]])
    d.line([pxy(a,b) for a,b in poly.exterior.coords],fill=(20,30,35),width=4)
    d.text((25,8),"1040 LiDAR roughness proxy — blue planar candidate, brown rough candidate; observational only",fill=(20,30,35))
    im.save(OUT/"Lombard_1040_LiDAR_Surface_Classification_v028.png")
    print(json.dumps({"returns":len(e),"cells":len(cells),"labels":labels,
                      "planar_fraction":report["planar_candidate_fraction"],
                      "output":str(OUT.relative_to(ROOT))},indent=2))

if __name__=="__main__":main()
