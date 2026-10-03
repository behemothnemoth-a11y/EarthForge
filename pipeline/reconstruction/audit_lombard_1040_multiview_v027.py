"""Generate candidate multi-view control points for 1040 Lombard references.

This is a source-truth aid only. It never authorizes Minecraft geometry.
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "lombard_sf"
OUT = PROJECT / "outputs" / "house_1040_source_truth_v027"
DOWNLOAD_AUDIT = OUT / "Lombard_1040_Reference_Download_v027.json"

RATIO = 0.72
RANSAC_PX = 1.8
MAX_PAIR_MATCHES = 80
MAX_DRAW_MATCHES = 30


class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x):
        p = self.parent[x]
        if p != x:
            self.parent[x] = self.find(p)
        return self.parent[x]

    def union(self, a, b):
        self.add(a)
        self.add(b)
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def read_image(row):
    path = ROOT / row["local_path"]
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read {path}")
    return image


def resize_for_sheet(image, width=720, height=520):
    h, w = image.shape[:2]
    scale = min(width / w, height / h)
    out = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    canvas = np.full((height, width, 3), 245, dtype=np.uint8)
    y = (height - out.shape[0]) // 2
    x = (width - out.shape[1]) // 2
    canvas[y:y + out.shape[0], x:x + out.shape[1]] = out
    return canvas


def main():
    if not DOWNLOAD_AUDIT.exists():
        raise SystemExit("Reference download audit is missing; materialize references first.")
    audit = json.loads(DOWNLOAD_AUDIT.read_text(encoding="utf-8"))
    rows = audit["references"]
    if len(rows) < 3:
        raise SystemExit("Need at least three references for multi-view analysis.")

    sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.02, edgeThreshold=12)
    matcher = cv2.BFMatcher(cv2.NORM_L2)

    images = []
    grays = []
    keypoints = []
    descriptors = []
    for row in rows:
        image = read_image(row)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        kp, desc = sift.detectAndCompute(gray, None)
        images.append(image)
        grays.append(gray)
        keypoints.append(kp)
        descriptors.append(desc)

    uf = UnionFind()
    pair_reports = []
    accepted_edges = []

    pairs_dir = OUT / "multiview_pairs"
    pairs_dir.mkdir(parents=True, exist_ok=True)

    for ia, ib in itertools.combinations(range(len(rows)), 2):
        da, db = descriptors[ia], descriptors[ib]
        if da is None or db is None or len(da) < 8 or len(db) < 8:
            continue
        raw = matcher.knnMatch(da, db, k=2)
        ratio_matches = []
        for item in raw:
            if len(item) != 2:
                continue
            m, n = item
            if m.distance < RATIO * n.distance:
                ratio_matches.append(m)
        ratio_matches.sort(key=lambda m: m.distance)

        inliers = []
        F = None
        if len(ratio_matches) >= 8:
            pts_a = np.float32([keypoints[ia][m.queryIdx].pt for m in ratio_matches])
            pts_b = np.float32([keypoints[ib][m.trainIdx].pt for m in ratio_matches])
            F, mask = cv2.findFundamentalMat(
                pts_a,
                pts_b,
                method=cv2.FM_RANSAC,
                ransacReprojThreshold=RANSAC_PX,
                confidence=0.995,
                maxIters=10000,
            )
            if mask is not None:
                inliers = [m for m, keep in zip(ratio_matches, mask.ravel().tolist()) if keep]
        inliers = inliers[:MAX_PAIR_MATCHES]

        pair = {
            "a_index": ia + 1,
            "b_index": ib + 1,
            "a_date": rows[ia]["date"],
            "b_date": rows[ib]["date"],
            "a_title": rows[ia]["title"],
            "b_title": rows[ib]["title"],
            "keypoints_a": len(keypoints[ia]),
            "keypoints_b": len(keypoints[ib]),
            "ratio_matches": len(ratio_matches),
            "fundamental_inliers": len(inliers),
            "candidate_only": True,
            "matches": [],
        }

        for m in inliers:
            pa = keypoints[ia][m.queryIdx].pt
            pb = keypoints[ib][m.trainIdx].pt
            pair["matches"].append({
                "a_kp": int(m.queryIdx),
                "b_kp": int(m.trainIdx),
                "a_px": [float(pa[0]), float(pa[1])],
                "b_px": [float(pb[0]), float(pb[1])],
                "descriptor_distance": float(m.distance),
            })
            uf.union((ia, int(m.queryIdx)), (ib, int(m.trainIdx)))
            accepted_edges.append(((ia, int(m.queryIdx)), (ib, int(m.trainIdx))))

        pair_reports.append(pair)

        if inliers:
            drawn = cv2.drawMatches(
                images[ia],
                keypoints[ia],
                images[ib],
                keypoints[ib],
                inliers[:MAX_DRAW_MATCHES],
                None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )
            out_path = pairs_dir / f"pair_{ia+1:02d}_{ib+1:02d}.jpg"
            cv2.imwrite(str(out_path), drawn, [int(cv2.IMWRITE_JPEG_QUALITY), 88])

    components = defaultdict(list)
    for node in uf.parent:
        components[uf.find(node)].append(node)

    tracks = []
    for nodes in components.values():
        by_image = defaultdict(list)
        for image_id, kp_id in nodes:
            by_image[image_id].append(kp_id)
        if len(by_image) < 3:
            continue
        if any(len(v) != 1 for v in by_image.values()):
            continue
        observations = []
        for image_id, ids in sorted(by_image.items()):
            kp_id = ids[0]
            pt = keypoints[image_id][kp_id].pt
            h, w = grays[image_id].shape[:2]
            observations.append({
                "image_index": image_id + 1,
                "date": rows[image_id]["date"],
                "kp": kp_id,
                "px": [float(pt[0]), float(pt[1])],
                "norm": [float(pt[0] / w), float(pt[1] / h)],
            })
        tracks.append({
            "track_id": len(tracks) + 1,
            "view_count": len(observations),
            "observations": observations,
            "candidate_only": True,
        })

    tracks.sort(key=lambda t: (-t["view_count"], t["track_id"]))
    for new_id, track in enumerate(tracks, start=1):
        track["track_id"] = new_id

    # Annotate the strongest multi-view tracks on each source image.
    annotations_dir = OUT / "multiview_annotations"
    annotations_dir.mkdir(parents=True, exist_ok=True)
    max_tracks_to_draw = min(60, len(tracks))
    colors = [
        (225, 48, 48), (48, 110, 225), (38, 160, 88), (220, 140, 30),
        (145, 70, 200), (20, 165, 180), (200, 70, 140), (80, 80, 80),
    ]
    obs_by_image = defaultdict(list)
    for track in tracks[:max_tracks_to_draw]:
        for obs in track["observations"]:
            obs_by_image[obs["image_index"] - 1].append((track["track_id"], obs["px"]))

    annotated_paths = []
    for image_id, image in enumerate(images):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil)
        for track_id, pt in obs_by_image.get(image_id, []):
            x, y = pt
            c = colors[(track_id - 1) % len(colors)]
            r = 9
            draw.ellipse((x-r, y-r, x+r, y+r), outline=c, width=3)
            draw.text((x+r+3, y-r), str(track_id), fill=c)
        path = annotations_dir / f"view_{image_id+1:02d}_{rows[image_id]['date']}.jpg"
        pil.save(path, quality=90)
        annotated_paths.append(path)

    # Make a compact contact sheet for human review.
    cards = [resize_for_sheet(img) for img in images]
    cols = 2
    rows_count = (len(cards) + cols - 1) // cols
    sheet = np.full((rows_count * 570 + 70, cols * 760 + 40, 3), 238, dtype=np.uint8)
    for i, card in enumerate(cards):
        y = 60 + (i // cols) * 570
        x = 20 + (i % cols) * 760
        sheet[y:y+520, x:x+720] = card
        cv2.putText(sheet, f"{i+1:02d} {rows[i]['date']}", (x, y-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (35, 45, 50), 2, cv2.LINE_AA)
    cv2.putText(sheet, "1040 Lombard B0 reference set - source images only; no geometry inferred",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 40, 45), 2, cv2.LINE_AA)
    contact_path = OUT / "Lombard_1040_B0_Reference_Contact_v027.jpg"
    cv2.imwrite(str(contact_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

    report = {
        "schema_version": 1,
        "gate": "1040_B0_MULTIVIEW_CANDIDATES",
        "method": {
            "detector": "OpenCV SIFT",
            "pair_matcher": "L2 kNN + Lowe ratio",
            "ratio_threshold": RATIO,
            "epipolar_filter": "fundamental matrix RANSAC",
            "ransac_threshold_px": RANSAC_PX,
        },
        "policy": "All correspondences are candidate observations only. Human/reference review is required before any track becomes a structural control point.",
        "geometry_generation_authorized": False,
        "reference_count": len(rows),
        "pair_count": len(pair_reports),
        "pairs_with_inliers": sum(1 for p in pair_reports if p["fundamental_inliers"] > 0),
        "multi_view_track_count": len(tracks),
        "tracks": tracks,
        "pairs": pair_reports,
        "review_artifacts": {
            "contact_sheet": str(contact_path.relative_to(ROOT)),
            "pair_match_dir": str(pairs_dir.relative_to(ROOT)),
            "annotated_view_dir": str(annotations_dir.relative_to(ROOT)),
        },
    }
    (OUT / "Lombard_1040_B0_Multiview_Candidates_v027.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    summary = [
        "# 1040 Lombard B0 multi-view candidate audit",
        "",
        f"- References: {len(rows)}",
        f"- Pair comparisons: {len(pair_reports)}",
        f"- Pairs with epipolar-consistent matches: {report['pairs_with_inliers']}",
        f"- Candidate tracks visible in 3+ views: {len(tracks)}",
        "",
        "**These are not measured architectural control points yet.**",
        "They are machine-generated candidates for the next human/source review gate.",
    ]
    (OUT / "Lombard_1040_B0_Multiview_Candidates_v027.md").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "reference_count": len(rows),
        "pairs_with_inliers": report["pairs_with_inliers"],
        "multi_view_track_count": len(tracks),
        "geometry_generation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
