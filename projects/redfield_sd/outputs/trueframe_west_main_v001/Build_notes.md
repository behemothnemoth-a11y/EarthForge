# Redfield West Main True-Frame v001

This is the first combined review candidate that puts the accepted 617-627
photo facades back into the locked EarthForge geographic frame.

## What changed

The earlier facade strip was a 50-block visual study. v001 resamples the exact
accepted facade geometry/materials into the mapped **45.5625 m** combined
frontage:

- 625-627: 15.875 m
- 623: 14.5625 m
- 621: 7.875 m
- 617-619: 7.25 m

The storefronts are also moved from the standalone x=-4 study plane to their
actual west-Main footprint fronts near local x=-15.6 m.

No facade is redesigned in this pass. The accepted city-archive-photo geometry
is nearest-neighbor resampled so openings, signs, materials, glass and fine
Astra detail survive the scale correction.

## Vertical fit and roofs

Facade visible heights are fitted to the 2012 LiDAR front-return bands plus
the photographed parapet morphology:

- 625-627: 8.0 m visible facade
- 623: 5.5 m
- 621: 10.0 m
- 617-619: 7.0 m

The building bodies use their true mapped depth. Side/rear shells are regular
brick blocks where full-block precision is sufficient.

The old uniform roof Y=10 deck is gone. Each building now uses an x-dependent
LiDAR modal roof profile. Examples:

- 625-627 roof surface: about Y 6.19-6.56
- 623: about Y 4.19-4.44
- 621: about Y 5.44-10.31, reflecting its stepped rear-to-front mass
- 617-619: about Y 5.31-7.44

Fractional roof surfaces and roof steps use Astra Microblocks.

## Ground

The accepted Main Street MicroGrade is included in this schematic, so this is
a combined test rather than an overlay that can accidentally erase the road.
Building facade bases are fitted to the MicroGrade sidewalk elevation for each
frontage.

## Validation

- exact block-map readback: PASS
- exact Astra cell/material readback: PASS
- geographic frontage: PASS
- MicroGrade carried forward: PASS
- old uniform roof deck removed: PASS
- Astra hosts: 6,669
- occupied microcells: 11,071,226
- full shell blocks: 1,695
- live Minecraft review: PENDING

Use the permanent Redfield yellow registration marker, rotation 0, mirror none,
Replace Blocks ALL.
