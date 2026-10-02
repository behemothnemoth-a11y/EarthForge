"""Reproduce and diagnose the v015 gap-fill defect before applying a local fix.

Uses the existing 2010 source returns in the locked v015 frame. The newer DWR
DEM is independent corroboration, not a replacement vertical datum or road.
"""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipeline.terrain.ground_support import interpolate_ground,observed_grid

PROJECT=ROOT/'projects/lombard_sf'
RAW=PROJECT/'downloads/raw'
AREAS=[
    {'id':'A','name':'tall fin','bounds':[113,-33,124,-25],'probe':[120.5,-30]},
    {'id':'B','name':'lower shoulder','bounds':[124,-35,138,-24],'probe':[131.5,-29.5]},
    {'id':'C','name':'smaller upstream tip','bounds':[96,-30,103,-24],'probe':[99.5,-26.5]},
]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def legacy_fill(observed,reverse=False):
    grid=observed.copy()
    missing=np.argwhere(~np.isfinite(grid))
    if reverse:missing=missing[::-1]
    for iz,ix in missing:
        for rad in range(1,17):
            block=grid[max(0,iz-rad):iz+rad+1,max(0,ix-rad):ix+rad+1]
            values=block[np.isfinite(block)]
            if len(values):grid[iz,ix]=np.median(values);break
    return grid


def derive():
    grid_file=RAW/'lombard_poc001_ground_grid_050cm_v001.npz'
    points_file=RAW/'lombard_poc001_lidar_roi_v001.npz'
    d=np.load(grid_file);old=d['grid'].astype(float)
    meta={k:float(d[k]) for k in ['xmin','xmax','zmin','zmax','res']}
    p=np.load(points_file);keep=p['classification']==2
    pts=np.c_[p['x'][keep],p['z'][keep]];heights=p['elev'][keep]
    observed=observed_grid(pts,heights,old.shape,meta['xmin'],meta['zmin'],meta['res'])
    xx,zz=np.meshgrid(meta['xmin']+np.arange(old.shape[1])*meta['res'],meta['zmin']+np.arange(old.shape[0])*meta['res'])
    local=np.zeros(old.shape,bool)
    for area in AREAS:
        x0,z0,x1,z1=area['bounds'];local|=(xx>=x0)&(xx<=x1)&(zz>=z0)&(zz<=z1)
    values,quality=interpolate_ground(pts,heights,np.c_[xx[local],zz[local]])
    tin=np.full(old.shape,np.nan);tin[local]=values
    nearest=np.full(old.shape,np.nan);nearest[local]=quality['nearest_ground_m']
    edge=np.full(old.shape,np.nan);edge[local]=quality['longest_triangle_edge_m']
    missing=~np.isfinite(observed)
    excess=old-tin
    # The evidence is for excessive invented height, not a global surface reset.
    # A smooth 0.125..0.5 m ramp avoids an arbitrary threshold seam.
    weight=np.clip((excess-.125)/.375,0,1);weight=weight*weight*(3-2*weight)
    changed=local&missing&np.isfinite(tin)&(excess>.125)
    patched=old.copy();patched[changed]=old[changed]-weight[changed]*excess[changed]
    original_preserved=bool(np.array_equal(patched[~missing],old[~missing]))
    recreated=legacy_fill(observed);reversed_grid=legacy_fill(observed,True)
    smooth_old=uniform_filter(old,3,mode='nearest')
    smooth_new=uniform_filter(patched,3,mode='nearest')
    report={'schema_version':1,'source_points_sha256':sha(points_file),'legacy_grid_sha256':sha(grid_file),
      'source_class':2,'ground_points':int(keep.sum()),'cause':'recursive in-place gap fill propagates synthesized elevations; clipping exposes the erroneous surface',
      'classification':'c: reconstruction/interpolation artifact; canopy contributes to observation gaps, not proven class-2 tree contamination',
      'legacy_reproduction_max_abs_m':float(np.nanmax(abs(recreated-old))),
      'observed_bins_unchanged':original_preserved,'changed_missing_grid_bins':int(changed.sum()),
      'support_limits':{'nearest_ground_m':3,'longest_triangle_edge_m':20,'outside_convex_hull':'reject'},
      'smoothing':'same 3x3 / 1.5m box as v015','areas':[]}
    for area in AREAS:
        x,z=area['probe'];ix=round((x-meta['xmin'])/meta['res']);iz=round((z-meta['zmin'])/meta['res'])
        near=np.hypot(pts[:,0]-x,pts[:,1]-z)<=2
        report['areas'].append({**area,'probe_observed_bin':bool(not missing[iz,ix]),
          'legacy_raw_navd88_m':float(old[iz,ix]),'original_point_tin_navd88_m':float(tin[iz,ix]),
          'legacy_reversed_scan_navd88_m':float(reversed_grid[iz,ix]),
          'nearest_ground_m':float(nearest[iz,ix]),'longest_triangle_edge_m':float(edge[iz,ix]),
          'ground_returns_within_2m':int(near.sum()),'nearby_ground_range_m':[float(heights[near].min()),float(heights[near].max())],
          'old_smoothed_navd88_m':float(smooth_old[iz,ix]),'corrected_smoothed_navd88_m':float(smooth_new[iz,ix])})
    if not original_preserved or report['legacy_reproduction_max_abs_m']>.02:
        raise RuntimeError('Source lineage check failed; do not generate')
    if any(not np.isfinite(a['original_point_tin_navd88_m']) for a in report['areas']):
        raise RuntimeError('Suspect probe lacks interpolation support')
    return smooth_old,smooth_new,meta,report,patched,changed


if __name__=='__main__':
    _,_,_,report,_,_=derive()
    print(json.dumps(report,indent=2,allow_nan=False))
