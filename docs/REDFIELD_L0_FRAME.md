# Redfield POC 001 — L0 Frame

Drop 0003 turns the broad review acquisition into the first reproducible
EarthForge block frame.

## Frame derivation

The generator derives the POC frame from the imported geometry:

- **south:** Main Street × 7th Avenue centerline intersection;
- **north:** Main Street × 6th Avenue centerline intersection;
- **west:** nearest qualifying north/south service alley west of Main;
- **east:** nearest qualifying north/south service alley east of Main.

This makes the block selection reproducible from source geometry instead of
depending on a hand-drawn crop.

## Minecraft orientation

EarthForge now uses the conventional Minecraft horizontal orientation:

- `+X = east`
- `-X = west`
- `+Z = south`
- `-Z = north`

The project anchor for POC 001 is the Main Street / 7th Avenue centerline
intersection.

The anchor's local horizontal coordinate is:

```text
X = 0
Z = 0
```

The 6th Avenue end of the test block therefore has negative Z values.

## L0 output

The generator produces:

- selected block footprints in WGS84;
- selected and clipped transport geometry;
- a local-meter geometry model;
- an unmatched building queue ordered by side and south-to-north position;
- a Minecraft diagnostic block-plan CSV;
- an SVG plan preview;
- a generation report;
- a locked frame descriptor.

The diagnostic block plan is **not yet a Litematica file**. Its purpose is to
prove that the geometry, scale, orientation and selection are sane before
packing the same cells into NBT/Litematica.

## Address matching

Drop 0003 does not guess addresses from footprint order.

The address inventory and selected geometry are kept separate until storefront
references provide enough evidence to match them confidently.

## Litematica registration

The future Litematica exporter will use the registration convention already
defined by EarthForge.

Drop 0003 reserves a safe registration reference point outside the real block
geometry. When Litematica export begins, that reference will be translated to
the schematic placement origin so a later revision can be aligned while the
player stands on the existing marker block.
