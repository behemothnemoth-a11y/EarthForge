"""B0 evidence audit for 1040 Lombard. Produces no Minecraft geometry."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely import contains_xy
from shapely.geometry import LineString, shape

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/"projects"/"lombard_sf"
OUT=PROJECT/"outputs"/"house_1040_source_truth_v027"
BUILDING_ID="201006.0032105"
REFREG=OUT/"Lombard_1040_Reference_Resolution_v027.json"
CP_PATH=PROJECT/"source_manifests/1040_lombard_control_points_v028.json"
LIDAR_CLASS=OUT/"Lombard_1040_LiDAR_Surface_Classification_v028.json"
MULTIVIEW=OUT/"Lombard_1040_Multiview_Track_Candidates_v028.json"

def qstats(values):
    if len(values)==0:return {"count":0}
    q=np.percentile(values,[0,5,25,50,75,95,100])
    return {"count":int(len(values)),"min":float(q[0]),"p05":float(q[1]),"p25":float(q[2]),"median":float(q[3]),"p75":float(q[4]),"p95":float(q[5]),"max":float(q[6])}

def control_point_status(cp):
    by_view=Counter();eligible=[];planes=set()
    for point in cp.get("points",[]):
        good=[]
        for view,obs in point.get("observations",{}).items():
            if isinstance(obs,dict) and isinstance(obs.get("pixel"),list) and len(obs["pixel"])==2:
                good.append(view);by_view[view]+=1
        if len(good)>=3:
            eligible.append(point["id"]);planes.add(point.get("plane","unknown"))
    gate=cp.get("minimum_gate",{})
    passed=(len(eligible)>=int(gate.get("points_with_three_or_more_observations",8))
            and len(by_view)>=int(gate.get("geotagged_views",3))
            and len(planes)>=int(gate.get("planes_represented",3)))
    return {"eligible_points":eligible,"eligible_point_count":len(eligible),
            "observations_by_view":dict(by_view),"eligible_planes":sorted(planes),
            "gate":gate,"gate_passed":passed}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    truth=json.loads((PROJECT/"poc_001/l0_source_truth_v001.json").read_text())
    buildings=json.loads((PROJECT/"poc_001/l2_building_source_truth_v002.json").read_text())
    manifest=json.loads((PROJECT/"source_manifests/1040_lombard_source_truth_v027.json").read_text())
    cp=json.loads(CP_PATH.read_text())
    refreg=json.loads(REFREG.read_text()) if REFREG.exists() else None
    lidar_class=json.loads(LIDAR_CLASS.read_text()) if LIDAR_CLASS.exists() else None
    multiview=json.loads(MULTIVIEW.read_text()) if MULTIVIEW.exists() else None

    rec=next(b for b in buildings["buildings"] if b["sf16_bldgid"]==BUILDING_ID)
    geom=shape(rec["geometry_local"]);poly=max(geom.geoms,key=lambda g:g.area) if hasattr(geom,"geoms") else geom
    road=LineString(truth["crooked_road"]["centerline_nodes"])
    edges=[]
    coords=list(poly.exterior.coords)
    for a,b in zip(coords,coords[1:]):
        seg=LineString([a,b])
        edges.append({"a":[float(a[0]),float(a[1])],"b":[float(b[0]),float(b[1])],
                      "length_m":float(seg.length),"distance_to_road_m":float(seg.distance(road))})
    street_edge=min(edges,key=lambda e:e["distance_to_road_m"])

    frame=truth["coordinate_frame"];anchor_e=frame["anchor_epsg3717_m"]["easting"];anchor_n=frame["anchor_epsg3717_m"]["northing"]
    tf=Transformer.from_crs(4326,3717,always_xy=True)
    cameras=[]
    for image in manifest["imagery"]:
        camera=image.get("camera")
        if not camera:continue
        lat,lon=camera;e,n=tf.transform(lon,lat);x=float(e-anchor_e);z=float(anchor_n-n)
        dx=float(poly.centroid.x-x);dz=float(poly.centroid.y-z)
        cameras.append({
            "date":image["date"],"title":image["title"],"local_x_m":x,"local_z_m":z,
            "distance_to_building_centroid_m":math.hypot(dx,dz),
            "bearing_to_building_local_deg":math.degrees(math.atan2(dx,-dz))%360.0,
            "camera_altitude_m":image.get("camera_altitude_m"),
            "camera_model":image.get("camera_model"),"focal_length_mm":image.get("focal_length_mm"),
            "focal_35mm_equiv_mm":image.get("focal_35mm_equiv_mm"),
            "source_page":image["page"],
            "registration_limit":"Position plus focal metadata are priors only; heading/pitch/roll and facade correspondences remain unsolved."
        })

    raw_path=PROJECT/"downloads/raw/lombard_poc001_lidar_roi_v001.npz"
    raw_materialized=raw_path.exists()
    if raw_materialized:
        raw=np.load(raw_path)
        inside=contains_xy(poly,raw["x"],raw["z"]);near=contains_xy(poly.buffer(1.5),raw["x"],raw["z"])
        ground=inside&(raw["classification"]==2);nonground=inside&(raw["classification"]!=2)
        lidar={
            "raw_source":str(raw_path.relative_to(ROOT)),"materialized_on_runner":True,
            "inside_footprint_points":int(inside.sum()),
            "inside_class_counts":{str(k):v for k,v in sorted(Counter(map(int,raw["classification"][inside])).items())},
            "within_1_5m_class_counts":{str(k):v for k,v in sorted(Counter(map(int,raw["classification"][near])).items())},
            "ground_elevation_navd88_m":qstats(raw["elev"][ground]),
            "non_ground_elevation_navd88_m":qstats(raw["elev"][nonground]),
            "non_ground_height_above_manifest_ground_min_m":qstats(raw["elev"][nonground]-manifest["building"]["source_ground_min_navd88_m"]),
            "interpretation_limit":"Non-ground returns are observations only. This audit does not classify individual returns as building versus vegetation and does not infer storeys or roof planes."
        }
        inside_count=int(inside.sum())
    else:
        lidar={"raw_source":str(raw_path.relative_to(ROOT)),"materialized_on_runner":False,
               "tracked_source_summary":truth.get("lidar",{}),
               "interpretation_limit":"Raw LiDAR is not stored in Git. B0 vertical classification is blocked until public source materialization."}
        inside_count=None

    cpstat=control_point_status(cp)
    ref_ok=bool(refreg and refreg.get("count")==len(manifest["imagery"]) and refreg.get("all_dimensions_verified"))
    intrinsic_count=sum(1 for i in manifest["imagery"] if i.get("focal_length_mm") is not None)
    checks={
        "identity_has_datasf_id":manifest["building"]["datasf_building_id"]==BUILDING_ID,
        "identity_has_osm_way":bool(manifest["building"].get("osm_way")),
        "footprint_loaded":poly.area>100,
        "street_edge_derived_from_footprint_and_road":street_edge["length_m"]>5,
        "reference_registry_has_multi_year_views":len(manifest["imagery"])>=5,
        "reference_originals_resolved_and_dimension_checked":ref_ok,
        "multiple_geotagged_cameras_registered":len(cameras)>=3,
        "camera_intrinsics_partially_recovered":intrinsic_count>=4,
        "control_point_schema_present":len(cp.get("points",[]))>=8,
        "control_point_measurement_gate_met":cpstat["gate_passed"],
        "raw_lidar_materialized":raw_materialized,
        "lidar_surface_proxy_available":bool(lidar_class and lidar_class.get("cell_count",0)>20),
        "multiview_candidate_tracks_generated":bool(multiview and multiview.get("candidate_track_count",0)>0),
        "vertical_returns_kept_observational":True,
        "rejected_geometry_not_locked":all(term in manifest["not_locked"] for term in ["bay projection depths","window widths/heights","terrace depth","pergola dimensions"])
    }
    unresolved=[]
    if not ref_ok:unresolved.append("Resolve and dimension-check every canonical Wikimedia reference original on the cloud runner.")
    if intrinsic_count<4:unresolved.append("Recover usable focal/intrinsic metadata for enough reference cameras.")
    if not cpstat["gate_passed"]:
        if multiview and multiview.get("candidate_track_count",0)>0:
            unresolved.append("Curate machine-proposed multi-view tracks into the canonical control-point manifest: at least 8 stable architectural points in 3+ views spanning 3+ planes.")
        else:
            unresolved.append("Generate and then curate stable facade control points: at least 8 points in 3+ views spanning 3+ architectural planes.")
    if not raw_materialized:unresolved.append("Materialize the public raw LiDAR ROI/source on the cloud runner.")
    if not lidar_class:
        unresolved.append("Run the observational LiDAR local-roughness classifier before deriving vertical architectural bands.")
    else:
        unresolved.append("Cross-check planar LiDAR candidates against multi-year imagery before treating any return as building rather than vegetation.")
    unresolved += [
        "Solve camera heading/pitch/roll from stable multi-view correspondences; GPS/bearing-to-building is only a prior.",
        "Derive the garage/driveway threshold elevation from source-supported site-interface evidence.",
        "Solve facade scale and projection depths with uncertainty from registered multi-view correspondences.",
        "Produce measured elevation/depth controls before any B4 Minecraft shell is authorized."
    ]
    report={
        "schema_version":2,"gate":"1040_B0_SOURCE_TRUTH","result":"BLOCKED" if unresolved else "PASS",
        "building":{"datasf_building_id":BUILDING_ID,"osm_way":rec.get("osm_way"),
                    "address":f'{rec.get("address")} {rec.get("street")}',
                    "footprint_area_m2_derived":float(poly.area),
                    "centroid_local_m":[float(poly.centroid.x),float(poly.centroid.y)]},
        "street_facing_edge":street_edge,"registered_cameras":cameras,
        "reference_resolution":{"resolved":ref_ok,"count":refreg.get("count") if refreg else 0,
                                "intrinsic_metadata_views":intrinsic_count,
                                "report":str(REFREG.relative_to(ROOT))},
        "control_points":cpstat,
        "multiview_candidates":{"available":bool(multiview),
            "report":str(MULTIVIEW.relative_to(ROOT)),
            "candidate_track_count":multiview.get("candidate_track_count") if multiview else 0,
            "tracks_4plus":sum(1 for t in multiview.get("tracks",[]) if t.get("view_count",0)>=4) if multiview else 0,
            "interpretation_limit":"Machine tracks are annotation aids only. They are not architectural control points until curated into the canonical manifest."},
        "lidar":lidar,
        "lidar_surface_classification":{"available":bool(lidar_class),"report":str(LIDAR_CLASS.relative_to(ROOT)),
            "label_counts":lidar_class.get("label_counts") if lidar_class else None,
            "planar_candidate_fraction":lidar_class.get("planar_candidate_fraction") if lidar_class else None,
            "interpretation_limit":"A planar proxy is evidence triage only and never authorizes roof/storey geometry."},
        "checks":checks,"unresolved":unresolved,
        "geometry_generation_authorized":False
    }
    (OUT/"Lombard_1040_B0_Source_Truth_v027.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"Lombard_1040_B0_Control_Point_Status_v028.json").write_text(json.dumps(cpstat,indent=2)+"\n")

    pts=list(road.coords)+list(poly.exterior.coords)+[(c["local_x_m"],c["local_z_m"]) for c in cameras]
    minx=min(p[0] for p in pts)-4;maxx=max(p[0] for p in pts)+4;minz=min(p[1] for p in pts)-4;maxz=max(p[1] for p in pts)+4;W,H=1600,900
    def px(x,z):return (int(60+(x-minx)/max(1e-9,maxx-minx)*(W-120)),int(60+(z-minz)/max(1e-9,maxz-minz)*(H-120)))
    im=Image.new("RGB",(W,H),"white");d=ImageDraw.Draw(im)
    d.line([px(x,z) for x,z in road.coords],fill=(153,84,74),width=8)
    d.polygon([px(x,z) for x,z in poly.exterior.coords],fill=(220,224,223),outline=(35,52,58),width=4)
    d.line([px(*street_edge["a"]),px(*street_edge["b"])],fill=(20,104,156),width=10)
    cx,cz=poly.centroid.x,poly.centroid.y
    for c in cameras:
        p=px(c["local_x_m"],c["local_z_m"]);d.ellipse((p[0]-7,p[1]-7,p[0]+7,p[1]+7),fill=(52,116,66))
        d.line([p,px(cx,cz)],fill=(120,160,126),width=2);d.text((p[0]+10,p[1]-8),c["date"],fill=(30,60,35))
    d.text((50,20),"1040 Lombard B0 — registered footprint, road, and geotagged camera priors",fill=(25,35,40))
    d.text((50,H-32),"Blue = derived street-facing edge. Green = camera GPS. Rays point to centroid only; they are not solved optical axes.",fill=(55,65,70))
    im.save(OUT/"Lombard_1040_B0_Camera_Plan_v027.png")

    md=["# 1040 Lombard B0 source-truth audit","",f"**Result: {report['result']}**","",
        f"- DataSF building: {BUILDING_ID}",f"- Derived footprint area: {poly.area:.2f} m²",
        f"- Derived street-facing footprint edge: {street_edge['length_m']:.3f} m",
        f"- Canonical references resolved: {refreg.get('count') if refreg else 0}/{len(manifest['imagery'])}",
        f"- Geotagged camera priors: {len(cameras)}",f"- Views with focal metadata: {intrinsic_count}",
        f"- Machine multi-view candidate tracks: {multiview.get('candidate_track_count',0) if multiview else 0}",
        f"- Control points meeting 3-view rule: {cpstat['eligible_point_count']}",
        f"- Raw LiDAR points inside footprint: {inside_count if inside_count is not None else 'not materialized'}",
        "","## Unresolved before geometry",""]+[f"- {x}" for x in unresolved]
    (OUT/"Lombard_1040_B0_Source_Truth_v027.md").write_text("\n".join(md)+"\n")
    print(json.dumps({"result":report["result"],"checks":checks,"unresolved_count":len(unresolved),
                      "reference_count":refreg.get("count") if refreg else 0,
                      "control_point_gate":cpstat["gate_passed"],
                      "output":str(OUT.relative_to(ROOT))},indent=2))

if __name__=="__main__":main()
