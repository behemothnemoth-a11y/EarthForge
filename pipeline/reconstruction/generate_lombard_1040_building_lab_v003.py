"""1040 lab v003: source-proportioned architectural front, not a facade diagram.
Uses shared FacadeCanvas, exact Astra codec and Redfield greedy preview meshing.
The current v002 is the preserved parent; only the front construction zone changes.
"""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipeline.microblocks.facade_canvas import FacadeCanvas
from pipeline.microblocks import astra_microblock_codec as ac
from pipeline.export.litematic_codec import NBTWriter,read_back_block_map,canonical_state,write_single_region_litematic
from pipeline.reconstruction.generate_redfield_621_hybrid_restart_v003 import rectangles
LAB=ROOT/'projects/lombard_sf/building_labs/1040_lombard'
OUT=ROOT/'projects/lombard_sf/outputs/building_labs/1040_lombard_v003'
PARENT=OUT.parent/'1040_lombard_v002/Lombard_1040_BuildingLab_v002.litematic'
REGION='LOMBARD_1040_BUILDING_LAB_V003'; NAME='Lombard_1040_BuildingLab_v003'
R=206; U0=16; Z0=32; WALL=42; W=175; H=202; DECK=155
RGB=lambda s:'astra_microblocks:rgb_'+s
M={'body':RGB('9db0c2'),'panel':RGB('aebfce'),'shadow':RGB('637786'),'timber':RGB('344650'),'edge':RGB('4b5e6d'),'dark':RGB('25353f'),'white':RGB('e6e5dd'),'white_shade':RGB('b8c1c2'),'garage':RGB('a6becd'),'garage_line':RGB('859eaf'),'glass':'minecraft:gray_stained_glass'}
def mc(x):return round(x*16)
def load_cells(path,region):
 blocks,meta=read_back_block_map(path,region);vs={};off=meta['region_position']
 for t in meta['tile_entities']:
  if t.get('id')!=ac.BLOCK_ENTITY_ID:continue
  p=tuple(int(t[k])+off[j] for j,k in enumerate(('x','y','z')))
  v=ac.MicroVolume(t['volume_v4']['original']);v.cells=list(ac.decode_volume_v4(t['volume_v4']));vs[p]=v
 return blocks,vs,meta

def allowed(x,y,z):
 u=R-x-U0
 return -4<=u<=W+4 and 2<=y<DECK and 25<=z<=56

def main():
 OUT.mkdir(parents=True,exist_ok=True);spec=json.loads((LAB/'lab_v003.json').read_text())
 blocks,vols,_=load_cells(PARENT,'LOMBARD_1040_BUILDING_LAB_V002')
 baseline={p:(v.original,v.cells.copy()) for p,v in vols.items()}
 for (hx,hy,hz),v in vols.items():
  for i,mat in enumerate(v.cells):
   if mat is not None and allowed(hx*16+(i&15),hy*16+(i>>8),hz*16+((i>>4)&15)):v.cells[i]=None
 c=FacadeCanvas(W,H);features=[];opens=[]
 def b(d0,d1,y0,y1,u0,u1,mat,role='assembly'):
  c.box(d0,d1,mc(y0),mc(y1),round(u0*W),round(u1*W),M.get(mat,mat));features.append(role)
 def line(u0,y0,u1,y1,face,role,width=2):
  c.stroke_uy(face,face+2,u0*W,mc(y0),u1*W,mc(y1),width,M['timber'],exclude=protected)
  features.append(role)
 modules=spec['candidate_modules']
 protected=[(round(q['u'][0]*W)-1,round(q['u'][1]*W)+1,mc(q['y_m'][0])-1,mc(q['y_m'][1])+1) for k,q in modules.items() if k!='garage']
 # Primary structure with distinct frame return planes, not a painted outline.
 b(-5,1,.125,9.6875,0,1,'body','main_wall')
 def bay(u0,u1,y0,y1,face):
  b(face-3,face+1,y0,y1,u0,u1,'panel','bay_face')
  b(-2,face+1,y0,y1,u0,u0+.012,'timber','bay_left_return')
  b(-2,face+1,y0,y1,u1-.012,u1,'timber','bay_right_return')
  for ya,yb in [(y0,y0+.125),(y1-.125,y1)]:b(-2,face+2,ya,yb,u0,u1,'timber','bay_horizontal_return')
 bay(.13,.615,2.10,5.30,10)
 bay(.17,.60,5.30,8.62,5)
 bay(.60,.982,.125,8.62,5)
 # Layered rail/reveal interfaces copied as TECHNIQUE from accepted Redfield, never its style.
 for y,u0,u1,face in [(2.10,.13,.615,10),(3.075,.13,.615,10),(5.30,.13,.982,10),(6.55,.17,.60,5),(8.10,.17,.60,5),(8.62,.10,.99,10)]:
  b(face-2,face+2,y-.09,y+.015,u0,u1,'dark','sill_underface')
  b(face+1,face+3,y+.015,y+.0775,u0,u1,'edge','sill_lip')
 # Source-visible spandrel divisions. Occluded fields are not filled with invented repeating Xs.
 for u in [.13,.385,.605,.685,.977]:
  face=10 if u<.615 else 5
  b(face,face+2,2.125,8.60,u,u+.010,'timber','vertical_member')
 for args in [(.15,3.0,.29,2.2,10),(.385,2.2,.56,3.0,10),(.20,5.40,.40,6.40,5),(.40,6.40,.575,5.40,5),(.62,5.30,.81,8.45,5),(.62,6.30,.91,8.43,5),(.80,8.43,.926,7.80,5)]:
  line(*args,'photo_panel_diagonal')
 for u0,u1 in [(.19,.345),(.345,.51),(.51,.60)]:
  line(u0,8.14,u1,8.57,5,'upper_frieze_diagonal')
 b(7,11,8.62,9.6875,.10,.99,'panel','terrace_fascia')
 for y in [8.62,9.5625]: b(7,13,y,y+.125,.10,.99,'timber','fascia_cap')
 for u in [.10,.20,.32,.58,.69,.95,.982]: b(10,12,8.70,9.5625,u,u+.01,'timber','fascia_panel_stile')
 for mid in [.46,.82]:
  line(mid-.065,8.76,mid+.065,9.50,10,'fascia_cross')
  line(mid+.065,8.76,mid-.065,9.50,10,'fascia_cross')
 # Garage shutter has raised panels and subtle beads, not black grid bars.
 ga=modules['garage'];l,r=[round(q*W) for q in ga['u']];yb,yt=[mc(q) for q in ga['y_m']]
 c.clear(-24,20,2,yt+3,l-2,r+2)
 c.box(-1,3,2,yt,l,r,M['garage'])
 for u in [l-2,r]:c.box(-3,6,2,yt+3,u,u+2,M['timber'])
 c.box(-3,6,yt,yt+3,l-2,r+2,M['timber'])
 for j in range(4):
  y0=2+round((yt-2)*j/4); y1=2+round((yt-2)*(j+1)/4)
  for k in range(3):
   a=l+round((r-l)*k/3);bb=l+round((r-l)*(k+1)/3)
   c.box(3,4,y0+2,y1-1,a+2,bb-2,M['garage_line'])
   c.box(4,5,y0+3,y1-2,a+3,bb-3,M['garage'])
 # Entry is an actual inset door assembly, connected by reveals to the wall.
 l,r=0,round(.128*W);et=mc(2.85)
 c.clear(-24,20,2,et,l,r);c.box(-10,-8,2,et,l,r,M['dark'])
 c.box(-9,1,et-2,et,l,r,M['timber']);c.box(-9,1,2,et,r-2,r,M['timber'])
 c.box(-8,-7,4,et-3,3,r-3,M['timber']);c.box(-7,-6,10,22,6,r-5,M['dark'])
 # Four window groups: real frame/reveal/glazing/sash assemblies.
 def window(name,q,face):
  l,r=[round(v*W) for v in q['u']];yb,yt=[mc(v) for v in q['y_m']];n=q['casements']
  c.clear(-24,face+12,yb-1,yt+1,l-1,r+1)
  for a,bb,y0,y1 in [(l-1,l+1,yb-1,yt+1),(r-1,r+1,yb-1,yt+1),(l,r,yb-1,yb+1),(l,r,yt-1,yt+1)]:
   c.box(-5,face+1,y0,y1,a,bb,M['white_shade']);c.box(face+1,face+3,y0,y1,a,bb,M['white'])
  c.box(face-3,face-2,yb+1,yt-1,l+1,r-1,M['glass'])
  for k in range(n):
   a=l+round((r-l)*k/n);bb=l+round((r-l)*(k+1)/n)
   for u in [a,bb-1]:c.box(face-1,face+2,yb+1,yt-1,u,u+1,M['white'])
   mid=(a+bb)//2
   if bb-a>=8:c.box(face-1,face,yb+1,yt-1,mid,mid+1,M['white_shade'])
  rows=4 if name in ('lower_main','right_lower') else 5
  for k in range(1,rows):
   yy=yb+round((yt-yb)*k/rows)
   c.box(face-1,face,yy,yy+1,l+1,r-1,M['white_shade'])
  # Fine projecting sill and header over a darker underside.
  c.box(face,face+4,yb-3,yb-1,l-2,r+2,M['white_shade'])
  c.box(face+2,face+4,yb-1,yb,l-2,r+2,M['white'])
  c.box(face,face+3,yt+1,yt+3,l-2,r+2,M['white_shade'])
  opens.append({'name':name,'bounds':[l,r,yb,yt],'face':face,'glass_depth':[face-3,face-2]})
 for name,face in [('lower_main',10),('upper_main',5),('right_upper',5),('right_lower',5)]:window(name,modules[name],face)
 # Photo-visible small lower right door, not a white painted rectangle.
 l,r=round(.852*W),round(.965*W);yt=mc(2.1)
 c.clear(-24,20,2,yt,l,r);c.box(0,2,2,yt,l,r,M['white_shade'])
 c.box(2,3,4,yt-2,l+2,r-2,M['white']);c.box(3,4,10,21,l+4,r-4,M['white_shade'])
 c.box(3,4,25,yt-3,l+3,r-3,M['dark']);c.box(4,5,25,yt-3,(l+r)//2,(l+r)//2+1,M['white'])
 def put(x,y,z,mat):
  if not allowed(x,y,z):raise ValueError(('outside front scope',x,y,z))
  p=(x//16,y//16,z//16);i=(y%16)*256+(z%16)*16+x%16
  if p not in vols:vols[p]=ac.MicroVolume()
  vols[p].cells[i]=mat;blocks[p]=ac.HOST_STATE
 for (d,y,u),mat in c.cells.items():
  if 2<=y<DECK:put(R-U0-u,y,WALL-d,mat)
 # Close the missing facade-to-side returns at the exact source footprint edge.
 fp=Polygon(spec['footprint_ud_m']);ring=fp.boundary.buffer(.09375,cap_style=2,join_style=2)
 for u in range(-2,W+3):
  for dep in range(10,25):
   if ring.covers(Point((u+.5)/16,(dep+.5)/16)):
    for y in range(2,DECK):put(R-U0-u,y,Z0+dep,M['body'])
 for p in list(vols):
  if not any(vols[p].cells):vols.pop(p);blocks.pop(p,None)
 coords=np.array(list(blocks));lo=coords.min(0);hi=coords.max(0);bounds=tuple(lo.tolist()+hi.tolist());writer=NBTWriter()
 entities=[ac.tile_entity_payload(writer,tuple(p[i]-lo[i] for i in range(3)),v) for p,v in sorted(vols.items())]
 target=OUT/(NAME+'.litematic')
 print('Exporting source-led facade assemblies',len(vols),'hosts',flush=True)
 stats=write_single_region_litematic(target,blocks,bounds,REGION,NAME,'Isolated photo-led facade assemblies; native glazed windows, fine profiles and connected returns. Source proportions provisional, no site integration.',data_version=4903,tile_entity_payloads=entities)
 rb,rv,_=load_cells(target,REGION)
 changed=0;outside=0
 for p in baseline.keys()|rv.keys():
  a=baseline[p][1] if p in baseline else [None]*4096;b1=rv[p].cells if p in rv else [None]*4096
  for i,(a0,b0) in enumerate(zip(a,b1)):
   if a0!=b0:
    changed+=1
    if not allowed(p[0]*16+(i&15),p[1]*16+(i>>8),p[2]*16+((i>>4)&15)):outside+=1
 def get(d,y,u):
  x=R-U0-u;z=WALL-d;p=(x//16,y//16,z//16)
  return rv[p].cells[(y%16)*256+(z%16)*16+x%16] if p in rv else None
 aperture=[]
 for q in opens:
  l,r,yb,yt=q['bounds'];face=q['face'];pane=0;blockers=0
  for u in range(l+2,r-2):
   for y in range(yb+2,yt-2):
    # Exclude intentional sash bars, then verify the whole remaining viewing ray.
    if any(c.cells.get((d,y,u)) in (M['white'],M['white_shade']) for d in range(face-1,face+4)):continue
    pane+=1
    if get(face-3,y,u)!=M['glass']:blockers+=1
    if any(get(d,y,u) is not None for d in range(face-2,face+5)):blockers+=1
  aperture.append({'name':q['name'],'pane_rays':pane,'bad_rays':blockers})
 checks={'exact_block_map':rb=={p:canonical_state(s) for p,s in blocks.items()},'exact_astra':set(rv)==set(vols) and all(rv[p].cells==v.cells and rv[p].original==v.original for p,v in vols.items()),'all_changes_in_front_scope':outside==0,'all_window_assemblies_clear_except_glazing':all(a['pane_rays']>10 and a['bad_rays']==0 for a in aperture),'source_footprint_unchanged':spec['footprint_ud_m']==json.loads((LAB/'lab_v002.json').read_text())['footprint_ud_m'],'parent_not_modified':hashlib.sha256(PARENT.read_bytes()).hexdigest()=='29630dc9b4ccd069374e60dfd75edaed7b93c88a7600e0d0b4d39b2f2bea9557'}
 from scipy.ndimage import label
 opaque=np.zeros((208,208,336),bool)
 for (x,y,z),v in rv.items():
  v1=np.array([m is not None and 'glass' not in m for m in v.cells]).reshape(16,16,16).transpose(2,0,1)
  opaque[x*16:x*16+16,y*16:y*16+16,z*16:z*16+16]=v1
 _,components=label(opaque)
 checks['one_connected_opaque_structure']=components==1
 report={**stats,'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'changed_microcells':changed,'outside_scope_changes':outside,'apertures':aperture,'features':{k:features.count(k) for k in set(features)},'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'visual_status':'USER_REVIEW_REQUIRED','geometry_accepted':False,'integration_allowed':False,'limits':spec['remaining_unknowns'],'glazing_policy':'Replaces the old no-glass diagnostic with accepted Redfield native glazing; no claim of matched optical properties.'}
 (OUT/(NAME+'_validation.json')).write_text(json.dumps(report,indent=2)+'\n')
 if not all(checks.values()):raise RuntimeError(checks)
 # Exact decoded front slice and oblique exposed-face preview (Redfield meshing helper).
 render(rb,rv,OUT)
 print(json.dumps({'status':report['status'],'sha256':stats['sha256'],'changed_cells':changed,'checks':checks,'apertures':aperture},indent=2))
 return report

def render(blocks,vs,out):
 mats=sorted({m for v in vs.values() for m in v.cells if m is not None});ids={m:i+1 for i,m in enumerate(mats)}
 a=np.zeros((336,208,208),np.uint16)
 for (x,y,z),v in vs.items():
  vol=np.array([ids.get(m,0) for m in v.cells],dtype=np.uint16).reshape(16,16,16).transpose(1,0,2)
  a[z*16:z*16+16,y*16:y*16+16,x*16:x*16+16]=vol
 lut=[(238,240,237)]
 for m in mats:
  if m.startswith('astra_microblocks:rgb_'):h=m[-6:];lut.append(tuple(int(h[j:j+2],16) for j in (0,2,4)))
  else:lut.append((99,123,131))
 lut=np.array(lut,np.uint8)
 # Full front-facing silhouette; transparent glass represented with a tint, not optical rendering.
 occupied=a!=0;dep=occupied.argmax(0);yy,xx=np.indices(dep.shape);im=lut[a[dep,yy,xx]];im[~occupied.any(0)]=lut[0]
 pic=Image.fromarray(im[::-1,::-1]).resize((832,832),Image.Resampling.NEAREST);pic.save(out/(NAME+'_front.png'))
 # Render three visible surfaces from actual decoded voxels, not an idealized elevation.
 a=a[::-1];faces=[]
 for axis in range(3):
  v=np.moveaxis(a,axis,0)
  for i in range(len(v)):
   nxt=v[i+1] if i+1<len(v) else np.zeros_like(v[i]);surface=np.where((v[i]!=0)&(nxt==0),v[i],0)
   if not np.any(surface):continue
   for x0,y0,x1,y1,mat in rectangles(surface):
    pts=[]
    for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
     p=[y,x];p.insert(axis,i+1);pts.append(p)
    faces.append((np.mean([p[0]+.34*p[2]+.26*p[1] for p in pts]),axis,mat,pts))
 def project(p):d,y,u=p;return np.array([-u+.34*d,-y+.12*u+.26*d])
 pp=np.array([project(p) for _,_,_,vs1 in faces for p in vs1]);mn=pp.min(0);span=pp.max(0)-mn;scale=min(1040/span[0],940/span[1])
 im=Image.new('RGB',(1160,1080),tuple(lut[0]));dr=ImageDraw.Draw(im)
 # Depth-buffer the exposed rectangles. Painter sorting by face-centre alone can
 # incorrectly paint a large pane over foreground muntins in an oblique view.
 pixels=np.array(im);zb=np.full(pixels.shape[:2],-np.inf,np.float32)
 for _,axis,mat,pts in faces:
  q=np.array([(project(p)-mn)*scale+[60,72] for p in pts])
  depth=np.array([p[0]+.3008*p[1]+.34*p[2] for p in pts])
  matrix=np.c_[q[:3],np.ones(3)]
  if abs(np.linalg.det(matrix))<1e-9:continue
  coeff=np.linalg.solve(matrix,depth[:3])
  x0=max(0,math.floor(q[:,0].min()));x1=min(pixels.shape[1],math.ceil(q[:,0].max()))
  y0=max(0,math.floor(q[:,1].min()));y1=min(pixels.shape[0],math.ceil(q[:,1].max()))
  if x0>=x1 or y0>=y1:continue
  yy,xx=np.mgrid[y0:y1,x0:x1];xx=xx+.5;yy=yy+.5
  cross=[]
  for j in range(4):
   r0=q[j];r1=q[(j+1)%4]
   cross.append((r1[0]-r0[0])*(yy-r0[1])-(r1[1]-r0[1])*(xx-r0[0]))
  cross=np.array(cross);inside=(cross>=-1e-6).all(0)|(cross<=1e-6).all(0)
  dep=coeff[0]*xx+coeff[1]*yy+coeff[2]
  visible=inside&(dep>zb[y0:y1,x0:x1])
  zb[y0:y1,x0:x1][visible]=dep[visible]
  pixels[y0:y1,x0:x1][visible]=(lut[mat]*[.84,1,.68][axis]).astype(np.uint8)
 im=Image.fromarray(pixels);dr=ImageDraw.Draw(im)
 dr.text((25,22),'1040 LAB v003 - decoded full-building geometry; glazing shown as opaque tint',fill=(30,45,50))
 dr.text((25,1040),'Front assemblies corrected. Side/rear/roof envelope is retained provisional geometry, NOT accepted.',fill=(30,45,50))
 im.save(out/(NAME+'_oblique.png'))

if __name__=='__main__':main()
