# EarthForge Pipeline

## Stage 0 — Project definition
- select project bounds
- select a world anchor
- define horizontal and vertical Minecraft scale
- define source and working CRS
- define export target

## Stage 1 — Acquisition
Collect or reference:
- roads
- building footprints
- terrain/elevation
- parcel or lot context when useful
- public geographic datasets
- reference imagery identifiers and notes

Raw licensed imagery should remain local unless redistribution is explicitly allowed.

## Stage 2 — Georeference
Convert source coordinates into a local project coordinate system and then
Minecraft X/Z coordinates.

## Stage 3 — Terrain
Create terrain surface, grades, drainage-scale features, major vegetation zones,
and cut/fill decisions required for playable Minecraft terrain.

## Stage 4 — Roads and lots
Generate road centerlines, lanes, curbs, sidewalks, parking areas, alleys, and
lot boundaries.

## Stage 5 — Building massing
Use footprints, height evidence, roof evidence, and references to make
block-scale building shells.

## Stage 6 — Build Studio reconstruction
Use image/reference evidence to reconstruct facade organization, openings,
roof forms, visible materials, and distinctive architectural features.

## Stage 7 — Microblock refinement
Use Astra Microblocks for details that would otherwise be lost at one-block
resolution: mullions, trim, signs, railings, cornices, shaped roof edges, etc.

## Stage 8 — Export
Targets may include:
- Minecraft world region
- Litematica
- Sponge schematic
- project preview meshes

## Stage 9 — Validation
Compare:
- footprint alignment
- road spacing
- building heights
- facade rhythm
- landmark recognition
- player-scale usability
