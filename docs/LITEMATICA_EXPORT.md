# EarthForge Litematica Export

EarthForge's first Litematica export is intentionally an L0 diagnostic.

It contains a single flat layer representing the accepted L0 block-plan cells
plus the permanent revision-registration block.

It does **not** yet contain:

- extruded buildings;
- facade reconstruction;
- interiors;
- Microblocks.

## Placement reference

The schematic origin is the player's feet while standing on the yellow
registration block.

In schematic coordinates:

```text
player feet / placement origin = (0, 0, 0)
yellow registration block     = (0,-1, 0)
```

The rest of the L0 diagnostic layer is also placed at `Y=-1`, so the top of
the diagnostic surface is level with the player's feet.

For a later revision:

1. stand on the existing yellow registration block;
2. set the new schematic placement origin to the player's current block
   position;
3. keep rotation at zero and mirror disabled.

Because EarthForge preserves the same registration reference and project
orientation across revisions, no visual dragging/alignment should be needed.

## Validation

The exporter immediately reopens the generated gzip NBT, unpacks the entire
palette-index array, compares every non-air block against the source plan, and
verifies the yellow marker at schematic `(0,-1,0)`.
