# Lombard v016 — lower terrain gap-fill repair

v015's tall fin (A), lower shoulder (B), and smaller upstream tip (C) are
reconstruction/interpolation artifacts, category **(c)**. They are not supported
bare-earth landforms. The temporary review clip exposed the erroneous filled
surface; adding endpoint pavement did not repair that upstream surface.

## Evidence before geometry

The user's 30.55-second Minecraft capture was inspected at 9, 12, and 15 seconds.
The two principal shapes were matched to the lower north-side terrain patches.
The additional upstream tip was checked as the same failure class. Coordinates
below are in the existing v015 frame: EPSG:3717-derived local X east, Z south.

| Area | Probe X,Z m | Old raw grid, NAVD88 m | Original class-2 TIN m | DWR 2025 DEM m | Ground returns within 2m |
|---|---|---:|---:|---:|---:|
| A — tall fin | 120.5,-30.0 | 62.623 | 56.915 | 56.020 | 7 |
| B — lower shoulder | 131.5,-29.5 | 56.784 | 53.664 | 53.139 | 2 |
| C — upstream tip | 99.5,-26.5 | 64.300 | 62.137 | 61.418 | 24 |

All three probe grid cells originally had **no measured ground return**. Their
nearest actual class-2 observations are 1.11, 1.17, and 0.72m away respectively.
The legacy algorithm filled its own input grid while iterating from north to
south. Each synthetic height could then become a donor for the next empty cell.
It reproduces the cached grid within 0.000035m. Reversing its scan, without
changing any returns, produces 56.345, 53.284, and 61.924m at A/B/C. That large
order dependence establishes a processing defect.

The 2010 cloud only exposes classes 1,2,7,12 in this ROI. Non-ground returns
cannot be confidently relabeled as trees versus buildings. Private aerial and
Commons street references show canopy and adjacent houses, plausibly explaining
ground-return gaps; they do not establish a specific misclassified tree.
The false heights persist even though the grid input filters to class 2.

The DWR 2025 DEM corroborates absence of the fins. It uses NAVD88 US survey feet;
samples were transformed into the existing horizontal frame and converted by
1200/3937. The 0.52–0.89m differences from the 2010 TIN remain recorded, not
silently reconciled. Different acquisition dates, geodetic realizations,
interpolation and landscaping can contribute. No DWR elevations replace the
accepted road or the project's vertical zero.

Sources and exact request are in the v016 reference manifest. The new main
branch was inspected at `6a10802`, including road-outward guidance and the DWR
sampling helper. Its separate `lombard_street_sf` candidate frame/centerline was
not substituted into the accepted `lombard_sf` v015 review build.

## Narrow correction

Start by decoding the exact validated v015 parent. Repair only excessive
synthetic heights in the three documented investigation boxes; preserve every
observed grid bin. Original-point triangulation has a 3m nearest-ground limit,
20m longest triangle-edge limit, and no extrapolation outside the convex hull.
Values without adequate support stay unresolved. Actual probe triangle edges
are only 2.06–4.66m. Keep the original 1.5m box smoothing and shallow four-cell
shell. A 0.125–0.5m transition in the correction weight avoids a threshold seam.

Only existing parent terrain columns are rebuilt. Changes are 17,970 columns
(70.195m²), with a maximum quantized lowering of 5.75m. Another 1,875 dependent
edge/wall cells inherited false elevations and are recalculated using the same
existing rule. All 962,398 occupied v009 road/curb cells remain identical.
Total changed microcells: 131,507. No boundary face, new layer, or footprint
expansion is introduced. The full v015 region bounds are retained so a paste
including air clears removed hosts.

The resulting corrected columns also pass a separate point-support gate:
maximum absolute residual 0.554m, below the explicit 1.0m review threshold.
This is a conservative rejection threshold, not a target accuracy or permission
to smooth real supported terrain. The geometric inference remains provisional
until the user's flyaround.

## Prevention and validation

- `pipeline/terrain/ground_support.py`: immutable observations, deterministic
  TIN interpolation, bounded support and a fail-closed residual gate.
- The acquisition entrypoint now uses this helper; it no longer recursively
  fills gaps. Unsupported samples raise before geometry generation. The legacy
  raw cache is intentionally preserved for reproducing accepted v015 geometry.
- `pipeline/terrain/audit_lombard_ground_v016.py`: exact source hashes, legacy
  reproduction, scan-order diagnostic, measured-bin preservation, per-area QA.
- v016 generator: exact parent hash, local scope, accepted-cell protection,
  corrected-column support check, original bounds, and exact export readbacks.
- CI tests reject unsupported fins and extrapolation, preserve missingness,
  and require order-independent interpolation.

Run from the branch root:

```text
python pipeline/terrain/audit_lombard_ground_v016.py
python pipeline/reconstruction/generate_lombard_terrain_repair_v016.py
python -m unittest discover -s tests -p test_ground_support.py -v
```

Exact Litematica block readback, Astra host set, microcells, original material,
registration marker, and accepted road/curb preservation pass. Stop at
`TERRAIN_REPAIR_V016_FLYAROUND_REQUIRED`.

Load `Lombard_Terrain_Repair_Astra_v016.litematic` at the same v015 origin, with
rotation 0, mirror none, replace ALL and air included. Check A/B/C and the two
locally shortened wall tops. Do not expand stairs, planting or buildings until
this review is accepted.
