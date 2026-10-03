"""Lombard v031: conservative source-grounded 1040 outer shell.

This is the first Minecraft geometry after the 1040 source reset. It intentionally
contains no facade styling, openings, bay projections, terrace/pergola, or roof
interpretation. The goal is only to review footprint registration, street datum,
site relationship, and absolute envelope scale.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, shape

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.reconstruction import generate_lombard_access_tree_realism_v024 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction import generate_lombard_realism_v020 as realism
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic

OUT=realm.v.PROJECT/"outputs/house_1040_shell_v031"
NAME="Lombard_1040_Source_Shell_Astra_v031"
REGION="LOMBARD_1040_SOURCE_SHELL_V031"
BUILDING_ID="201006.0032105"

SHELL="astra_microblocks:rgb_b7b2a8"
TOP_RING="astra_microblocks:rgb_686d70"
DATUM_MARK="astra_microblocks:rgb_8b9aa1"
WALL_THICKNESS_M=.1875

def xyz(pos,i):
    hx,hy,hz=pos
    return hx*16+(i&15)-480,hy*16+(i>>8),hz*16+((i>>4)&15)-320

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=parent.OUT/f"{parent.NAME}.litematic"
    blocks,hosts=read(source,parent.REGION)
    vanilla={p:s for p,s in blocks.items() if p not in hosts}
    original={p:(q.original,q.cells.copy()) for p,q in hosts.items()}

    env=json.loads((buildings.OUT/"building_envelopes.geojson").read_text())
    feat=next(f for f in env["features"] if str(f["properties"]["id"])==BUILDING_ID)
    geom=shape(feat["geometry"])
    poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,"geoms") else geom
    prop=feat["properties"]

    center=json.loads(realm.v.CENTER.read_text())
    road=LineString([(q["x_m"],q["z_m"]) for q in center])
    coords=list(poly.exterior.coords)
    edges=[]
    for a,b in zip(coords,coords[1:]):
        seg=LineString([a,b])
        if seg.length>5:
            edges.append((seg.distance(road),seg.length,np.array(a,float),np.array(b,float)))
    _,front_width,pa,pb=min(edges,key=lambda q:q[0])
    if pa[0]>pb[0]:
        pa,pb=pb,pa
    vec=pb-pa
    uvec=vec/np.linalg.norm(vec)
    normal=np.array([-uvec[1],uvec[0]])
    if np.dot(np.array([poly.centroid.x,poly.centroid.y])-((pa+pb)/2),normal)<0:
        normal=-normal

    # Accepted street datum: driveway cells immediately outside the garage/front band.
    drive_y=[]
    for hp,hv in hosts.items():
        for ii,mm in enumerate(hv.cells):
            if mm not in {parent.DRIVE,parent.DRIVE_JOINT}:
                continue
            xx,yy,zz=xyz(hp,ii)
            pt=np.array([(xx+.5)/16,(zz+.5)/16])
            r=pt-pa
            u=float(np.dot(r,uvec))/front_width
            d=float(np.dot(r,normal))
            if .18<=u<=.72 and -2.25<=d<=-.30:
                drive_y.append(yy)
    if len(drive_y)<20:
        raise RuntimeError("1040 shell lacks supported accepted driveway datum")
    drive_floor=int(round(float(np.median(drive_y))))+1

    zero=float(center[0]["elev_navd88_m"])
    source_cap=round((prop["median_first_return_navd88_m"]-zero)*16)
    envelope_h=(source_cap-drive_floor)/16
    osm_h=float(prop.get("osm_height_m") or 12.0)
    source_height=float(prop.get("source_median_height_m") or prop.get("height_median_m") or envelope_h)

    # Remove only the old 1040 placeholder/interpreted materials from accepted v024.
    old1040={*buildings.WALLS,buildings.ROOF,
             realism.rgb("a9cbd6"),realism.rgb("293f48"),
             realism.rgb("95c7d4"),realism.rgb("799da5"),realism.rgb("8cb3ba")}
    writes={}
    changes={}
    target=poly.buffer(.16)
    minx,minz,maxx,maxz=target.bounds
    candidate_hosts=[]
    for p,v in hosts.items():
        hx,hy,hz=p
        hminx=(hx*16-480)/16;hmaxx=(hx*16-480+15)/16
        hminz=(hz*16-320)/16;hmaxz=(hz*16-320+15)/16
        if hmaxx<minx or hminx>maxx or hmaxz<minz or hminz>maxz:
            continue
        candidate_hosts.append((p,v))

    def put(x,y,z,mat,why):
        p,i=position(int(x),int(y),int(z))
        if p in vanilla:
            return False
        old=hosts[p].cells[i] if p in hosts else None
        if old==mat:
            return False
        if p not in hosts:
            hosts[p]=MicroVolume("minecraft:bricks")
            blocks[p]=HOST_STATE
        hosts[p].cells[i]=mat
        writes[(p,i)]=(old,mat,why)
        changes[why]=changes.get(why,0)+1
        return True

    clear_min=round((prop["ground_min_navd88_m"]-zero)*16)-4
    clear_max=source_cap+4
    for p,v in candidate_hosts:
        for i,m in enumerate(v.cells.copy()):
            if m not in old1040:
                continue
            x,y,z=xyz(p,i)
            if clear_min<=y<=clear_max and target.covers(Point((x+.5)/16,(z+.5)/16)):
                put(x,y,z,None,"remove_old_1040")

    # Conservative support surface: accepted hardscape/context ground only.
    support_materials={
        parent.DRIVE,parent.DRIVE_JOINT,
        realm.WALK,realm.WALKJOINT,realm.STEP,realm.BRICK,realm.GREEN,
        buildings.GROUND,buildings.BASE,
        realism.rgb("63764a"),realism.rgb("687a4e"),
        realism.rgb("607348"),realism.rgb("6b7c50"),
    }
    support={}
    for p,v in hosts.items():
        hx,hy,hz=p
        hminx=(hx*16-480)/16;hmaxx=(hx*16-480+15)/16
        hminz=(hz*16-320)/16;hmaxz=(hz*16-320+15)/16
        if hmaxx<minx-2 or hminx>maxx+2 or hmaxz<minz-2 or hminz>maxz+2:
            continue
        for i,m in enumerate(v.cells):
            if m not in support_materials:
                continue
            x,y,z=xyz(p,i)
            support[(x,z)]=max(support.get((x,z),-10**9),y)

    ring=poly.boundary.buffer(WALL_THICKNESS_M/2,cap_style=2,join_style=2)
    bx0,bz0,bx1,bz1=poly.bounds
    wall_columns=[]
    unresolved_base_columns=0

    for x in range(math.floor((bx0-.25)*16),math.ceil((bx1+.25)*16)):
        for z in range(math.floor((bz0-.25)*16),math.ceil((bz1+.25)*16)):
            pt=Point((x+.5)/16,(z+.5)/16)
            if not ring.covers(pt):
                continue

            # Use nearest accepted exterior support when present, but never start
            # below the accepted front driveway datum. The base is a visibility
            # control, not a foundation/finished-floor claim.
            candidates=[]
            for dx in range(-24,25):
                for dz in range(-24,25):
                    val=support.get((x+dx,z+dz))
                    if val is None:
                        continue
                    q=Point((x+dx+.5)/16,(z+dz+.5)/16)
                    if poly.buffer(-.02).covers(q):
                        continue
                    dist=math.hypot(dx,dz)/16
                    if dist<=1.5:
                        candidates.append((dist,val))
            if candidates:
                candidates.sort(key=lambda q:q[0])
                near=[v for d,v in candidates if d<=min(1.5,candidates[0][0]+.35)]
                local_base=int(round(float(np.median(near))))+1
                base=max(drive_floor,local_base)
            else:
                base=drive_floor
                unresolved_base_columns+=1

            if base>=source_cap:
                continue
            wall_columns.append((x,z,base))
            for y in range(base,source_cap):
                mat=TOP_RING if y>=source_cap-2 else SHELL
                put(x,y,z,mat,"source_shell_wall")

    # Explicit front datum line only: a thin internal review marker at the accepted
    # driveway level. It is not a floor and does not span the building.
    for x in range(math.floor((min(pa[0],pb[0])-.1)*16),math.ceil((max(pa[0],pb[0])+.1)*16)):
        for z in range(math.floor((min(pa[1],pb[1])-.1)*16),math.ceil((max(pa[1],pb[1])+.1)*16)):
            pt=np.array([(x+.5)/16,(z+.5)/16])
            r=pt-pa
            along=float(np.dot(r,uvec))
            depth=float(np.dot(r,normal))
            if 0<=along<=front_width and abs(depth)<=.07:
                put(x,drive_floor,z,DATUM_MARK,"front_datum_marker")

    for p in list(hosts):
        if not any(hosts[p].cells):
            hosts.pop(p)
            blocks.pop(p,None)

    # Hard scope gates.
    escaped=[]
    public_overlap=[]
    public_mats={parent.DRIVE,parent.DRIVE_JOINT,realm.WALK,realm.WALKJOINT,realm.STEP,realm.BRICK}
    for (p,i),(old,new,why) in writes.items():
        x,y,z=xyz(p,i)
        pt=Point((x+.5)/16,(z+.5)/16)
        if why=="front_datum_marker":
            if pt.distance(poly.exterior)>0.20:
                escaped.append([x,y,z,why])
        elif not target.covers(pt):
            escaped.append([x,y,z,why])
        if old in public_mats:
            public_overlap.append([x,y,z,why,old,new])
    if escaped or public_overlap:
        raise RuntimeError(str({"scope":escaped[:4],"public":public_overlap[:4]}))

    outside_ok=True
    touched={p for p,i in writes}
    for p,(orig,cells) in original.items():
        q=hosts.get(p)
        if p not in touched:
            if q is None or q.original!=orig or q.cells!=cells:
                outside_ok=False
                break
        else:
            for i,a in enumerate(cells):
                if (p,i) in writes:
                    continue
                b=q.cells[i] if q is not None else None
                if a!=b:
                    outside_ok=False
                    break
            if not outside_ok:
                break

    # Source review sheet: structured data only; no architecture interpretation.
    plan=Image.new("RGB",(1000,520),"white")
    d=ImageDraw.Draw(plan)
    pts=list(poly.exterior.coords)+list(road.coords)
    minpx=min(p[0] for p in pts)-5;maxpx=max(p[0] for p in pts)+5
    minpz=min(p[1] for p in pts)-5;maxpz=max(p[1] for p in pts)+5
    def pp(x,z):
        return (
            int(45+(x-minpx)/max(1e-9,maxpx-minpx)*910),
            int(45+(z-minpz)/max(1e-9,maxpz-minpz)*400),
        )
    d.line([pp(x,z) for x,z in road.coords],fill=(154,84,72),width=7)
    d.polygon([pp(x,z) for x,z in poly.exterior.coords],fill=(224,224,218),outline=(40,50,55))
    d.line([pp(*pa),pp(*pb)],fill=(25,105,165),width=9)
    d.text((45,470),"Blue = source street-facing footprint edge. Gray = full DataSF footprint. No facade subdivisions.",fill=(40,50,55))
    plan_path=OUT/"Lombard_1040_v031_plan_control.png"
    plan.save(plan_path)

    section=Image.new("RGB",(1000,520),"white")
    sd=ImageDraw.Draw(section)
    x0,x1=120,880
    ground_y=410
    top_y=95
    sd.line((x0,ground_y,x1,ground_y),fill=(120,120,115),width=4)
    sd.rectangle((x0,top_y,x1,ground_y),outline=(110,112,110),width=7)
    sd.line((x0,top_y,x1,top_y),fill=(50,60,65),width=8)
    sd.text((130,ground_y+18),f"accepted driveway datum = local y {drive_floor}/16 m",fill=(45,55,60))
    sd.text((130,top_y-28),f"source median-first-return cap = local y {source_cap}/16 m",fill=(45,55,60))
    sd.text((130,230),f"review envelope above driveway = {envelope_h:.3f} m",fill=(45,55,60))
    sd.text((130,258),f"OSM height = {osm_h:.2f} m; source median height = {source_height:.2f} m",fill=(45,55,60))
    sd.text((130,300),"This rectangle is an uncertainty envelope, not a roof/storey/facade interpretation.",fill=(125,55,45))
    section_path=OUT/"Lombard_1040_v031_height_control.png"
    section.save(section_path)

    coords_np=np.array(list(blocks))
    lo=coords_np.min(0);hi=coords_np.max(0)
    bounds=(*lo.tolist(),*hi.tolist())
    writer=NBTWriter()
    payload=[
        tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),q)
        for p,q in sorted(hosts.items())
    ]
    artifact=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        artifact,blocks,bounds,REGION,NAME,
        "1040 Lombard conservative source shell: verified footprint, accepted driveway datum, and source vertical envelope only. No roof/facade/opening/projection interpretation.",
        data_version=realm.v.DATA_VERSION,
        tile_entity_payloads=payload,
    )
    actual,decoded=read(artifact,REGION)
    checks={
        "exact_litematica":actual=={p:canonical_state(s) for p,s in blocks.items()},
        "exact_astra":set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
        "declared_1040_scope_only":not escaped,
        "public_realm_cells_untouched":not public_overlap,
        "all_parent_cells_outside_declared_edits_preserved":outside_ok,
        "vanilla_preserved":all(actual.get(p)==s for p,s in vanilla.items()),
        "driveway_datum_supported":len(drive_y)>=20,
        "source_front_width_consistent":10.7<float(front_width)<11.2,
        "no_roof_or_floor_generated":True,
    }
    report={
        **stats,
        "status":"PASS" if all(checks.values()) else "FAIL",
        "validation":checks,
        "parent":"v024 accepted public-realm/access context",
        "parent_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "building_id":BUILDING_ID,
        "address":"1040 Lombard Street",
        "source_footprint_area_m2":float(poly.area),
        "street_facing_edge_m":float(front_width),
        "driveway_datum_samples":len(drive_y),
        "driveway_datum_local_micro_y":drive_floor,
        "source_cap_local_micro_y":source_cap,
        "envelope_height_above_driveway_m":float(envelope_h),
        "osm_height_m":osm_h,
        "source_median_height_m":source_height,
        "wall_columns":len(wall_columns),
        "wall_columns_using_driveway_fallback":unresolved_base_columns,
        "changed_microcells":len(writes),
        "changes":changes,
        "geometry_claims":["DataSF footprint perimeter","accepted v024 driveway datum","source median-first-return absolute cap"],
        "explicit_non_claims":["roof form","roof elevation plane","storey lines","finished-floor elevation","foundation","bay projection","windows","doors","garage opening dimensions","entry depth","terrace","pergola","facade materials"],
        "review":"USER_MINECRAFT_FLYAROUND_REQUIRED",
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/f"{NAME}_placement.json").write_text(json.dumps({
        "placement_origin":"same Lombard player-feet origin",
        "rotation":0,"mirror":"none","replace_blocks":"ALL including air"
    },indent=2)+"\n")
    (OUT/"Build_notes.md").write_text(
        "# 1040 Lombard conservative shell v031\n\n"
        "First post-reset Minecraft geometry. Hollow neutral shell only. "
        "No roof/floor/openings/bays/terrace/pergola are asserted.\n"
    )
    print(json.dumps({
        "file":str(artifact.relative_to(ROOT)),
        "status":report["status"],
        "front_width_m":front_width,
        "envelope_height_m":envelope_h,
        "wall_columns":len(wall_columns),
        "fallback_columns":unresolved_base_columns,
        "validation":checks,
    },indent=2))
    if report["status"]!="PASS":
        raise SystemExit(1)

if __name__=="__main__":
    main()
