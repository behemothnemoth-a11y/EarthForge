# Building drawing and existing-asset discovery

## Purpose and position in the workflow
Before deriving a real building from photographs, perform and record a bounded search for architectural drawings. This is an acquisition check, not permission to skip identity, source review, physically staged reconstruction, or Minecraft visual gates. The user clarified that blueprints are the priority; existing Minecraft schematics and 3D models are a separate useful search.

## A. Architectural drawings first
Look for original or measured/as-built plans, permit drawing sets, planning application attachments, elevations, sections, roof plans, site plans, and credible published floor plans. Check public building/planning portals, architectural or historic archives, identified architect/project publications, and address-matched listing material where available. Sanborn maps and cadastral outlines can corroborate footprint/history but are not facade blueprints.

Use the exact address, city, parcel/block-lot and building identifier; follow verified historical aliases when supported. An address mention, permit index, room count, illustration or generic house plan is not a recovered blueprint.

For each candidate record: provider, URL/file ID, title, address/parcel match, author if available, issue/revision/date, sheet number, drawing type, existing/proposed/as-built status, units, written dimensions, scale and crop/resizing limitations, coverage, retrieval status, rights and access restrictions. Prefer written dimensions to scaled pixels. A proposed or approved plan is not proof that the work was constructed. Cross-check drawing era and actual built features against independent photographs/GIS; report conflicts rather than silently choosing a source.

## B. Existing schematics and models separately
Search address/building-specific schematics, world downloads, CAD/BIM/3D models and wider-area builds that may contain the target. Treat them as third-party interpretation unless their measured provenance is verified. Record source/creator, license and adaptation/redistribution terms, availability and cost, file format, required mods/version, scale on all axes, orientation, footprint, incomplete regions and evidence of identity.

A visual resemblance, download button, or claimed 1:1 scale is not validation. Inspect untrusted files in isolation; do not execute bundled code or modify a Minecraft world as part of discovery. No automatic import, nonuniform stretching, or use of a third-party model to validate itself. Re-author useful verified geometry at source-controlled scale when necessary.

## C. Honest, bounded search outcomes
Maintain separate drawing and reuse ledgers with queries/providers checked, results and unresolved routes. Use NOT_SEARCHED, INCOMPLETE, NO_VERIFIED_MATCH_IN_CHECKED_SOURCES, ACCESS_UNRESOLVED, or VERIFIED_CANDIDATE as appropriate. A provider error, poor search result or unsearched archive is not proof of absence. A verified candidate still requires feature-level applicability review; it is not automatically accepted geometry.

Search available online evidence first. Record request-only/paywalled/restricted routes; do not contact owners/agencies, order paid records, submit requests, accept terms or bypass controls without authorization. Keep raw material private/ignored unless redistribution is verified.

Do not turn discovery into an indefinite infrastructure project. Report what was checked and what remains. Missing drawings leave dependent dimensions unresolved; any explicitly authorized provisional geometry must still label those dimensions as provisional. Discovery does not authorize another schematic or reset.

## D. Review presentation and gates
Show the actual source photos and, when acquired, the relevant drawing sheets directly in chat with attribution and a short statement of what they support. Label generated diagrams as derived, not source plans. Compare current geometry to those sources before further detail.

Track discovery completion, serialization validation, source applicability, visual acceptance and site integration separately. A successful test or search cannot promote geometry. For 1040, keep all work isolated on the building-lab branch until explicit integration acceptance.

## Existing EarthForge precedents
- docs/FORT_GARRY_MAIN_FLOOR_INTERIOR_V001.md uses a published hotel floor plan.
- docs/REDFIELD_ACQUISITION.md includes official CADD and archival sources.
- docs/SINGLE_BUILDING_TRUTH_LAB.md isolates a building for diagnosis.

These precedents are useful, but do not prove that a blueprint search has been completed for another building.
