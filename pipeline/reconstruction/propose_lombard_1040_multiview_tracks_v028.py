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
from PIL import Image, ImageDraw, ImageFont

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
    manifest=json.loads((PROJECT/"source_manifests/1040_lombard_source_truth_v027.json").read_text())
    meta={m["date"]:m for m in manifest["imagery"]}
    data=[]
    sift=cv2.SIFT_create(nfeatures=5500,contrastThreshold=.022,edgeThreshold=12)
    for idx,ref in enumerate(refs):
        path=ROOT/ref["cache_path"]
        color=cv2.imread(str(path),cv2.IMREAD_COLOR)
        if color is None:raise SystemExit(f"Could not read {path}")
        h,w=color.shape[:2];scale=min(1.0,MAX_DIM/max(h,w))
        small_color=cv2.resize(color,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA) if scale<1 else color
        small=cv2.cvtColor(small_color,cv2.COLOR_BGR2GRAY)
        sh,sw=small.shape
        item=meta.get(ref["date"],{})
        roi=item.get("analysis_roi_norm",[0,0,1,1])
        x0=max(0,min(sw-1,round(float(roi[0])*sw)));y0=max(0,min(sh-1,round(float(roi[1])*sh)))
        x1=max(x0+1,min(sw,round(float(roi[2])*sw)));y1=max(y0+1,min(sh,round(float(roi[3])*sh)))
        mask=np.zeros((sh,sw),dtype=np.uint8);mask[y0:y1,x0:x1]=255

        # Lombard's bougainvillea/trees dominate naive feature matching. Suppress
        # saturated green and magenta pixels (plus a small dilation halo) so SIFT
        # preferentially proposes persistent building/window/frame features.
        hsv=cv2.cvtColor(small_color,cv2.COLOR_BGR2HSV)
        hh,ss,vv=cv2.split(hsv)
        green=((hh>=25)&(hh<=95)&(ss>=55))
        magenta=((hh>=135)&(hh<=179)&(ss>=60))
        vegetation=(green|magenta).astype(np.uint8)*255
        vegetation=cv2.dilate(vegetation,np.ones((9,9),np.uint8),iterations=1)
        mask[vegetation>0]=0

        kp,des=sift.detectAndCompute(small,mask)
        data.append({"ref":ref,"kp":kp,"des":des,"scale":scale,"shape":[w,h],
                     "mask":mask,"roi_norm":roi,
                     "masked_fraction":float((mask==0).sum()/mask.size)})
        print(f"{idx} {ref['date']} keypoints={len(kp)} scale={scale:.4f} masked={data[-1]['masked_fraction']:.3f}",flush=True)

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

    # Ephemeral visual review sheet. Source images remain in the gitignored private cache;
    # this downscaled overlay is uploaded only as workflow evidence.
    obs_by_img=defaultdict(list)
    for t in tracks:
        for o in t["observations"]:
            obs_by_img[o["image_index"]].append((t["candidate_id"],o["pixel"]))
    TILE_W,TILE_H=760,530
    sheet=Image.new("RGB",(TILE_W*2,TILE_H*3),(238,238,233))
    sd=ImageDraw.Draw(sheet)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
        smallfont=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
    except Exception:
        font=smallfont=None
    for idx,d0 in enumerate(data):
        ref=d0["ref"];src=Image.open(ROOT/ref["cache_path"]).convert("RGB")
        maxw,maxh=TILE_W-20,TILE_H-72
        scale=min(maxw/src.width,maxh/src.height)
        nw,nh=max(1,round(src.width*scale)),max(1,round(src.height*scale))
        tile=src.resize((nw,nh),Image.Resampling.LANCZOS)
        td=ImageDraw.Draw(tile)
        for cid,pix in obs_by_img.get(idx,[]):
            x=float(pix[0])*scale;y=float(pix[1])*scale
            rr=11
            td.ellipse((x-rr,y-rr,x+rr,y+rr),outline=(255,45,25),width=4)
            td.rectangle((x+12,y-12,x+72,y+9),fill=(255,245,230))
            td.text((x+15,y-11),cid,fill=(130,10,0),font=smallfont)
        ox=(idx%2)*TILE_W+(TILE_W-nw)//2
        oy=(idx//2)*TILE_H+30
        sheet.paste(tile,(ox,oy))
        m=meta.get(ref["date"],{})
        sd.text(((idx%2)*TILE_W+10,(idx//2)*TILE_H+5),f'{ref["date"]} — {m.get("artist","")} / {m.get("license","")}',fill=(25,35,40),font=font)
        sd.text(((idx%2)*TILE_W+10,(idx//2)*TILE_H+TILE_H-28),"Red IDs = machine track candidates only; not accepted control points.",fill=(60,60,60),font=smallfont)
    overlay_path=OUT/"Lombard_1040_Multiview_Track_Candidates_v028_contact.jpg"
    sheet.save(overlay_path,quality=88)

    report={"schema_version":1,"status":"MACHINE_PROPOSALS_ONLY",
            "method":{"detector":"SIFT","ratio_test":0.72,"pair_geometry":"fundamental matrix RANSAC","ransac_px":1.6,
                      "min_track_views":3,
                      "feature_mask":"human-reviewed broad 1040 ROI + saturated green/magenta vegetation suppression with 9px dilation at analysis scale",
                      "warning":"ROIs and masks are analysis aids only. Candidates can still be wrong or land on repeated texture; human/source review is mandatory before copying any point into the canonical control-point manifest."},
            "images":[{"index":i,"date":d["ref"]["date"],"title":d["ref"]["title"],"dimensions":d["shape"],"keypoints":len(d["kp"]),
                       "analysis_roi_norm":d["roi_norm"],"masked_fraction":d["masked_fraction"]} for i,d in enumerate(data)],
            "review_overlay":str(overlay_path.relative_to(ROOT)),
            "pair_stats":pair_stats,"candidate_track_count":len(tracks),"tracks":tracks}
    path=OUT/"Lombard_1040_Multiview_Track_Candidates_v028.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    summary={"candidate_tracks":len(tracks),
             "tracks_5plus":sum(t["view_count"]>=5 for t in tracks),
             "tracks_4plus":sum(t["view_count"]>=4 for t in tracks),
             "pair_inliers":sum(p["ransac_inliers"] for p in pair_stats),
             "top_tracks":[{"candidate_id":t["candidate_id"],"view_count":t["view_count"],
                            "mean_match_distance":t["mean_match_distance"],
                            "observations":[{"date":o["date"],"image_index":o["image_index"],
                                             "normalized":[round(o["normalized"][0],6),round(o["normalized"][1],6)]}
                                            for o in t["observations"]]}
                           for t in tracks[:20]],
             "output":str(path.relative_to(ROOT))}
    print(json.dumps(summary,indent=2))

if __name__=="__main__":main()
