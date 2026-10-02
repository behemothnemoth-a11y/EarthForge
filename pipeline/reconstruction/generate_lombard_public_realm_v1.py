"""Complete no-house Lombard public-realm v1 on the accepted road spine.

Revision v017. Explicitly authorized full-corridor assembly after v016 repair.
All dimensions are meters; the surface realization is 1/16m Astra cells.
"""
from __future__ import annotations
import json,math,sys,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import uniform_filter
from scipy.spatial import cKDTree
from shapely.geometry import Point,LineString,Polygon,shape
from shapely.ops import unary_union
from shapely import contains_xy,line_locate_point,points
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_endpoint_roads_v015 as v
from pipeline.reconstruction import generate_lombard_stairs_v013 as stairs
from pipeline.reconstruction import generate_lombard_core_isolation_v005 as context
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read,position
from pipeline.terrain.ground_support import interpolate_ground
from pipeline.export.litematic_codec import NBTWriter,canonical_state,write_single_region_litematic
from pipeline.microblocks.astra_microblock_codec import MicroVolume,HOST_STATE,tile_entity_payload

OUT=v.PROJECT/'outputs/public_realm_v1'
NAME='Lombard_Complete_No_Houses_V1_Astra_v017';REGION='LOMBARD_PUBLIC_REALM_V1_V017'
PARENT=v.PROJECT/'outputs/terrain_repair_v016/Lombard_Terrain_Repair_Astra_v016.litematic'
PARENT_REGION='LOMBARD_TERRAIN_REPAIR_ASTRA_V016'
GREEN='astra_microblocks:rgb_66794c';SOIL='astra_microblocks:rgb_665244'
HEDGE='astra_microblocks:rgb_3d6339';HEDGE2='astra_microblocks:rgb_506f45'
WALK='astra_microblocks:rgb_b9b4a8';WALKJOINT='astra_microblocks:rgb_a6a196'
STEP='astra_microblocks:rgb_aeaa9f';BRICK='astra_microblocks:rgb_986052'
BLACK='astra_microblocks:rgb_292e2c';WHITE='astra_microblocks:rgb_e2dfd4';STEEL='astra_microblocks:rgb_777b79'
WOOD='minecraft:oak_log';LEAF='astra_microblocks:rgb_365b36';LEAF2='astra_microblocks:rgb_48683c'
FLOWERS=['astra_microblocks:rgb_b5b2c6','astra_microblocks:rgb_b885aa','astra_microblocks:rgb_d3c5d1']
ASPHALT={v.HYDE_TOP,v.HYDE_BASE,v.LEAV_TOP,v.LEAV_BASE,'astra_microblocks:rgb_686661','astra_microblocks:rgb_5d5c59'}


def raster(poly):
    if poly.is_empty:return np.empty(0,dtype=int),np.empty(0,dtype=int)
    x0,z0,x1,z1=poly.bounds
    gx,gz=np.meshgrid(np.arange(math.floor(x0*16),math.ceil(x1*16)),np.arange(math.floor(z0*16),math.ceil(z1*16)))
    valid=contains_xy(poly,(gx+.5)/16,(gz+.5)/16)
    return gx[valid],gz[valid]


def node_sources(truth):
    ae=truth['coordinate_frame']['anchor_epsg3717_m']['easting'];an=truth['coordinate_frame']['anchor_epsg3717_m']['northing']
    tf=Transformer.from_crs(4326,3717,always_xy=True);result=[]
    for node in ET.parse(context.OSM).getroot().findall('node'):
        tags={t.attrib['k']:t.attrib['v'] for t in node.findall('tag')}
        if not tags:continue
        e,n=tf.transform(float(node.attrib['lon']),float(node.attrib['lat']))
        result.append({'id':node.attrib['id'],'x':e-ae,'z':an-n,'tags':tags})
    return result


def city_pavement_width(city,cnn,line):
    row=next(shape(r['geometry']) for r in city['right_of_way'] if str(r['properties'].get('cnn'))==cnn)
    sidewalk=next(float(r['properties']['sidewalk_f'])*.3048 for r in city['sidewalk_widths'] if str(r['properties'].get('cnn'))==cnn)
    widths=[]
    for f in np.linspace(.2,.8,13):
        station=line.length*f;p=line.interpolate(station);a=line.interpolate(station-.5);b=line.interpolate(station+.5)
        dx,dz=b.x-a.x,b.y-a.y;ll=math.hypot(dx,dz);nx,nz=-dz/ll,dx/ll
        cut=LineString([(p.x-nx*30,p.y-nz*30),(p.x+nx*30,p.y+nz*30)])
        widths.append(cut.intersection(row).length)
    width=float(np.median(widths))-2*sidewalk
    if not 5<width<18:raise RuntimeError('Outgoing Lombard width needs investigation')
    return width,sidewalk


class Builder(v.RoadBuilder):
    def __init__(self,blocks,locked):
        super().__init__();self.blocks=dict(blocks);self.hosts={};self.locked=locked;self.skipped=0
        for pos,vol in locked.items():
            copy=MicroVolume(vol.original);copy.cells=vol.cells.copy();self.hosts[pos]=copy;self.blocks[pos]=HOST_STATE
    def set_micro_local(self,gx,y,gz,mat):
        gx,y,gz=int(gx),int(y),int(gz);pos,i=position(gx,y,gz)
        if pos in self.locked and self.locked[pos].cells[i] is not None:
            self.skipped+=1;return
        if mat is None and pos not in self.hosts:return
        if pos not in self.hosts:self.hosts[pos]=MicroVolume('minecraft:bricks');self.blocks[pos]=HOST_STATE
        self.hosts[pos].cells[i]=mat
    def prune_empty_hosts(self):
        empty=[p for p,vv in self.hosts.items() if not any(m is not None for m in vv.cells)]
        for p in empty:del self.hosts[p];del self.blocks[p]
        return len(empty)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    print('Loading accepted parent and original source observations',flush=True)
    parent_blocks,parent=read(PARENT,PARENT_REGION)
    _,road_locked=read(v.V009,'LOMBARD_CURB_ASTRA_V009')
    # Accepted road, curb and both endpoint road surfaces are immutable.
    locked={}
    for pos,vol in parent.items():
        cells=[m if m in ASPHALT or (pos in road_locked and road_locked[pos].cells[i] is not None) else None for i,m in enumerate(vol.cells)]
        if any(m is not None for m in cells):
            vv=MicroVolume(vol.original);vv.cells=cells;locked[pos]=vv
    vanilla={p:s for p,s in parent_blocks.items() if p not in parent}
    builder=Builder(vanilla,locked)
    road_top={}
    for (hx,hy,hz),vol in locked.items():
        for i,m in enumerate(vol.cells):
            if m is None:continue
            gx=hx*16+(i&15)-480;gz=hz*16+((i>>4)&15)-320;y=hy*16+(i>>8)
            road_top[(gx,gz)]=max(y+1,road_top.get((gx,gz),-9999))
    center=json.loads(v.CENTER.read_text());zero=float(center[0]['elev_navd88_m'])
    roadline=LineString([(p['x_m'],p['z_m']) for p in center]);roadpoly,_=v.variable_road_polygon(roadline)
    core_stairs=stairs.load_core_stairs();truth=json.loads(context.TRUTH.read_text());ways=context.parse_osm_local(truth);nodes=node_sources(truth)
    # Reconcile mapped stair traces with the immutable, accepted road footprint.
    # Move only colliding segments outward; retain every original trace in QA.
    road_clearance=roadpoly.buffer(1.0)
    site_center=v.crooked_row_polygon().centroid
    for stair in core_stairs:
        source_line=stair['line'];adjusted=[];offsets=[]
        for distance in np.linspace(0,source_line.length,max(2,math.ceil(source_line.length/.25)+1)):
            pt=source_line.interpolate(float(distance));a=source_line.interpolate(max(0,distance-.3));b=source_line.interpolate(min(source_line.length,distance+.3))
            dx,dz=b.x-a.x,b.y-a.y;length=math.hypot(dx,dz);nx,nz=-dz/length,dx/length
            if nx*(pt.x-site_center.x)+nz*(pt.y-site_center.y)<0:nx,nz=-nx,-nz
            offset=0.
            while road_clearance.covers(Point(pt.x+nx*offset,pt.y+nz*offset)):
                offset+=.0625
                if offset>8:raise RuntimeError('Stair alignment conflict exceeds bounded local correction')
            adjusted.append((pt.x+nx*offset,pt.y+nz*offset));offsets.append(offset)
        # Keep a straight source trace where it fits. Modified portions follow
        # the accepted curb with enough room for the 1.45m walking width.
        stair['source_line']=source_line;stair['line']=LineString(adjusted)
        stair['alignment_max_offset_m']=max(offsets)
    stair_system=unary_union([s['line'].buffer(1.1,cap_style=1,join_style=2) for s in core_stairs])
    # Source public stair alignments bound the whole block, including portions
    # omitted from the old city-ROW-only review clipping.
    core=unary_union([v.crooked_row_polygon(),stair_system]).convex_hull
    city=json.loads(v.CITY.read_text());buildings=unary_union([shape(b['geometry']) for b in city['buildings']])
    oldgrid,oldgm=v.load_smoothed_ground_grid()
    endpoints=[]
    for name,cnns,width,side in [('Hyde',['7144000','7145000'],11.96,4.572),('Leavenworth',['8268000','8269000'],13.48,3.6576)]:
        line,station=v.combined_intersection_line(*cnns);ss,hh,_=v.endpoint_profile(line,oldgrid,oldgm,zero)
        pavement=line.buffer(width/2,cap_style=2,join_style=2)
        whole=line.buffer(width/2+side,cap_style=2,join_style=2)
        endpoints.append({'name':name,'cnns':cnns,'line':line,'pavement':pavement,'whole':whole,'width':width,'sidewalk':side,'s':ss,'h':hh})
    accepted_roads=unary_union([roadpoly,*[e['pavement'] for e in endpoints]])
    apron_specs=[]
    for e,cnn in zip(endpoints,['8450000','8447000']):
        line=v.street_line_by_cnn(cnn);width,side=city_pavement_width(city,cnn,line)
        # Complete the intersection mouths only within the already scoped
        # cross-street/sidewalk strip. No extra length of an outgoing block.
        poly=line.buffer(width/2,cap_style=2).intersection(e['whole']).difference(accepted_roads)
        apron_specs.append({'endpoint':e,'cnn':cnn,'line':line,'width':width,'sidewalk_source_m':side,'poly':poly})
    roads=unary_union([accepted_roads,*[a['poly'] for a in apron_specs]])
    scope=unary_union([core,*[e['whole'] for e in endpoints],roadpoly]).buffer(0)
    # Building footprints are used only to reserve house sites, never extruded.
    garden=core.difference(buildings.difference(stair_system)).difference(roads.buffer(.1875))
    terrain_scope=unary_union([garden,stair_system.intersection(core)]).difference(roads.buffer(.1875))
    p=np.load(v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz');ground=p['classification']==2
    pts=np.c_[p['x'][ground],p['z'][ground]];elev=p['elev'][ground]
    # Original measurements only. This grid never consumes v015's recursive fill.
    gx0,gz0,gx1,gz1=scope.bounds
    xs=np.arange(math.floor(gx0)-2,math.ceil(gx1)+2.5,.5);zs=np.arange(math.floor(gz0)-2,math.ceil(gz1)+2.5,.5)
    xx,zz=np.meshgrid(xs,zs);tin=LinearNDInterpolator(pts,elev)(xx,zz)
    grid=uniform_filter(tin,3,mode='nearest');gm={'xmin':xs[0],'zmin':zs[0],'xmax':xs[-1],'zmax':zs[-1],'res':.5}
    samplemask=contains_xy(terrain_scope,xx,zz)
    _,support=interpolate_ground(pts,elev,np.c_[xx[samplemask],zz[samplemask]],max_distance_m=5,max_triangle_edge_m=20)
    if not support['supported'].all():raise RuntimeError('Whole-corridor public ground has unsupported samples')
    def height(x,z):
        value=v.grid_sample(grid,gm,float(x),float(z))-zero
        if not math.isfinite(value):raise RuntimeError('Unsupported terrain sample')
        return value
    def top(gx,gz):return round(height((gx+.5)/16,(gz+.5)/16)*16)
    ground_top={};surface_top={};surface_material={};feature_audit=[]
    for apron in apron_specs:
        e=apron['endpoint'];gx,gz=raster(apron['poly'])
        for x,z in zip(gx,gz):
            px,pz=(x+.5)/16,(z+.5)/16;pt=Point(px,pz);station=e['line'].project(pt);sp=e['line'].interpolate(station)
            dx,dz=px-sp.x,pz-sp.y;distance=math.hypot(dx,dz)
            edgepoint=(sp.x+dx/distance*e['width']/2,sp.y+dz/distance*e['width']/2)
            grade=float(np.interp(station,e['s'],e['h']))+height(px,pz)-height(*edgepoint)
            t=round(grade*16);base=v.HYDE_BASE if e['name']=='Hyde' else v.LEAV_BASE;mat=v.HYDE_TOP if e['name']=='Hyde' else v.LEAV_TOP
            for y in range(t-3,t-1):builder.set_micro_local(x,y,z,base)
            builder.set_micro_local(x,t-1,z,v.asphalt_top(mat,int(x),int(z)));road_top[(int(x),int(z))]=t
        feature_audit.append({'type':'intersection_apron','street':e['name'],'outgoing_lombard_cnn':apron['cnn'],'pavement_width_m':apron['width'],'sidewalk_width_source_m':apron['sidewalk_source_m'],
            'area_m2':apron['poly'].area,'extent':'Inside existing cross-street-and-sidewalk footprint only','grade':'Original-point ground slope tied continuously to accepted cross-street edge'})
    print('Stage 1: full supporting ground footprint',flush=True)
    gx,gz=raster(terrain_scope)
    for x,z in zip(gx,gz):
        x,z=int(x),int(z);t=top(x,z);ground_top[(x,z)]=t;surface_top[(x,z)]=t;surface_material[(x,z)]=GREEN
    print('Stage 2: endpoint sidewalks, connections and curb openings',flush=True)
    connectors=[w for w in ways if w['tags'].get('highway')=='footway' and w['line'].intersects(scope)]
    marked=[w for w in connectors if w['tags'].get('crossing:markings') in ['zebra','ladder']]
    curb_openings=unary_union([w['line'].buffer(1.25,cap_style=2) for w in marked])
    # Public-road continuations remain open; no curb closes a road mouth.
    roadmouths=[roadpoly.buffer(.25),*[a['poly'].buffer(.05).intersection(a['endpoint']['whole']) for a in apron_specs]]
    roadmouths=unary_union(roadmouths)
    openings=unary_union([roadmouths,curb_openings])
    walk_polys=[];curb_polys=[]
    for e in endpoints:
        walk=e['whole'].difference(e['pavement']).difference(roadmouths).difference(roadpoly.buffer(.1875))
        # Only the long physical pavement sides get curbs; segment end caps do not.
        longedge=unary_union([e['line'].offset_curve(e['width']/2),e['line'].offset_curve(-e['width']/2)])
        curb=longedge.buffer(.125,cap_style=2).difference(openings).difference(roads)
        walk_polys.append(walk);curb_polys.append(curb)
        for poly,kind in [(walk,'walk'),(curb,'curb')]:
            gx,gz=raster(poly);st=line_locate_point(e['line'],points((gx+.5)/16,(gz+.5)/16));tops=np.rint(np.interp(st,e['s'],e['h'])*16).astype(int)+2
            for x,z,t in zip(gx,gz,tops):
                key=(int(x),int(z));surface_top[key]=int(t);ground_top[key]=int(t)-2
                if kind=='walk' and curb_openings.covers(Point((x+.5)/16,(z+.5)/16)):
                    # Lowered pedestrian entries fill the crossing corridor;
                    # a curb opening must not become a hole in the sidewalk.
                    distance=e['pavement'].distance(Point((x+.5)/16,(z+.5)/16))
                    surface_top[key]=int(t)-2+round(min(1.,distance)*2)
                surface_material[key]=v.CURB_MATERIAL if kind=='curb' else (WALKJOINT if x%24==0 or z%24==0 else WALK)
        feature_audit.append({'type':'endpoint_sidewalk','name':e['name'],'source_cnns':e['cnns'],'street_length_m':e['line'].length,'sidewalk_width_m':e['sidewalk'],'new_curb_end_caps':False})
    # Source mapped footways establish the only cross-block connectors.
    footways=[]
    for w in connectors:
        if w['line'].length>35 and not w['line'].intersects(core):continue
        poly=w['line'].buffer(.725,cap_style=2,join_style=2).intersection(scope).difference(roads)
        if poly.is_empty:continue
        footways.append(poly)
        gx,gz=raster(poly)
        for x,z in zip(gx,gz):
            key=(int(x),int(z));
            # Engineered endpoint sidewalks already control their own heights.
            if key in surface_material and surface_material[key] in {WALK,WALKJOINT,v.CURB_MATERIAL}:continue
            t=top(*key);surface_top[key]=t;ground_top.setdefault(key,t);surface_material[key]=WALK
        feature_audit.append({'type':'footway','osm_id':w['id'],'source_surface':w['tags'].get('surface'),'area_m2':poly.area})
    print('Stage 3: nine supported stair runs and source-node landings',flush=True)
    stair_profiles=[];stair_polys=[]
    for s in core_stairs:
        line=s['line'];length=line.length
        stations=np.linspace(0,length,max(3,math.ceil(length/.2)+1))
        raw=np.array([height(*line.interpolate(float(d)).coords[0]) for d in stations])
        # Monotonic interpolation follows measured along-stair controls and
        # preserves endpoints; tagged counts override inferred nominal counts.
        smooth=np.convolve(np.pad(raw,4,mode='edge'),np.ones(9)/9,mode='valid')
        delta=raw[-1]-raw[0];trend=np.maximum.accumulate(smooth) if delta>=0 else np.minimum.accumulate(smooth)
        trend=raw[0]+(trend-trend[0])*(delta/(trend[-1]-trend[0]))
        count=int(s['tags'].get('step_count') or max(1,round(abs(delta)/.18)))
        def stair_h(distance,ss=stations,hh=trend,n=count,e0=raw[0],de=delta,L=length):
            if distance<=.35:return float(e0)
            if distance>=L-.35:return float(e0+de)
            continuous=float(np.interp(distance,ss,hh));phase=np.clip((continuous-e0)/de,0,1)
            return float(e0+de*min(n,math.floor(phase*n))/n)
        stair_profiles.append((s,stair_h))
        poly=line.buffer(.725,cap_style=2,join_style=2)
        # Flat landings only at actual way endpoints; shape vertices are not
        # automatically interpreted as physical landings.
        landings=[stairs.oriented_landing(line.coords[0],np.array(line.coords[1])-line.coords[0],width=1.7,depth=.7),
                  stairs.oriented_landing(line.coords[-1],np.array(line.coords[-1])-line.coords[-2],width=1.7,depth=.7)]
        system=unary_union([poly,*landings]).intersection(scope).difference(roads.buffer(.1875))
        stair_polys.append(system)
        gx,gz=raster(system);dist=line_locate_point(line,points((gx+.5)/16,(gz+.5)/16))
        for x,z,station in zip(gx,gz,dist):
            key=(int(x),int(z));t=round(stair_h(float(station))*16)
            ground_top.setdefault(key,top(*key));surface_top[key]=t;surface_material[key]=BRICK if s['tags'].get('surface')=='bricks' else STEP
        feature_audit.append({'type':'stairs','osm_id':s['osm_id'],'length_m':length,'width_m':1.45,'step_count':count,'step_count_source':'OSM tag' if s['tags'].get('step_count') else 'class-2 endpoint drop / nominal 0.18m',
            'source_line_xz_m':list(s['source_line'].coords),'modeled_line_xz_m':list(line.coords),'alignment_max_offset_m':s['alignment_max_offset_m'],'alignment_reason':'Mapped stair/accepted-road conflict reconciled outward with 1m centerline clearance; zero offset elsewhere',
            'endpoint_elevations_rel_m':[float(raw[0]),float(raw[-1])],'average_riser_m':abs(delta)/count,'flat_endpoint_landings':2,
            'note':'Widths/landing depth and untagged counts are v1 approximations; source counts retained even where shallow measured risers warrant later review.'})
    walk_union=unary_union([*walk_polys,*footways,*stair_polys])
    print('Realizing ground and pedestrian surfaces',len(surface_top),'columns',flush=True)
    # A structural shell, not arbitrary deep fill. Stairs get at least 0.375m.
    for (gx,gz),t in surface_top.items():
        mat=surface_material[(gx,gz)];depth=6 if mat in {BRICK,STEP} else 4
        for y in range(t-depth,t-1):builder.set_micro_local(gx,y,gz,SOIL if mat==GREEN else 'minecraft:smooth_stone')
        builder.set_micro_local(gx,t-1,gz,mat)
    # Real stair cuts/fill edges have source-backed paths; never treat the
    # temporary outer footprint as a retaining wall.
    sidewall_columns=0
    for poly in stair_polys:
        gx,gz=raster(poly.boundary.buffer(.0625).intersection(scope).difference(roads.buffer(.1875)))
        for x,z in zip(gx,gz):
            key=(int(x),int(z));t=surface_top.get(key)
            if t is None:continue
            gt=ground_top.get(key,t)
            if abs(t-gt)<3:continue
            for y in range(min(t,gt)-3,max(t,gt)):builder.set_micro_local(x,y,z,STEP)
            sidewall_columns+=1
    profile=v.build_engineered_profile(center)
    curb_ring=roadpoly.buffer(.1875,join_style=1,resolution=16).difference(roadpoly).difference(v.endpoint_opening_mask(roadline))
    loader=v.load_smoothed_ground_grid
    try:
        v.load_smoothed_ground_grid=lambda:(grid,gm)
        edge=v.rasterize_local_edge_raises(builder,curb_ring,garden,roadline,profile,center)
        retaining=v.rasterize_retaining_walls(builder,curb_ring,garden,roadline,profile,center)
    finally:v.load_smoothed_ground_grid=loader
    print('Stage 4: railings, mapped hedges and planting beds',flush=True)
    for s,stair_h in stair_profiles:
        if s['tags'].get('handrail')!='yes':continue
        line=s['line'];n=max(1,math.ceil(line.length*32));previous={}
        for i in range(n+1):
            station=line.length*i/n;pt=line.interpolate(station);a=line.interpolate(max(0,station-.15));b=line.interpolate(min(line.length,station+.15));dx,dz=b.x-a.x,b.y-a.y;ll=max(1e-9,math.hypot(dx,dz));nx,nz=-dz/ll,dx/ll
            base=round(stair_h(station)*16)
            for side in [-1,1]:
                x,z=pt.x+nx*.68*side,pt.y+nz*.68*side;gx,gz=round(x*16),round(z*16)
                if (gx,gz) not in surface_top:continue
                base=surface_top[(gx,gz)]
                if i%32==0 or i==n:
                    for y in range(base,base+16):builder.set_micro_local(gx,y,gz,BLACK)
                # Continuous rail samples, bridging quantized riser jumps.
                last=previous.get(side,base+15)
                for y in range(min(last,base+15),max(last,base+15)+1):builder.set_micro_local(gx,y,gz,BLACK)
                previous[side]=base+15
        feature_audit.append({'type':'handrail_pair','osm_id':s['osm_id'],'height_m':.9375,'approximation':'nominal 0.95m rounded to 15 cells; source handrail=yes, two sides'})
    hedge_footprints=[];beds=[];hedge_audit=[]
    for w in ways:
        if w['tags'].get('barrier')!='hedge' or not w['line'].intersects(core):continue
        poly=w['line'].buffer(.24,cap_style=1,join_style=1).intersection(garden).difference(walk_union.buffer(.12))
        if poly.is_empty:continue
        # Earlier OSM duplicate hedge outlines lose to height-tagged outlines.
        if not w['tags'].get('height') and any(q['tags'].get('height') and w['line'].intersection(q['line'].buffer(.3)).length>.8*w['line'].length for q in ways if q['tags'].get('barrier')=='hedge'):continue
        height_cells=max(1,round(float(w['tags'].get('height',.8))*16));gx,gz=raster(poly)
        for x,z in zip(gx,gz):
            key=(int(x),int(z));base=surface_top.get(key)
            if base is None:continue
            for y in range(base,base+height_cells):builder.set_micro_local(x,y,z,HEDGE if (int(x)//4+int(z)//4+y//4)%3 else HEDGE2)
        hedge_footprints.append(poly)
        if w['closed'] and Polygon(w['line']).is_valid:beds.append(Polygon(w['line']).intersection(garden).difference(walk_union.buffer(.2)))
        hedge_audit.append({'osm_id':w['id'],'height_m':height_cells/16,'height_source':'OSM height' if w['tags'].get('height') else 'v1 reference-based nominal mass','width_m':.48})
    bed_union=unary_union(beds).difference(unary_union(hedge_footprints).buffer(.12))
    gx,gz=raster(bed_union)
    for x,z in zip(gx,gz):
        key=(int(x),int(z));base=surface_top.get(key)
        if base is None:continue
        # Low grouped planting masses inside mapped enclosed beds. Botanical
        # arrangement is illustrative, never a source for subsequent geometry.
        h=((int(x)//8)*73856093)^((int(z)//8)*19349663)
        extra=3+(h%4)
        for y in range(base,base+extra-1):builder.set_micro_local(x,y,z,HEDGE2)
        mat=FLOWERS[(h>>3)%3] if h%5==0 else HEDGE2
        builder.set_micro_local(x,base+extra-1,z,mat)
    print('Stage 5: mapped tree massing and street fixtures',flush=True)
    tree_audit=[]
    for node in nodes:
        x,z=node['x'],node['z']
        if node['tags'].get('natural')!='tree' or not garden.covers(Point(x,z)):continue
        gx,gz=round(x*16),round(z*16);base=surface_top.get((gx,gz),top(gx,gz))
        mask=(np.hypot(p['x']-x,p['z']-z)<1.8)&(p['classification']!=2)&(p['elev']>zero+base/16+2)
        h=float(np.percentile(p['elev'][mask],90)-zero-base/16) if mask.sum()>=10 else 5.0
        h=min(14.,max(3.,h));radius=1.8;ry=max(1.3,min(3.5,h*.37));cy=base/16+h-ry
        for dx in range(-2,3):
            for dz in range(-2,3):
                if dx*dx+dz*dz>5:continue
                for y in range(base,round((cy+.3)*16)):builder.set_micro_local(gx+dx,y,gz+dz,WOOD)
        # Half-meter crown cubes give foliage mass without pretending to have
        # measured individual branches. Crown is allowed to overhang public paths.
        for dx in np.arange(-radius,radius+.01,.5):
            for dz in np.arange(-radius,radius+.01,.5):
                for dy in np.arange(-ry,ry+.01,.5):
                    if (dx/radius)**2+(dz/radius)**2+(dy/ry)**2>1:continue
                    sx,sy,sz=round((x+dx)*16),round((cy+dy)*16),round((z+dz)*16)
                    mat=LEAF if (sx//8+sz//8+sy//8)%3 else LEAF2
                    for vx in range(sx-4,sx+4):
                        for vz in range(sz-4,sz+4):
                            if roads.covers(Point((vx+.5)/16,(vz+.5)/16)) and sy/16-height((vx+.5)/16,(vz+.5)/16)<2.6:continue
                            for vy in range(sy-4,sy+4):
                                pedestrian_top=surface_top.get((vx,vz))
                                if surface_material.get((vx,vz)) in {WALK,WALKJOINT,BRICK,STEP} and pedestrian_top is not None and vy<pedestrian_top+36:continue
                                builder.set_micro_local(vx,vy,vz,mat)
        tree_audit.append({'osm_id':node['id'],'x_m':x,'z_m':z,'height_m':h,'nearby_non_ground_returns':int(mask.sum()),'crown_radius_m':radius,
            'confidence':'mapped location; simplified crown, p90 height candidate may include nearby structure returns'})
    # Markings are a 1/16m overlay; preserve every accepted pavement cell.
    crossing_audit=[]
    for w in marked:
        poly=w['line'].buffer(1.2,cap_style=2).intersection(roads);gx,gz=raster(poly)
        station=line_locate_point(w['line'],points((gx+.5)/16,(gz+.5)/16));written=0
        for x,z,ss in zip(gx,gz,station):
            key=(int(x),int(z));t=road_top.get(key)
            if t is None:continue
            if ss%.7>.32:continue
            builder.set_micro_local(x,t,z,WHITE);written+=1
        crossing_audit.append({'osm_id':w['id'],'markings':w['tags'].get('crossing:markings'),'paint_cells':written,'overlay_m':.0625,'width_m':2.4,'stripe_period_m':.7,'stripe_width_m':.32})
    rail_audit=[]
    for w in ways:
        if w['tags'].get('railway')!='tram':continue
        clip=w['line'].intersection(endpoints[0]['pavement'])
        lines=list(clip.geoms) if hasattr(clip,'geoms') else [clip]
        for line in lines:
            if line.is_empty or line.geom_type!='LineString':continue
            gauge=float(w['tags'].get('gauge',1067))/1000
            for i in range(math.ceil(line.length*32)+1):
                station=min(line.length,i/32);pt=line.interpolate(station);a=line.interpolate(max(0,station-.1));b=line.interpolate(min(line.length,station+.1));dx,dz=b.x-a.x,b.y-a.y;ll=max(1e-9,math.hypot(dx,dz));nx,nz=-dz/ll,dx/ll
                for offset,mat in [(-gauge/2,STEEL),(0,BLACK),(gauge/2,STEEL)]:
                    gx,gz=round((pt.x+nx*offset)*16),round((pt.y+nz*offset)*16);t=road_top.get((gx,gz))
                    if t is not None:builder.set_micro_local(gx,t,gz,mat)
            rail_audit.append({'osm_id':w['id'],'length_m':line.length,'track_centerline_source':'OSM railway=tram','source_gauge_m':gauge,'rail_pair':True,'center_cable_slot':True,'quantization_m':.0625})
    fixtures=[];fixture_omissions=[]
    paved_walk_keys=np.array([key for key,mat in surface_material.items() if mat in {WALK,WALKJOINT,BRICK,STEP,v.CURB_MATERIAL}])
    walk_tree=cKDTree((paved_walk_keys+.5)/16)
    for node in nodes:
        x,z=node['x'],node['z'];gx,gz=round(x*16),round(z*16);base=surface_top.get((gx,gz))
        relocation=0.
        if base is None and node['tags'].get('traffic_sign')=='stop' and scope.buffer(1.5).covers(Point(x,z)):
            relocation,index=walk_tree.query([x,z])
            if relocation<=1.5:
                gx,gz=map(int,paved_walk_keys[index]);base=surface_top[(gx,gz)]
            else:fixture_omissions.append({'osm_id':node['id'],'reason':'Mapped pole does not fit source-width sidewalk within 1.5m; defer placement conflict'})
        if base is None:continue
        if node['tags'].get('emergency')=='fire_hydrant':
            for dx in range(-2,3):
                for dz in range(-2,3):
                    if dx*dx+dz*dz>5:continue
                    for y in range(base,base+11):builder.set_micro_local(gx+dx,y,gz+dz,WHITE)
            for dx in range(-4,5):builder.set_micro_local(gx+dx,base+7,gz,WHITE)
            fixtures.append({'type':'hydrant','osm_id':node['id'],'shape':'simplified white pillar'})
        if node['tags'].get('traffic_sign')=='stop':
            for y in range(base,base+35):builder.set_micro_local(gx,y,gz,STEEL)
            # Panel is 0.75m wide; axis aligned to face the closest street.
            nearest=min(endpoints,key=lambda e:e['line'].distance(Point(x,z)))
            along_x=abs(nearest['line'].coords[-1][0]-nearest['line'].coords[0][0])<abs(nearest['line'].coords[-1][1]-nearest['line'].coords[0][1])
            for u in range(-6,6):
                for h in range(-6,6):
                    if abs(u+.5)+abs(h+.5)>9:continue
                    border=abs(u+.5)>4.5 or abs(h+.5)>4.5 or abs(u+.5)+abs(h+.5)>7.5
                    mat=WHITE if border else 'astra_microblocks:rgb_a93932'
                    builder.set_micro_local(gx+(u if along_x else 0),base+35+h,gz+(0 if along_x else u),mat)
            fixtures.append({'type':'stop_sign','osm_id':node['id'],'panel_width_m':.75,'source_xz_m':[x,z],'modeled_xz_m':[(gx+.5)/16,(gz+.5)/16],'sidewalk_snap_distance_m':float(relocation),'note':'Simplified octagonal sign; mounting dimensions approximate; small sidewalk snap recorded where source datasets disagree'})
    builder.prune_empty_hosts()
    print('Validating immutable road spine and serializing',len(builder.hosts),'hosts',flush=True)
    locked_cells=0;locked_mismatches=0
    for pos,vol in locked.items():
        new=builder.hosts.get(pos)
        for i,m in enumerate(vol.cells):
            if m is not None:locked_cells+=1;locked_mismatches+=new is None or new.cells[i]!=m
    if locked_mismatches:raise RuntimeError('Accepted road cells changed')
    lock_ok,lock_report=v.compare_v009_cells(builder)
    if not lock_ok:raise RuntimeError('v009 lock failed')
    coords=np.array(list(builder.blocks));oldcoords=np.array(list(parent_blocks));lo=np.minimum(coords.min(axis=0),oldcoords.min(axis=0));hi=np.maximum(coords.max(axis=0),oldcoords.max(axis=0));bounds=(*lo.tolist(),*hi.tolist())
    writer=NBTWriter();payload=[]
    for (x,y,z),vol in sorted(builder.hosts.items()):payload.append(tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),vol))
    path=OUT/f'{NAME}.litematic';stats=write_single_region_litematic(path,builder.blocks,bounds,REGION,NAME,
      'Complete Lombard public-realm v1: accepted road and existing 50m endpoint streets, supported stairs/paths, landscaping and mapped street features; no houses. Source approximations documented.',data_version=v.DATA_VERSION,tile_entity_payloads=payload)
    actual,decoded=read(path,REGION)
    exact_block=actual=={p:canonical_state(s) for p,s in builder.blocks.items()}
    exact_host=set(decoded)==set(builder.hosts)
    exact_cells=exact_host and all(decoded[p].cells==builder.hosts[p].cells and decoded[p].original==builder.hosts[p].original for p in decoded)
    checks={'exact_litematica_readback':exact_block,'exact_astra_host_set':exact_host,'exact_astra_microcells_and_original':exact_cells,
        'v009_road_curb_locked':lock_ok,'v015_endpoint_roads_locked':locked_mismatches==0,'registration_marker':actual.get((0,-1,0))==v.MARKER,
        'all_ground_review_samples_supported':bool(support['supported'].all()),'houses_generated':False}
    report={**stats,'schema_version':1,'status':'valid' if all(value for key,value in checks.items() if key!='houses_generated') else 'invalid','review_status':'COMPLETE_NO_HOUSES_V1_FLYAROUND_REQUIRED',
        'scope':'Full crooked Lombard public corridor plus the existing 50m Hyde and 50m Leavenworth segments; no houses',
        'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'source_roi_sha256':hashlib.sha256((v.PROJECT/'downloads/raw/lombard_poc001_lidar_roi_v001.npz').read_bytes()).hexdigest(),
        'validation':checks,'road_curb_lock':lock_report,'all_accepted_road_cells_checked':locked_cells,'all_accepted_road_cell_mismatches':locked_mismatches,
        'terrain':{'public_scope_area_m2':scope.area,'ground_pedestrian_columns':len(surface_top),'source_sample_count':int(samplemask.sum()),'max_nearest_original_ground_m':float(support['nearest_ground_m'].max()),'support_distance_limit_m':5,'max_triangle_edge_limit_m':20,'method':'class-2 original-point TIN, same 1.5m smoothing; no recursive fill','review_boundary_faces':0},
        'features':feature_audit,'hedges':hedge_audit,'planted_bed_area_m2':bed_union.area,'trees':tree_audit,'crossings':crossing_audit,'cable_tracks':rail_audit,'fixtures':fixtures,'fixture_omissions':fixture_omissions,
        'retaining':retaining,'stair_sidewall_columns':sidewall_columns,
        'approximations':['Stair width 1.45m and endpoint landing depth 0.7m require eventual detail confirmation','Tagged step counts retained; untagged counts inferred from measured drop at nominal 0.18m risers','Mapped tree locations; p90 non-ground heights are candidates, crowns are simplified 1.8m-radius masses','Planting colors and low shrub masses illustrate reference character within mapped hedge beds, not surveyed individual plants','Sidewalk crossfall, curb ramps and sign mounting details are simplified v1 interpretations','Crossing and rail overlays are one microcell high to preserve every accepted pavement cell'],
        'excluded':['houses/building massing','interiors','unmapped decorative street furniture','street extensions beyond existing 50m endpoint lengths'],
        'stop_after':'User flyaround of assembled v1; do not mark survey/visual acceptance automatically'}
    (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (OUT/f'{NAME}_placement.json').write_text(json.dumps({'yellow_marker':[0,-1,0],'placement_origin':'same player-feet origin as v015/v016','rotation':0,'mirror':'none','replace_blocks':'ALL','paste_air':True},indent=2)+'\n')
    features={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'layer':'scope'},'geometry':scope.__geo_interface__},{'type':'Feature','properties':{'layer':'garden'},'geometry':garden.__geo_interface__},{'type':'Feature','properties':{'layer':'road'},'geometry':roads.__geo_interface__},{'type':'Feature','properties':{'layer':'pedestrian'},'geometry':walk_union.__geo_interface__},{'type':'Feature','properties':{'layer':'planting_beds'},'geometry':bed_union.__geo_interface__},*[{'type':'Feature','properties':{'layer':'hedge'},'geometry':q.__geo_interface__} for q in hedge_footprints]]}
    (OUT/'public_realm_plan.geojson').write_text(json.dumps(features,separators=(',',':'))+'\n')
    # Dense column caches are derived visualization inputs, not accepted truth.
    keys=np.array(list(surface_top));np.savez_compressed(OUT/'surface_preview.npz',xz=keys,top=np.array([surface_top[tuple(k)] for k in keys]),material=np.array([surface_material[tuple(k)] for k in keys]))
    print(json.dumps({'file':str(path),'status':report['status'],'validation':checks,'road_cells_checked':locked_cells,'stairs':len(core_stairs),'hedges':len(hedge_audit),'trees':len(tree_audit),'tracks':len(rail_audit),'crossings':len(crossing_audit),'fixtures':len(fixtures),'hosts':len(builder.hosts)},indent=2),flush=True)
    if report['status']!='valid':raise SystemExit(1)


if __name__=='__main__':main()
