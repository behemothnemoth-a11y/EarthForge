# Copilot task — audit one building's evidence, then stop

This is a prepared task, **not a record of a launched or completed Copilot session**.

## Copy into Copilot Chat with the EarthForge repository open

> Work only on the branch `experiment/farnsworth-reference-v001` in EarthForge. Read the repository README, docs/PIPELINE.md, docs/SOURCE_POLICY.md, docs/COORDINATE_SYSTEM.md and projects/farnsworth_house_il/README.md first. Independently audit the Farnsworth reference package. Check measured sheet 3 against the dimension ledger and reconcile conflicts C01, C02 and C03 using the listed HABS sheets and report. Inspect the selected photographic views. Record a source sheet/page and the exact endpoints or vertical datum for every measurement you add. Preserve competing source values where unresolved. Propose a local metric coordinate frame and identify the existing EarthForge exporter paths that can realize this building; do not create a separate generator. Keep the task limited to reference review, a minimal ledger correction when supported, and a short REVIEW.md in this project's folder. Stop for my approval before generating a model, schematic, or any Minecraft changes.

## Hard limits

1. Only edit `projects/farnsworth_house_il/**`. Keep main, Lombard, Redfield, existing exports, Minecraft saves, and unrelated work untouched. Do not import the Redfield single-building patch's wipe behavior.
2. No paid services, subscription changes, new infrastructure, dependency installations, workflow changes, automatic merges, or unattended follow-on tasks.
3. No guessed geometry, pixel-based scale guesses when dimension labels exist, nonuniform scaling, or silent block-grid rounding. Exact unit conversion is not a claim of survey precision.
4. Raw source scans stay in an ignored/local temporary reference cache. Repository changes contain links, attribution, measurements, and findings only unless rights are specifically cleared.
5. Use the 2009 HABS baseline as a proposal, not an approved decision. Flag furniture and repair-state differences. Do not redesign the house or add surroundings.
6. If browsing or image viewing is unavailable, say which checks you could not perform. Never report an image as inspected merely because its caption is available.
7. Keep geometry generation blocked. A successful evidence review does not itself authorize the next stage.

## Acceptance

- Source IDs resolve to the manifest, with sheet numbers or both PDF and printed report pagination.
- The D03 longitudinal chain and all metre conversions are independently checked.
- C01-C03 are resolved with evidence, or left explicitly unresolved with a precise next check. C04 remains a baseline choice, not a hidden edit.
- The review distinguishes confirmed transcriptions, reported values, inference, unresolved data, and renderer limitations.
- The review identifies actual existing EarthForge modules to reuse, without claiming untested export capability.
- A diff confirms only this project folder changed. JSON parses with the repository's existing JSON validation tool; report the actual result and any pre-existing failure.
- Return a short summary in ordinary language and stop.

## Session record

Agent: not started.
Evidence author for this initial package: ChatGPT-assisted source review.
User reference approval: pending.
Build generation: not authorized.
