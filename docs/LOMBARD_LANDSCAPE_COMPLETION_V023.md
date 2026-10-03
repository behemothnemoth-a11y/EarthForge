# Lombard landscape + site-connectivity completion v023

v023 follows the accepted v022 retaining/planter finish. The user's 2026-10-03 flyaround accepted v022 and explicitly requested completion of the remaining Lombard landscaping before returning to buildings, including the visibly unfinished upper green/site band at the end of the capture.

## Scope and evidence
This pass is additive botanical work only. It may place planting above green ground that already exists in the accepted v022 artifact; it does not create new terrain levels, retaining walls, sidewalks, roads, stairs, property boundaries, patios, or building geometry.
The public-realm garden footprint remains the primary landscape authority. A narrow connector zone may extend at most 2.25 m beyond it only where it overlaps the immediate pedestrian-site band and where v022 already contains supported green ground. This closes review-era visual seams without treating the review boundary as geometry.
Landscape character is checked against Andrew Napier's Lombard Street references (CC BY 2.0), Toi & Moi's uphill garden view (CC BY-SA 2.0), and Cornflower123's upper-garden reference (CC0). They support dense layered hedge/flower/tree character, not surveyed individual plant positions or seasonal species.

## Trees
All OSM natural=tree nodes are audited against supported green ground in the current artifact. Existing mapped trees are preserved exactly. A missing mapped tree may be added only when its mapped point resolves within 1.25 m of supported green ground; height uses the same bounded local non-ground LiDAR p90 candidate method as v017.
The v023 audit finds 29 mapped tree nodes: 18 existing trees preserved, 1 source-mapped tree added, and 10 nodes omitted because no supported green base exists at the mapped position. No decorative tree is invented to fill those gaps.

## Hard gates
Every occupied v022 microcell is immutable. v023 additions must write only into parent air; all vanilla blocks and the registration marker are preserved. Exact Litematica and exact Astra readback are required. Buildings, road/curb/pavers, sidewalks, stairs/landings/rails, and the v022 retaining finish are frozen.
Validation PASS: 141,657 supported plain-green candidate columns; 100,543 connector columns vegetated; 541,289 groundcover cells and 32,100 bloom cells added. Review remains a Minecraft flyaround gate, not automatic acceptance.

Load `Projects / Lombard Stress Build / Lombard_Landscape_Completion_Astra_v023.litematic` at the established origin, rotation 0, mirror none, replace ALL including air.