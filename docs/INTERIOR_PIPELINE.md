# EarthForge Interior Pipeline

Interiors are not generated in Redfield v006, but the exterior pipeline is now
required to preserve enough information that interiors can be added without
rebuilding the structure.

## Interior readiness contract

Every building should eventually know:

- floor count;
- floor-to-floor height;
- exterior entrances;
- rear/service entrance;
- vertical-circulation zone;
- front public/commercial zone;
- rear service/storage zone;
- upper-floor use;
- roof-access location;
- interior confidence.

## Stages

### I0 — Interior program

Data only.

Examples:

```text
restaurant
front dining
rear kitchen/service
restroom core
rear delivery door
```

```text
retail
front sales floor
rear stock/service
optional office
```

```text
civic
public lobby
service counter / offices
secure/service zone
vertical circulation
```

### I1 — Room seed

EarthForge derives approximate room zones from the real footprint and frontage
direction.

No walls are generated yet.

### I2 — Block-only interior shell

After the exterior building pipeline stabilizes:

- floors;
- stairs;
- room partitions;
- service corridors;
- major fixtures.

### I3 — Interior detail

Furniture and decorative detail.

Microblocks can later be used selectively for counters, trim and custom
fixtures, but they are not a prerequisite for I2.

## Current Redfield status

v006 creates I0 and I1 metadata only. This lets us inspect whether the planned
room logic makes sense before any interior blocks are committed to the world.
