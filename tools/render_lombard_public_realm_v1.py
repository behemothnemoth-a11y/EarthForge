"""Render the decoded schematic, not a separate idealized design."""
import sys,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read
REALISM='--realism' in sys.argv
LANDSCAPE='--landscape' in sys.argv or REALISM
BLOCKOUT='--blockout' in sys.argv or LANDSCAPE
if REALISM:
 from pipeline.reconstruction.generate_lombard_realism_v020 import OUT,NAME,REGION
elif LANDSCAPE:
 from pipeline.reconstruction.generate_lombard_landscape_v019 import OUT,NAME,REGION
elif BLOCKOUT:
 from pipeline.reconstruction.generate_lombard_neighborhood_v018 import OUT,NAME,REGION
else:
 from pipeline.reconstruction.generate_lombard_public_realm_v1 import OUT,NAME,REGION
PREFIX='Lombard_Realism_V020' if REALISM else ('Lombard_Landscape_V019' if LANDSCAPE else ('Lombard_Blockout_V018' if BLOCKOUT else 'Lombard_V1'))
O=Path(sys.argv[1]) if len(sys.argv)>1 else OUT;O.mkdir(parents=True,exist_ok=True)
blocks,hosts=read(OUT/f'{NAME}.litematic',REGION)
materials=sorted({m for v in hosts.values() for m in v.cells if m is not None}|{str(s) for p,s in blocks.items() if p not in hosts})
lookup={m:i+1 for i,m in enumerate(materials)}
def color(m):
 if 'rgb_' in m:
  q=m.split('rgb_')[1][:6];return tuple(int(q[k:k+2],16) for k in (0,2,4))
 for key,c in [('light_gray_concrete',(186,186,174)),('yellow_concrete',(244,199,34)),('polished_andesite',(135,137,132)),('smooth_stone',(162,163,154)),('oak_log',(103,80,48)),('bricks',(150,83,68)),('stone',(125,126,120))]:
  if key in m:return c
 return (155,155,155)
palette=np.array([(0,0,0)]+[color(m) for m in materials],dtype=np.uint8)
pos=np.array(list(blocks));lo=pos.min(axis=0);hi=pos.max(axis=0);size=hi-lo+1
array=np.zeros((size[1]*4,size[2]*4,size[0]*4),np.uint8)
for (hx,hy,hz),vol in hosts.items():
 a=np.array([lookup.get(m,0) for m in vol.cells],np.uint8).reshape(16,16,16)
 # Sample each quarter-meter cube by its most common occupied material.
 q=a.reshape(4,4,4,4,4,4).transpose(0,2,4,1,3,5).reshape(64,64)
 result=np.zeros(64,np.uint8)
 for i,items in enumerate(q):
  counts=np.bincount(items,minlength=len(palette));counts[0]=0
  if counts.max():result[i]=counts.argmax()
 by,bz,bx=(hy-lo[1])*4,(hz-lo[2])*4,(hx-lo[0])*4
 array[by:by+4,bz:bz+4,bx:bx+4]=result.reshape(4,4,4)
for p,m in blocks.items():
 if p in hosts:continue
 x,y,z=(np.array(p)-lo)*4;array[y:y+4,z:z+4,x:x+4]=lookup[str(m)]
print('Decoded render grid',array.shape,flush=True)
np.savez_compressed(O/'v1_render_cache.npz',array=array,palette=palette,lo=lo)
# True proportions, orthographic camera from the lower southeast side.
camera=np.array([.65,.75,1.]);camera/=np.linalg.norm(camera)
right=np.array([camera[2],0,-camera[0]]);right/=np.linalg.norm(right)
up=np.cross(camera,right)
faces=[];facecolors=[];shade=[]
occupied=array!=0
for axis,mult in [(0,1.0),(1,.68),(2,.82)]:
 neighbor=np.zeros(array.shape,bool)
 s1=[slice(None)]*3;s2=[slice(None)]*3;s1[axis]=slice(None,-1);s2[axis]=slice(1,None)
 neighbor[tuple(s1)]=occupied[tuple(s2)]
 iy,iz,ix=np.where(occupied&~neighbor)
 centers=np.c_[ix+.5,iy+.5,iz+.5]*.25+np.array([lo[0],lo[1],lo[2]])
 centers[:,[1,2,0][axis]]+=.125
 faces.append((centers,axis));facecolors.append(palette[array[iy,iz,ix]]*mult)
centers=np.vstack([p[0] for p in faces]);axes=np.concatenate([np.full(len(p[0]),p[1],int) for p in faces]);colors=np.vstack(facecolors).astype(np.uint8)
screen=np.c_[centers@right,-centers@up];depth=centers@camera
mins=screen.min(axis=0);maxs=screen.max(axis=0)
W,H=2400,1450;scale=min((W-100)/(maxs[0]-mins[0]),(H-230)/(maxs[1]-mins[1]));offset=np.array([50,150])-mins*scale
image=Image.new('RGB',(W,H),'#edf0e9');draw=ImageDraw.Draw(image)
vertices={
 0:np.array([[-.125,0,-.125],[.125,0,-.125],[.125,0,.125],[-.125,0,.125]]),
 1:np.array([[-.125,-.125,0],[.125,-.125,0],[.125,.125,0],[-.125,.125,0]]),
 2:np.array([[0,-.125,-.125],[0,.125,-.125],[0,.125,.125],[0,-.125,.125]])}
projected={a:np.c_[v@right,-v@up]*scale for a,v in vertices.items()}
xy=screen*scale+offset
for i in np.argsort(depth):
 polygon=xy[i]+projected[int(axes[i])]
 draw.polygon([tuple(v) for v in polygon],fill=tuple(colors[i]))
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
draw.text((55,28),('LOMBARD / REALISM REVIEW V020' if REALISM else 'LOMBARD / LANDSCAPE FORM PASS V019' if LANDSCAPE else ('LOMBARD / NEIGHBORHOOD BLOCKOUT' if BLOCKOUT else 'LOMBARD / COMPLETE PUBLIC REALM V1')),font=font(42),fill='#173a36')
draw.text((58,87),('Round blooms / Flush crossings / Finer outer ground / First photo-led building group' if REALISM else 'Rounded flowering shrubs and varied tree crowns / Simple colors / Buildings and hardscape preserved' if LANDSCAPE else ('City footprints and height envelopes / Plain materials / Existing corridor preserved' if BLOCKOUT else 'Full crooked block / No houses / Existing 50m endpoint streets')),font=font(25),fill='#526a64')
draw.text((58,H-67),'Decoded schematic preview at 0.25 m display sampling. Geometry and export validation remain at 1/16 m.',font=font(23),fill='#526a64')
image.save(O/f'{PREFIX}_Overview.png')
# Plan from the same decoded volume: the highest visible surface in each column.
iy=np.max(np.where(occupied,np.arange(array.shape[0])[:,None,None],-1),axis=0)
iz,ix=np.indices(iy.shape);ids=array[np.maximum(iy,0),iz,ix];rgb=palette[ids];rgb[iy<0]=(237,240,233)
plan=Image.fromarray(rgb).resize((rgb.shape[1]*3,rgb.shape[0]*3),Image.Resampling.NEAREST)
canvas=Image.new('RGB',(plan.width,plan.height+120),'#edf0e9');canvas.paste(plan,(0,105));dr=ImageDraw.Draw(canvas);dr.text((24,16),('Lombard v020 / realism review plan' if REALISM else 'Lombard v019 / landscape form plan' if LANDSCAPE else ('Lombard v018 / neighborhood massing plan' if BLOCKOUT else 'Lombard V1 / decoded schematic plan')),font=font(35),fill='#173a36');dr.text((24,61),('North is up; Hyde at left. Flat caps indicate height envelopes, not verified roof forms.' if BLOCKOUT else 'North is up; Hyde at left, Leavenworth at right. Buildings intentionally absent.'),font=font(22),fill='#526a64');canvas.save(O/f'{PREFIX}_Plan.png')
for filename in [f'{PREFIX}_Overview.png',f'{PREFIX}_Plan.png']:
 import shutil
 if O.resolve()!=OUT.resolve():shutil.copy2(O/filename,OUT/filename)
print('Rendered',len(centers),'visible-direction voxel faces',flush=True)

import hashlib
(O/'render_manifest.json').write_text(json.dumps({'schematic_sha256':hashlib.sha256((OUT/f'{NAME}.litematic').read_bytes()).hexdigest(),'decoded_hosts':len(hosts),'display_sampling_m':0.25},indent=2)+'\n')
