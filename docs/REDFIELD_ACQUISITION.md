# Redfield POC 001 Acquisition

## Source hierarchy

EarthForge uses structured geometry for coordinates and imagery for appearance,
with cross-checks when sources disagree.

Current source classes:

1. South Dakota DOT CADD mapping.
2. OpenStreetMap geometry as a machine-readable starting layer.
3. Esri / orthophoto imagery for roofs, rear form and surface context.
4. SDGS / USGS LiDAR for terrain and height checks.
5. Google Maps / Street View for current street-level verification.
6. Mapillary and KartaView for alternate street-level views when available.
7. Redfield City's 21 Feet of History archive for storefront evidence.
8. Library of Congress Sanborn maps for historical lots and building form.
9. Spink County mapping/GIS as an additional local-government cross-check.

See `REDFIELD_MULTISOURCE_ACQUISITION_V001.md` for the active acquisition plan.
## Machine-readable OSM pull

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_FETCH_BASE.ps1
```

This writes ignored local OSM/Overpass downloads and normalized review GeoJSON.

Generated geometry is evidence, not final truth. It must be compared against
official mapping and visual reference before Minecraft generation.

## Multisource public pull

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_FETCH_MULTISOURCE.ps1
```

This currently acquires the Redfield SDDOT PDF/DGN/DWG and the seven-sheet
1916 Library of Congress Sanborn preview set.
## Street-level reference work

Street-level imagery is now a multi-provider layer rather than a Google-only
step. Use Google Street View first, then check Mapillary and KartaView for
alternate angles/dates.

Raw licensed imagery stays local. Commit source metadata, panorama/image IDs,
dates, URLs, headings, notes, confidence and derived geometry, not raw captures
unless redistribution is clearly permitted.

Capture targets are stored in:

`projects/redfield_sd/source_manifests/street_level_capture_targets_v001.json`

The source stack registry is:

`projects/redfield_sd/source_manifests/redfield_multisource_acquisition_v001.json`

## Large GIS data

Do not download county-wide LiDAR or NAIP by default. First identify the tiles
or extract that intersect the 600 block. Record the dataset/version and preserve
the original CRS/metadata before transforming into the locked EarthForge frame.
