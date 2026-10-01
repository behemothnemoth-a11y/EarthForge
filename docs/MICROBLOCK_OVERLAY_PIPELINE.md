# EarthForge Microblock Overlay Pipeline

EarthForge now treats Astra Microblocks as a **precision overlay layer** rather
than a replacement for ordinary Minecraft construction.

## Resolution

Astra uses a persistent **16 × 16 × 16** cell grid inside one Minecraft block.

EarthForge vocabulary:

```text
normal block shell
      ↓
micro overlay host
      ↓
4096 addressable cells
      ↓
cornice / mullion / pilaster / frame / thin ledge / surround
```

## Structural rule

Normal Minecraft blocks remain responsible for:

- building mass;
- floors;
- roofs;
- navigation;
- primary walls;
- structural openings;
- room envelopes.

Astra Microblocks are responsible for:

- cornice projection;
- parapet edge shaping;
- window mullions;
- transoms;
- thin pilasters;
- sign frames;
- door surrounds;
- facade dividers;
- narrow ledges;
- scale correction where one vanilla block is too coarse.

This keeps EarthForge regeneratable. Removing the micro overlay should leave a
valid, recognizable building.

## Direct Astra export

EarthForge writes real Astra hosts into Litematica:

```text
block state:
astra_microblocks:test_host[orientation=0]

block entity:
astra_microblocks:test_host
```

The block entity contains:

- `grid_format_v1`
- 64 occupancy longs (`grid_0` … `grid_63`)
- `materials_v2`
- `volume_v4`
- local palette materials
- packed 4096-cell material indices
- saved Astra orientation

The serialization path must match the currently supported Astra Microblocks contract. Lombard requires Astra Microblocks **0.7.0 or newer compatible serialization**, and exact block-entity/microcell readback is required before promotion.

## v006 limits

The first Redfield micro pass is deliberately bounded.

- priority buildings get mullions + pilasters + cornices;
- other storefronts get light cornice/trim refinement only;
- micro hosts have a global budget;
- glass remains vanilla because Astra's current material catalog intentionally
  excludes transparent glass;
- micro mullions sit in the mostly-empty block immediately in front of vanilla
  glazing.

## Compatibility test

The v006 build creates a separate:

`Astra_EarthForge_Compatibility_v001.litematic`

Paste that first if desired. It contains a small set of Astra hosts with:

- thin cornice;
- vertical mullion;
- horizontal transom;
- projecting pilaster;
- mixed-material frame.

If those shapes render correctly, the integrated Redfield v006 uses the same
serialization path.
