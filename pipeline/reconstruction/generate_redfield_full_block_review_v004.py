#!/usr/bin/env python3
"""Redfield Main 600 block review candidate v004.

Starts from the pushed rear/service v003 candidate, preserves the accepted
617-627 true-frame facades and all evidence-backed streets/rears, then
re-authors selected native facades from the verified current Redfield 21 Feet
reference set. Raw imagery remains private and gitignored.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from pipeline.export.litematic_codec import (
    NBTWriter, canonical_state, read_back_block_map, write_single_region_litematic
)
from pipeline.microblocks.astra_microblock_codec import (
    BLOCK_ENTITY_ID, HOST_STATE, MicroVolume, decode_volume_v4, tile_entity_payload
)
from pipeline.reconstruction import generate_redfield_full_block_alpha_v001 as alpha
from pipeline.reconstruction import generate_redfield_full_block_rear_v003 as rear
from pipeline.terrain import generate_redfield_poc001_micrograde_v001 as micrograde

PROJECT=ROOT/"projects"/"redfield_sd"
SOURCE=PROJECT/"outputs/full_block_rear_v003/Redfield_POC_001_FullBlock_RearService_v003.litematic"
SOURCE_REGION="REDFIELD_POC001_FULLBLOCK_REAR_SERVICE_V003"
AUTH=PROJECT/"poc_001/full_block_facade_authority_v001.json"
OUT=PROJECT/"outputs/full_block_review_v004"
NAME="Redfield_POC_001_FullBlock_ReviewCandidate_v004"
REGION="REDFIELD_POC001_FULLBLOCK_REVIEW_V004"
REF_X=-78
REF_Z=9

def load_model():
    blocks,meta=read_back_block_map(SOURCE,SOURCE_REGION)
    rp=meta["region_position"]
    hosts={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
            v=MicroVolume()
            v.cells=decode_volume_v4(te["volume_v4"])
            hosts[p]=v
    return blocks,hosts

def clear_canvas(c):
    # Remove prior authored facade skin/awnings while leaving street furniture
    # and deeper shell geometry alone.
    c.clear(0,1,.15,c.height/16,-12,26)

def mat(value):
    return alpha.rgb(value)

GLYPHS={
    "A":["010","101","111","101","101"],
    "C":["111","100","100","100","111"],
    "E":["111","100","110","100","111"],
    "L":["100","100","100","100","111"],
    "S":["111","100","111","001","111"],
    "T":["111","010","010","010","010"],
    "U":["101","101","101","101","111"],
    "Y":["101","101","010","010","010"],
}

def pixel_text(c,text,uf0,uf1,y0m,scale,material,depth=5):
    units=sum(3 for _ in text)+max(0,len(text)-1)
    width=units*scale
    start=c.U((uf0+uf1)/2)-width//2
    base=c.Y(y0m)
    x=start
    for ch in text:
        glyph=GLYPHS[ch]
        for row,bits in enumerate(glyph):
            yy=base+(4-row)*scale
            for col,on in enumerate(bits):
                if on=="1":
                    for dx in range(scale):
                        for dy in range(scale):
                            c.cell(x+col*scale+dx,yy+dy,depth,material)
        x+=4*scale

def author_602(c,item):
    body=alpha.palette(item,"body"); tower=alpha.palette(item,"tower")
    sign=alpha.palette(item,"sign"); trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.rect(0,.69,0,4.65,-2,1,body)
    c.rect(.03,.67,3.25,4.15,0,3,sign)
    c.rect(.05,.67,3.08,3.23,0,5,trim)
    c.window(.12,.31,.65,2.45,glass,trim,-5,2,False,True)
    c.window(.35,.54,.65,2.45,glass,trim,-5,2,False,True)
    c.door(.56,.66,2.55,body,trim,glass,-6)
    c.rect(.70,.95,0,6.5,-3,2,tower)
    c.vertical_seams(.70,.95,0,6.5,7,mat("rgb_552522"),2)
    c.window(.75,.91,1.05,2.15,glass,trim,-5,2,False,True)
    c.rect(.79,.88,4.15,5.65,1,4,sign)

def author_604(c,item):
    body=alpha.palette(item,"body"); awn=alpha.palette(item,"awning")
    base=alpha.palette(item,"base"); trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.wall(body,3); c.rect(0,1,0,.45,-2,1,base)
    c.awning(.03,.97,3.35,20,11,awn,trim)
    for a,b in [(.07,.22),(.32,.47),(.57,.72),(.80,.94)]:
        c.window(a,b,.6,2.45,glass,trim,-5,2,False,True)
    c.door(.23,.31,2.5,body,trim,glass,-6)
    c.door(.72,.80,2.5,body,trim,glass,-6)

def author_605(c,item):
    brick=alpha.palette(item,"brick"); roof=alpha.palette(item,"roof")
    trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    alpha.brick_texture(c,brick,mat("rgb_824234"))
    c.rect(.02,.98,4.55,5.05,0,5,trim)
    c.awning(.02,.98,3.55,22,12,roof,trim)
    bays=[(.07,.23),(.25,.41),(.43,.59),(.61,.77),(.79,.94)]
    for a,b in bays:
        c.window(a,b,.55,2.7,glass,trim,-5,2,False,True)

def author_610(c,item):
    body=alpha.palette(item,"body"); brick=alpha.palette(item,"brick")
    trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.wall(body,3); c.vertical_seams(0,1,0,7.0,8,mat("rgb_65737a"),2)
    c.rect(0,1,7.0,8.1,-2,1,brick)
    c.rect(.06,.94,7.55,7.8,0,4,mat("rgb_5e382f"))
    c.window(.12,.31,4.9,5.35,glass,trim,-5,2,False)
    c.window(.52,.82,4.55,6.05,glass,trim,-5,2,False,True)
    c.rect(.38,.58,3.15,3.7,0,3,mat("rgb_4f5b5e"))
    c.window(.08,.28,.55,2.5,glass,trim,-5,2,False)
    c.door(.39,.50,2.6,body,trim,glass,-6)
    c.window(.53,.91,.55,2.5,glass,trim,-5,2,False,True)

def author_612(c,item):
    brick=alpha.palette(item,"brick"); body=alpha.palette(item,"body")
    trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    alpha.brick_texture(c,brick,mat("rgb_573c35"))
    c.rect(.05,.95,5.55,5.85,0,5,trim)
    c.rect(.10,.35,5.85,6.0,0,4,trim)
    c.rect(.65,.90,5.85,6.0,0,4,trim)
    c.rect(.08,.92,3.95,4.15,0,5,trim)
    c.rect(.06,.94,0,3.2,-2,1,body)
    c.horizontal_seams(.1,3.15,7,mat("rgb_8d5429"),2)
    c.awning(.06,.94,2.95,10,7,body,trim)
    c.window(.11,.38,.5,2.25,glass,trim,-5,2,False)
    c.door(.44,.56,2.45,mat("rgb_4c382e"),trim,glass,-6)
    c.window(.62,.89,.5,2.25,glass,trim,-5,2,False)

def author_613(c,item):
    brick=alpha.palette(item,"brick"); roof=alpha.palette(item,"roof")
    lower=alpha.palette(item,"lower"); trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    alpha.brick_texture(c,brick,mat("rgb_7f3e32"))
    for a,b in [(.20,.40),(.58,.78)]:
        c.rect(a,b,4.7,6.25,-4,1,mat("rgb_a17e70"))
        c.rect(a-.015,b+.015,4.62,6.34,0,2,trim)
    c.awning(.01,.99,3.55,14,12,roof,roof)
    c.rect(.24,.78,.45,2.35,-2,1,lower)
    c.horizontal_seams(.55,2.3,5,mat("rgb_7f5648"),2)
    c.door(.05,.17,2.45,roof,trim,glass,-6)
    c.door(.84,.96,2.45,roof,trim,glass,-6)

def author_615(c,item):
    brick=alpha.palette(item,"brick"); cream=alpha.palette(item,"cream")
    stone=alpha.palette(item,"stone"); trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    alpha.brick_texture(c,brick,mat("rgb_794737"))
    mural=[mat("rgb_53a5b6"),mat("rgb_d65b72"),mat("rgb_e7c84d"),mat("rgb_4d85af")]
    for i,(a,b) in enumerate([(.14,.28),(.31,.45),(.55,.69),(.72,.86)]):
        c.rect(a,b,5.15,7.2,-4,1,mural[i])
        c.rect(a-.012,b+.012,5.05,7.3,0,2,trim)
    c.rect(0,1,2.7,4.35,-2,1,cream)
    c.rect(.43,.80,3.25,3.85,1,4,mat("rgb_395db4"))
    for a,b in [(.02,.17),(.33,.46),(.55,.68),(.83,.98)]:
        c.rect(a,b,0,2.7,-2,1,stone)
    c.window(.19,.31,.45,2.35,glass,trim,-5,2,False)
    c.door(.46,.55,2.55,mat("rgb_1f2425"),trim,glass,-7)
    c.window(.70,.81,.45,2.35,glass,trim,-5,2,False)

def author_620(c,item):
    body=alpha.palette(item,"body"); roof=alpha.palette(item,"roof")
    trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.rect(0,1,0,3.15,-2,1,body)
    c.vertical_seams(0,1,0,3.15,8,mat("rgb_244a50"),2)
    c.awning(0,1,4.25,12,14,roof,roof)
    c.horizontal_seams(3.4,4.65,4,mat("rgb_343a3e"),2)
    c.rect(.05,.44,4.25,4.65,1,3,trim)
    for a,b in [(.05,.22),(.24,.41),(.43,.60),(.62,.79),(.81,.96)]:
        c.window(a,b,.65,2.55,glass,trim,-5,2,False,True)

def author_622(c,item):
    body=alpha.palette(item,"body"); parapet=alpha.palette(item,"parapet")
    trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.rect(0,1,0,3.15,-2,1,body)
    c.vertical_seams(0,1,0,3.15,9,mat("rgb_bab8b2"),2)
    c.rect(.02,.98,3.15,4.55,-3,1,parapet)
    c.rect(0,1,3.02,3.16,0,7,trim)
    c.window(.10,.38,.55,2.45,glass,trim,-5,2,False)
    c.window(.43,.62,.55,2.45,glass,trim,-5,2,False)
    c.door(.63,.73,2.55,body,trim,glass,-6)
    c.window(.75,.92,.55,2.45,glass,trim,-5,2,False)

def author_624(c,item):
    body=alpha.palette(item,"body"); trim=alpha.palette(item,"trim")
    sign=alpha.palette(item,"sign"); glass=alpha.palette(item,"glass")
    c.wall(body,3); c.horizontal_seams(.1,5.25,6,mat("rgb_4f514e"),2)
    c.rect(.03,.97,5.15,5.6,0,7,trim)
    c.rect(.10,.90,3.0,5.05,0,2,body)
    pixel_text(c,"ALLEY",.12,.88,4.10,2,sign,5)
    pixel_text(c,"CUTS",.18,.82,3.28,2,sign,5)
    c.window(.08,.34,.5,2.35,glass,trim,-5,2,False,True)
    c.door(.41,.59,2.55,body,trim,glass,-6)
    c.window(.66,.92,.5,2.35,glass,trim,-5,2,False,True)

def author_626(c,item):
    brick=alpha.palette(item,"brick"); stone=alpha.palette(item,"stone")
    dark=alpha.palette(item,"dark"); trim=alpha.palette(item,"trim"); glass=alpha.palette(item,"glass")
    c.wall(brick,4); c.rect(0,1,0,.72,0,4,stone)
    c.rect(.02,.98,7.55,7.82,0,7,trim)
    c.rect(.06,.94,7.82,8.14,0,5,trim)
    c.rect(.10,.90,8.2,8.48,0,3,brick)
    c.clear(.31,.69,.82,7.28,-28,8)
    c.rect(.33,.67,2.8,7.20,-10,-5,dark)
    c.door(.42,.58,2.8,dark,trim,glass,-9)
    c.round_column(.37,.85,6.75,4,stone,4)
    c.round_column(.63,.85,6.75,4,stone,4)
    c.rect(.32,.68,6.65,6.98,0,10,stone)
    c.window(.08,.18,1.15,2.75,glass,trim,-5,2,False)
    c.window(.82,.92,1.15,2.75,glass,trim,-5,2,False)
    u=c.U(.50)
    c.line(u,c.Y(8.35),u,c.Y(9.18),0,2,trim,0)

def author_terrys(c,item616,item614):
    brick=alpha.palette(item616,"brick"); accent=alpha.palette(item616,"accent")
    body=alpha.palette(item616,"body"); stone=alpha.palette(item616,"stone")
    roof=alpha.palette(item616,"roof"); trim=alpha.palette(item616,"trim"); glass=alpha.palette(item616,"glass")
    split=.50
    c.rect(0,1,0,4.0,-2,1,body)
    c.rect(0,1,0,1.55,-2,2,stone)
    c.awning(.02,.98,2.75,12,8,roof,trim)
    c.rect(0,split,4.0,8.5,-3,1,brick)
    c.rect(.04,split-.04,6.45,7.78,0,3,accent)
    c.rect(.08,split-.08,7.02,7.30,2,5,mat("rgb_4e2929"))
    c.rect(.06,split-.06,8.08,8.42,0,4,trim)
    c.rect(.12,.20,8.38,8.5,0,5,trim)
    c.rect(.34,.42,8.38,8.5,0,5,trim)
    c.window(.05,.22,.45,2.30,glass,trim,-5,2,False)
    c.door(.24,.33,2.42,body,trim,glass,-6)
    c.window(.35,.48,.45,2.30,glass,trim,-5,2,False)
    c.door(.56,.65,2.35,body,trim,glass,-6)
    c.window(.68,.95,.45,2.22,glass,trim,-5,2,False,True)
    c.rect(split,.98,2.82,4.60,0,3,body)
    for uf in (.58,.66,.74,.82,.90):
        c.rect(uf,uf+.025,3.55,4.18,4,6,mat("rgb_4d4a45"))

REFINED={
    "602":author_602,
    "604":author_604,
    "605":author_605,
    "610":author_610,
    "612":author_612,
    "613":author_613,
    "615":author_615,
    "620":author_620,
    "622":author_622,
    "624":author_624,
    "626":author_626,
}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blocks,hosts=load_model()
    authority=json.loads(AUTH.read_text())
    items=authority["facades"]
    _,_,_,row_cells,_,_,_,_,_=micrograde.build_surface()

    def set_cell(sx,sy,sz,material):
        rear.set_micro(blocks,hosts,sx,sy,sz,material)

    refined=[]
    for item in items:
        fn=REFINED.get(item["id"])
        if fn is None:
            continue
        c=alpha.make_canvas(item,row_cells,REF_X,REF_Z,set_cell)
        clear_canvas(c)
        fn(c,item)
        refined.append(item["id"])

    i614=next(i for i in items if i["id"]=="614")
    i616=next(i for i in items if i["id"]=="616")
    terry={**i616,"id":"614-616",
           "z0_m":min(i614["z0_m"],i616["z0_m"]),
           "z1_m":max(i614["z1_m"],i616["z1_m"]),
           "front_x_m":min(i614["front_x_m"],i616["front_x_m"]),
           "facade_height_m":8.5}
    tc=alpha.make_canvas(terry,row_cells,REF_X,REF_Z,set_cell)
    clear_canvas(tc)
    author_terrys(tc,i616,i614)
    refined.extend(["614","616"])

    empty=[p for p,v in hosts.items() if v.occupied_count()==0]
    for p in empty:
        hosts.pop(p,None)
        if blocks.get(p)==HOST_STATE:
            blocks.pop(p,None)
    for p in hosts:
        blocks[p]=HOST_STATE

    xs=[p[0] for p in blocks]; ys=[p[1] for p in blocks]; zs=[p[2] for p in blocks]
    bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
    writer=NBTWriter()
    tes=[tile_entity_payload(writer,(x-bounds[0],y-bounds[1],z-bounds[2]),v)
         for (x,y,z),v in sorted(hosts.items())]
    out=OUT/f"{NAME}.litematic"
    stats=write_single_region_litematic(
        out,blocks,bounds,REGION,NAME,
        "Registered Redfield Main 600-block review candidate: v003 streets/rears preserved; selected native facades refined from verified current references; accepted 617-627 v002 facades unchanged.",
        data_version=4903,tile_entity_payloads=tes
    )
    reread,meta=read_back_block_map(out,REGION)
    assert reread=={p:canonical_state(s) for p,s in blocks.items()}
    rp=meta["region_position"]; decoded={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
            decoded[p]=decode_volume_v4(te["volume_v4"])
    assert set(decoded)==set(hosts)
    for p,v in hosts.items():
        assert decoded[p]==v.cells,p
    assert reread.get((0,-1,0))=="minecraft:yellow_concrete"

    report={
        **stats,
        "source_candidate":"projects/redfield_sd/outputs/full_block_rear_v003/Redfield_POC_001_FullBlock_RearService_v003.litematic",
        "authority":"projects/redfield_sd/poc_001/full_block_facade_authority_v001.json",
        "refined_native_facades":refined,
        "preserved_v002_facades":["617-619","621","623","625-627"],
        "preserved_evidence_layers":{
            "micrograde":"2012 SDGS class-2 LiDAR",
            "roof_bands":"2012 SDGS first-return LiDAR with aerial and OSM footprint review",
            "streetscape":"full_block_streetscape_v002",
            "rear_service":"full_block_rear_v003"
        },
        "reference_policy":{
            "current_facades":"verified Redfield 21 Feet current-photo set",
            "aerial_manifest":"projects/redfield_sd/source_manifests/redfield_west_main_roof_blockout_v001.json",
            "raw_images_embedded":False,
            "private_reference_material_committed":False
        },
        "astra":{"hosts":len(hosts),"occupied_microcells":sum(v.occupied_count() for v in hosts.values())},
        "validation":{
            "exact_block_readback":True,
            "exact_astra_readback":True,
            "registration_marker":True,
            "accepted_617_627_not_reauthored":True,
            "raw_reference_images_embedded":False,
            "in_game_review":False
        }
    }
    (OUT/f"{NAME}_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"Build_notes.md").write_text(
        "# Redfield Full Block Review Candidate v004\n\n"
        "Starts from rear/service v003 and preserves its intersections, alleys, secondary structures, MicroGrade and LiDAR roof bands. "
        "The accepted 617-627 true-frame facades are not touched.\n\n"
        "Native facade refinement targets 602, 604, 605, 610, 612-616, 620, 622, 624 and 626 using the verified current Redfield 21 Feet reference set. "
        "This pass corrects awning heights, storefront bay rhythm, boarded and upper openings, stone-pier placement, Terry's shared frontage, Alley Cuts signage massing and City Hall's recessed classical center.\n\n"
        "Licensed/raw imagery remains under references/private and is excluded by .gitignore; this output contains only derived geometry and provenance metadata.\n"
    )
    print(json.dumps({
        "file":str(out),
        "sha256":stats["sha256"],
        "region_size":stats["region_size"],
        "refined_facades":refined,
        "astra_hosts":len(hosts),
        "occupied_microcells":sum(v.occupied_count() for v in hosts.values()),
        "validation":"PASS"
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())