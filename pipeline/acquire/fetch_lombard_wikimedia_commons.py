#!/usr/bin/env python3
"""Acquire freely licensed Wikimedia Commons references for Lombard Street.

Images are kept under references/private for working analysis. The committed
manifest records source URLs, authorship/license metadata and local filenames.
"""
from __future__ import annotations
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
PRIVATE=PROJECT/"references"/"private"/"wikimedia_commons"
MANIFEST=PROJECT/"source_manifests"/"wikimedia_commons_lombard_v001.json"
API="https://commons.wikimedia.org/w/api.php"
UA="EarthForge/0.1 (Lombard Street reconstruction source research)"

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)

def get_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read()

def clean_text(v):
    if isinstance(v,dict):v=v.get("value","")
    v=html.unescape(str(v or ""))
    v=re.sub(r"<[^>]+>"," ",v)
    return re.sub(r"\s+"," ",v).strip()

def main():
    PRIVATE.mkdir(parents=True,exist_ok=True);MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    params={
        "action":"query","generator":"categorymembers",
        "gcmtitle":"Category:Lombard Street (San Francisco)",
        "gcmtype":"file","gcmlimit":"500",
        "prop":"imageinfo","iiprop":"url|extmetadata",
        "iiurlwidth":"1000","format":"json","formatversion":"2",
    }
    url=API+"?"+urllib.parse.urlencode(params)
    data=get_json(url)
    pages=data.get("query",{}).get("pages",[])
    records=[]
    for idx,p in enumerate(sorted(pages,key=lambda x:x.get("title","")),1):
        ii=(p.get("imageinfo") or [{}])[0]
        meta=ii.get("extmetadata") or {}
        thumb=ii.get("thumburl") or ii.get("url")
        if not thumb:continue
        suffix=Path(urllib.parse.urlparse(ii.get("url",thumb)).path).suffix
        if suffix.lower() not in (".jpg",".jpeg",".png",".webp",".tif",".tiff"):
            suffix=".jpg"
        safe=re.sub(r"[^A-Za-z0-9._-]+","_",p.get("title","File").removeprefix("File:"))[:120]
        dest=PRIVATE/f"{idx:03d}_{safe}{suffix.lower()}"
        if not dest.exists():
            try:dest.write_bytes(get_bytes(thumb))
            except Exception as exc:
                print("SKIP",p.get("title"),exc);continue
        rec={
            "index":idx,"title":p.get("title"),"page_url":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(p.get("title","").replace(" ","_")),
            "original_url":ii.get("url"),"working_thumbnail_url":thumb,
            "private_file":str(dest.relative_to(PROJECT)).replace("\\","/"),
            "artist":clean_text(meta.get("Artist")),
            "license_short_name":clean_text(meta.get("LicenseShortName")),
            "license_url":clean_text(meta.get("LicenseUrl")),
            "credit":clean_text(meta.get("Credit")),
            "description":clean_text(meta.get("ImageDescription")),
            "date_time_original":clean_text(meta.get("DateTimeOriginal") or meta.get("DateTime")),
            "categories":clean_text(meta.get("Categories")),
            "bytes":dest.stat().st_size,
        }
        records.append(rec)
        print(idx,p.get("title"),dest.stat().st_size)
    out={
        "schema_version":1,
        "source_id":"wikimedia_commons_lombard_v001",
        "provider":"Wikimedia Commons contributors",
        "category":"Category:Lombard Street (San Francisco)",
        "acquired_at":"2026-10-01",
        "raw_policy":"working images under references/private; metadata committed",
        "count":len(records),
        "items":records,
    }
    MANIFEST.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("WROTE",MANIFEST,len(records))
if __name__=="__main__":main()
