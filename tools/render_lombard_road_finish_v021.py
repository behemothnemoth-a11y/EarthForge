"""Actual 1/16m decoded detail crops, preserving the flower silhouette."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pipeline.reconstruction import generate_lombard_road_finish_v021 as g
from pipeline.reconstruction.generate_lombard_terrain_repair_v016 import read
O=Path(sys.argv[1]) if len(sys.argv)>1 else g.OUT;O.mkdir(parents=True,exist_ok=True)
path=g.OUT/f'{g.NAME}.litematic';blocks,hosts=read(path,g.REGION)
def color(m):
 if 'rgb_' in m:return tuple(bytes.fromhex(m.split('rgb_')[1][:6]))
 return {'minecraft:light_gray_concrete':(186,186,174),'minecraft:smooth_stone':(162,163,154),'minecraft:oak_log':(103,80,48)}.get(m,(145,145,139))
materials=sorted({m for v in hosts.values() for m in v.cells if m});lookup={m:i+1 for i,m in enumerate(materials)};palette=np.array([(0,0,0)]+[color(m) for m in materials],np.uint8)
cache=np.load(g.v.OUT/'surface_preview.npz');xz=cache['xz']/16;top=cache['top']/16
specs=[('Pavers',28,46,-18,-4),('Hyde_Join',-7,15,-12,12),('Leavenworth_Join',134,155,-38,-13)]
allowed=g.OLD_RED|g.ASPHALT|{g.road.CURB_MATERIAL,g.v.WHITE,g.v.STEEL,g.v.BLACK}|set(g.material(c) for c in g.reference_palette()[1])
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
for name,x0,x1,z0,z1 in specs:
 if name=='Pavers':
  mask=(xz[:,0]>=x0)&(xz[:,0]<x1)&(xz[:,1]>=z0)&(xz[:,1]<z1);y0=math.floor(top[mask].min())-1;y1=math.ceil(top[mask].max())+2
 elif name=='Hyde_Join':y0=-2;y1=3
 else:y0=-35;y1=-30
 lo=np.array([x0+30,y0,z0+20],int);hi=np.array([x1+30,y1,z1+20],int);sz=hi-lo;arr=np.zeros((sz[1]*16,sz[2]*16,sz[0]*16),np.uint8)
 for p,v in hosts.items():
  if not np.all(np.array(p)>=lo) or not np.all(np.array(p)<hi):continue
  x,y,z=(np.array(p)-lo)*16;arr[y:y+16,z:z+16,x:x+16]=np.array([lookup.get(m,0) if m in allowed else 0 for m in v.cells],np.uint8).reshape(16,16,16)
 occ=arr>0;cam=np.array([.45,.6,1.]);cam/=np.linalg.norm(cam);right=np.array([cam[2],0,-cam[0]]);right/=np.linalg.norm(right);up=np.cross(cam,right);centers=[];colors=[];axes=[]
 for axis,shade in [(0,1.),(1,.7),(2,.83)]:
  nb=np.zeros(arr.shape,bool);a=[slice(None)]*3;b=a.copy();a[axis]=slice(None,-1);b[axis]=slice(1,None);nb[tuple(a)]=occ[tuple(b)]
  y,z,x=np.where(occ&~nb);p=np.c_[x+.5,y+.5,z+.5]/16+lo;p[:,[1,2,0][axis]]+=1/32;centers.append(p);colors.append(palette[arr[y,z,x]]*shade);axes.extend([axis]*len(p))
 centers=np.vstack(centers);colors=np.vstack(colors).astype(np.uint8);axes=np.array(axes);screen=np.c_[centers@right,-centers@up];depth=centers@cam;W,H=2000,1400;sc=min((W-90)/np.ptp(screen[:,0]),(H-220)/np.ptp(screen[:,1]));xy=screen*sc+np.array([45,140])-screen.min(0)*sc
 q=1/32;verts={0:np.array([[-q,0,-q],[q,0,-q],[q,0,q],[-q,0,q]]),1:np.array([[-q,-q,0],[q,-q,0],[q,q,0],[-q,q,0]]),2:np.array([[0,-q,-q],[0,-q,q],[0,q,q],[0,q,-q]])};proj={k:np.c_[v@right,-v@up]*sc for k,v in verts.items()}
 im=Image.new('RGB',(W,H),'#edf0e9');dr=ImageDraw.Draw(im)
 for j in np.argsort(depth):dr.polygon([tuple(p) for p in xy[j]+proj[int(axes[j])]],fill=tuple(colors[j]))
 dr.text((35,25),'LOMBARD V021 / '+name.replace('_',' ').upper(),font=font(38),fill='#173a36');dr.text((35,80),'Decoded road materials at full 1/16m; surroundings hidden for join inspection',font=font(24),fill='#526a64');dr.text((35,H-60),'Reference-sampled brick colors; 6mm joints area-sampled to avoid dark 62.5mm stripes.',font=font(23),fill='#526a64');im.save(O/f'Lombard_V021_{name}.png');print(name,len(centers),flush=True)
(O/'detail_render_manifest.json').write_text(json.dumps({'schematic_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'display_sampling_m':.0625,'crops':specs},indent=2)+'\n')
