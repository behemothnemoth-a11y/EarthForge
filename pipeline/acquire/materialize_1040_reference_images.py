"""Resolve and cache the canonical 1040 Lombard Wikimedia reference originals.

Original images stay under the gitignored references/private tree. Only a
metadata/hash resolution report is written to the generated B0 output bundle.
"""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
MANIFEST=PROJECT/"source_manifests/1040_lombard_source_truth_v027.json"
CACHE=PROJECT/"references"/"private"/"1040_source_v027"
OUT=PROJECT/"outputs"/"house_1040_source_truth_v027"
API="https://commons.wikimedia.org/w/api.php"
UA="EarthForge/1040-source-truth-v027 (reproducible research cache)"

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def safe_name(title:str)->str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in title)

def download_with_backoff(session, url, path):
    clean=url.split("?",1)[0]
    last=None
    for attempt in range(7):
        try:
            with session.get(clean,stream=True,timeout=120,headers={"Referer":"https://commons.wikimedia.org/"}) as r:
                if r.status_code==429:
                    wait=float(r.headers.get("Retry-After") or min(60,5*(2**attempt)))
                    print(f"Wikimedia rate limit for {path.name}; waiting {wait:.0f}s",flush=True)
                    time.sleep(wait);continue
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(1024*1024):
                        if chunk:f.write(chunk)
                return
        except requests.RequestException as exc:
            last=exc
            if attempt==6:break
            wait=min(60,3*(2**attempt))
            print(f"Reference download retry {attempt+1}/7 for {path.name}: {exc}; waiting {wait}s",flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Could not download {clean}: {last}")

def main():
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    session=requests.Session();session.headers.update({"User-Agent":UA})
    resolved=[]
    for item in manifest["imagery"]:
        title=item["title"]
        q=session.get(API,params={
            "action":"query","format":"json","formatversion":2,
            "prop":"imageinfo","titles":"File:"+title,
            "iiprop":"url|size|sha1|mime|metadata|extmetadata",
        },timeout=45)
        q.raise_for_status()
        pages=q.json().get("query",{}).get("pages",[])
        if not pages or "imageinfo" not in pages[0]:
            raise SystemExit(f"Commons image could not be resolved: {title}")
        info=pages[0]["imageinfo"][0]
        path=CACHE/safe_name(title)
        if not path.exists() or path.stat().st_size!=int(info["size"]):
            download_with_backoff(session,info["url"],path)
            time.sleep(2.0)
        with Image.open(path) as im:
            dims=[int(im.width),int(im.height)]
        expected=[int(x) for x in item["dimensions"]]
        if dims!=expected:
            raise SystemExit(f"Reference dimension mismatch for {title}: {dims} != {expected}")
        resolved.append({
            "date":item["date"],"title":title,"page":item["page"],
            "commons_original_url":info["url"],
            "commons_api_sha1":info.get("sha1"),
            "commons_bytes":int(info["size"]),"mime":info.get("mime"),
            "dimensions":dims,"download_sha256":sha256(path),
            "camera":item.get("camera"),"camera_altitude_m":item.get("camera_altitude_m"),
            "camera_model":item.get("camera_model"),"focal_length_mm":item.get("focal_length_mm"),
            "focal_35mm_equiv_mm":item.get("focal_35mm_equiv_mm"),
            "commons_sha1_hex_documented":item.get("commons_sha1_hex"),
            "cache_path":str(path.relative_to(ROOT)),
        })
    report={
        "schema_version":1,
        "source_manifest":str(MANIFEST.relative_to(ROOT)),
        "count":len(resolved),
        "all_dimensions_verified":len(resolved)==len(manifest["imagery"]),
        "originals_gitignored":True,
        "policy":"Originals are transient/private source cache. Geometry may use them only through later registered measurement gates.",
        "references":resolved,
    }
    (OUT/"Lombard_1040_Reference_Resolution_v027.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"resolved":len(resolved),"output":str((OUT/"Lombard_1040_Reference_Resolution_v027.json").relative_to(ROOT))},indent=2))

if __name__=="__main__":main()
