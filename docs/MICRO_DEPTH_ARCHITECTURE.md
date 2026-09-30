# EarthForge Microblock Depth Architecture

The previous Micro-Only pass proved that 1/16 geometry can carry a full
building, but it still read too much like a decorated vertical sheet.

This pass changes the architectural model from **surface detail** to
**sectional depth**.

## Core rule

A facade feature is not complete until EarthForge knows both:

1. its shape in elevation; and
2. its depth relative to the primary wall field.

## Depth stack

For an east-facing Main Street facade, EarthForge now treats the street-facing
boundary as a stack of measured planes:

```text
inside building                                         street
     ←                                                       →

recess / shadow plane
        wall body plane
              outer wall face
                    trim projection
                         sign/fascia projection
                              cornice / awning projection
```

The exact cell values are stored in the building spec.

## 621 v003 depth targets

All values are in Astra 1/16-block cells.

- brick body thickness: 5 cells
- storefront opening reveal: 8 cells
- storefront lattice plane: 8 cells behind outer face
- door plane: 9 cells behind outer face
- upper-window reveal: 7 cells
- upper lattice plane: 7 cells behind outer face
- trim projection: 3 cells into the exterior host
- sign fascia projection: 7 cells
- cornice projection: 13 cells
- awning projection: 15 cells
- sill/header projection: 5 cells
- pilaster projection: 6 cells

This is intentionally strong. Previous Blackglass / Tide Hall / Batcave testing
showed that projection/recess hierarchy and player-eye readability matter more
than simply increasing decorative density.

## Visual-density rule

v003 uses fewer, stronger forms:

- 3 upper windows;
- 2 storefront display bays;
- one centered door pair;
- 3 cornice bracket groups;
- restrained parapet ornaments.

This avoids the “extremely busy” failure mode from earlier build testing.

## No glass

Window voids remain open.

Microblock trim, lattice, mullions, transoms, sills and headers are present,
but no vanilla or Astra glass is generated.
