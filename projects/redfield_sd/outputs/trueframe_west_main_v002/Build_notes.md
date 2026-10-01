# Redfield West Main True-Frame v002

v002 fixes the distortion seen in the in-game v001 review.

## Root cause

v001 kept the correct combined mapped frontage, but divided that frontage using
per-address OSM polygons. Those internal OSM assignments contradict the verified
modern storefront photographs, so 623 became far too wide while 621 and
617-619 were compressed.

v002 rejects those internal OSM boundaries.

The combined west-Main outer frontage remains locked at **45.5625 m**. Internal
facade proportions instead follow the accepted photo-led strip at one shared
horizontal scale:

- 625-627: 14.5625 m
- 623: 6.375 m
- 621: 11.875 m
- 617-619: 12.75 m

Every facade now uses essentially the same ~0.91 photo-to-true-frame scale,
rather than a different stretch factor for each address.

## Why the proportion model is reasonable

Redfield's official **21 Feet of History** project explains that Main Street was
originally platted in roughly 21-foot storefront allotments, with some
businesses taking multiple lots and some widths reduced by walkways.

Source:
https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/

That historical module supports the visual rhythm in the accepted photo strip:
623 reads as the narrow single-storefront unit, while 617-619, 621 and the
625-627 upper composition are substantially broader multi-module facades.

The 21-foot rule is corroborating evidence, not a claim that every current wall
is exactly on a historic lot line.

## Geometry

- accepted Main Street MicroGrade is carried forward
- one unioned mapped outer building footprint is used
- unverified OSM internal party walls are not emitted
- facade fronts use the locked west-Main street plane
- accepted photo materials, signs, glazing and depth are preserved
- visible facade heights retain the LiDAR/photo fit from v001
- roof bands are recalculated by the corrected facade zones over the unioned
  footprint
- side/rear shells remain intentionally plain pending oblique/rear imagery

## Validation

- exact Litematica block-map readback: PASS
- exact Astra microcell/material readback: PASS
- registration marker: PASS
- true combined frontage: 45.5625 m
- per-address OSM width use: REMOVED
- Astra hosts: 6,745
- occupied microcells: 11,016,476
- regular outer-shell blocks: 917
- live Minecraft review: PENDING
