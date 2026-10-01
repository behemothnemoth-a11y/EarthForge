#!/usr/bin/env python3
"""Redfield full-block rear/service evidence pass v003.

Adds only features with structured evidence:
- three OSM secondary/rear structures (604, 621, 624);
- west-north OSM parking aisle;
- informal west-alley-to-621 path;
- OSM 621 rear step/footway traces as surface geometry.

No invented rear doors or utility fixtures are added.
"""
from __future__ import annotations
import csv, json, math, statistics, sys
from pathlib import Path
from collections import defaultdict, Counter

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter, canonical_state, read_back_block_map, write_single_region_litematic
)
from pipeline.microblocks.astra_microblock_codec import (
    BLOCK_ENTITY_ID, HOST_STATE, MicroVolume, decode_volume_v4, tile_entity_payload
)
from pipeline.reconstruction import generate_redfield_full_block_streetscape_v002 as street

PROJECT=ROOT/"projects"/"redfield_sd"
SOURCE=PROJECT/"outputs/full_block_streetscape_v002/Redfield_POC_001_FullBlock_Streetscape_v002.litematic"
SOURCE_REGION="REDFIELD_POC001_FULLBLOCK_STREETSCAPE_V002"
GEOM=PROJECT/"poc_001/l0_geometry_local.json"
ADDR=PROJECT/"poc_001/address_match_v003.json"
LIDAR=PROJECT/"downloads/multisource_v001/lidar_spink_2012/redfield_poc001_roi_points.csv"
OUT=PROJECT/"outputs/full_block_rear_v003"
NAME="Redfield_POC_001_FullBlock_RearService_v003"
REGION="REDFIELD_POC001_FULLBLOCK_REAR_SERVICE_V003"
REF_X=-78;REF_Z=9

WALL={
    1474301437:"minecraft:bricks",
    1474301443:"minecraft:bricks",
    1474301409:"minecraft:gray_concrete",
}
FALLBACK_H={1474301437:3.5,1474301443:3.1,1474301409:3.4}
ROOF="astra_microblocks:rgb_55585a"
WALK="astra_microblocks:rgb_a9a79f"
SERVICE="astra_microblocks:rgb_6f706d"

def floor16(v):
    h=math.floor(v/16);return h,v-h*16

def load_model():
    blocks,meta=read_back_block_map(SOURCE,SOURCE_REGION);rp=meta["region_position"];hosts={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2]);v=MicroVolume();v.cells=decode_volume_v4(te["volume_v4"]);hosts[p]=v
    return blocks,hosts

def set_micro(blocks,hosts,sx,sy,sz,mat):
    hx,lx=floor16(sx);hy,ly=floor16(sy);hz,lz=floor16(sz);p=(hx,hy,hz)
    if p in blocks and blocks[p]!=HOST_STATE:
        old=blocks[p];v=MicroVolume(old);v.fill_box(0,0,0,16,16,16,old);hosts[p]=v;blocks[p]=HOST_STATE
    v=hosts.get(p)
    if v is None:v=MicroVolume("minecraft:stone");hosts[p]=v;blocks[p]=HOST_STATE
    v.set(lx,ly,lz,mat)

def poly_inside(x,z,p):
    inside=False;j=len(p)-1
    for i,(xi,zi) in enumerate(p):
        xj,zj=p[j]
        if ((zi>z)!=(zj>z)) and x<(xj-xi)*(z-zi)/(zj-zi+1e-300)+xi:inside=not inside
        j=i
    return inside

def raster(poly):
    xs=[x for x,z in poly];zs=[z for x,z in poly];out=set()
    for x in range(math.floor(min(xs)),math.ceil(max(xs))):
        for z in range(math.floor(min(zs)),math.ceil(max(zs))):
            if poly_inside(x+.5,z+.5,poly):out.add((x,z))
    return out

def lidar_points():
    pts=[]
    with LIDAR.open() as f:
        for a in csv.DictReader(f):pts.append((float(a["x_local_m"]),float(a["z_local_m"]),float(a["elev_m"]),int(a["class"])))
    return pts

def structure_height(poly,pts,ground_median,fallback):
    vals=[]
    for x,z,e,c in pts:
        if c!=1 or not poly_inside(x,z,poly):continue
        g=ground_median(x,z);h=e-g
        if 1.5<=h<=12:vals.append(h)
    if not vals:return fallback,0
    hist=Counter(round(v*4)/4 for v in vals);return hist.most_common(1)[0][0],len(vals)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blocks,hosts=load_model();geom=json.loads(GEOM.read_text());addr=json.loads(ADDR.read_text())
    byid={b["osm_id"]:b for b in geom["buildings"]};secondary=addr["secondary"];pts=lidar_points()
    med,base=street.load_ground_bins()
    def ground(x,z):
        e=street.ground_elev(med,x,z);return e if e is not None else base
    audit={}
    for sec in secondary:
        oid=sec["osm_id"];poly=byid[oid]["polygon_xz_m"];cells=raster(poly)
        cx=sum(x for x,z in poly)/len(poly);cz=sum(z for x,z in poly)/len(poly)
        base_cells=street.height_cells(med,base,cx,cz)
        h,n=structure_height(poly,pts,ground,FALLBACK_H[oid]);top=base_cells+round(h*16)
        perim={c for c in cells if any((c[0]+dx,c[1]+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}
        for x,z in perim:
            sx=(x-REF_X)*16;sz=(z-REF_Z)*16
            for lx in range(16):
                for lz in range(16):
                    # keep a 2-cell shell rather than solid structure
                    edge=(lx<2 or lx>=14 or lz<2 or lz>=14)
                    if edge:
                        for y in range(base_cells,top):set_micro(blocks,hosts,sx+lx,y,sz+lz,WALL[oid])
        for x,z in cells:
            sx=(x-REF_X)*16;sz=(z-REF_Z)*16
            for lx in range(16):
                for lz in range(16):
                    for y in range(max(base_cells,top-2),top):set_micro(blocks,hosts,sx+lx,y,sz+lz,ROOF)
        audit[str(oid)]={"name":sec["name"],"footprint_blocks":len(cells),"height_m":h,"lidar_return_count":n,"base_microcells":base_cells,"top_microcells":top}

    # Structured service geometries from OSM.
    transport={f["osm_id"]:f for f in geom["transport"]}
    service_ids=[1474301446,1474301450,1474301420,1474301452]
    surf_audit={}
    for oid in service_ids:
        f=transport[oid];line=f["line_xz_m"];radius=2 if oid==1474301446 else 1
        touched=set()
        for (x0,z0),(x1,z1) in zip(line,line[1:]):
            steps=max(1,round(math.hypot(x1-x0,z1-z0)*2))
            for i in range(steps+1):
                x=x0+(x1-x0)*i/steps;z=z0+(z1-z0)*i/steps
                for bx in range(round(x)-radius,round(x)+radius+1):
                    for bz in range(round(z)-radius,round(z)+radius+1):
                        if (bx-x)**2+(bz-z)**2<=radius*radius+0.7:touched.add((bx,bz))
        for x,z in touched:
            h=street.height_cells(med,base,x,z)
            street.surface_column(blocks,hosts,x,z,h,"minecraft:smooth_stone",SERVICE if oid in (1474301446,1474301450) else WALK)
        surf_audit[str(oid)]={"role":f["tags"],"surface_blocks":len(touched)}

    for p in hosts:blocks[p]=HOST_STATE
    xs=[p[0] for p in blocks];ys=[p[1] for p in blocks];zs=[p[2] for p in blocks];bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    w=NBTWriter();tes=[tile_entity_payload(w,(x-bounds[0],y-bounds[1],z-bounds[2]),v) for (x,y,z),v in sorted(hosts.items())]
    out=OUT/f"{NAME}.litematic";stats=write_single_region_litematic(out,blocks,bounds,REGION,NAME,"Full-block streetscape plus OSM secondary rear structures and service circulation. No invented rear openings/utilities.",data_version=4903,tile_entity_payloads=tes)
    reread,meta=read_back_block_map(out,REGION);assert reread=={p:canonical_state(s) for p,s in blocks.items()}
    rp=meta["region_position"];decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2]);decoded[p]=decode_volume_v4(te["volume_v4"])
    assert set(decoded)==set(hosts)
    for p,v in hosts.items():assert decoded[p]==v.cells,p
    report={**stats,"secondary_structures":audit,"service_surfaces":surf_audit,"astra":{"hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values())},"validation":{"exact_block_readback":True,"exact_astra_readback":True,"registration_marker":reread.get((0,-1,0))=="minecraft:yellow_concrete","invented_rear_doors":False,"invented_utilities":False,"in_game_review":False}}
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"Build_notes.md").write_text("# Redfield Full Block Rear/Service v003\n\nAdds the three OSM secondary structures (604, 621, 624) plus the mapped west-north parking aisle, informal alley path and 621 rear footway/steps surfaces. Building heights use LiDAR where returns exist; 624 uses a documented fallback because the small rear footprint has no clean first returns. Rear doors and utilities remain intentionally absent pending direct imagery.\n")
    print(json.dumps({"file":str(out),"sha256":stats["sha256"],"secondary":audit,"service_surfaces":surf_audit,"astra_hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values()),"validation":"PASS"},indent=2))

if __name__=="__main__":main()
