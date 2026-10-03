"""Propose corner-driven multi-view tracks for 1040 Lombard.

Uses Shi-Tomasi structural corners plus SIFT descriptors inside human-reviewed
house ROIs with vegetation suppression. Outputs annotation candidates only.
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
REFREG=OUT/"Lombard_1040_Reference_Resolution_v027.json"
MANIFEST=PROJECT/"source_manifests/1040_lombard_source_truth_v027.json"
MAX_DIM=1400


class UF:
    def __init__(self):
        self.p={}
        self.images={}

    def add(self,n,img):
        if n not in self.p:
            self.p[n]=n
            self.images[n]={img}

    def find(self,x):
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]]
            x=self.p[x]
        return x

    def union(self,a,b):
        ra,rb=self.find(a),self.find(b)
        if ra==rb:return True
        if self.images[ra]&self.images[rb]:return False
        if len(self.images[ra])<len(self.images[rb]):ra,rb=rb,ra
        self.p[rb]=ra
        self.images[ra]|=self.images[rb]
        return True


def structural_mask(color, roi):
    h,w=color.shape[:2]
    mask=np.zeros((h,w),dtype=np.uint8)
    x0=max(0,min(w-1,round(float(roi[0])*w)))
    y0=max(0,min(h-1,round(float(roi[1])*h)))
    x1=max(x0+1,min(w,round(float(roi[2])*w)))
    y1=max(y0+1,min(h,round(float(roi[3])*h)))
    mask[y0:y1,x0:x1]=255

    hsv=cv2.cvtColor(color,cv2.COLOR_BGR2HSV)
    hh,ss,_=cv2.split(hsv)
    green=((hh>=25)&(hh<=95)&(ss>=55))
    magenta=((hh>=135)&(hh<=179)&(ss>=60))
    vegetation=(green|magenta).astype(np.uint8)*255
    vegetation=cv2.dilate(vegetation,np.ones((9,9),np.uint8),iterations=1)
    mask[vegetation>0]=0
    return mask


def main():
    if not REFREG.exists():
        raise SystemExit("Reference resolution report missing")
    refs=json.loads(REFREG.read_text())["references"]
    manifest=json.loads(MANIFEST.read_text())
    meta={m["date"]:m for m in manifest["imagery"]}

    sift=cv2.SIFT_create(nfeatures=5000,contrastThreshold=.02,edgeThreshold=12)
    data=[]
    for idx,ref in enumerate(refs):
        path=ROOT/ref["cache_path"]
        color=cv2.imread(str(path),cv2.IMREAD_COLOR)
        if color is None:raise SystemExit(f"Could not read {path}")
        h0,w0=color.shape[:2]
        scale=min(1.0,MAX_DIM/max(h0,w0))
        small_color=cv2.resize(color,(round(w0*scale),round(h0*scale)),interpolation=cv2.INTER_AREA) if scale<1 else color
        gray=cv2.cvtColor(small_color,cv2.COLOR_BGR2GRAY)
        item=meta.get(ref["date"],{})
        roi=item.get("analysis_roi_norm",[0,0,1,1])
        mask=structural_mask(small_color,roi)

        corners=cv2.goodFeaturesToTrack(
            gray,
            maxCorners=1800,
            qualityLevel=.008,
            minDistance=7,
            mask=mask,
            blockSize=7,
            useHarrisDetector=False,
        )
        if corners is None:
            kp=[];des=None
        else:
            pts=corners.reshape(-1,2).astype(np.float32)
            cv2.cornerSubPix(
                gray,pts,(5,5),(-1,-1),
                (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,30,.01)
            )
            kp=[cv2.KeyPoint(float(x),float(y),18) for x,y in pts]
            kp,des=sift.compute(gray,kp)
        data.append({
            "ref":ref,"kp":kp,"des":des,"scale":scale,"shape":[w0,h0],
            "roi_norm":roi,"masked_fraction":float((mask==0).sum()/mask.size)
        })
        print(f"{idx} {ref['date']} structural_corners={len(kp)} scale={scale:.4f}",flush=True)

    bf=cv2.BFMatcher(cv2.NORM_L2)
    uf=UF();edges=[];pair_stats=[]
    for a in range(len(data)):
        for b in range(a+1,len(data)):
            da,db=data[a]["des"],data[b]["des"]
            if da is None or db is None or len(da)<8 or len(db)<8:
                pair_stats.append({"a":a,"b":b,"ratio_matches":0,"ransac_inliers":0})
                continue
            raw=bf.knnMatch(da,db,k=2)
            good=[m for m,n in raw if m.distance<.74*n.distance]
            if len(good)<8:
                pair_stats.append({"a":a,"b":b,"ratio_matches":len(good),"ransac_inliers":0})
                continue
            p1=np.float32([data[a]["kp"][m.queryIdx].pt for m in good])
            p2=np.float32([data[b]["kp"][m.trainIdx].pt for m in good])
            F,mask=cv2.findFundamentalMat(p1,p2,cv2.FM_RANSAC,1.8,.995)
            keep=[m for m,ok in zip(good,mask.ravel() if mask is not None else np.zeros(len(good))) if ok]
            keep=sorted(keep,key=lambda m:m.distance)[:180]
            pair_stats.append({"a":a,"b":b,"ratio_matches":len(good),"ransac_inliers":len(keep)})
            for m in keep:
                na=(a,int(m.queryIdx));nb=(b,int(m.trainIdx))
                uf.add(na,a);uf.add(nb,b)
                if uf.union(na,nb):edges.append((na,nb,float(m.distance)))

    comps=defaultdict(list)
    for n in uf.p:
        comps[uf.find(n)].append(n)
    edge_by_node=defaultdict(list)
    for a,b,d in edges:
        edge_by_node[a].append(d);edge_by_node[b].append(d)

    tracks=[]
    for nodes in comps.values():
        images={n[0] for n in nodes}
        if len(images)<3:continue
        obs=[];responses=[]
        for img,kidx in sorted(nodes):
            kp=data[img]["kp"][kidx];scale=data[img]["scale"]
            ox=float(kp.pt[0]/scale);oy=float(kp.pt[1]/scale)
            w,h=data[img]["shape"]
            obs.append({
                "image_index":img,"date":data[img]["ref"]["date"],"title":data[img]["ref"]["title"],
                "pixel":[ox,oy],"normalized":[ox/w,oy/h],"keypoint_response":float(kp.response)
            })
            responses.append(float(kp.response))
        dists=[d for n in nodes for d in edge_by_node.get(n,[])]
        tracks.append({
            "view_count":len(images),
            "mean_keypoint_response":float(np.mean(responses)) if responses else 0.0,
            "mean_match_distance":float(np.mean(dists)) if dists else None,
            "observations":obs
        })
    tracks.sort(key=lambda t:(-t["view_count"],t["mean_match_distance"] if t["mean_match_distance"] is not None else 999))
    tracks=tracks[:300]
    for i,t in enumerate(tracks,1):
        t["candidate_id"]=f"CT{i:03d}"

    # Visual contact sheet for the strongest corner tracks.
    show=tracks[:50]
    obs_by_img=defaultdict(list)
    for t in show:
        for o in t["observations"]:
            obs_by_img[o["image_index"]].append((t["candidate_id"],o["pixel"]))

    TW,TH=760,530
    sheet=Image.new("RGB",(TW*2,TH*3),(238,238,233))
    sd=ImageDraw.Draw(sheet)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
        smallfont=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
    except Exception:
        font=smallfont=None

    for idx,d0 in enumerate(data):
        ref=d0["ref"];src=Image.open(ROOT/ref["cache_path"]).convert("RGB")
        maxw,maxh=TW-20,TH-72
        sc=min(maxw/src.width,maxh/src.height)
        nw,nh=max(1,round(src.width*sc)),max(1,round(src.height*sc))
        tile=src.resize((nw,nh),Image.Resampling.LANCZOS)
        td=ImageDraw.Draw(tile)
        for cid,pix in obs_by_img.get(idx,[]):
            x=float(pix[0])*sc;y=float(pix[1])*sc;r=8
            td.ellipse((x-r,y-r,x+r,y+r),outline=(20,95,210),width=3)
            td.rectangle((x+10,y-10,x+64,y+8),fill=(240,248,255))
            td.text((x+12,y-10),cid,fill=(5,55,145),font=smallfont)
        ox=(idx%2)*TW+(TW-nw)//2
        oy=(idx//2)*TH+30
        sheet.paste(tile,(ox,oy))
        m=meta.get(ref["date"],{})
        sd.text(((idx%2)*TW+10,(idx//2)*TH+5),
                f'{ref["date"]} — {m.get("artist","")} / {m.get("license","")}',
                fill=(25,35,40),font=font)
        sd.text(((idx%2)*TW+10,(idx//2)*TH+TH-28),
                "Blue IDs = structural-corner candidates only; not accepted control points.",
                fill=(60,60,60),font=smallfont)
    overlay=OUT/"Lombard_1040_Corner_Track_Candidates_v029_contact.jpg"
    sheet.save(overlay,quality=88)

    report={
        "schema_version":1,
        "status":"MACHINE_PROPOSALS_ONLY",
        "method":{
            "corner_detector":"Shi-Tomasi goodFeaturesToTrack + subpixel refinement",
            "descriptor":"SIFT at detected structural corners",
            "ratio_test":0.74,
            "pair_geometry":"fundamental matrix RANSAC",
            "ransac_px":1.8,
            "feature_mask":"human-reviewed 1040 ROI + green/magenta vegetation suppression",
            "warning":"Candidates remain untrusted until source-reviewed and copied into the canonical control-point manifest."
        },
        "images":[{"index":i,"date":d["ref"]["date"],"corners":len(d["kp"]),
                   "analysis_roi_norm":d["roi_norm"],"masked_fraction":d["masked_fraction"]}
                  for i,d in enumerate(data)],
        "pair_stats":pair_stats,
        "candidate_track_count":len(tracks),
        "tracks_4plus":sum(t["view_count"]>=4 for t in tracks),
        "tracks_5plus":sum(t["view_count"]>=5 for t in tracks),
        "tracks":tracks,
        "review_overlay":str(overlay.relative_to(ROOT)),
        "geometry_generation_authorized":False
    }
    out=OUT/"Lombard_1040_Corner_Track_Candidates_v029.json"
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({
        "candidate_tracks":len(tracks),
        "tracks_4plus":report["tracks_4plus"],
        "tracks_5plus":report["tracks_5plus"],
        "output":str(out.relative_to(ROOT))
    },indent=2))


if __name__=="__main__":
    main()
