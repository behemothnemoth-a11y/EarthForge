"""Lombard v032: richer source-led first architectural pass for 1040 Lombard.

The pass starts from accepted v024, removes the entire old 1040 placeholder,
then rebuilds the source-visible hierarchy: garage/recessed entry, lower and
upper central bays, broad right body, terrace fascia, open rail and pergola.
Photo-proportioned dimensions are review candidates, not survey truth.
"""
from pathlib import Path
import sys, json, math, hashlib
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point, LineString, shape
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.reconstruction import generate_lombard_access_tree_realism_v024 as parent
from pipeline.reconstruction import generate_lombard_neighborhood_v018 as buildings
from pipeline.reconstruction import generate_lombard_public_realm_v1 as realm
from pipeline.reconstruction import generate_lombard_realism_v020 as realism
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read, position
from pipeline.microblocks.astra_microblock_codec import MicroVolume, HOST_STATE, tile_entity_payload
from pipeline.export.litematic_codec import NBTWriter, canonical_state, write_single_region_litematic

OUT=realm.v.PROJECT/'outputs/house_1040_source_firstpass_v032'
NAME='Lombard_1040_Source_FirstPass_Astra_v032'
REGION='LOMBARD_1040_SOURCE_FIRSTPASS_V032'
BUILDING_ID='201006.0032105'
MEASURE=realm.v.PROJECT/'source_manifests/1040_lombard_photo_measurements_v032.json'

BODY='astra_microblocks:rgb_91b9ca'; BODY2='astra_microblocks:rgb_82aec2'
NAVY='astra_microblocks:rgb_203743'; NAVY2='astra_microblocks:rgb_2b4551'
WHITE='astra_microblocks:rgb_e7e4da'; WINDOW='astra_microblocks:rgb_cdd8d6'
GARAGE='astra_microblocks:rgb_a7cdd9'; GARAGE_SHADOW='astra_microblocks:rgb_7fa6b2'
DARK='astra_microblocks:rgb_17262c'; ROOF='astra_microblocks:rgb_3b4a50'

def xyz(pos,i):
    hx,hy,hz=pos
    return hx*16+(i&15)-480, hy*16+(i>>8), hz*16+((i>>4)&15)-320

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=parent.OUT/f'{parent.NAME}.litematic'
    blocks,hosts=read(source,parent.REGION)
    vanilla={p:s for p,s in blocks.items() if p not in hosts}
    original={p:(q.original,q.cells.copy()) for p,q in hosts.items()}

    env=json.loads((buildings.OUT/'building_envelopes.geojson').read_text())
    feat=next(f for f in env['features'] if str(f['properties']['id'])==BUILDING_ID)
    geom=shape(feat['geometry'])
    poly=max(geom.geoms,key=lambda q:q.area) if hasattr(geom,'geoms') else geom
    m=json.loads(MEASURE.read_text())

    center=json.loads(realm.v.CENTER.read_text())
    road=LineString([(q['x_m'],q['z_m']) for q in center])
    edges=[]
    coords=list(poly.exterior.coords)
    for a,b in zip(coords,coords[1:]):
        seg=LineString([a,b])
        if seg.length>5:
            edges.append((seg.distance(road),seg.length,np.array(a,float),np.array(b,float)))
    _,width,pa,pb=min(edges,key=lambda q:q[0])
    if pa[0]>pb[0]: pa,pb=pb,pa
    vec=pb-pa; width=float(np.linalg.norm(vec)); uvec=vec/width
    normal=np.array([-uvec[1],uvec[0]])
    if np.dot(np.array([poly.centroid.x,poly.centroid.y])-(pa+pb)/2,normal)<0:
        normal=-normal

    drive_y=[]
    for hp,hv in hosts.items():
        for ii,mat in enumerate(hv.cells):
            if mat not in {parent.DRIVE,parent.DRIVE_JOINT}: continue
            xx,yy,zz=xyz(hp,ii); pt=np.array([(xx+.5)/16,(zz+.5)/16]); rr=pt-pa
            u=float(np.dot(rr,uvec))/width; d=float(np.dot(rr,normal))
            if .14<=u<=.58 and -2.25<=d<=-.30: drive_y.append(yy)
    if len(drive_y)<20: raise RuntimeError('1040 front datum lacks accepted driveway support')
    floor=int(round(float(np.median(drive_y))))+1

    prop=feat['properties']; zero=float(center[0]['elev_navd88_m'])
    source_cap=round((prop['median_first_return_navd88_m']-zero)*16)
    total_h=(source_cap-floor)/16
    dm=m['derived_candidate_proportions']['vertical_m_above_driveway']
    dz=m['derived_candidate_proportions']['depth_m_from_source_front_edge']
    zones=m['derived_candidate_proportions']['front_zones']

    garage_head=float(dm['garage_door_head']); lower_sill=float(dm['lower_bay_sill'])
    lower_head=float(dm['lower_bay_head']); interlevel=float(dm['interlevel_band'])
    upper_sill=float(dm['upper_bay_sill']); upper_head=float(dm['upper_bay_head'])
    fascia_bottom=float(dm['terrace_fascia_bottom']); deck_h=float(dm['terrace_deck'])
    rail_top=float(dm['railing_top']); pergola_top=min(float(dm['pergola_top']),total_h-.10)
    if not (8.5<deck_h<10.3 and 11.5<pergola_top<=total_h):
        raise RuntimeError('photo-proportion bands do not fit source envelope')

    writes={}; changes={}; preserved_context_collisions=0
    def put(x,y,z,mat,why):
        nonlocal preserved_context_collisions
        p,i=position(int(x),int(y),int(z))
        if p in vanilla:
            preserved_context_collisions+=1; return False
        old=hosts[p].cells[i] if p in hosts else None
        if old is not None and (p,i) not in writes:
            preserved_context_collisions+=1; return False
        if old==mat: return False
        if p not in hosts:
            hosts[p]=MicroVolume('minecraft:bricks'); blocks[p]=HOST_STATE
        hosts[p].cells[i]=mat
        prior=writes.get((p,i),(old,None,None))[0]
        writes[(p,i)]=(prior,mat,why); changes[why]=changes.get(why,0)+1
        return True

    def remove(x,y,z,why):
        p,i=position(int(x),int(y),int(z)); q=hosts.get(p)
        if q is None or q.cells[i] is None: return False
        old=q.cells[i]; q.cells[i]=None
        prior=writes.get((p,i),(old,None,None))[0]
        writes[(p,i)]=(prior,None,why); changes[why]=changes.get(why,0)+1
        return True

    old_build=set(buildings.WALLS)|{
        buildings.ROOF,realism.rgb('a9cbd6'),realism.rgb('293f48'),
        realism.rgb('95c7d4'),realism.rgb('799da5'),realism.rgb('8cb3ba')}
    target=poly.buffer(.16); minx,minz,maxx,maxz=target.bounds
    clear_floor=round((prop['ground_min_navd88_m']-zero)*16)-5; clear_cap=source_cap+5
    candidate_hosts=[]
    for p,v in hosts.items():
        hx,hy,hz=p
        hminx=(hx*16-480)/16; hmaxx=(hx*16-480+15)/16
        hminz=(hz*16-320)/16; hmaxz=(hz*16-320+15)/16
        if hmaxx<minx or hminx>maxx or hmaxz<minz or hminz>maxz: continue
        if hy*16+15<clear_floor or hy*16>clear_cap: continue
        candidate_hosts.append((p,v))

    for p,v in candidate_hosts:
        for i,mat in enumerate(v.cells.copy()):
            if mat not in old_build: continue
            x,y,z=xyz(p,i); pt=Point((x+.5)/16,(z+.5)/16)
            if clear_floor<=y<=clear_cap and target.covers(pt):
                remove(x,y,z,'remove_entire_old_1040')
    for p,_ in candidate_hosts:
        if p in hosts and not any(hosts[p].cells):
            hosts.pop(p); blocks.pop(p,None)

    support_mats={
        parent.DRIVE,parent.DRIVE_JOINT,realm.WALK,realm.WALKJOINT,
        realm.STEP,realm.BRICK,realm.GREEN,buildings.GROUND,buildings.BASE,
        realism.rgb('63764a'),realism.rgb('687a4e'),
        realism.rgb('607348'),realism.rgb('6b7c50')}
    support_pts=[]; support_y=[]
    halo=poly.buffer(2.0); interior=poly.buffer(-.04)
    for p,v in hosts.items():
        hx,hy,hz=p; cx=(hx*16-480+8)/16; cz=(hz*16-320+8)/16
        if not halo.buffer(1.0).covers(Point(cx,cz)): continue
        for i,mat in enumerate(v.cells):
            if mat not in support_mats: continue
            x,y,z=xyz(p,i); q=Point((x+.5)/16,(z+.5)/16)
            if not halo.covers(q): continue
            if not interior.is_empty and interior.covers(q): continue
            support_pts.append([q.x,q.y]); support_y.append(y)
    support_tree=cKDTree(np.asarray(support_pts,float)) if support_pts else None
    support_y=np.asarray(support_y,int)

    def local_base(x,z):
        if support_tree is None: return floor
        q=np.array([(x+.5)/16,(z+.5)/16])
        k=min(12,len(support_pts))
        dist,idx=support_tree.query(q,k=k,distance_upper_bound=1.6)
        dist=np.atleast_1d(dist); idx=np.atleast_1d(idx)
        good=[int(j) for dd,j in zip(dist,idx) if np.isfinite(dd) and int(j)<len(support_y)]
        if not good: return floor
        return max(floor,int(round(float(np.median(support_y[good]))))+1)

    body_top_y=floor+round(deck_h*16)
    body_ring=poly.boundary.buffer(.10,cap_style=2,join_style=2)
    bx0,bz0,bx1,bz1=poly.bounds
    for x in range(math.floor((bx0-.15)*16),math.ceil((bx1+.15)*16)):
        for z in range(math.floor((bz0-.15)*16),math.ceil((bz1+.15)*16)):
            pt=Point((x+.5)/16,(z+.5)/16)
            if not body_ring.covers(pt): continue
            rr=np.array([pt.x,pt.y])-pa
            u=float(np.dot(rr,uvec))/width; d=float(np.dot(rr,normal))
            if -.02<=u<=1.02 and -.08<=d<=.24: continue
            base=local_base(x,z)
            if base>=body_top_y: continue
            for y in range(base,body_top_y):
                put(x,y,z,BODY2 if ((x//8+z//8)&1) else BODY,'body_side_rear_shell')

    for x in range(math.floor(bx0*16),math.ceil(bx1*16)):
        for z in range(math.floor(bz0*16),math.ceil(bz1*16)):
            pt=Point((x+.5)/16,(z+.5)/16)
            if poly.buffer(-.03).covers(pt):
                put(x,body_top_y,z,ROOF,'provisional_body_top_cap')

    cols=[]
    for x in range(math.floor((bx0-.15)*16),math.ceil((bx1+.15)*16)):
        for z in range(math.floor((bz0-.15)*16),math.ceil((bz1+.15)*16)):
            p=np.array([(x+.5)/16,(z+.5)/16]); rr=p-pa
            along=float(np.dot(rr,uvec)); d=float(np.dot(rr,normal)); u=along/width
            if -.02<=u<=1.02 and -.08<=d<=2.35 and poly.buffer(.03).covers(Point(*p)):
                cols.append((x,z,u,d,along))

    def near(v,t,tol=.055):
        return abs(v-t)<=tol

    def big_window(u,yy,u0,u1,y0,y1,cols_n,rows_n=2):
        if not (u0<=u<=u1 and y0<=yy<=y1): return None
        ux=(u-u0)/(u1-u0); vy=(yy-y0)/(y1-y0)
        border=min(ux,1-ux,vy,1-vy)<.032
        mull=any(abs(ux-k/cols_n)<.010 for k in range(1,cols_n))
        mull=mull or any(abs(vy-k/rows_n)<.014 for k in range(1,rows_n))
        return WHITE if border or mull else WINDOW

    main_d=float(dz['main_wall'])
    for x,z,u,d,along in cols:
        if .10<=u<=.99 and near(d,main_d):
            for y in range(floor+2,floor+round(fascia_bottom*16)):
                yy=(y-floor)/16
                major=any(abs(yy-q)<.07 for q in [2.42,interlevel,8.15])
                put(x,y,z,NAVY if major else BODY,'recessed_main_wall')

    entry0,entry1=map(float,zones['entry_recess_u']); entry_d=float(dz['entry_back_wall'])
    for x,z,u,d,along in cols:
        if entry0<=u<=entry1 and near(d,entry_d):
            for y in range(floor+2,floor+round(2.85*16)):
                put(x,y,z,DARK,'recessed_entry')
        if near(u,entry1,.007) and main_d<=d<=entry_d:
            for y in range(floor+2,floor+round(2.85*16)):
                put(x,y,z,NAVY,'entry_return')

    gu0,gu1=map(float,zones['garage_opening_u']); garage_d=float(dz['garage_face'])
    for x,z,u,d,along in cols:
        if .10<=u<=.60 and near(d,garage_d):
            for y in range(floor+2,floor+round(2.45*16)):
                yy=(y-floor)/16
                if gu0<=u<=gu1 and .12<=yy<=garage_head:
                    ux=(u-gu0)/(gu1-gu0)
                    edge=min(ux,1-ux,yy-.12,garage_head-yy)<.045
                    hseam=abs(((yy-.12)%0.48)-.24)<.028
                    vseam=any(abs(ux-k/4)<.012 for k in [1,2,3])
                    mat=NAVY if edge else GARAGE_SHADOW if hseam or vseam else GARAGE
                    put(x,y,z,mat,'garage_door')
                else: put(x,y,z,BODY,'garage_surround')

    cu0,cu1=map(float,zones['central_bay_u']); lower_d=float(dz['lower_bay_face'])
    for x,z,u,d,along in cols:
        if cu0<=u<=cu1 and near(d,lower_d):
            for y in range(floor+round(2.45*16),floor+round(5.18*16)):
                yy=(y-floor)/16
                win=big_window(u,yy,cu0+.025,cu1-.025,lower_sill,lower_head,6,2)
                if win: mat=win
                else:
                    border=min(abs(u-cu0),abs(u-cu1))*width<.09 or any(abs(yy-q)<.075 for q in [2.48,5.13])
                    ux=(u-cu0)/max(.01,cu1-cu0)
                    vy=(yy-2.45)/max(.2,lower_sill-2.45)
                    diag=yy<lower_sill and (abs(ux-vy)<.026 or abs((1-ux)-vy)<.026)
                    mat=NAVY if border or diag else BODY2
                put(x,y,z,mat,'lower_projecting_bay')
        if (near(u,cu0,.007) or near(u,cu1,.007)) and lower_d<=d<=main_d:
            for y in range(floor+round(2.45*16),floor+round(5.18*16)):
                yy=(y-floor)/16
                mat=NAVY if any(abs(yy-q)<.07 for q in [2.48,5.13]) else BODY2
                put(x,y,z,mat,'lower_bay_return')
        if cu0<=u<=cu1 and lower_d<=d<=main_d:
            for qy in [2.45,5.18]:
                put(x,floor+round(qy*16),z,NAVY2,'lower_bay_slab')

    upper_d=float(dz['upper_bay_face']); uu0,uu1=.17,.60
    for x,z,u,d,along in cols:
        if uu0<=u<=uu1 and near(d,upper_d):
            for y in range(floor+round(5.27*16),floor+round(8.20*16)):
                yy=(y-floor)/16
                win=big_window(u,yy,uu0+.035,uu1-.035,upper_sill,upper_head,4,2)
                if win: mat=win
                else:
                    border=min(abs(u-uu0),abs(u-uu1))*width<.09 or any(abs(yy-q)<.075 for q in [5.30,8.15])
                    ux=(u-uu0)/max(.01,uu1-uu0)
                    vy=(yy-5.30)/max(.3,upper_sill-5.30)
                    diag=5.30<=yy<upper_sill and (abs(ux-vy)<.023 or abs((1-ux)-vy)<.023)
                    mat=NAVY if border or diag else BODY
                put(x,y,z,mat,'upper_recessed_bay')
        if (near(u,uu0,.007) or near(u,uu1,.007)) and upper_d<=d<=main_d:
            for y in range(floor+round(5.27*16),floor+round(8.20*16)):
                yy=(y-floor)/16
                mat=NAVY if any(abs(yy-q)<.07 for q in [5.30,8.15]) else BODY
                put(x,y,z,mat,'upper_bay_return')
        if uu0<=u<=uu1 and upper_d<=d<=main_d:
            for qy in [5.27,8.20]:
                put(x,floor+round(qy*16),z,NAVY2,'upper_bay_slab')

    ru0,ru1=map(float,zones['right_vertical_body_u']); right_d=float(dz['right_vertical_body_face'])
    for x,z,u,d,along in cols:
        if ru0<=u<=ru1 and near(d,right_d):
            for y in range(floor+round(.25*16),floor+round(8.55*16)):
                yy=(y-floor)/16
                win=big_window(u,yy,.78,.91,6.25,7.72,2,3)
                if win: mat=win
                else:
                    border=min(abs(u-ru0),abs(u-ru1))*width<.09 or any(abs(yy-q)<.075 for q in [2.45,5.30,8.50])
                    ux=(u-ru0)/max(.01,ru1-ru0)
                    phase=((yy-2.50)/2.75)%1.0
                    diag=2.5<yy<8.45 and (abs(ux-phase)<.020 or abs((1-ux)-phase)<.020)
                    mat=NAVY if border or diag else BODY2
                put(x,y,z,mat,'right_vertical_body')

    for x,z,u,d,along in cols:
        if .10<=u<=.99 and near(d,.02):
            for y in range(floor+round(fascia_bottom*16),floor+round(deck_h*16)):
                yy=(y-floor)/16
                section=(u-.10)/.89; panel=(section*3)%1
                border=min(panel,1-panel)<.045 or any(abs(yy-q)<.07 for q in [fascia_bottom,deck_h-.05])
                vy=(yy-fascia_bottom)/max(.1,deck_h-fascia_bottom)
                cross=abs(panel-vy)<.030 or abs((1-panel)-vy)<.030
                put(x,y,z,NAVY if border or cross else BODY,'terrace_fascia')

    terrace_depth=float(dz['terrace_visible_depth'])
    for x,z,u,d,along in cols:
        if .10<=u<=.99 and 0<=d<=terrace_depth:
            put(x,body_top_y,z,NAVY2,'front_terrace_deck')

    rail_y0=floor+round((deck_h+.08)*16); rail_y1=floor+round(rail_top*16)
    for x,z,u,d,along in cols:
        if .10<=u<=.99 and near(d,.02):
            spacing=1.15; post=abs(((along-.10*width)%spacing)-spacing/2)<.045
            for y in range(rail_y0,rail_y1+1):
                yy=(y-floor)/16
                horiz=any(abs(yy-q)<.045 for q in [deck_h+.10,rail_top-.05])
                if post or horiz: put(x,y,z,NAVY,'open_front_railing')
        if near(u,.99,.007) and 0<=d<=terrace_depth:
            post=abs((d%1.05)-.525)<.045
            for y in range(rail_y0,rail_y1+1):
                yy=(y-floor)/16
                if post or any(abs(yy-q)<.045 for q in [deck_h+.10,rail_top-.05]):
                    put(x,y,z,NAVY,'open_right_railing')

    perg_y0=floor+round(deck_h*16); perg_y1=floor+round(pergola_top*16)
    for x,z,u,d,along in cols:
        post_u=any(abs(u-q)*width<.065 for q in [.10,.55,.99])
        post_d=near(d,.04,.065) or near(d,terrace_depth,.065)
        if post_u and post_d:
            for y in range(perg_y0,perg_y1+1):
                put(x,y,z,NAVY,'pergola_post')
        if .10<=u<=.99 and (near(d,.04,.065) or near(d,terrace_depth,.065)):
            for y in range(perg_y1-2,perg_y1+1):
                put(x,y,z,NAVY,'pergola_front_back_header')
        if 0<=d<=terrace_depth and any(abs(u-q)*width<.055 for q in [.10,.32,.55,.77,.99]):
            for y in range(perg_y1-2,perg_y1+1):
                put(x,y,z,NAVY2,'pergola_depth_beam')

    for p in list(hosts):
        if not any(hosts[p].cells):
            hosts.pop(p); blocks.pop(p,None)

    escaped=[]; public_overlap=[]
    public_mats={parent.DRIVE,parent.DRIVE_JOINT,realm.WALK,realm.WALKJOINT,realm.STEP,realm.BRICK}
    for (p,i),(old,new,why) in writes.items():
        x,y,z=xyz(p,i); pt=Point((x+.5)/16,(z+.5)/16)
        if not poly.buffer(.18).covers(pt):
            escaped.append([x,y,z,why])
        if old in public_mats:
            public_overlap.append([x,y,z,why,old,new])
    if escaped or public_overlap:
        raise RuntimeError(str({'escaped':escaped[:5],'public_overlap':public_overlap[:5]}))

    remaining_old=[]
    for p,v in hosts.items():
        hx,hy,hz=p; cx=(hx*16-480+8)/16; cz=(hz*16-320+8)/16
        if not target.buffer(1).covers(Point(cx,cz)): continue
        for i,mat in enumerate(v.cells):
            if mat not in old_build: continue
            x,y,z=xyz(p,i); pt=Point((x+.5)/16,(z+.5)/16)
            if clear_floor<=y<=clear_cap and target.covers(pt):
                remaining_old.append([x,y,z,mat])
                if len(remaining_old)>=5: break
        if len(remaining_old)>=5: break

    touched={p for p,i in writes}; outside_ok=True
    for p,(orig,cells0) in original.items():
        q=hosts.get(p)
        if p not in touched:
            if q is None or q.original!=orig or q.cells!=cells0:
                outside_ok=False; break
        else:
            for i,a in enumerate(cells0):
                if (p,i) in writes: continue
                b=q.cells[i] if q is not None else None
                if a!=b:
                    outside_ok=False; break
            if not outside_ok: break

    checks_pre={
        'declared_1040_scope_only':not escaped,
        'public_realm_cells_untouched':not public_overlap,
        'all_old_1040_placeholder_removed':not remaining_old,
        'all_parent_cells_outside_declared_edits_preserved':outside_ok,
        'driveway_datum_supported':len(drive_y)>=20,
        'source_front_width_10_93m':10.7<width<11.2,
        'body_stops_below_source_cap':body_top_y<source_cap-20,
        'open_structure_reaches_source_envelope':perg_y1<=source_cap and perg_y1>=source_cap-8,
    }
    if not all(checks_pre.values()):
        raise RuntimeError(str(checks_pre))

    plan=Image.new('RGB',(900,470),'white'); pd=ImageDraw.Draw(plan)
    def sx(u): return 55+u*790
    def sd(d): return 415-d/2.4*300
    pd.line((sx(.10),sd(main_d),sx(.99),sd(main_d)),fill='#80a8b8',width=5)
    pd.line((sx(cu0),sd(lower_d),sx(cu1),sd(lower_d)),fill='#203743',width=8)
    pd.line((sx(uu0),sd(upper_d),sx(uu1),sd(upper_d)),fill='#2b4551',width=6)
    pd.line((sx(ru0),sd(right_d),sx(ru1),sd(right_d)),fill='#385c6b',width=7)
    pd.line((sx(entry0),sd(entry_d),sx(entry1),sd(entry_d)),fill='#17262c',width=7)
    pd.text((55,24),'v032 source-first depth hierarchy — photo proportions, not survey depth',fill='#243338')
    plan_path=OUT/'Lombard_1040_v032_depth_intent.png'; plan.save(plan_path)

    elev=Image.new('RGB',(900,740),'#eef1f1'); ed=ImageDraw.Draw(elev)
    def ex(u): return 50+u*800
    def ey(h): return 690-h/max(total_h,12.6)*630
    ed.rectangle((ex(.10),ey(deck_h),ex(.99),ey(.15)),fill=(145,185,202),outline=(32,55,67),width=3)
    ed.rectangle((ex(gu0),ey(garage_head),ex(gu1),ey(.12)),fill=(167,205,217),outline=(32,55,67),width=3)
    for u0,u1,y0,y1 in [
        (cu0+.025,cu1-.025,lower_sill,lower_head),
        (uu0+.035,uu1-.035,upper_sill,upper_head),
        (.78,.91,6.25,7.72)]:
        ed.rectangle((ex(u0),ey(y1),ex(u1),ey(y0)),fill=(205,216,214),outline=(237,234,222),width=4)
    ed.rectangle((ex(.10),ey(deck_h),ex(.99),ey(fascia_bottom)),outline=(32,55,67),width=4)

    ed.line((ex(.10),ey(rail_top),ex(.99),ey(rail_top)),fill=(32,55,67),width=3)
    ed.line((ex(.10),ey(deck_h+.1),ex(.99),ey(deck_h+.1)),fill=(32,55,67),width=2)
    ed.line((ex(.10),ey(pergola_top),ex(.99),ey(pergola_top)),fill=(32,55,67),width=6)
    for q in [.10,.55,.99]:
        ed.line((ex(q),ey(pergola_top),ex(q),ey(deck_h)),fill=(32,55,67),width=3)
    ed.text((50,20),'v032 facade hierarchy — garage + two enclosed facade levels + open rooftop structure',fill='#243338')
    elev_path=OUT/'Lombard_1040_v032_elevation_intent.png'; elev.save(elev_path)

    coords_np=np.array(list(blocks))
    lo=coords_np.min(0); hi=coords_np.max(0); bounds=(*lo.tolist(),*hi.tolist())
    writer=NBTWriter()
    payload=[
        tile_entity_payload(writer,(p[0]-bounds[0],p[1]-bounds[1],p[2]-bounds[2]),q)
        for p,q in sorted(hosts.items())]
    artifact=OUT/f'{NAME}.litematic'
    stats=write_single_region_litematic(
        artifact,blocks,bounds,REGION,NAME,
        '1040 Lombard richer source-first review pass: full source footprint body, source-bounded facade hierarchy, projected bays, broad right body and open terrace/pergola. Photo-proportioned dimensions remain candidate until flyaround.',
        data_version=realm.v.DATA_VERSION,tile_entity_payloads=payload)

    actual,decoded=read(artifact,REGION)
    checks={
        **checks_pre,
        'exact_litematica':actual=={p:canonical_state(s) for p,s in blocks.items()},
        'exact_astra':set(decoded)==set(hosts) and all(decoded[p].cells==q.cells and decoded[p].original==q.original for p,q in hosts.items()),
        'vanilla_preserved':all(actual.get(p)==s for p,s in vanilla.items()),
    }

    report={
        **stats,
        'status':'PASS' if all(checks.values()) else 'FAIL',
        'validation':checks,
        'parent':'v024 accepted public-realm/access context',
        'parent_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'building_id':BUILDING_ID,
        'address':'1040 Lombard Street',
        'source_footprint_area_m2':float(poly.area),
        'front_width_m':width,
        'driveway_datum_samples':len(drive_y),
        'driveway_floor_micro_y':floor,
        'source_cap_micro_y':source_cap,
        'source_total_height_m':total_h,
        'photo_measurement_manifest':str(MEASURE.relative_to(ROOT)),
        'body_top_m':deck_h,
        'railing_top_m':rail_top,
        'pergola_top_m':pergola_top,
        'preserved_context_collisions':preserved_context_collisions,
        'changed_microcells':len(writes),
        'changes':changes,
        'confidence':m['confidence'],
        'geometry_claims':[
            'DataSF source footprint and registration',
            'accepted v024 driveway datum',
            'source absolute first-return envelope',
            'persistent facade hierarchy across 2008/2009/2013/2014/2019 references'],
        'candidate_only':[
            'facade horizontal fractions',
            'vertical subdivisions',
            'bay/recess depth offsets',
            'provisional flat body-top cap'],
        'explicit_non_claims':[
            'interior layout','foundation truth','final rear roof form',
            'survey-grade window dimensions','survey-grade bay depths'],
        'review':'USER_MINECRAFT_FLYAROUND_REQUIRED',
    }
    (OUT/f'{NAME}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/f'{NAME}_placement.json').write_text(json.dumps({
        'placement_origin':'same Lombard player-feet origin',
        'rotation':0,'mirror':'none','replace_blocks':'ALL including air'},indent=2)+'\n')
    (OUT/'Build_notes.md').write_text(
        '# 1040 Lombard source-first first pass v032\n\n'
        'Richer first-pass architecture from verified footprint/site controls plus photo-proportioned persistent facade hierarchy. '
        'This is intentionally much more informative than v031, but photo-derived dimensions remain review candidates.\n')
    print(json.dumps({
        'file':str(artifact),
        'status':report['status'],
        'front_width_m':width,
        'total_height_m':total_h,
        'body_top_m':deck_h,
        'changed_microcells':len(writes),
        'changes':changes,
        'validation':checks},indent=2))
    if report['status']!='PASS':
        raise SystemExit(1)

if __name__=='__main__':
    main()
