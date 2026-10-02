#!/usr/bin/env python3
from __future__ import annotations

import json, math, sys
from pathlib import Path
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.export.litematic_codec import write_single_region_litematic, read_back_block_map

PROJECT = ROOT / "projects" / "lombard_sf"
SRC = PROJECT / "roads" / "datasf_street_controls_v001.geojson"
SLICE = PROJECT / "slices" / "hyde_turn_001"
OUT = PROJECT / "outputs" / "slices" / "hyde_turn_001" / "Lombard_HydeTurn_Centerline_v001.litematic"
VAL = PROJECT / "validation" / "lombard_hyde_turn_centerline_v001.json"

CNN = "8449000"
VERTEX_START = 0
VERTEX_END = 8
OFFSET_X = 20
OFFSET_Z = 20

def load_source():
    fc = json.loads(SRC.read_text(encoding="utf-8"))
    feat = next(f for f in fc["features"] if str(f["properties"]["cnn"]) == CNN)
    coords = list(reversed(feat["geometry"]["coordinates"]))  # Hyde -> east
    return feat, coords[VERTEX_START:VERTEX_END+1]

def transform_vertices(coords):
    tr = Transformer.from_crs(4326, 7131, always_xy=True)
    xy = [tr.transform(lon, lat) for lon, lat in coords]
    x0, n0 = xy[0]
    out=[]
    chain=0.0
    prev=None
    for i,((lon,lat),(e,n)) in enumerate(zip(coords,xy)):
        local_x=e-x0
        local_z=-(n-n0)
        if prev is not None:
            chain += math.hypot(local_x-prev[0], local_z-prev[1])
        out.append({
            "source_vertex_index":VERTEX_START+i,
            "longitude":lon,"latitude":lat,
            "easting_m":round(e,4),"northing_m":round(n,4),
            "local_x_m":round(local_x,4),"local_z_m":round(local_z,4),
            "chainage_m":round(chain,4)
        })
        prev=(local_x,local_z)
    return out

def rasterize(vertices):
    pts=set()
    for a,b in zip(vertices,vertices[1:]):
        x0,z0=a["local_x_m"],a["local_z_m"]
        x1,z1=b["local_x_m"],b["local_z_m"]
        d=math.hypot(x1-x0,z1-z0)
        steps=max(1,math.ceil(d/0.20))
        for j in range(steps+1):
            t=j/steps
            x=round(x0+(x1-x0)*t)
            z=round(z0+(z1-z0)*t)
            pts.add((x+OFFSET_X,-1,z+OFFSET_Z))
    return pts

def write_svg(vertices):
    xs=[v["local_x_m"] for v in vertices]; zs=[v["local_z_m"] for v in vertices]
    minx,maxx=min(xs),max(xs); minz,maxz=min(zs),max(zs)
    scale=8; pad=24
    w=(maxx-minx)*scale+pad*2 or 100
    h=(maxz-minz)*scale+pad*2 or 100
    def p(v):
        return f'{pad+(v["local_x_m"]-minx)*scale:.1f},{pad+(v["local_z_m"]-minz)*scale:.1f}'
    poly=" ".join(p(v) for v in vertices)
    circles="\n".join(f'<circle cx="{p(v).split(",")[0]}" cy="{p(v).split(",")[1]}" r="3"/><text x="{float(p(v).split(",")[0])+5:.1f}" y="{float(p(v).split(",")[1])-5:.1f}" font-size="10">{v["source_vertex_index"]}</text>' for v in vertices)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.1f} {h:.1f}">
<rect width="100%" height="100%" fill="white"/>
<polyline points="{poly}" fill="none" stroke="black" stroke-width="2"/>
{circles}
<text x="10" y="{h-8:.1f}" font-size="11">DataSF CNN {CNN}, vertices {VERTEX_START}-{VERTEX_END}; +X east, +Z south; 1 unit = 1 m</text>
</svg>'''
    (SLICE/"centerline_preview.svg").write_text(svg,encoding="utf-8")

def main():
    feat, coords=load_source()
    vertices=transform_vertices(coords)
    SLICE.mkdir(parents=True,exist_ok=True)
    source_doc={
      "schema_version":1,"slice_id":"LOMBARD_HYDE_TURN_001",
      "purpose":"First stress-build slice: Hyde entry and first verified switchback centerline only.",
      "source_dataset":"DataSF Streets Active and Retired (3psu-pn9h)",
      "source_cnn":CNN,"source_data_as_of":feat["properties"].get("data_as_of"),
      "source_vertex_range":[VERTEX_START,VERTEX_END],
      "working_crs":"EPSG:7131",
      "minecraft_scale":"1 block = 1 meter bulk grid",
      "orientation":"+X east, +Z south",
      "export_translation_blocks":[OFFSET_X,0,OFFSET_Z],
      "truth_scope":["centerline plan geometry"],
      "explicitly_not_truth_yet":["terrain elevation","road width","curbs","sidewalks","stairs","retaining walls","planters","landscaping","houses"],
      "vertices":vertices
    }
    (SLICE/"source_geometry.json").write_text(json.dumps(source_doc,indent=2)+"\n",encoding="utf-8")
    write_svg(vertices)

    path=rasterize(vertices)
    blocks={(0,-1,0):"minecraft:yellow_concrete"}
    for p in path: blocks[p]="minecraft:cyan_concrete"
    blocks[(OFFSET_X,-1,OFFSET_Z)]="minecraft:red_concrete"
    end=vertices[-1]
    endp=(round(end["local_x_m"])+OFFSET_X,-1,round(end["local_z_m"])+OFFSET_Z)
    blocks[endp]="minecraft:orange_concrete"

    minx=min(x for x,y,z in blocks); maxx=max(x for x,y,z in blocks)
    minz=min(z for x,y,z in blocks); maxz=max(z for x,y,z in blocks)
    meta=write_single_region_litematic(
      OUT,blocks,(minx,-1,minz,maxx,-1,maxz),
      "lombard_hyde_turn_001","Lombard Hyde Turn Centerline v001",
      "Stress-build Slice 001. DataSF centerline only. Red=Hyde start, orange=slice end, cyan=centerline."
    )
    actual,_=read_back_block_map(OUT,"lombard_hyde_turn_001")
    exact=actual==blocks
    report={
      "schema_version":1,"slice_id":"LOMBARD_HYDE_TURN_001",
      "status":"valid" if exact else "invalid",
      "file":str(OUT.relative_to(ROOT)).replace("\\","/"),
      "sha256":meta["sha256"],
      "source_cnn":CNN,"source_vertex_range":[VERTEX_START,VERTEX_END],
      "source_polyline_length_m":vertices[-1]["chainage_m"],
      "raster_centerline_blocks":len(path),
      "registration_marker_ok":actual.get((0,-1,0))=="minecraft:yellow_concrete",
      "exact_block_map":exact,
      "review_gate":"USER_MINECRAFT_FLYAROUND_REQUIRED",
      "notes_requested":["overall 1:1 scale impression","curve shape/spacing","orientation/readability","whether this is a useful slice size"]
    }
    VAL.parent.mkdir(parents=True,exist_ok=True)
    VAL.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not exact: raise SystemExit(1)

if __name__=="__main__":
    main()
