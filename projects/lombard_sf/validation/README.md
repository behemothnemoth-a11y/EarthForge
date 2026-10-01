# Lombard validation

Every generated revision must record:
1. source geometry inputs + versions/IDs;
2. Litematica exact block readback counts and mismatches;
3. Astra Microblocks 0.7.0 block-entity count, host positions, microcell occupancy, and exact readback mismatches;
4. registration marker at schematic `(0,-1,0)`, placement origin player feet, rotation 0, mirror none;
5. visual-gate status and unresolved discrepancies.

A revision is not promoted merely because it loads. Geometry truth and readback truth are separate gates.
