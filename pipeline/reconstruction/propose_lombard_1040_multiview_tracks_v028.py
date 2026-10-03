"""Propose multi-view feature tracks for 1040 Lombard reference images.

Machine tracks are annotation aids only. They are never promoted directly to
architectural dimensions or Minecraft geometry.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
OUT=PROJECT/"outputs"/"house_1040_source_truth_v027"
REFREG=OUT/"Lombard_1040_Reference_Resolution_v027.json"
MAX_DIM=1400

class UF:
    def __init__(self):self.p={};self.images={}
    def add(self,n,img):
        if n not in self.p:self.p[n]=n;self.images[n]={img}
    def find(self,x):
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def union(self,a,b):
        ra,rb=self.find(a),self.find(b)
        if ra==rb:return True
        if self.images[ra]&self.images[rb]:return False
        if len(self.images[ra])<len(self.images[rb]):ra,rb=rb,ra
        self.p[rb]=ra;self.images[ra]|=self.images[rb];return True

def main():
    if not REFREG.exists():raise SystemExit("Reference resolution report missing")
    refs=json.loads(REFREG.read_text())["references"]
    data=[]
    sift=cv2.SIFT_create(nfeatures=4500,contrastThreshold=.025,edgeThreshold=12)
    for idx,ref in enumerate(refs):
        path=ROOT/ref["cache_path"]
        im=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
        if im is None:raise SystemExit(f"Could not read {path}")
        h,w=im.shape;scale=min(1.0,MAX_DIM/max(h,w))
        small=cv2.resize(im,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA) if scale<1 else im
        kp,des=sift.detectAndCompute(small,None)
        data.append({"ref":ref,"kp":kp,"des":des,"scale":scale,"shape":[w,h]})
        print(f"{idx} {ref['date']} keypoints={len(kp)} scale={scale:.4f}",flush=True)

    uf=UF();edges=[];pair_stats=[]
    bf=cv2.BFMatcher(cv2.NORM_L2)
    for a in range(len(data)):
        for b in range(a+1,len(data)):
            da,db=data[a]["des"],data[b]["des"]
            if da is None or db is None:continue
            raw=bf.knnMatch(da,db,k=2)
            good=[m for m,n in raw if m.distance<.72*n.distance]
            if len(good)<10:
                pair_stats.append({"a":a,"b":b,"ratio_matches":len(good),"ransac_inliers":0});continue
            p1=np.float32([data[a]["kp"][m.queryIdx].pt for m in good])
            p2=np.float32([data[b]["kp"][m.trainIdx].pt for m in good])
            F,mask=cv2.findFundamentalMat(p1,p2,cv2.FM_RANSAC,1.6,.995)
            keep=[m for m,ok in zip(good,mask.ravel() if mask is not None else np.zeros(len(good))) if ok]
            pair_stats.append({"a":a,"b":b,"ratio_matches":len(good),"ransac_inliers":len(keep)})
            for m in sorted(keep,key=lambda q:q.distance):
                na=(a,int(m.queryIdx));nb=(b,int(m.trainIdx))
                uf.add(na,a);uf.add(nb,b)
                if uf.union(na,nb):edges.append((na,nb,float(m.distance)))

    comps=defaultdict(list)
    for n in uf.p:comps[uf.find(n)].append(n)
    edge_by_node=defaultdict(list)
    for a,b,d in edges:edge_by_node[a].append(d);edge_by_node[b].append(d)
    tracks=[]
    for nodes in comps.values():
        images={n[0] for n in nodes}
        if len(images)<3:continue
        obs=[]
        responses=[]
        for img,kidx in sorted(nodes):
            kp=data[img]["kp"][kidx];scale=data[img]["scale"]
            ox=float(kp.pt[0]/scale);oy=float(kp.pt[1]/scale)
            w,h=data[img]["shape"]
            obs.append({"image_index":img,"date":data[img]["ref"]["date"],"title":data[img]["ref"]["title"],
                        "pixel":[ox,oy],"normalized":[ox/w,oy/h],"keypoint_response":float(kp.response)})
            responses.append(float(kp.response))
        dists=[d for n in nodes for d in edge_by_node.get(n,[])]
        tracks.append({"view_count":len(images),"mean_keypoint_response":float(np.mean(responses)),
                       "mean_match_distance":float(np.mean(dists)) if dists else None,"observations":obs})
    tracks.sort(key=lambda t:(-t["view_count"],t["mean_match_distance"] if t["mean_match_distance"] is not None else 999,-t["mean_keypoint_response"]))
    tracks=tracks[:250]
    for i,t in enumerate(tracks,1):t["candidate_id"]=f"MT{i:03d}"

    report={"schema_version":1,"status":"MACHINE_PROPOSALS_ONLY",
            "method":{"detector":"SIFT","ratio_test":0.72,"pair_geometry":"fundamental matrix RANSAC","ransac_px":1.6,
                      "min_track_views":3,"warning":"Candidates can land on vegetation/repeated texture. Human/source review is mandatory before copying any point into the canonical control-point manifest."},
            "images":[{"index":i,"date":d["ref"]["date"],"title":d["ref"]["title"],"dimensions":d["shape"],"keypoints":len(d["kp"])} for i,d in enumerate(data)],
            "pair_stats":pair_stats,"candidate_track_count":len(tracks),"tracks":tracks}
    path=OUT/"Lombard_1040_Multiview_Track_Candidates_v028.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"candidate_tracks":len(tracks),
                      "tracks_5plus":sum(t["view_count"]>=5 for t in tracks),
                      "tracks_4plus":sum(t["view_count"]>=4 for t in tracks),
                      "pair_inliers":sum(p["ransac_inliers"] for p in pair_stats),
                      "output":str(path.relative_to(ROOT))},indent=2))

if __name__=="__main__":main()
