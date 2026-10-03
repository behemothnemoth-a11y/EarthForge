# Current review: v003 architectural assemblies

See `docs/LOMBARD_1040_BUILDING_LAB_V003.md` and the lab project.json. Front assemblies are rebuilt using the successful Redfield/410 methods; broader source dimensions remain unresolved and integration remains blocked. Earlier headings below are historical.

# Current pass: v002

See `docs/LOMBARD_1040_BUILDING_LAB_V002.md`. v002 fixes view handedness and facade framing only. v001 is preserved as the diagnostic parent; no site integration.

# 1040 Lombard isolated diagnostic lab

## Scope
This branch isolates one building using the existing EarthForge Single-Building Truth Lab workflow and the actual continuous FacadeCanvas. It contains the normalized DataSF footprint, provisional architecture and one yellow registration block; no Lombard streets, trees or neighbors are imported.

## What is and is not solved
The previous v032 custom whole-site generator used EarthForge codecs but bypassed the shared FacadeCanvas. This lab uses that shared canvas for continuous geometry, openings and splitting to Astra hosts. It still carries rejected v032 provisional facade ratios for diagnosis. It is NOT a new measured or accepted reconstruction.

The front preview already shows oversized braces and a brace crossing the upper-right window. A successful codec check does not fix that. The side/rear/top geometry also remains provisional. Next architectural work must correct source proportions and module boundaries, not merely add decoration.

## Safety and placement
Use a NEW empty scratch area (at least 20 x 20 x 25 blocks). The file is only 13 x 13 x 20 blocks. Rotation 0, mirror none. The front faces -Z. Never paste at the full Lombard origin; no site merge is authorized. The global-frame transform is retained as metadata for a later explicitly accepted integration.

## Gates
Serialization: exact block map AND exact per-host microcell/material comparison.
Visual/source acceptance: NEEDS_REWORK.
Integration: BLOCKED.

No Minecraft world files are edited by this lab. The codex/lombard-sf-hardmode branch is unchanged.

## Blueprint-first acquisition

The user clarified that real architectural blueprints are the primary additional source to search. Existing schematics/models remain a separate useful check. Follow `docs/BUILDING_DRAWING_AND_REUSE_DISCOVERY.md`; the initial search is recorded in `source_discovery_v001.json` as INCOMPLETE, with no verified plan set or reusable asset acquired. No absence claim or geometry promotion is made.
