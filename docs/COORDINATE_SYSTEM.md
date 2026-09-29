# Coordinate System

## Redfield POC defaults

Source geographic coordinates:
- WGS84 latitude/longitude (`EPSG:4326`)

Working projected coordinates:
- UTM Zone 14N (`EPSG:32614`)

Minecraft default scale:
- horizontal: 1 meter = 1 block
- vertical: 1 meter = 1 block initially

The Redfield POC will define one real-world anchor:

```text
(anchor latitude, anchor longitude, anchor elevation)
                 ↓
(local East, North, Up meters)
                 ↓
(Minecraft X, Z, Y)
```

The actual anchor is intentionally not hard-coded yet. It will be selected when
we choose the first Redfield test area.

## Rule

Every generated object must be traceable back to project-local metric
coordinates. Minecraft coordinates are an output representation, not the
primary source of truth.
