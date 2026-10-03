# Farnsworth House — reference-first single-building test

Status: **REFERENCE REVIEW ONLY — NO BUILD GENERATION APPROVED**

This experiment reconstructs the Edith Farnsworth House in Plano, Illinois, through EarthForge. It is independent of Lombard and Redfield. No existing project or Minecraft world is to be cleared, patched, or replaced.

## Scope

- One building at 1:1 scale: 1 real-world metre = 1 Minecraft block on every axis.
- Include the house, its attached upper and lower terraces, and the two stair runs.
- Exclude roads, river, forest, neighboring structures, outbuildings, and site landscaping.
- Preserve real-world metric geometry in EarthForge. Minecraft is a generated realization, not a second source of truth.
- Reuse EarthForge's reconstruction/export paths. Do not write an unrelated one-off building generator.
- Keep exact dimensions until realization. Do not inflate thin steel, glass, or slab edges to full blocks merely for convenience; evaluate existing microblock support after approval.
- A future schematic must have its own identity and isolated placement frame, not inherit the Redfield patch's wipe behavior.

## Evidence package

The source register indexes all eight HABS measured sheets, eight selected photographs, the complete photo index, and the historical/architectural report. The LOC catalog lists 32 photos, eight measured drawings, 54 data pages, and three caption pages. The retrieved report PDF contains 55 PDF pages including covers; use the ledger's explicit PDF page numbers rather than assuming printed and PDF pagination match.

- [Source register](references/source_manifest.json)
- [Dimension ledger and unresolved conflicts](references/measurements.json)
- [Bounded Copilot review task](COPILOT_TASK.md)

Primary record: [Library of Congress, HABS IL-1105](https://www.loc.gov/item/il0323/).

## First findings

| Feature | Measured sheet 3 transcription | Exact unit conversion |
| --- | --- | --- |
| Upper plan overall east-west span | 77 ft 4 1/8 in | 23.574375 m |
| Upper plan north-south span | 28 ft 8 in | 8.7376 m |
| Lower terrace east-west span | 55 ft 3 in | 16.8402 m |
| Lower stair plan width | 12 ft 0 1/4 in | 3.66395 m |

These are **verified transcriptions of drawing labels, not an approved complete geometry model**. Conversion precision does not imply a survey accuracy of a fraction of a millimetre.

The five-part upper longitudinal dimension chain closes exactly to the sheet's overall span. However, the historical report gives 77 ft 3 in for the overall length, while its later addendum gives 29 ft 4 1/2 in for the depth. Preserve these competing statements. Check which edges the dimension leaders measure before deciding whether this is a transcription error, a boundary-definition difference, or a genuine conflict.

Upper terrace offsets, levels, roof/slab thicknesses, column sections and glazing details still need cross-checking against sheets 4, 5, 7 and 8. Do not fill these gaps from memory or appearance.

## Baseline and visual references

Proposed baseline: the 2009 HABS documentation campaign, submitted in 2010 (report PDF page 55), rather than a mixture of original 1951, 1971 and present-day furnishing states. This baseline is proposed for user review, not yet approved. The caption index identifies photos 11–32 as Leslie Schwartz, 2009; photos 1–10 as Jack E. Boucher, February 1971.

Open the plan and selected views directly at their source:

- [Measured plan — sheet 3](https://www.loc.gov/resource/hhh.il0323.sheet.00003a)
- [North elevation — photo 11](https://www.loc.gov/resource/hhh.il0323.photos.397645p)
- [East elevation with scale bar — photo 12](https://www.loc.gov/resource/hhh.il0323.photos.397646p)
- [South view — photo 14](https://www.loc.gov/resource/hhh.il0323.photos.397648p)
- [West elevation — photo 15](https://www.loc.gov/resource/hhh.il0323.photos.397649p)
- [Terrace connection — photo 18](https://www.loc.gov/resource/hhh.il0323.photos.397652p)

Photo 22 explicitly notes that the wardrobe was absent during photography, although it appears on the plan. That is a documented state difference, not permission to improvise the interior.

## Review gate

Before generating anything, return a short review containing the selected baseline, resolved or explicitly open dimension conflicts, a proposed metric coordinate frame, and a list of exporter limitations. The LOC coordinate is only a site locator; it is not a surveyed building origin or an elevation datum. Approval of this reference stage must precede the first structural pass. Furniture and decorative detail come later.

## What this commit does not do

No schematic, mesh, Minecraft installation, generator code, workflow change, paid service activation, or Copilot session is included. It does not change main or any existing project. Raw scans are not redistributed: references are linked with attribution because the LOC rights advisory is conditional, and National Trust authorship is not automatically US-government public-domain authorship.
