# 1040 Lombard street facade skeleton v025

The user explicitly moved architecture forward after v024, choosing the blue house first. The old v020 blue facade is rejected and is not propagated as truth. v025 starts over from the source-identified building and rebuilds only the road-facing facade slice.

## Identity and scale
DataSF building 201006.0032105 overlaps OSM way 262548811, which carries the address 1040 Lombard Street. The footprint edge nearest the accepted crooked roadway is 10.9348 m long and is the only architectural face edited in this pass.

The facade base is not derived from the parcel-wide minimum ground elevation. v025 samples the accepted v024 driveway cells immediately outside the garage band (660 samples) and anchors the facade floor to that local street/access datum. This reduces the road-facing envelope to 12.625 m and avoids inventing an extra lower storey on the sloping parcel.

## Source-led facade identity
Andrew Napier's 2013 street overview (CC BY 2.0) is the committed visual reference. Dedicated 1040 Commons photographs from August 2013 (CC0) and July 2019 (CC BY-SA 2.0) were independently checked for facade hierarchy.

Locked visual facts for this slice:
- light-blue solid infill/wall fields, not a curtain wall;
- dark blue vertical, horizontal and diagonal framing;
- discrete white-framed multi-lite windows;
- street-level blue garage;
- recessed dark entry at the west side of the facade;
- an open, framed/railed upper terrace rather than another full glass storey.

Opening sizes and timber spacing are photo-proportioned rather than survey-measured. They are review geometry, not final measured facade dimensions.

## Edit scope and gates
Only the first 0.50 m inside the source-identified 1040 street facade and its local driveway-anchored vertical envelope may change. v025 changes 119,622 microcells. Exact Litematica/Astra readback passes; every parent cell outside declared edits is preserved; vanilla blocks are preserved; the measured 10.93 m front-width gate passes.

Explicitly deferred: bay/projection depth verification, roof/pergola geometry, side and rear facades, interiors, and facade vegetation. The v024 tree morphology also remains a known visual issue deferred for a later tree pass.

Load Projects / Lombard Stress Build / Lombard_1040_Facade_Skeleton_Astra_v025.litematic at the same origin, rotation 0, mirror none, replace ALL including air. Stop for flyaround before adding depth or roof detail.
