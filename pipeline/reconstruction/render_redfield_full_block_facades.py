#!/usr/bin/env python3
from __future__ import annotations
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipeline.export.litematic_codec import read_back_block_map
from pipeline.microblocks.astra_microblock_codec import HOST_STATE, BLOCK_ENTITY_ID, cell_index, decode_volume_v4
from pipeline.reconstruction.generate_redfield_west_main_trueframe_v002 import material_rgb
from pipeline.reconstruction.facade_module_compiler import FacadePlacement

PROJECT=ROOT/"projects"/"redfield_sd"
AUTH=PROJECT/"poc_001/full_block_facade_authority_v001.json"
LITEMATIC=PROJECT/"outputs/full_block_alpha_v001/Redfield_POC_001_FullBlock_FacadeAlpha_v001.litematic"
REGION="REDFIELD_POC001_FULLBLOCK_FACADE_ALPHA_V001"
OUT=PROJECT/"outputs/full_block_alpha_v001"
REF_X=-78
REF_Z=9

def floor16(v):
    h=math.floor(v/16); return h,v-h*16

def main():
    auth=json.loads(AUTH.read_text())
    blocks,meta=read_back_block_map(LITEMATIC,REGION)
    rp=meta["region_position"]
    tes={}
    for te in meta["tile_entities"]:
        if te.get("id")==BLOCK_ENTITY_ID:
            p=(te["x"]+rp[0],te["y"]+rp[1],te["z"]+rp[2])
            tes[p]=decode_volume_v4(te["volume_v4"])
    def mat_at(sx,sy,sz):
        hx,lx=floor16(sx);hy,ly=floor16(sy);hz,lz=floor16(sz)
        state=blocks.get((hx,hy,hz))
        if state is None:return None
        if state==HOST_STATE:
            cells=tes.get((hx,hy,hz))
            return None if cells is None else cells[cell_index(lx,ly,lz)]
        return state.split("[",1)[0]

    fp=Path("C:/Windows/Fonts/segoeui.ttf")
    font=lambda n:ImageFont.truetype(str(fp),n)
    for side in ("west","east"):
        items=[i for i in auth["facades"] if i["side"]==side]
        # Render each facade in photo orientation.
        panels=[]
        for item in items:
            south=max(item["z0_m"],item["z1_m"]); north=min(item["z0_m"],item["z1_m"])
            p=FacadePlacement(
                side=side,
                front_x_micro=round(item["front_x_m"]*16),
                south_z_micro=round(south*16),
                north_z_micro=round(north*16),
                base_y_micro=0,
                ref_x_block=REF_X,
                ref_z_block=REF_Z,
            )
            w=p.width; h=round(item["facade_height_m"]*16)+24
            pix=Image.new("RGB",(w,h),(239,238,230))
            pd=ImageDraw.Draw(pix)
            for u in range(w):
                # photo-left mapping
                if side=="west":
                    lz=p.south_z_micro-u
                else:
                    lz=p.north_z_micro+u
                sz=lz-REF_Z*16
                for y in range(h):
                    # Street-to-building ray.
                    found=None
                    ds=range(28,-34,-1)
                    for d in ds:
                        lx=p.front_x_micro + d if side=="west" else p.front_x_micro-d
                        sx=lx-REF_X*16
                        m=mat_at(sx,y,sz)
                        if m is not None:
                            found=m;break
                    if found:
                        pix.putpixel((u,h-1-y),material_rgb(found))
            # scale for display
            display_h=360
            sc=max(1,round(display_h/h))
            pix=pix.resize((w*sc,h*sc),Image.Resampling.NEAREST)
            panel=Image.new("RGB",(pix.width+20,pix.height+55),"white")
            panel.paste(pix,(10,35))
            ImageDraw.Draw(panel).text((10,8),f"{item['id']}  {item['width_m']:.2f}m",font=font(17),fill="#243c39")
            panels.append((item,panel))
        # Order by address south->north for both strips
        panels.sort(key=lambda q:max(q[0]["z0_m"],q[0]["z1_m"]),reverse=True)
        total=sum(p.width for _,p in panels)+20*(len(panels)-1)+40
        height=max(p.height for _,p in panels)+100
        sheet=Image.new("RGB",(total,height),"#efeee7")
        d=ImageDraw.Draw(sheet);x=20
        d.text((20,height-52),f"{side.upper()} SIDE — exported microcell facade readback",font=font(20),fill="#243c39")
        for _,p in panels:
            sheet.paste(p,(x,20));x+=p.width+20
        sheet.save(OUT/f"Redfield_FullBlock_{side}_FacadeReadback_v001.png")
        print(side,total,height)

if __name__=="__main__":
    main()
