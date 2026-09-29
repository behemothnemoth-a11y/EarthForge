# Redfield POC 001 Acquisition

## Source hierarchy

EarthForge should prefer structured geometry for geometry and imagery for
appearance.

Initial source classes:

1. official City of Redfield maps;
2. South Dakota DOT CADD mapping;
3. OpenStreetMap geometry as a machine-readable starting layer;
4. Google Maps / Street View as visual and placement verification;
5. Redfield City's 21 Feet of History archive as an independent facade /
   storefront reference.

## Current capture window

The current repository bounds are **provisional** and intentionally wider than
the final build. They are centered around the 600 block of Main Street and
should be tightened after the first acquisition review.

Do not interpret the provisional bounding polygon as a surveyed property line.

## First machine-readable pull

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_FETCH_BASE.ps1
```

This downloads an OpenStreetMap/Overpass snapshot to the ignored local
`downloads/` directory and writes normalized review GeoJSON for:

- buildings;
- roads / paths;
- surface context such as parking and landuse.

Generated geometry is evidence, not final truth. It must be compared against
official mapping and visual reference before Minecraft generation.

## Google reference work

Raw Google imagery should remain local. EarthForge should commit source
metadata, query URLs, panorama identifiers when available, notes, and
confidence—not raw captures unless redistribution is clearly permitted.
