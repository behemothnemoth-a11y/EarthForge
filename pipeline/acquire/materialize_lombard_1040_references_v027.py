"""Materialize the dedicated 1040 Lombard Commons reference set on a CI runner.

Downloaded images are stored under references/private (gitignored). Only hashes,
source metadata, attribution, and derived review products are written to outputs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "lombard_sf"
MANIFEST = PROJECT / "source_manifests" / "1040_lombard_source_truth_v027.json"
PRIVATE = PROJECT / "references" / "private" / "1040_v027"
OUT = PROJECT / "outputs" / "house_1040_source_truth_v027"
API = "https://commons.wikimedia.org/w/api.php"
UA = "EarthForge/1040-source-truth (+https://github.com/behemothnemoth-a11y/EarthForge)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_title(page_url: str) -> str:
    path = unquote(urlparse(page_url).path)
    marker = "/wiki/File:"
    if marker not in path:
        raise ValueError(f"Not a Commons File URL: {page_url}")
    return path.split(marker, 1)[1].replace("_", " ")


def safe_name(index: int, title: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")
    stem = stem[:-4] if stem.lower().endswith(".jpg") else stem
    return f"{index:02d}_{stem}.jpg"


def main() -> None:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers["User-Agent"] = UA
    rows = []
    attribution = ["# 1040 Lombard CI reference set", ""]

    for index, item in enumerate(manifest["imagery"], start=1):
        title = file_title(item["page"])
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 1800,
            "titles": f"File:{title}",
        }
        response = session.get(API, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        page = next(iter(data["query"]["pages"].values()))
        if "imageinfo" not in page:
            raise RuntimeError(f"Commons imageinfo missing for {title}")
        info = page["imageinfo"][0]
        download_url = info.get("thumburl") or info["url"]
        dest = PRIVATE / safe_name(index, title)
        with session.get(download_url, stream=True, timeout=90) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
        with Image.open(dest) as im:
            width, height = im.size
        if min(width, height) < 500:
            raise RuntimeError(f"Reference thumbnail unexpectedly small: {title}: {width}x{height}")
        row = {
            "index": index,
            "date": item["date"],
            "title": title,
            "page": item["page"],
            "artist_manifest": item["artist"],
            "license_manifest": item["license"],
            "camera": item.get("camera"),
            "camera_altitude_m": item.get("camera_altitude_m"),
            "local_path": str(dest.relative_to(ROOT)),
            "download_url": download_url,
            "download_width": width,
            "download_height": height,
            "source_width": info.get("width"),
            "source_height": info.get("height"),
            "mime": info.get("mime"),
            "sha256": sha256(dest),
            "uses": item.get("use", []),
        }
        rows.append(row)
        attribution += [
            f"## {index:02d} — {title}",
            f"- Date: {item['date']}",
            f"- Artist: {item['artist']}",
            f"- License: {item['license']}",
            f"- Source: {item['page']}",
            f"- CI materialized size: {width}x{height}",
            f"- SHA-256: {row['sha256']}",
            "",
        ]

    report = {
        "schema_version": 1,
        "purpose": "Ephemeral CI materialization of dedicated 1040 Lombard references for source-truth analysis.",
        "raw_reference_policy": "Files live only under gitignored references/private on the runner. Do not commit raw licensed imagery.",
        "count": len(rows),
        "references": rows,
    }
    (OUT / "Lombard_1040_Reference_Download_v027.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "Lombard_1040_Reference_Attribution_v027.md").write_text(
        "\n".join(attribution) + "\n", encoding="utf-8"
    )
    print(json.dumps({"materialized": len(rows), "output": str(OUT.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
