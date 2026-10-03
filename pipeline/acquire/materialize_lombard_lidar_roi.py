"""Materialize the canonical Lombard LiDAR ROI from NOAA's public COPC object.

The raw tile and derived NPZ remain gitignored. This script reproduces the ROI
used by prepare_lombard_poc001_sources.py and verifies it against tracked L0
source-truth counts before downstream use.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from laspy.copc import Bounds, CopcReader

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
RAW=PROJECT/"downloads"/"raw"
OUT=RAW/"lombard_poc001_lidar_roi_v001.npz"
COPC_URL="https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/laz/geoid18/584/20100225_C5505_41835_ld_p1005.copc.laz"

def main():
    RAW.mkdir(parents=True,exist_ok=True)
    truth=json.loads((PROJECT/"poc_001/l0_source_truth_v001.json").read_text())
    expected=truth["lidar"]
    anchor=truth["coordinate_frame"]["anchor_epsg3717_m"]
    ae=float(anchor["easting"]);an=float(anchor["northing"])
    xmin,xmax=ae-45,ae+190
    ymin,ymax=an-80,an+90
    with CopcReader.open(COPC_URL,http_num_threads=10) as cr:
        pts=cr.query(Bounds(np.array([xmin,ymin]),np.array([xmax,ymax])))
    arr=np.column_stack((
        np.asarray(pts.x)-ae,
        an-np.asarray(pts.y),
        np.asarray(pts.z),
        np.asarray(pts.classification),
        np.asarray(pts.return_number),
        np.asarray(pts.number_of_returns),
    ))
    classes={str(int(k)):int(v) for k,v in zip(*np.unique(arr[:,3].astype(int),return_counts=True))}
    if int(arr.shape[0])!=int(expected["roi_points"]):
        raise SystemExit(f"ROI point count mismatch: {arr.shape[0]} != {expected['roi_points']}")
    if classes!={str(k):int(v) for k,v in expected["class_counts"].items()}:
        raise SystemExit(f"ROI class counts mismatch: {classes} != {expected['class_counts']}")
    np.savez_compressed(
        OUT,
        x=arr[:,0].astype(np.float32),
        z=arr[:,1].astype(np.float32),
        elev=arr[:,2].astype(np.float32),
        classification=arr[:,3].astype(np.uint8),
        return_number=arr[:,4].astype(np.uint8),
        num_returns=arr[:,5].astype(np.uint8),
    )
    print(json.dumps({
        "source":COPC_URL,
        "output":str(OUT.relative_to(ROOT)),
        "roi_points":int(arr.shape[0]),
        "class_counts":classes,
        "verified_against":"projects/lombard_sf/poc_001/l0_source_truth_v001.json",
    },indent=2))

if __name__=="__main__":main()
