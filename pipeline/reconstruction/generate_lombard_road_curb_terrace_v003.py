#!/usr/bin/env python3
"""Lombard Street POC 001 - L1 terrain and hardscape.

Builds the crooked Hyde-to-Leavenworth block from source-derived terrain and
public-realm geometry. Houses are intentionally absent at this gate.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import unary_union, transform as shp_transform
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter,
    canonical_state,
    read_back_block_map,
    write_single_region_litematic,
)
from pipeline.microblocks.astra_microblock_codec import (
    BLOCK_ENTITY_ID,
    HOST_STATE,
    MicroVolume,
    decode_volume_v4,
    tile_entity_payload,
)

PROJECT=ROOT/"projects"/"lombard_sf"
POC=PROJECT/"poc_001"
RAW=PROJECT/"downloads"/"raw"
OUT=PROJECT/"outputs"/"road_curb_terrace_v003"

TRUTH=POC/"l0_source_truth_v001.json"
CENTER=POC/"l0_crooked_centerline_v001.json"
HARDSCAPE=POC/"l0_osm_hardscape_v001.json"
CITY=POC/"l0_city_layers_v001.json"
BUILDINGS=POC/"l2_building_source_truth_v002.json"
GRID=RAW/"lombard_poc001_ground_grid_050cm_v001.npz"
OSM=RAW/"osm_map_poc001.osm"

NAME="Lombard_Road_Curb_Terrace_Astra_v003"
REGION="LOMBARD_ROAD_CURB_TERRACE_ASTRA_V003"
DATA_VERSION=4903

# Permanent project registration: outside the upper/west site.
REG_LOCAL_X=-30.0
REG_LOCAL_Z=-20.0
BASE_Y=-42
TERRAIN_SHELL_DEPTH_BLOCKS=4
TERRAIN_CLIP=(-25.0,-70.0,170.0,50.0)

STONE="minecraft:stone"
DIRT="minecraft:dirt"
PAD="minecraft:polished_andesite"
MARKER="minecraft:yellow_concrete"

GRASS="astra_microblocks:rgb_637a49"
GARDEN="astra_microblocks:rgb_526d3f"
SOIL="astra_microblocks:rgb_665244"
ROAD_A="astra_microblocks:rgb_9d5041"
ROAD_B="astra_microblocks:rgb_87453a"
CURB="astra_microblocks:rgb_c8c3b8"
SIDEWALK="astra_microblocks:rgb_aeaba2"
ASPHALT="astra_microblocks:rgb_565958"
CONCRETE="astra_microblocks:rgb_858784"
BRICK_STEP="astra_microblocks:rgb_986052"
CONCRETE_STEP="astra_microblocks:rgb_a7a49b"
HEDGE_A="astra_microblocks:rgb_3d6339"
HEDGE_B="astra_microblocks:rgb_506f45"
RAIL="astra_microblocks:rgb_777b79"
WALL_STONE="astra_microblocks:rgb_918a7d"
WALL_CAP="astra_microblocks:rgb_b4aea3"
CROSSWALK="astra_microblocks:rgb_e2dfd4"
CABLE_SLOT="astra_microblocks:rgb_303233"
HOUSE_NORTH="astra_microblocks:rgb_d8d0af"
HOUSE_SOUTH="astra_microblocks:rgb_c8c3b8"
HOUSE_ROOF="astra_microblocks:rgb_6f706d"

def font(size):
    p=Path("C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(p),size) if p.exists() else None

def floor16(v:int):
    h=math.floor(v/16)
    return h,v-h*16

class Builder:
    def __init__(self):
        self.blocks={}
        self.hosts={}
        self.terrain_top={} # (local integer x,z) -> surface microheight
        self.stats=Counter()

    def set_micro_schematic(self,sx,sy,sz,material):
        hx,lx=floor16(int(sx));hy,ly=floor16(int(sy));hz,lz=floor16(int(sz))
        pos=(hx,hy,hz)
        if pos in self.blocks and self.blocks[pos]!=HOST_STATE:
            old=self.blocks[pos]
            v=MicroVolume(old)
            v.fill_box(0,0,0,16,16,16,old)
            self.hosts[pos]=v
            self.blocks[pos]=HOST_STATE
        v=self.hosts.get(pos)
        if v is None:
            v=MicroVolume(STONE);self.hosts[pos]=v;self.blocks[pos]=HOST_STATE
        v.set(lx,ly,lz,material)

    def set_micro_local(self,x_micro,y_micro,z_micro,material):
        sx=x_micro-round(REG_LOCAL_X*16)
        sz=z_micro-round(REG_LOCAL_Z*16)
        self.set_micro_schematic(sx,y_micro,sz,material)

    def fill_local_vertical(self,x_micro,z_micro,y0,y1,material):
        for y in range(int(y0),int(y1)):
            self.set_micro_local(x_micro,y,z_micro,material)

    def clear_local_vertical(self,x_micro,z_micro,y0,y1):
        self.fill_local_vertical(x_micro,z_micro,y0,y1,None)

    def add_terrain_column(self,x,z,top_micro):
        sx=round(x-REG_LOCAL_X); sz=round(z-REG_LOCAL_Z)
        top_block=math.floor((top_micro-1)/16)
        cap=top_micro-top_block*16
        # Hollow terrain policy: preserve only a shallow structural shell under
        # the visible surface. Deep buried fill does not contribute to the
        # reconstruction and is intentionally omitted.
        shell_bottom=max(BASE_Y, top_block-(TERRAIN_SHELL_DEPTH_BLOCKS-1))
        for y in range(shell_bottom,top_block):
            self.blocks[(sx,y,sz)]=DIRT if y>=top_block-1 else STONE
        pos=(sx,top_block,sz)
        v=MicroVolume(DIRT)
        v.fill_box(0,0,0,16,cap,16,DIRT)
        self.hosts[pos]=v;self.blocks[pos]=HOST_STATE
        # green top layer
        if cap>0:
            for lx in range(16):
                for lz in range(16):
                    v.set(lx,cap-1,lz,GRASS)
        self.terrain_top[(x,z)]=top_micro

    def existing_top(self,x_micro,z_micro):
        bx=math.floor(x_micro/16);bz=math.floor(z_micro/16)
        return self.terrain_top.get((bx,bz))

    def surface(self,x_micro,z_micro,top_micro,material,thickness=2,clear_margin=6):
        existing=self.existing_top(x_micro,z_micro)
        if existing is not None and existing>top_micro:
            self.clear_local_vertical(x_micro,z_micro,top_micro,existing+clear_margin)
        for y in range(top_micro-thickness,top_micro):
            self.set_micro_local(x_micro,y,z_micro,material)

def load_grid():
    d=np.load(GRID)
    return d["grid"],{k:float(d[k]) for k in ("xmin","xmax","zmin","zmax","res")}

def grid_sample(grid,m,x,z):
    fx=(x-m["xmin"])/m["res"];fz=(z-m["zmin"])/m["res"]
    fx=max(0,min(grid.shape[1]-1.001,fx));fz=max(0,min(grid.shape[0]-1.001,fz))
    ix=int(math.floor(fx));iz=int(math.floor(fz));tx=fx-ix;tz=fz-iz
    ix1=min(grid.shape[1]-1,ix+1);iz1=min(grid.shape[0]-1,iz+1)
    return float(
        grid[iz,ix]*(1-tx)*(1-tz)+grid[iz,ix1]*tx*(1-tz)+
        grid[iz1,ix]* (1-tx)*tz+grid[iz1,ix1]*tx*tz
    )
def local_city_geometry(rec):
    return shape(rec["geometry"])

def row_geometries(city):
    bycnn={}
    for r in city["right_of_way"]:
        cnn=str(r["properties"].get("cnn"))
        bycnn.setdefault(cnn,[]).append(local_city_geometry(r))
    def uni(ids):
        arr=[]
        for i in ids:arr.extend(bycnn.get(i,[]))
        return unary_union(arr) if arr else Polygon()
    return {
        "crooked":uni(["8448000","8449000"]),
        "hyde":uni(["7144000","7145000"]),
        "leavenworth":uni(["8268000","8269000"]),
    }

def street_lines(city):
    d={}
    for r in city["streets"]:
        cnn=str(r["properties"].get("cnn"))
        d[cnn]=local_city_geometry(r)
    return d

def parse_osm_local(truth):
    root=ET.parse(OSM).getroot()
    nodes={n.attrib["id"]:(float(n.attrib["lat"]),float(n.attrib["lon"])) for n in root.findall("node")}
    tf=Transformer.from_crs(4326,3717,always_xy=True)
    ae=truth["coordinate_frame"]["anchor_epsg3717_m"]["easting"]
    an=truth["coordinate_frame"]["anchor_epsg3717_m"]["northing"]
    def loc(lon,lat):
        e,n=tf.transform(lon,lat);return e-ae,an-n
    ways=[]
    for w in root.findall("way"):
        tags={t.attrib["k"]:t.attrib["v"] for t in w.findall("tag")}
        coords=[]
        for nd in w.findall("nd"):
            if nd.attrib["ref"] in nodes:
                lat,lon=nodes[nd.attrib["ref"]];coords.append(loc(lon,lat))
        if len(coords)>=2:ways.append({"id":w.attrib["id"],"tags":tags,"line":LineString(coords),"closed":coords[0]==coords[-1]})
    return ways

def terrain_mask(rows):
    clip=box(*TERRAIN_CLIP)
    public=unary_union([rows["crooked"],rows["hyde"],rows["leavenworth"]])
    # Six-meter soil/yard context around public ROW, enough to read terrain
    # without pretending to reconstruct whole private parcels at L1.
    return public.buffer(6.0,join_style=2).intersection(clip), public.intersection(clip)

def micro_bbox(poly,margin=0):
    a,b,c,d=poly.bounds
    return (
        math.floor((a-margin)*16),math.ceil((c+margin)*16),
        math.floor((b-margin)*16),math.ceil((d+margin)*16)
    )

def iter_micro_polygon(poly,step=1):
    pp=prep(poly)
    x0,x1,z0,z1=micro_bbox(poly)
    for xm in range(x0,x1,step):
        x=(xm+.5)/16
        for zm in range(z0,z1,step):
            if pp.contains(Point(x,(zm+.5)/16)):
                yield xm,zm

def surface_height(grid,gm,top_navd,xm,zm):
    e=grid_sample(grid,gm,(xm+.5)/16,(zm+.5)/16)
    return round((e-top_navd)*16)

def add_micro_surface(builder,poly,grid,gm,top_navd,material_fn,thickness=2,raise_cells=0):
    n=0
    for xm,zm in iter_micro_polygon(poly):
        top=surface_height(grid,gm,top_navd,xm,zm)+raise_cells
        mat=material_fn(xm,zm) if callable(material_fn) else material_fn
        builder.surface(xm,zm,top,mat,thickness)
        n+=1
    return n

def add_hedge(builder,line,grid,gm,top_navd,height_cells=13):
    poly=line.buffer(.24,cap_style=1,join_style=1)
    n=0
    for xm,zm in iter_micro_polygon(poly):
        top=surface_height(grid,gm,top_navd,xm,zm)
        for y in range(top,top+height_cells):
            builder.set_micro_local(xm,y,zm,HEDGE_A if ((xm//3+zm//3+y//3)&1)==0 else HEDGE_B)
        n+=1
    return n

def add_handrails(builder,line,tags,grid,gm,top_navd):
    if tags.get("handrail")!="yes": return 0
    # Rails on both sides of the mapped stair centerline, 0.62m offset.
    coords=list(line.coords)
    if len(coords)<2:return 0
    total=line.length
    steps=max(2,math.ceil(total*8))
    n=0
    for i in range(steps+1):
        frac=i/steps
        p=line.interpolate(frac,normalized=True)
        eps=min(1,total/steps)
        a=line.interpolate(max(0,line.project(p)-eps))
        b=line.interpolate(min(total,line.project(p)+eps))
        dx=b.x-a.x; dz=b.y-a.y; ll=max(1e-6,math.hypot(dx,dz))
        nx=-dz/ll; nz=dx/ll
        elev=grid_sample(grid,gm,p.x,p.y)
        base=round((elev-top_navd)*16)
        for side in (-1,1):
            x=p.x+nx*.62; z=p.y+nz*.62
            xm=round(x*16); zm=round(z*16)
            # 0.95m rail height; posts every ~1m, continuous top rail.
            if i%8==0:
                for y in range(base,base+15):
                    builder.set_micro_local(xm,y,zm,RAIL); n+=1
            for off in range(-1,2):
                builder.set_micro_local(xm+off,base+15,zm,RAIL); n+=1
    return n

def add_crossing(builder,line,grid,gm,top_navd):
    tags=getattr(line,"tags",None)
    poly=line.buffer(.9,cap_style=2,join_style=2)
    n=0
    # Use mapped crossing geometry. Ladder/zebra ways get white bands;
    # unmarked crossings remain pavement only and are handled by streets.
    for xm,zm in iter_micro_polygon(poly):
        top=surface_height(grid,gm,top_navd,xm,zm)+1
        builder.surface(xm,zm,top,CROSSWALK,1,4); n+=1
    return n

def variable_road_polygon(road_line):
    # Keep the detailed 157-node centerline as plan authority, but flare the
    # pavement modestly where local heading changes show a real hairpin.
    coords=list(road_line.coords)
    pieces=[]
    halfwidths=[]
    for i in range(len(coords)-1):
        p0=coords[i]; p1=coords[i+1]
        j0=max(0,i-2); j1=min(len(coords)-1,i+3)
        a=coords[j0]; b=coords[i]; c=coords[j1]
        v1=(b[0]-a[0],b[1]-a[1]); v2=(c[0]-b[0],c[1]-b[1])
        l1=max(1e-6,math.hypot(*v1)); l2=max(1e-6,math.hypot(*v2))
        dot=max(-1.0,min(1.0,(v1[0]*v2[0]+v1[1]*v2[1])/(l1*l2)))
        turn=math.degrees(math.acos(dot))
        # 2.70m straight-run half-width; up to +0.55m in the tightest turns.
        half=2.70+min(0.55,(turn/70.0)*0.55)
        halfwidths.append(half)
        pieces.append(LineString([p0,p1]).buffer(half,cap_style=1,join_style=1,resolution=12))
    poly=unary_union(pieces).buffer(.04,join_style=1).buffer(-.04,join_style=1)
    return poly,halfwidths

def add_retaining_walls(builder,road_poly,road_line,grid,gm,top_navd):
    # Sample the corrected curb edge itself. Build a low planter/retaining face
    # only where LiDAR says adjacent garden terrain sits above nearby pavement.
    boundary=road_poly.boundary
    geoms=list(boundary.geoms) if boundary.geom_type=="MultiLineString" else [boundary]
    n=0
    for seg in geoms:
        length=seg.length
        steps=max(1,math.ceil(length*8))
        for i in range(steps+1):
            p=seg.interpolate(i/steps,normalized=True)
            roadp=road_line.interpolate(road_line.project(p))
            er=grid_sample(grid,gm,roadp.x,roadp.y)
            eg=grid_sample(grid,gm,p.x,p.y)
            diff=eg-er
            if diff<.12:
                continue
            bottom=round((er-top_navd)*16)+3
            top=round((eg-top_navd)*16)
            if top<=bottom:
                continue
            xm=round(p.x*16); zm=round(p.y*16)
            for y in range(bottom,top):
                builder.set_micro_local(xm,y,zm,WALL_STONE); n+=1
            for y in range(top,top+2):
                for dx in (-1,0,1):
                    for dz in (-1,0,1):
                        builder.set_micro_local(xm+dx,y,zm+dz,WALL_CAP)
    return n

def add_step_way(builder,line,tags,grid,gm,top_navd):
    poly=line.buffer(.72,cap_style=2,join_style=2)
    e0=grid_sample(grid,gm,*line.coords[0]);e1=grid_sample(grid,gm,*line.coords[-1])
    count=tags.get("step_count")
    if count:
        count=max(1,int(count))
    else:
        count=max(1,round(abs(e1-e0)/0.18))
    material=BRICK_STEP if tags.get("surface")=="bricks" else CONCRETE_STEP
    pp=prep(poly);x0,x1,z0,z1=micro_bbox(poly);n=0
    for xm in range(x0,x1):
        x=(xm+.5)/16
        for zm in range(z0,z1):
            z=(zm+.5)/16
            pt=Point(x,z)
            if not pp.contains(pt):continue
            frac=line.project(pt,normalized=True)
            idx=min(count,max(0,math.floor(frac*count)))
            elev=e0+(e1-e0)*(idx/count)
            top=round((elev-top_navd)*16)+1
            builder.surface(xm,zm,top,material,3,10)
            n+=1
    return {"cells":n,"count":count,"endpoint_drop_m":e0-e1,"material":material}
def add_footway(builder,line,tags,grid,gm,top_navd):
    width=1.2
    poly=line.buffer(width/2,cap_style=2,join_style=2)
    mat=BRICK_STEP if tags.get("surface")=="bricks" else SIDEWALK
    return add_micro_surface(builder,poly,grid,gm,top_navd,mat,2,1)

def road_brick(xm,zm):
    # restrained paver variation with a staggered six-by-three-cell rhythm.
    row=math.floor(zm/3)
    col=math.floor((xm+(row&1)*3)/6)
    return ROAD_B if ((row+col)%7==0) else ROAD_A

def add_cable_rail(builder,line,grid,gm,top_navd):
    # Track way represents one rail alignment in OSM. Two-cell steel strip with
    # a dark one-cell cable/slot shadow beside it.
    n=0
    length=line.length
    steps=max(1,math.ceil(length*16))
    for i in range(steps+1):
        pt=line.interpolate(i/steps,normalized=True)
        xm=round(pt.x*16);zm=round(pt.y*16)
        top=surface_height(grid,gm,top_navd,xm,zm)+1
        builder.surface(xm,zm,top,RAIL,2,4)
        builder.surface(xm+2,zm,top,CABLE_SLOT,1,4)
        n+=1
    return n

def add_building_shell(builder, rec, top_navd):
    geom=shape(rec["geometry_local"])
    if geom.is_empty:
        return {"wall_microcells":0,"roof_microcells":0}
    base=round((float(rec["ground_min_navd88_m"])-top_navd)*16)
    height=max(64,round(float(rec["height_median_m"])*16))
    top=base+height
    wall_mat=HOUSE_NORTH if rec.get("side")=="north" else HOUSE_SOUTH
    wall_band=geom.boundary.buffer(.12,cap_style=2,join_style=2)
    wall_cells=0
    for xm,zm in iter_micro_polygon(wall_band):
        for y in range(base,top):
            builder.set_micro_local(xm,y,zm,wall_mat)
            wall_cells+=1
    roof_cells=0
    for xm,zm in iter_micro_polygon(geom):
        for y in range(top-2,top):
            builder.set_micro_local(xm,y,zm,HOUSE_ROOF)
            roof_cells+=1
    return {
        "wall_microcells":wall_cells,
        "roof_microcells":roof_cells,
        "base_y_micro":base,
        "top_y_micro":top,
        "height_m":float(rec["height_median_m"]),
        "address":rec.get("address"),
        "street":rec.get("street"),
        "sf16_bldgid":rec.get("sf16_bldgid")
    }

def add_registration(builder):
    # Permanent pad surface y=-1 so player feet are exactly schematic y=0.
    for x in range(-5,6):
        for z in range(-5,6):
            builder.blocks[(x,-1,z)]=PAD
    builder.blocks[(0,-1,0)]=MARKER
    # East-pointing gold arrow on pad.
    for x in range(1,5):builder.blocks[(x,-1,0)]="minecraft:gold_block"
    for z in (-1,1):builder.blocks[(4,-1,z)]="minecraft:gold_block"

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    truth=json.loads(TRUTH.read_text())
    center=json.loads(CENTER.read_text())
    hard=json.loads(HARDSCAPE.read_text())
    city=json.loads(CITY.read_text())
    building_truth=json.loads(BUILDINGS.read_text())
    grid,gm=load_grid()
    top_navd=truth["coordinate_frame"]["vertical_zero_navd88_m"]
    rows=row_geometries(city); streets=street_lines(city)
    ways=parse_osm_local(truth)
    terrain,public=terrain_mask(rows)
    building_geoms=[shape(rec["geometry_local"]) for rec in building_truth["buildings"]]
    if building_geoms:
        terrain=unary_union([terrain,unary_union(building_geoms).buffer(2.0,join_style=2)]).intersection(box(*TERRAIN_CLIP))

    b=Builder()
    # Terrain bulk at 1 m, micro-quantized top.
    pp=prep(terrain)
    xmin,xmax,zmin,zmax=map(math.floor,(terrain.bounds[0],terrain.bounds[2],terrain.bounds[1],terrain.bounds[3]))
    # explicit bounds order for clarity
    minx,maxx=math.floor(terrain.bounds[0]),math.ceil(terrain.bounds[2])
    minz,maxz=math.floor(terrain.bounds[1]),math.ceil(terrain.bounds[3])
    tcount=0
    for x in range(minx,maxx):
        for z in range(minz,maxz):
            if not pp.contains(Point(x+.5,z+.5)):continue
            elev=grid_sample(grid,gm,x+.5,z+.5)
            top=round((elev-top_navd)*16)
            b.add_terrain_column(x,z,top);tcount+=1

    # Public ROW remainder gets a darker garden/terrace surface.
    garden=rows["crooked"].difference(LineString([tuple(r["x_m"] for r in [])]) if False else Polygon())
    garden_cells=add_micro_surface(b,rows["crooked"],grid,gm,top_navd,GARDEN,1,0)

    # Crooked road + curbs.
    road_line=LineString([(r["x_m"],r["z_m"]) for r in center])
    road_poly,road_halfwidths=variable_road_polygon(road_line)
    # A 0.28m curb ring follows the corrected variable-width pavement edge.
    curb_outer=road_poly.buffer(.28,join_style=1,resolution=12)
    curb_poly=curb_outer.difference(road_poly)
    road_cells=add_micro_surface(b,road_poly,grid,gm,top_navd,road_brick,2,0)
    curb_cells=add_micro_surface(b,curb_poly,grid,gm,top_navd,CURB,3,3)

    # Cross streets and straight Lombard context.
    cross_specs=[
        ("7144000",5.4,CONCRETE),("7145000",5.4,ASPHALT),
        ("8268000",5.2,ASPHALT),("8269000",5.2,ASPHALT),
        ("8450000",5.2,ASPHALT),("8447000",5.2,CONCRETE),
    ]
    cross_cells=0
    clip=box(*TERRAIN_CLIP)
    for cnn,half,mat in cross_specs:
        line=streets.get(cnn)
        if line is None:continue
        poly=line.buffer(half,cap_style=2,join_style=1).intersection(clip)
        cross_cells+=add_micro_surface(b,poly,grid,gm,top_navd,mat,2,0)
        ring=line.buffer(half+.28,cap_style=2,join_style=1).difference(line.buffer(half,cap_style=2,join_style=1)).intersection(clip)
        cross_cells+=add_micro_surface(b,ring,grid,gm,top_navd,CURB,3,3)

    # Steps, footways, hedges. Restrict to immediate crooked-block context.
    main_context=rows["crooked"].buffer(5)
    step_audit=[];foot_cells=0;hedge_cells=0;handrail_cells=0;crossing_cells=0
    for f in hard["features"]:
        tags=f["tags"];line=LineString(f["line_xz_m"])
        if not line.intersects(main_context):continue
        if tags.get("highway")=="steps":
            step_audit.append({"osm_id":f["osm_id"],**add_step_way(b,line,tags,grid,gm,top_navd)})
            handrail_cells+=add_handrails(b,line,tags,grid,gm,top_navd)
        elif tags.get("highway") in ("footway","path"):
            if tags.get("footway")=="crossing" and tags.get("crossing:markings") in ("ladder","zebra"):
                crossing_cells+=add_crossing(b,line,grid,gm,top_navd)
            else:
                foot_cells+=add_footway(b,line,tags,grid,gm,top_navd)
        elif tags.get("barrier")=="hedge":
            hedge_cells+=add_hedge(b,line,grid,gm,top_navd)

    # Hyde cable-car rail ways.
    retaining_cells=add_retaining_walls(b,road_poly,road_line,grid,gm,top_navd)

    rail_cells=0
    rail_clip=rows["hyde"].intersection(box(-20,-42,25,42))
    for w in ways:
        if w["tags"].get("railway")=="tram":
            seg=w["line"].intersection(rail_clip)
            if seg.is_empty:continue
            if seg.geom_type=="MultiLineString":
                for s in seg.geoms:rail_cells+=add_cable_rail(b,s,grid,gm,top_navd)
            elif seg.geom_type=="LineString":
                rail_cells+=add_cable_rail(b,seg,grid,gm,top_navd)

    # Rough bordering-house massing from DataSF footprints + LiDAR median heights.
    building_audit=[]
    for rec in building_truth["buildings"]:
        building_audit.append(add_building_shell(b,rec,top_navd))

    add_registration(b)
    for p in b.hosts:b.blocks[p]=HOST_STATE

    xs=[p[0] for p in b.blocks];ys=[p[1] for p in b.blocks];zs=[p[2] for p in b.blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    writer=NBTWriter();tes=[]
    for (x,y,z),v in sorted(b.hosts.items()):
        tes.append(tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v))

    litematic=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        litematic,b.blocks,bounds,REGION,NAME,
        "Lombard Street rough full-site v001: LiDAR terrain, full crooked road/hardscape, mapped stairs/footways/hedges, retaining conditions, Hyde cable-car context, and rough bordering-house Astra massing from DataSF footprints + LiDAR median heights.",
        data_version=DATA_VERSION,tile_entity_payloads=tes
    )

    reread,meta=read_back_block_map(litematic,REGION)
    expected={p:canonical_state(s) for p,s in b.blocks.items()}
    assert reread==expected
    rp=meta["region_position"];decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
            decoded[p]=decode_volume_v4(te["volume_v4"])
    assert set(decoded)==set(b.hosts)
    for p,v in b.hosts.items():assert decoded[p]==v.cells,p
    assert reread.get((0,-1,0))==MARKER

    # Review preview from exact vectors + height shade.
    W,H=1600,950;im=Image.new("RGB",(W,H),"#efeee8");d=ImageDraw.Draw(im)
    d.text((35,25),"LOMBARD / ROAD-CURB-TERRACE TRUTH v003",font=font(30),fill="#243c39")
    d.text((35,70),f"LiDAR drop {truth['crooked_road']['endpoint_drop_m']:.2f}m | crooked centerline {truth['crooked_road']['horizontal_centerline_length_m']:.1f}m | {len(building_audit)} rough structures",font=font(17),fill="#56605d")
    pxmin,pxmax,pzmin,pzmax=-38,170,-48,48
    sc=min(1430/(pxmax-pxmin),770/(pzmax-pzmin));ox=70-pxmin*sc;oz=120-pzmin*sc
    def pt(x,z):return ox+x*sc,oz+z*sc
    # terrain mask
    for geom,col in [(terrain,"#8b9a72"),(rows["crooked"],"#6f8656"),(road_poly,"#9d5041"),(curb_poly,"#c8c3b8")]:
        geoms=list(geom.geoms) if hasattr(geom,"geoms") else [geom]
        for g in geoms:
            if g.geom_type!="Polygon":continue
            d.polygon([pt(x,z) for x,z in g.exterior.coords],fill=col if geom!=terrain else None,outline=col)
    for f in hard["features"]:
        line=LineString(f["line_xz_m"])
        if not line.intersects(main_context):continue
        coords=[pt(x,z) for x,z in line.coords]
        if f["tags"].get("highway")=="steps":d.line(coords,fill="#8a6657",width=4)
        elif f["tags"].get("barrier")=="hedge":d.line(coords,fill="#315d36",width=4)
    d.line([pt(r["x_m"],r["z_m"]) for r in center],fill="#5c2520",width=2)
    # registration
    rx,rz=pt(REG_LOCAL_X,REG_LOCAL_Z);d.rectangle((rx-6,rz-6,rx+6,rz+6),fill="#e3b72e",outline="#222")
    d.text((rx+10,rz-10),"LOAD PAD",font=font(14),fill="#243c39")
    im.save(OUT/f"{NAME}_plan.png")

    report={
        **stats,
        "astra_min_version":"0.7.0",
        "source_truth":"projects/lombard_sf/poc_001/l0_source_truth_v001.json",
        "registration":{"project_local_m":[REG_LOCAL_X,REG_LOCAL_Z],"schematic_marker":[0,-1,0],"player_feet":[0,0,0],"rotation":0,"mirror":"none"},
        "features":{
            "terrain_columns":tcount,"garden_surface_microcells":garden_cells,
            "road_surface_microcells":road_cells,"curb_microcells":curb_cells,
            "road_geometry":{"method":"157-node centerline + curvature-driven variable width","straight_halfwidth_m":2.70,"max_halfwidth_m":3.25,"actual_min_halfwidth_m":min(road_halfwidths),"actual_max_halfwidth_m":max(road_halfwidths),"mean_full_width_m":2*sum(road_halfwidths)/len(road_halfwidths),"curb_ring_m":0.28},
            "cross_street_surface_microcells":cross_cells,
            "step_ways":step_audit,"footway_microcells":foot_cells,
            "hedge_plan_microcells":hedge_cells,"handrail_microcells":handrail_cells,"marked_crossing_microcells":crossing_cells,"retaining_wall_microcells":retaining_cells,"cable_track_samples":rail_cells,
            "building_massing":{"structure_count":len(building_audit),"source":"projects/lombard_sf/poc_001/l2_building_source_truth_v002.json","height_policy":"DataSF LiDAR hgt_median_m","audit":building_audit}
        },
        "astra":{"host_count":len(b.hosts),"occupied_microcells":sum(v.occupied_count() for v in b.hosts.values()),"materials":sorted({m for v in b.hosts.values() for m in v.materials()})},
        "terrain":{"base_y_blocks":BASE_Y,"hyde_surface_y_blocks":0.0,"leavenworth_surface_y_blocks":round(-truth["crooked_road"]["endpoint_drop_m"],3)},
        "validation":{"exact_block_readback":True,"exact_astra_cell_readback":True,"registration_marker":True,"buildings_generated":True,"roofs_generated":True,"interiors_generated":False,"in_game_review":False,"review_status":"ROAD_CURB_TERRACE_V003_FLYAROUND_REQUIRED"},
        "limitations":[
            "v003 refines only the crooked road, curb and planter/retaining relationship; terrain and building massing are intentionally frozen.",
            "The detailed 157-node centerline remains plan authority. DataSF ROW and the 15 ft SIDEWALK_F records are treated as public-envelope/width evidence, not literal pavement polygons.",
            "Mapped hedges and retaining conditions are massing/evidence layers, not final landscape or wall reconstruction.",
            "Buildings use DataSF footprints and LiDAR median heights only; garages, facade planes, roof forms, openings and architectural details are intentionally deferred."
        ]
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/f"{NAME}_placement.json").write_text(json.dumps({"yellow_marker":[0,-1,0],"stand_above_marker":True,"placement_origin":"player feet","rotation":0,"mirror":"none","replace_blocks":"ALL"},indent=2)+"\n")
    (OUT/"Build_notes.md").write_text(
        "# Lombard Road / Curb / Terrace Truth v003\n\n"
        "This pass freezes terrain and house massing from v002 and refines only the crooked road/curb/terrace relationship. The detailed 157-node centerline remains plan authority. Straight runs use a 2.70 m half-width and curvature flares tight turns up to 3.25 m; a 0.28 m curb ring follows the resulting edge. Planter/retaining lips are sampled from that corrected edge and only appear where LiDAR shows adjacent garden terrain above pavement.\n\n"
        "DataSF ROW and 15 ft actual-sidewalk records remain cross-check evidence rather than literal pavement outlines because a direct ROW inset breaks the crooked road into disconnected polygons.\n\n"
        "Next action: Minecraft flyaround and user notes. Do not continue to stair/wall detail until this gate is reviewed.\n"
    )

    print(json.dumps({
        "file":str(litematic),"sha256":stats["sha256"],
        "region_position":stats["region_position"],"region_size":stats["region_size"],
        "terrain_columns":tcount,"astra_hosts":len(b.hosts),
        "occupied_microcells":sum(v.occupied_count() for v in b.hosts.values()),
        "road_cells":road_cells,"curb_cells":curb_cells,
        "steps":len(step_audit),"validation":"PASS"
    },indent=2))

if __name__=="__main__":
    main()
