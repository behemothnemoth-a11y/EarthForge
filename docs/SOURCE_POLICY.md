# Source and Reference Policy

EarthForge should keep provenance for every external input.

For map imagery, Street View, aerial imagery, photographs, or other licensed
reference material:

- store source URLs, panorama IDs, timestamps, notes, and attribution metadata
  in source manifests;
- keep raw captures in the local ignored reference folders unless the source
  license clearly permits redistribution;
- do not treat a screenshot as geographic truth when a structured geographic
  source is available;
- record confidence when geometry must be inferred from incomplete views.

This is a project policy designed to keep the repository portable and avoid
mixing source licensing with generated project data.

## Building drawings and reuse discovery

For real-building reconstruction, perform the architectural blueprint/plan search and the separate existing schematic/model check in `docs/BUILDING_DRAWING_AND_REUSE_DISCOVERY.md`. Record the search outcome and feature-level applicability before using any result. This is an explicit acquisition check, not an automated retrieval service or a geometry-acceptance gate.
