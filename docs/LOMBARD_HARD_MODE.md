# Lombard Street Hard-Mode Reconstruction Doctrine

Target: the famous crooked block of Lombard Street between Hyde Street (top/west)
and Leavenworth Street (bottom/east), plus the immediate intersections and bordering
context needed for the block to read correctly.

## Why this project exists

This is an EarthForge stress test for terrain-led urban reconstruction. Redfield
showed that facade, footprint and roof cannot be generated independently and glued
together afterward. Lombard is deliberately structured so that the site geometry is
the first authority and all later architecture must physically explain itself against
that geometry.

## Locked L0/L1 facts

- Coordinate anchor: Hyde/Lombard centerline, OSM node 65360287.
- Scale: 1 meter = 1 Minecraft block.
- Vertical datum: NAVD88.
- Measured Hyde-to-Leavenworth endpoint drop: ~32.85 m.
- Straight control distance: ~146.78 m.
- OSM crooked centerline path length: ~197.39 m.
- Hairpin count: 8.
- Centerline turn radii from source-derived audit: approximately 5.7–6.3 m.
- Road direction: one-way eastbound/downhill.
- L1 road/terrain grade is source-derived from classified LiDAR, not hand-shaped.

## Hard stop gates

### Gate A — L1 terrain/hardscape
User must inspect in Minecraft and approve:
- overall slope and total drop;
- all 8 hairpins;
- turn radii and road width;
- north/south stair runs and landings;
- retaining/planter edge placement;
- curb/sidewalk relationship;
- project scale.

No house geometry may be generated before this gate passes.

### Gate B — L2 building massing
After L1 approval, house massing may use:
- DataSF building footprints;
- LiDAR ground/first-return height statistics;
- OSM addresses/heights where available;
- aerial/street-level roof-form verification.

User must approve building placement, base elevation, stories, roof volume and
driveway/garage relationship before facade detailing.

### Gate C — L3 architectural refinement
Only after L2 approval:
- bay windows;
- garage openings;
- stairs/railings;
- facade trim;
- roof-edge detail;
- planting/hedge refinement;
- lamps/signage and other small civic geometry.

## Source precedence

Geometry:
1. classified LiDAR / official city GIS;
2. official ROW / street / building datasets;
3. OSM detailed hardscape;
4. aerial imagery;
5. street-level imagery for visual correction.

Appearance:
1. current street-level imagery;
2. current freely licensed/reference photos;
3. aerial imagery;
4. historical imagery.

A source that is stronger for one question is not automatically stronger for another.
For example, LiDAR can set roof height but does not get to invent a facade or roof
shape.

## Microblock policy

Astra Microblocks 0.7.0 is not a license to add unsupported detail. It is used where
the evidence requires sub-block resolution:

- curved switchback edges;
- fractional road grade;
- retaining-wall caps;
- stair nosings/landings;
- planter lips;
- thin railings;
- hedge shaping;
- facade/roof transitions after later gates.

Bulk terrain and building mass stay full-block when micro-resolution adds no
evidence-driven value.

## Rejection rule

If an in-game result looks architecturally or spatially wrong, do not patch over it
with more detail. Return to the earliest wrong layer, record the discrepancy, and
rebuild from that layer.

## Current state

The current review candidate is:

projects/lombard_sf/outputs/l1_hardscape_v002/
Lombard_POC_001_L1_Terrain_Hardscape_v002.litematic

L2 building source truth has been prepared for research only. It is not authorization
to generate house geometry before L1 approval.
