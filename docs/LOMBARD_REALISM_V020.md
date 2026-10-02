# Lombard realism v020

User authorization on 2026-10-02 expands the pass to all five flyaround findings. No photoreal texture pass. The artifact remains a review candidate, not a claim that source gaps are resolved.

## Evidence and decisions

- Flowers: the 18:02:35 capture exposes pale repeated tips. Andrew Napier's Commons photos `Lombard Street (10064478253).jpg` and `Lombard Street (10064415846).jpg` show rounded hydrangea heads embedded in leafy masses. Replace column-random tips with sparse connected ellipsoids and larger leafy clusters. Individual planting remains illustrative.
- Green slope bands: central ground already has 1/16m height quantization. Preserve those elevations; reduce horizontally uniform color and increase connected planting cover. Do not mislabel quantization as contaminated LiDAR.
- Outer ground: v018 used quarter-metre samples replicated over 4x4 microcell patches. Resample the same existing context columns at 1/16m using original class-2 observations, 5m nearest and 20m triangle support gates. Unsupported columns retain their previous state; original support gaps remain explicit. No scope expansion or vertical walls at a review boundary.
- First building group: reference 021 visibly identifies the blue framed house as 1040. Its mapped footprint is `201006.0032105`. Add simple blue/dark framing, opening divisions, garage impression and upper glazing within the existing envelope. The adjacent western footprint `201006.0038369` is matched by adjacency to the yellow mansard house; its address association is provisional. Rebuild its upper envelope as a provisional inward-sloping roof with paired dormer impressions. Preserve footprint and top elevation. These are photo-led interpretations, not measured facade dimensions.
- Building access: recolor only existing supported ground immediately along the visible fronts as provisional aprons. Do not invent entry elevations, terraces, patios, or retaining walls to conceal missing ground observations. Walking access and source dimensions remain a later targeted pass.
- Raised crossings: v017 intentionally added paint 0.0625m above accepted pavement. Remove that layer and recolor the existing top pavement cell. This is a documented exception to material preservation; accepted road occupancy remains fixed. Rails remain unchanged.
- Hyde red endpoint: it belongs to the accepted v009 road. The references inspected do not establish a registered replacement boundary across Hyde. Keep it pending direct intersection evidence rather than trim accepted geometry on appearance alone.

## Reproduction and gates

Run `pipeline/reconstruction/generate_lombard_realism_v020.py`, then `tools/test_lombard_public_realm_v1.py --realism`, `tools/test_lombard_realism_v020.py`, and `tools/render_lombard_public_realm_v1.py <output directory> --realism`.

Required: exact Litematica block-map and Astra cell/original-state readback; unchanged host and registration preservation; v009 road/curb plus endpoint-asphalt occupancy; only declared paint recoloring of accepted materials; pedestrian and stair clearance; flower components touching shrubs. Previews must come from the decoded export and carry its SHA.

## Future artifact prevention

1. Audit accepted layers by their source membership, not material name alone: old terrain can share concrete with accepted curbs.
2. Paint belongs within the surface, not in an added collision layer. Record material-only exceptions separately from geometry changes.
3. Use connected flower volumes and test their connection to foliage; per-column random tips produce pegs even when an overview looks acceptable.
4. Record horizontal sampling and vertical quantization independently. A fine export grid does not make coarse source sampling fine.
5. Never promote filled cells to new ground observations. Missing source support is a reported gap, not permission to invent a terrace.
6. Match visible building identity before transferring facade features; record adjacency-based identities and unmeasured roof proportions as provisional.

Source photos remain in ignored private reference storage. Commons attribution: Andrew Napier, CC BY 2.0; https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064415846).jpg and https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064478253).jpg.

Same schematic placement, rotation 0, mirror none, replace ALL including air. Stop for the user's flyaround after validation and installation.
