#!/usr/bin/env python3
"""Prepare normalized geospatial truth for the Lombard Street POC.

Inputs are kept under projects/lombard_sf/downloads/raw and are gitignored.
Outputs are small derived JSON/CSV/PNG files suitable for review and Git.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import laspy
import numpy as np
from scipy.spatial import cKDTree
from laspy.copc import Bounds, CopcReader
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import shape, Point, LineString, Polygon
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipeline.terrain.ground_support import interpolate_ground, observed_grid
PROJECT = ROOT / "projects" / "lombard_sf"
RAW = PROJECT / "downloads" / "raw"
POC = PROJECT / "poc_001"
OUT = PROJECT / "outputs" / "l0_source_truth_v001"

OSM = RAW / "osm_map_poc001.osm"
LIDAR = RAW / "20100225_C5505_41835_ld_p1005.copc.laz"
BLDG = RAW / "building_footprints.geojson"
CONTOURS = RAW / "elevation_contours.geojson"
ROW = RAW / "right_of_way.geojson"
STREETS = RAW / "streets.geojson"
SIDEWALKS = RAW / "sidewalk_widths.geojson"

HYDE_NODE = "65360287"
LEAV_NODE = "65362185"
CROOKED_WAY = "402111597"

# EarthForge convention.
X_POSITIVE = "east"
Z_POSITIVE = "south"
SCALE = "1 meter = 1 Minecraft block"

TF = Transformer.from_crs("EPSG:4326", "EPSG:3717", always_xy=True)

def font(size: int):
    p=Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(p), size) if p.exists() else None

def parse_osm():
    root=ET.parse(OSM).getroot()
    nodes={}
    for n in root.findall("node"):
        nodes[n.attrib["id"]]={
            "lat":float(n.attrib["lat"]),
            "lon":float(n.attrib["lon"]),
            "tags":{t.attrib["k"]:t.attrib["v"] for t in n.findall("tag")},
        }
    ways=[]
    for w in root.findall("way"):
        ways.append({
            "id":w.attrib["id"],
            "refs":[nd.attrib["ref"] for nd in w.findall("nd")],
            "tags":{t.attrib["k"]:t.attrib["v"] for t in w.findall("tag")},
        })
    return nodes,ways

def local_transform(anchor_e, anchor_n):
    def local_lonlat(lon,lat):
        e,n=TF.transform(lon,lat)
        return e-anchor_e, anchor_n-n
    return local_lonlat

def local_geometry(geom, local_lonlat):
    def fn(x,y,z=None):
        xx,zz=local_lonlat(x,y)
        return (xx,zz) if z is None else (xx,zz,z)
    return shp_transform(fn, geom)

def ground_query(anchor_e, anchor_n):
    # Context box roughly 235 m east-west x 170 m north-south.
    xmin=anchor_e-45
    xmax=anchor_e+190
    ymin=anchor_n-80   # north -> local z negative
    ymax=anchor_n+90   # south -> local z positive
    with CopcReader.open(LIDAR) as cr:
        pts=cr.query(Bounds(np.array([xmin,ymin]),np.array([xmax,ymax])))
    arr=np.column_stack((
        np.asarray(pts.x)-anchor_e,
        anchor_n-np.asarray(pts.y),
        np.asarray(pts.z),
        np.asarray(pts.classification),
        np.asarray(pts.return_number),
        np.asarray(pts.number_of_returns),
    ))
    return arr

def median_near(arr,x,z,r=2.0,classification=2):
    d2=(arr[:,0]-x)**2+(arr[:,1]-z)**2
    m=(d2<=r*r)
    if classification is not None:m &= (arr[:,3]==classification)
    vals=arr[m,2]
    return float(np.median(vals)) if len(vals) else None

def ground_grid(arr,xmin=-40,xmax=185,zmin=-75,zmax=75,res=0.5):
    g=arr[arr[:,3]==2]
    nx=round((xmax-xmin)/res)+1
    nz=round((zmax-zmin)/res)+1
    grid=observed_grid(g[:,:2],g[:,2],(nz,nx),xmin,zmin,res)
    missing=~np.isfinite(grid)
    iz,ix=np.where(missing)
    # v016 lesson: use original returns only. Missing/unsupported cells remain
    # NaN; never extend inferred values through a canopy/building void.
    values,_=interpolate_ground(g[:,:2],g[:,2],np.c_[xmin+ix*res,zmin+iz*res],
        max_distance_m=3.0,max_triangle_edge_m=20.0)
    grid[missing]=values
    return grid.astype(np.float32),dict(xmin=xmin,xmax=xmax,zmin=zmin,zmax=zmax,res=res,
        interpolation_method='immutable_class2_TIN_v016',unsupported_cells=int(np.isnan(grid).sum()))

def sample_grid(grid,meta,x,z):
    fx=(x-meta["xmin"])/meta["res"]; fz=(z-meta["zmin"])/meta["res"]
    ix0=max(0,min(grid.shape[1]-1,int(math.floor(fx))))
    iz0=max(0,min(grid.shape[0]-1,int(math.floor(fz))))
    ix1=min(grid.shape[1]-1,ix0+1); iz1=min(grid.shape[0]-1,iz0+1)
    tx=fx-ix0;tz=fz-iz0
    if not np.isfinite(grid[iz0:iz1+1,ix0:ix1+1]).all():
        raise ValueError(f'Unsupported ground interpolation at local {(x,z)}; acquire evidence before geometry')
    return float(
        grid[iz0,ix0]*(1-tx)*(1-tz)+grid[iz0,ix1]*tx*(1-tz)+
        grid[iz1,ix0]*(1-tx)*tz+grid[iz1,ix1]*tx*tz
    )
def main():
    POC.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    nodes,ways=parse_osm()
    top=nodes[HYDE_NODE]; bottom=nodes[LEAV_NODE]
    anchor_e,anchor_n=TF.transform(top["lon"],top["lat"])
    local_ll=local_transform(anchor_e,anchor_n)

    road_way=next(w for w in ways if w["id"]==CROOKED_WAY)
    road=[]
    for ref in road_way["refs"]:
        n=nodes[ref];x,z=local_ll(n["lon"],n["lat"]);road.append([x,z])
    bx,bz=local_ll(bottom["lon"],bottom["lat"])

    arr=ground_query(anchor_e,anchor_n)
    np.savez_compressed(
        RAW/"lombard_poc001_lidar_roi_v001.npz",
        x=arr[:,0].astype(np.float32),z=arr[:,1].astype(np.float32),
        elev=arr[:,2].astype(np.float32),classification=arr[:,3].astype(np.uint8),
        return_number=arr[:,4].astype(np.uint8),num_returns=arr[:,5].astype(np.uint8),
    )
    grid,gmeta=ground_grid(arr)
    original_ground=arr[arr[:,3]==2]
    observed=observed_grid(original_ground[:,:2],original_ground[:,2],grid.shape,
        gmeta['xmin'],gmeta['zmin'],gmeta['res'])
    gx,gz=np.meshgrid(gmeta['xmin']+np.arange(grid.shape[1])*gmeta['res'],
        gmeta['zmin']+np.arange(grid.shape[0])*gmeta['res'])
    nearest=cKDTree(original_ground[:,:2]).query(np.c_[gx.ravel(),gz.ravel()])[0].reshape(grid.shape)
    np.savez_compressed(RAW/"lombard_poc001_ground_grid_050cm_v001.npz",grid=grid,
        observed_mask=np.isfinite(observed),nearest_original_ground_m=nearest,
        source_roi_sha256=hashlib.sha256((RAW/'lombard_poc001_lidar_roi_v001.npz').read_bytes()).hexdigest(),**gmeta)

    top_e=median_near(arr,0,0,2.5,2)
    bottom_e=median_near(arr,bx,bz,3.0,2)
    if top_e is None or bottom_e is None:raise RuntimeError("endpoint ground not found")

    # Road sampled at source nodes.
    road_profile=[]
    horizontal=0.0
    distance=0.0
    prev=None
    for i,(x,z) in enumerate(road):
        elev=sample_grid(grid,gmeta,x,z)
        if prev is not None:
            step=math.hypot(x-prev[0],z-prev[1]);horizontal+=step
            distance+=math.sqrt(step*step+(elev-prev[2])**2)
        road_profile.append({"i":i,"x_m":x,"z_m":z,"elev_navd88_m":elev,"elev_rel_top_m":elev-top_e,"station_2d_m":horizontal,"station_3d_m":distance})
        prev=(x,z,elev)

    straight=math.hypot(bx,bz)
    drop=top_e-bottom_e
    straight_grade=drop/straight*100

    # OSM hardscape/context.
    features=[]
    for w in ways:
        tags=w["tags"]
        if w["id"]==CROOKED_WAY or tags.get("highway")=="steps" or tags.get("barrier") in ("hedge","retaining_wall","wall","fence") or tags.get("highway") in ("footway","path"):
            coords=[]
            for ref in w["refs"]:
                n=nodes.get(ref)
                if n:
                    x,z=local_ll(n["lon"],n["lat"]);coords.append([x,z])
            if coords:
                features.append({"osm_id":w["id"],"tags":tags,"line_xz_m":coords})

    # City geospatial layers transformed into local frame.
    derived_layers={}
    for key,path in [("buildings",BLDG),("contours",CONTOURS),("right_of_way",ROW)]:
        gj=json.loads(path.read_text(encoding="utf-8"))
        rows=[]
        for f in gj["features"]:
            geom=local_geometry(shape(f["geometry"]),local_ll)
            minx,minz,maxx,maxz=geom.bounds
            # Narrow retained context.
            if maxx<-45 or minx>190 or maxz<-80 or minz>80:continue
            rec={"properties":f["properties"],"geometry":geom.__geo_interface__}
            rows.append(rec)
        derived_layers[key]=rows

    # Street and sidewalk records near the target block.
    target_streets=[]
    for f in json.loads(STREETS.read_text())["features"]:
        geom=local_geometry(shape(f["geometry"]),local_ll)
        if geom.distance(Point((bx/2,bz/2)))<250:
            p=f["properties"]
            if p.get("street") in ("LOMBARD","HYDE","LEAVENWORTH"):
                target_streets.append({"properties":p,"geometry":geom.__geo_interface__})
    target_sidewalk=[]
    for f in json.loads(SIDEWALKS.read_text())["features"]:
        geom=local_geometry(shape(f["geometry"]),local_ll)
        if geom.distance(Point((bx/2,bz/2)))<250:
            p=f["properties"]
            if p.get("street") in ("LOMBARD","HYDE","LEAVENWORTH"):
                target_sidewalk.append({"properties":p,"geometry":geom.__geo_interface__})

    truth={
        "schema_version":1,
        "project_id":"lombard_sf",
        "poc_id":"LOMBARD_SF_POC_001_CROOKED_BLOCK",
        "coordinate_frame":{
            "anchor":"Hyde Street / Lombard Street centerline intersection, OSM node 65360287",
            "anchor_wgs84":{"lat":top["lat"],"lon":top["lon"]},
            "anchor_epsg3717_m":{"easting":anchor_e,"northing":anchor_n},
            "x_positive":X_POSITIVE,"z_positive":Z_POSITIVE,"scale":SCALE,
            "vertical_datum":"NAVD88 meters",
            "vertical_zero":"Hyde/Lombard class-2 LiDAR median ground elevation",
            "vertical_zero_navd88_m":top_e,
        },
        "controls":{
            "hyde_lombard":{"local_x_m":0.0,"local_z_m":0.0,"ground_navd88_m":top_e},
            "leavenworth_lombard":{"wgs84":{"lat":bottom["lat"],"lon":bottom["lon"]},"local_x_m":bx,"local_z_m":bz,"ground_navd88_m":bottom_e},
        },
        "crooked_road":{
            "osm_way":int(CROOKED_WAY),"surface":road_way["tags"].get("surface"),
            "oneway":road_way["tags"].get("oneway"),"centerline_nodes":road,
            "horizontal_centerline_length_m":horizontal,
            "three_d_centerline_length_m":distance,
            "straight_control_distance_m":straight,
            "endpoint_drop_m":drop,
            "straight_endpoint_grade_percent":straight_grade,
            "node_count":len(road),
        },
        "lidar":{
            "source":"2010 NOAA/USGS San Francisco Bay COPC tile",
            "tile":"20100225_C5505_41835_ld_p1005.copc.laz",
            "roi_points":int(arr.shape[0]),
            "class_counts":{str(int(k)):int(v) for k,v in zip(*np.unique(arr[:,3].astype(int),return_counts=True))},
            "ground_grid_resolution_m":gmeta["res"],
        },
        "hardscape_feature_count":len(features),
        "building_count_context":len(derived_layers["buildings"]),
        "contour_count_context":len(derived_layers["contours"]),
        "row_polygon_count_context":len(derived_layers["right_of_way"]),
    }
    (POC/"l0_source_truth_v001.json").write_text(json.dumps(truth,indent=2)+"\n")
    (POC/"l0_crooked_centerline_v001.json").write_text(json.dumps(road_profile,indent=2)+"\n")
    (POC/"l0_osm_hardscape_v001.json").write_text(json.dumps({"schema_version":1,"features":features},indent=2)+"\n")
    (POC/"l0_city_layers_v001.json").write_text(json.dumps({"schema_version":1,**derived_layers,"streets":target_streets,"sidewalk_widths":target_sidewalk},indent=2)+"\n")

    # Plan preview.
    W,H=1500,950; im=Image.new("RGB",(W,H),"#efeee8");d=ImageDraw.Draw(im)
    d.text((35,25),"LOMBARD STREET / SOURCE TRUTH v001",font=font(30),fill="#243c39")
    d.text((35,70),f"Hyde -> Leavenworth | drop {drop:.2f} m | straight grade {straight_grade:.1f}% | road path {horizontal:.1f} m",font=font(17),fill="#56605d")
    xmin,xmax,zmin,zmax=-40,185,-70,70
    scale=min(1320/(xmax-xmin),760/(zmax-zmin)); ox=80-xmin*scale; oz=125-zmin*scale
    def pt(x,z):return ox+x*scale,oz+z*scale
    # buildings
    for rec in derived_layers["buildings"]:
        geom=shape(rec["geometry"])
        polys=list(geom.geoms) if geom.geom_type=="MultiPolygon" else [geom]
        for p in polys:
            xy=[pt(x,z) for x,z in p.exterior.coords]
            d.polygon(xy,fill="#d7d1c4",outline="#8b887f")
    # hedges/steps
    for f in features:
        coords=[pt(x,z) for x,z in f["line_xz_m"]]
        if f["tags"].get("barrier")=="hedge":d.line(coords,fill="#60805c",width=3)
        elif f["tags"].get("highway")=="steps":d.line(coords,fill="#8d795e",width=4)
        elif f["tags"].get("highway") in ("footway","path"):d.line(coords,fill="#a6a198",width=2)
    # road centerline
    d.line([pt(x,z) for x,z in road],fill="#b45245",width=5)
    for i,(x,z) in enumerate(road[::20]):
        xx,yy=pt(x,z);d.ellipse((xx-3,yy-3,xx+3,yy+3),fill="#7a332c")
    # anchors
    for label,(x,z) in [("HYDE",(0,0)),("LEAVENWORTH",(bx,bz))]:
        xx,yy=pt(x,z);d.ellipse((xx-7,yy-7,xx+7,yy+7),fill="#e3b72e",outline="#333")
        d.text((xx+10,yy-10),label,font=font(15),fill="#243c39")
    im.save(OUT/"Lombard_L0_SourceTruth_v001_plan.png")

    # Profile.
    P=Image.new("RGB",(1500,650),"#efeee8");q=ImageDraw.Draw(P)
    q.text((35,25),"LOMBARD / CROOKED ROAD ELEVATION PROFILE",font=font(28),fill="#243c39")
    q.text((35,68),f"NAVD88 LiDAR | top {top_e:.2f} m | bottom {bottom_e:.2f} m | drop {drop:.2f} m",font=font(16),fill="#56605d")
    smax=max(r["station_2d_m"] for r in road_profile); vals=[r["elev_navd88_m"] for r in road_profile];emin=min(vals);emax=max(vals)
    px0,py0=70,120;pw,ph=1360,440
    pts=[]
    for r in road_profile:
        x=px0+r["station_2d_m"]/smax*pw
        y=py0+(emax-r["elev_navd88_m"])/(emax-emin)*ph
        pts.append((x,y))
    q.line(pts,fill="#9d4f42",width=4);q.rectangle((px0,py0,px0+pw,py0+ph),outline="#777")
    q.text((px0,py0+ph+20),"Hyde / top",font=font(15),fill="#243c39")
    q.text((px0+pw-120,py0+ph+20),"Leavenworth",font=font(15),fill="#243c39")
    P.save(OUT/"Lombard_L0_SourceTruth_v001_profile.png")

    print(json.dumps({
        "anchor_e":anchor_e,"anchor_n":anchor_n,"leavenworth_local":[bx,bz],
        "top_elev":top_e,"bottom_elev":bottom_e,"drop":drop,
        "straight_distance":straight,"straight_grade_percent":straight_grade,
        "road_length_2d":horizontal,"road_length_3d":distance,
        "lidar_points":arr.shape[0],"hardscape_features":len(features),
        "buildings":len(derived_layers["buildings"])
    },indent=2))

if __name__=="__main__":
    main()
