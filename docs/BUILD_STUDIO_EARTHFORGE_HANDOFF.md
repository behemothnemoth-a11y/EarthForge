# Build Studio → EarthForge Handoff

EarthForge is the world/geospatial authority.

Build Studio should be able to refine one building without deciding where that
building belongs in the town.

## EarthForge supplies

- project/building ID;
- WGS84/source footprint;
- EarthForge local footprint;
- Minecraft transform;
- facade side;
- address / site name;
- evidence URLs and confidence;
- current block-only architecture program;
- micro-overlay permission zones;
- interior program seed.

## Build Studio may return

- corrected facade segmentation;
- window/door measurements;
- parapet silhouette;
- roof-form evidence;
- palette/material suggestions;
- micro-overlay primitives;
- uncertainty notes.

## EarthForge retains authority over

- world position;
- project orientation;
- real-world scale;
- neighboring-building alignment;
- registration origin;
- final Litematica export.

The generated `build_studio_jobs_v001.json` is the first machine-readable
handoff package for the Redfield POC.
