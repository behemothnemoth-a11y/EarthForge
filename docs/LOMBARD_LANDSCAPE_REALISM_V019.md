# Lombard landscape form pass v019

The user requested more realism after the neighborhood blockout, while the previous instruction to defer photoreal textures remains active. This pass changes only illustrative planting and existing tree crown cells. Source ground, all public hardscape, building envelopes, tree trunks and mapped locations remain fixed.

## Evidence and interpretation

The 2026-10-02 17:49:03 Minecraft capture shows flat scattered flower patches and uniform solid crowns. The cached Andrew Napier reference at https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064478253).jpg (CC BY 2.0) shows rounded flowering shrubs within clipped hedge borders. It supports the change in general plant form, not exact present-day plant positions, season, species or bloom colors.

Replace only the old HEDGE2/flower cells above known bed ground in the existing mapped planted-bed mask. Generate deterministic irregularly spaced rounded shrub groups, varying approximately 0.46–0.68m in radius and up to 1m in total botanical height including blooms. Use small three-dimensional bloom tufts and simple solid-color materials. Keep mapped hedge outlines. Within existing tree crowns, vary green masses and selectively remove outer leaf cells, preserving trunks, locations and the old crown envelope.

## Validation and reproduction

Run `python pipeline/reconstruction/generate_lombard_landscape_v019.py`, then `python tools/test_lombard_public_realm_v1.py --landscape`, then `python tools/render_lombard_public_realm_v1.py OUTPUT_DIRECTORY --landscape`.

The generator records original snapshots for touched hosts and checks every changed cell against the botanical change rules before export. Unchanged hosts must retain their original content. Exact Litematica/Astra readback, vanilla blocks and registration are checked. The independent pedestrian audit also recognizes the new foliage colors and checks the unchanged walking surfaces and stair centerlines against the new artifact.

Building architectural detail, real roof forms, site/entrance connections, outer support gaps and raised crossing overlays remain outstanding. Do not imply those are finished by the landscape change. Use the same placement as v018, rotation 0, mirror none, replace ALL including air. The next artifact remains a flyaround candidate, not automatically accepted geometry.
