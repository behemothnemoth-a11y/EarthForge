#!/usr/bin/env python3
"""Acquire Redfield 21 Feet of History 600-block reference pages.

Raw images are intentionally written under references/private and are ignored by
Git. The generated manifest contains provenance, URLs, dimensions and selected
modern-reference metadata only.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
INDEX_URL = (
    "https://tourism.redfield-sd.com/candnw-rr-depot/"
    "21-feet-of-history/main-street/?cat=main"
)
PRIVATE = PROJECT / "references" / "private" / "redfield_21_feet_600block"
MANIFEST = PROJECT / "source_manifests" / "redfield_21feet_600block_v001.json"
UA = "EarthForge/0.1 (Redfield public-reference metadata acquisition)"

def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def absolute(url: str, base: str) -> str:
    return urllib.parse.urljoin(base, html.unescape(url))

def main() -> int:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    index = get(INDEX_URL).decode("utf-8", "replace")
    links = re.findall(
        r'href="([^"]*/21-feet-of-history/main-street/p/item/[^"]+)"',
        index,
        flags=re.I,
    )
    unique = []
    seen = set()
    for raw in links:
        url = absolute(raw, INDEX_URL).split("?", 1)[0]
        m = re.search(r"/item/(\d+)/([^/?#]+)", url)
        if not m:
            continue
        slug = m.group(2)
        addr = re.match(r"(\d{3}(?:\d{3})?)-main", slug)
        if not addr:
            continue
        digits = addr.group(1)
        first = int(digits[:3])
        if not (600 <= first <= 699):
            continue
        if url in seen:
            continue
        seen.add(url)
        unique.append((first, m.group(1), slug, url))

    unique.sort()
    rows = []
    for first, item_id, slug, url in unique:
        page = get(url).decode("utf-8", "replace")
        img_urls = [
            absolute(src, url)
            for src in re.findall(r'<img[^>]+src="([^"]+)"', page, flags=re.I)
            if "21_Feet" in src and "street-sub" not in src
        ]
        # De-duplicate while preserving order.
        imgs = []
        for u in img_urls:
            if u not in imgs:
                imgs.append(u)

        folder = PRIVATE / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "page.html").write_text(page, encoding="utf-8")

        files = []
        for i, u in enumerate(imgs, 1):
            ext = Path(urllib.parse.urlparse(u).path).suffix or ".img"
            dest = folder / f"image_{i:02d}{ext}"
            if not dest.exists():
                dest.write_bytes(get(u))
            files.append(
                {
                    "index": i,
                    "url": u,
                    "private_file": str(dest.relative_to(PROJECT)).replace("\\", "/"),
                    "bytes": dest.stat().st_size,
                }
            )

        # On these pages the final distinct item image is consistently the
        # present-day comparison image; record the assumption rather than
        # presenting it as source-authored metadata.
        modern = files[-1] if files else None
        rows.append(
            {
                "address_hint": slug.split("-main", 1)[0].replace("", "", 0),
                "sort_address": first,
                "item_id": item_id,
                "slug": slug,
                "page_url": url,
                "images": files,
                "selected_current_reference": modern,
                "selection_rule": (
                    "last distinct item image on page; verified pattern on existing "
                    "617-627 sources, but exact capture date is not claimed"
                ),
            }
        )
        print(first, slug, len(files))

    manifest = {
        "schema_version": 1,
        "source_id": "redfield_21feet_600block_v001",
        "provider": "Redfield City Tourism",
        "acquired_at": "2026-10-01",
        "index_url": INDEX_URL,
        "raw_policy": "raw images/page HTML private and gitignored",
        "items": rows,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {MANIFEST}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
