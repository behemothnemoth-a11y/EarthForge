# Litematica Revision Registration Convention

EarthForge exports must be easy to replace with a newer revision without
manually dragging the placement back into alignment each time.

## Registration block

Every Litematica revision will include one dedicated stand-on registration
block outside the real reconstruction.

Default block:

`minecraft:yellow_concrete`

The registration block is not part of the real-world reconstruction.

## Player-feet reference

EarthForge will define the placement reference at the player's feet while the
player stands on the registration block.

Exporter convention:

```text
placement reference / schematic origin: (0, 0, 0)
registration block offset:              (0,-1, 0)
```

This means the player can stand on the existing registration block and use
that position as the reference for the next schematic revision.

## Invariants

Every revision of the same EarthForge export must preserve:

- the same project orientation;
- no mirror;
- the same registration-block offset;
- the same world-to-project transform;
- the same export translation unless the export boundary is intentionally
  versioned;
- stable region-origin behavior.

A schematic revision must never silently rotate, mirror, or choose a different
registration reference.

## Why one block is sufficient

The stand block solves translation. Rotation is controlled by project metadata
and is fixed by the exporter, so the player should not need a second physical
orientation marker.

If a future exporter cannot guarantee fixed orientation, EarthForge may add a
secondary north marker, but POC 001 starts with the single-block convention.
