"""Refine visually triaged 1040 machine tracks to local image corners.

This stage improves image-coordinate repeatability only. It does not name
architectural dimensions, triangulate depth, or authorize Minecraft geometry.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
OUT=PROJECT/"outputs"/"house_1040_source_truth_v027"
REVIEW=PROJECT/"source_manifests/1040_lombard_candidate_track_review_v029.json"
REFREG=OUT/"Lombard_1040_Reference_Resolution_v027.json"
GENERIC=OUT/"Lombard_1040_Multiview_Track_Candidates_v028.json"
CORNERS=OUT/"Lombard_1040_Corner_Track_Candidates_v029.json"
SEARCH_RADIUS_PX=34.0


def load_tracks(path):
    data=json.loads(path.read_text())
    return {t["candidate_id"]:t for t in data.get("tracks",[])}


def refine_point(gray, x, y):
    h,w=gray.shape
    r=int(SEARCH_RADIUS_PX)
    x0=max(0,int(round(x))-r);x1=min(w,int(round(x))+r+1)
    y0=max(0,int(round(y))-r);y1=min(h,int(round(y))+r+1)
    patch=gray[y0:y1,x0:x1]
    if patch.size==0:
        return None
    corners=cv2.goodFeaturesToTrack(
        patch,maxCorners=60,qualityLevel=.006,minDistance=4,blockSize=7,useHarrisDetector=False
    )
    if corners is None:
        return None
    pts=corners.reshape(-1,2).astype(np.float32)
    cv2.cornerSubPix(
        patch,pts,(5,5),(-1,-1),
        (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,30,.01)
    )
    pts[:,0]+=x0;pts[:,1]+=y0
    d=np.hypot(pts[:,0]-x,pts[:,1]-y)
    j=int(np.argmin(d))
    return float(pts[j,0]),float(pts[j,1]),float(d[j])


def main():
    review=json.loads(REVIEW.read_text())
    refs=json.loads(REFREG.read_text())["references"]
    by_date={r["date"]:r for r in refs}
    tracks={}
    if GENERIC.exists():tracks.update(load_tracks(GENERIC))
    if CORNERS.exists():tracks.update(load_tracks(CORNERS))

    results=[]
    by_image=defaultdict(list)
    for item in review["promising"]:
        cid=item["candidate_id"]
        if cid not in tracks:
            results.append({"candidate_id":cid,"status":"MISSING_MACHINE_TRACK"})
            continue
        track=tracks[cid]
        observations=[]
        ok_count=0
        for obs in track["observations"]:
            date=obs["date"]
            ref=by_date.get(date)
            if not ref:
                observations.append({"date":date,"status":"REFERENCE_NOT_RESOLVED"})
                continue
            path=ROOT/ref["cache_path"]
            gray=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
            if gray is None:
                observations.append({"date":date,"status":"IMAGE_READ_FAILED"})
                continue
            x,y=map(float,obs["pixel"])
            refined=refine_point(gray,x,y)
            if refined is None:
                observations.append({"date":date,"status":"NO_LOCAL_CORNER","seed_pixel":[x,y]})
                continue
            rx,ry,shift=refined
            h,w=gray.shape
            accepted=shift<=SEARCH_RADIUS_PX
            if accepted:ok_count+=1
            row={
                "date":date,"status":"REFINED" if accepted else "SHIFT_TOO_LARGE",
                "seed_pixel":[x,y],"refined_pixel":[rx,ry],
                "refined_normalized":[rx/w,ry/h],"shift_px":shift,
                "image_dimensions":[w,h],
            }
            observations.append(row)
            if accepted:
                by_image[date].append((cid,(x,y),(rx,ry),shift))
        results.append({
            "candidate_id":cid,
            "method":item["method"],
            "visual_review":"promising",
            "source_reason":item["reason"],
            "refined_view_count":ok_count,
            "ready_for_named_landmark_review":ok_count>=3,
            "observations":observations,
        })

    # Human review sheet: red seed, blue refined point.
    TW,TH=760,530
    dates=[r["date"] for r in refs]
    sheet=Image.new("RGB",(TW*2,TH*3),(238,238,233))
    sd=ImageDraw.Draw(sheet)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
        small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
    except Exception:
        font=small=None

    for idx,ref in enumerate(refs):
        src=Image.open(ROOT/ref["cache_path"]).convert("RGB")
        maxw,maxh=TW-20,TH-72
        sc=min(maxw/src.width,maxh/src.height)
        nw,nh=max(1,round(src.width*sc)),max(1,round(src.height*sc))
        tile=src.resize((nw,nh),Image.Resampling.LANCZOS)
        td=ImageDraw.Draw(tile)
        for cid,seed,refined,shift in by_image.get(ref["date"],[]):
            sx,sy=seed[0]*sc,seed[1]*sc
            rx,ry=refined[0]*sc,refined[1]*sc
            td.line((sx,sy,rx,ry),fill=(85,85,85),width=2)
            td.ellipse((sx-7,sy-7,sx+7,sy+7),outline=(220,45,35),width=3)
            td.ellipse((rx-7,ry-7,rx+7,ry+7),outline=(35,95,220),width=3)
            td.rectangle((rx+9,ry-10,rx+75,ry+8),fill=(242,248,255))
            td.text((rx+11,ry-10),f"{cid} {shift:.1f}",fill=(15,60,155),font=small)
        ox=(idx%2)*TW+(TW-nw)//2
        oy=(idx//2)*TH+30
        sheet.paste(tile,(ox,oy))
        sd.text(((idx%2)*TW+10,(idx//2)*TH+5),ref["date"],fill=(25,35,40),font=font)
        sd.text(((idx%2)*TW+10,(idx//2)*TH+TH-28),
                "Red = machine seed; blue = nearest refined image corner. Still provisional.",
                fill=(60,60,60),font=small)
    overlay=OUT/"Lombard_1040_Refined_Track_Seeds_v030_contact.jpg"
    sheet.save(overlay,quality=89)

    report={
        "schema_version":1,
        "status":"PROVISIONAL_IMAGE_COORDINATES_ONLY",
        "search_radius_px":SEARCH_RADIUS_PX,
        "method":"Nearest Shi-Tomasi corner with subpixel refinement around visually triaged machine seed.",
        "policy":"Refined pixels improve repeatability only. A point must still be mapped to a named stable architectural landmark and explicitly accepted before entering the canonical control-point manifest.",
        "candidate_count":len(results),
        "three_view_refined_count":sum(1 for r in results if r.get("ready_for_named_landmark_review")),
        "results":results,
        "review_overlay":str(overlay.relative_to(ROOT)),
        "geometry_generation_authorized":False,
    }
    path=OUT/"Lombard_1040_Refined_Track_Seeds_v030.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({
        "candidates":len(results),
        "three_view_refined":report["three_view_refined_count"],
        "output":str(path.relative_to(ROOT))
    },indent=2))


if __name__=="__main__":
    main()
