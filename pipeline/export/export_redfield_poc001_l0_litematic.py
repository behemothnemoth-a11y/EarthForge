#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import time
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

CSV_IN = POC / "l0_block_plan.csv"
FRAME_IN = POC / "locked_frame.json"
CONFIG_IN = POC / "litematica_export.json"

OUT_DIR = PROJECT / "outputs" / "l0"
OUT_FILE = OUT_DIR / "Redfield_POC_001_L0_v001.litematic"
MANIFEST_OUT = OUT_DIR / "Redfield_POC_001_L0_v001.manifest.json"
VALIDATION_OUT = PROJECT / "validation" / "poc001_l0_litematic_validation.json"

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def u16_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) > 65535:
        raise ValueError("NBT string is too long")
    return struct.pack(">H", len(raw)) + raw


class NBTWriter:
    def named_header(self, tag_type: int, name: str) -> bytes:
        return bytes([tag_type]) + u16_string(name)

    def tag_int(self, name: str, value: int) -> bytes:
        return self.named_header(TAG_INT, name) + struct.pack(">i", int(value))

    def tag_long(self, name: str, value: int) -> bytes:
        return self.named_header(TAG_LONG, name) + struct.pack(">q", int(value))

    def tag_string(self, name: str, value: str) -> bytes:
        return self.named_header(TAG_STRING, name) + u16_string(value)

    def tag_int_array(self, name: str, values: List[int]) -> bytes:
        out = self.named_header(TAG_INT_ARRAY, name) + struct.pack(">i", len(values))
        out += b"".join(struct.pack(">i", int(v)) for v in values)
        return out

    def tag_long_array(self, name: str, values: List[int]) -> bytes:
        out = self.named_header(TAG_LONG_ARRAY, name) + struct.pack(">i", len(values))
        out += b"".join(struct.pack(">q", int(v)) for v in values)
        return out

    def tag_list_compounds(self, name: str, payloads: List[bytes]) -> bytes:
        out = self.named_header(TAG_LIST, name)
        out += bytes([TAG_COMPOUND])
        out += struct.pack(">i", len(payloads))
        out += b"".join(payloads)
        return out

    def tag_compound(self, name: str, payload: bytes) -> bytes:
        return self.named_header(TAG_COMPOUND, name) + payload + bytes([TAG_END])

    def root_compound(self, payload: bytes) -> bytes:
        return bytes([TAG_COMPOUND]) + u16_string("") + payload + bytes([TAG_END])


def compound_payload(entries: List[bytes]) -> bytes:
    return b"".join(entries)


def vec3i_payload(w: NBTWriter, x: int, y: int, z: int) -> bytes:
    return compound_payload([
        w.tag_int("x", x),
        w.tag_int("y", y),
        w.tag_int("z", z),
    ])


def palette_entry_payload(w: NBTWriter, block_name: str) -> bytes:
    # List entries are unnamed compound payloads and include their own TAG_End.
    return compound_payload([w.tag_string("Name", block_name)]) + bytes([TAG_END])


def bits_needed(palette_size: int) -> int:
    return max(2, math.ceil(math.log2(max(2, palette_size))))


def pack_palette_indices(values: List[int], nbits: int) -> List[int]:
    arr = [0] * math.ceil(len(values) * nbits / 64)
    mask = (1 << nbits) - 1
    u64 = (1 << 64) - 1

    for index, value in enumerate(values):
        if value < 0 or value > mask:
            raise ValueError(f"Palette index {value} does not fit in {nbits} bits")

        start_offset = index * nbits
        start_arr = start_offset >> 6
        end_arr = ((index + 1) * nbits - 1) >> 6
        start_bit = start_offset & 0x3F

        arr[start_arr] &= ~(mask << start_bit) & u64
        arr[start_arr] |= (value & mask) << start_bit
        arr[start_arr] &= u64

        if start_arr != end_arr:
            end_offset = 64 - start_bit
            spill_bits = nbits - end_offset
            low_mask = (1 << spill_bits) - 1
            arr[end_arr] &= ~low_mask & u64
            arr[end_arr] |= (value >> end_offset) & low_mask
            arr[end_arr] &= u64

    signed = []
    for value in arr:
        signed.append(value - (1 << 64) if value & (1 << 63) else value)
    return signed


def unpack_palette_indices(values_signed: List[int], count: int, nbits: int) -> List[int]:
    arr = [v & ((1 << 64) - 1) for v in values_signed]
    mask = (1 << nbits) - 1
    out = []

    for index in range(count):
        start_offset = index * nbits
        start_arr = start_offset >> 6
        end_arr = ((index + 1) * nbits - 1) >> 6
        start_bit = start_offset & 0x3F

        if start_arr == end_arr:
            value = (arr[start_arr] >> start_bit) & mask
        else:
            end_offset = 64 - start_bit
            value = ((arr[start_arr] >> start_bit) | (arr[end_arr] << end_offset)) & mask
        out.append(value)

    return out


class NBTReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError("Unexpected end of NBT")
        out = self.data[self.pos:self.pos+n]
        self.pos += n
        return out

    def byte(self) -> int:
        return self.take(1)[0]

    def i32(self) -> int:
        return struct.unpack(">i", self.take(4))[0]

    def i64(self) -> int:
        return struct.unpack(">q", self.take(8))[0]

    def string(self) -> str:
        n = struct.unpack(">H", self.take(2))[0]
        return self.take(n).decode("utf-8")

    def payload(self, tag_type: int):
        if tag_type == TAG_BYTE:
            return struct.unpack(">b", self.take(1))[0]
        if tag_type == TAG_SHORT:
            return struct.unpack(">h", self.take(2))[0]
        if tag_type == TAG_INT:
            return self.i32()
        if tag_type == TAG_LONG:
            return self.i64()
        if tag_type == TAG_FLOAT:
            return struct.unpack(">f", self.take(4))[0]
        if tag_type == TAG_DOUBLE:
            return struct.unpack(">d", self.take(8))[0]
        if tag_type == TAG_BYTE_ARRAY:
            return list(self.take(self.i32()))
        if tag_type == TAG_STRING:
            return self.string()
        if tag_type == TAG_LIST:
            elem_type = self.byte()
            count = self.i32()
            return [self.payload(elem_type) for _ in range(count)]
        if tag_type == TAG_COMPOUND:
            out = {}
            while True:
                child_type = self.byte()
                if child_type == TAG_END:
                    break
                name = self.string()
                out[name] = self.payload(child_type)
            return out
        if tag_type == TAG_INT_ARRAY:
            return [self.i32() for _ in range(self.i32())]
        if tag_type == TAG_LONG_ARRAY:
            return [self.i64() for _ in range(self.i32())]
        raise ValueError(f"Unsupported NBT tag type: {tag_type}")

    def root(self) -> dict:
        if self.byte() != TAG_COMPOUND:
            raise ValueError("NBT root is not a compound")
        self.string()
        result = self.payload(TAG_COMPOUND)
        if self.pos != len(self.data):
            raise ValueError("Trailing bytes after NBT root")
        return result


def load_block_plan() -> Dict[Tuple[int, int], str]:
    if not CSV_IN.exists():
        raise FileNotFoundError(f"Block plan not found: {CSV_IN}")

    cells: Dict[Tuple[int, int], str] = {}
    with CSV_IN.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"x", "y", "z", "block"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("L0 CSV does not have the required columns")

        for row in reader:
            x = int(row["x"])
            y = int(row["y"])
            z = int(row["z"])
            if y != 0:
                raise ValueError("Drop 0004 expects one flat y=0 diagnostic layer")
            cells[(x, z)] = row["block"]

    if not cells:
        raise ValueError("L0 block plan is empty")
    return cells


def write_gzip_nbt(path: Path, raw: bytes) -> None:
    # GzipFile supports mtime across the Python versions EarthForge targets,
    # unlike gzip.open on some older installs.
    with path.open("wb") as raw_fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_fh, compresslevel=9, mtime=0) as gz:
            gz.write(raw)


def build_litematic() -> dict:
    frame = read_json(FRAME_IN)
    config = read_json(CONFIG_IN)
    cells = load_block_plan()

    ref = frame["future_litematica_registration"]
    ref_x = int(ref["player_feet_x"])
    ref_z = int(ref["player_feet_z"])

    # Permanent stand-on revision registration marker.
    cells[(ref_x, ref_z)] = config["registration"]["block"]

    bounds = frame["plan_bounds_blocks"]
    min_project_x = min(int(bounds["min_x"]), min(x for x, _ in cells))
    max_project_x = max(int(bounds["max_x"]), max(x for x, _ in cells))
    min_project_z = min(int(bounds["min_z"]), min(z for _, z in cells))
    max_project_z = max(int(bounds["max_z"]), max(z for _, z in cells))

    # Schematic origin is player feet. All L0 surface cells are one block below.
    region_pos_x = min_project_x - ref_x
    region_pos_y = -1
    region_pos_z = min_project_z - ref_z

    width = max_project_x - min_project_x + 1
    height = 1
    length = max_project_z - min_project_z + 1
    volume = width * height * length

    palette_names = ["minecraft:air"]
    for block in sorted(set(cells.values())):
        if block != "minecraft:air" and block not in palette_names:
            palette_names.append(block)
    palette_index = {name: i for i, name in enumerate(palette_names)}

    states = [0] * volume
    expected_non_air = {}

    for (project_x, project_z), block in cells.items():
        sx = project_x - ref_x
        sy = -1
        sz = project_z - ref_z

        lx = sx - region_pos_x
        ly = sy - region_pos_y
        lz = sz - region_pos_z

        if not (0 <= lx < width and 0 <= ly < height and 0 <= lz < length):
            raise AssertionError("Translated block is outside the region")

        index = (ly * width * length) + (lz * width) + lx
        states[index] = palette_index[block]
        expected_non_air[(sx, sy, sz)] = block

    nbits = bits_needed(len(palette_names))
    packed = pack_palette_indices(states, nbits)

    now_ms = int(time.time() * 1000)
    w = NBTWriter()

    palette_payloads = [palette_entry_payload(w, name) for name in palette_names]

    region_payload = compound_payload([
        w.tag_compound("Position", vec3i_payload(w, region_pos_x, region_pos_y, region_pos_z)),
        w.tag_compound("Size", vec3i_payload(w, width, height, length)),
        w.tag_list_compounds("BlockStatePalette", palette_payloads),
        w.tag_list_compounds("Entities", []),
        w.tag_list_compounds("TileEntities", []),
        w.tag_list_compounds("PendingBlockTicks", []),
        w.tag_list_compounds("PendingFluidTicks", []),
        w.tag_long_array("BlockStates", packed),
    ])

    metadata_payload = compound_payload([
        w.tag_compound("EnclosingSize", vec3i_payload(w, width, height, length)),
        w.tag_string("Author", "EarthForge"),
        w.tag_string(
            "Description",
            "Redfield POC 001 L0 diagnostic. Stand on yellow block and set placement origin to player position for revision alignment."
        ),
        w.tag_string("Name", "Redfield POC 001 - L0 v001"),
        w.tag_string("Software", "EarthForge_0.1"),
        w.tag_int("RegionCount", 1),
        w.tag_long("TimeCreated", now_ms),
        w.tag_long("TimeModified", now_ms),
        w.tag_int("TotalBlocks", len(expected_non_air)),
        w.tag_int("TotalVolume", volume),
        w.tag_int_array("PreviewImageData", []),
    ])

    regions_payload = w.tag_compound(config["litematica"]["region_name"], region_payload)

    root_payload = compound_payload([
        w.tag_int("Version", int(config["litematica"]["version"])),
        w.tag_int("SubVersion", int(config["litematica"]["subversion"])),
        w.tag_int("MinecraftDataVersion", int(config["litematica"]["minecraft_data_version"])),
        w.tag_compound("Metadata", metadata_payload),
        w.tag_compound("Regions", regions_payload),
    ])

    raw = w.root_compound(root_payload)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_gzip_nbt(OUT_FILE, raw)

    return {
        "config": config,
        "palette_names": palette_names,
        "expected_non_air": expected_non_air,
        "region_position": (region_pos_x, region_pos_y, region_pos_z),
        "region_size": (width, height, length),
        "volume": volume,
        "nbits": nbits,
    }


def validate_litematic(expected: dict) -> dict:
    with gzip.open(OUT_FILE, "rb") as fh:
        raw = fh.read()

    root = NBTReader(raw).root()
    config = expected["config"]
    region_name = config["litematica"]["region_name"]
    errors = []

    def check(condition: bool, message: str):
        if not condition:
            errors.append(message)

    check(root.get("Version") == config["litematica"]["version"], "Version mismatch")
    check(root.get("SubVersion") == config["litematica"]["subversion"], "SubVersion mismatch")
    check(root.get("MinecraftDataVersion") == config["litematica"]["minecraft_data_version"], "MinecraftDataVersion mismatch")

    metadata = root.get("Metadata") or {}
    regions = root.get("Regions") or {}
    check(region_name in regions, "Expected region is missing")
    if region_name not in regions:
        raise ValueError("; ".join(errors))

    region = regions[region_name]
    pos = region.get("Position") or {}
    size = region.get("Size") or {}
    actual_pos = (pos.get("x"), pos.get("y"), pos.get("z"))
    actual_size = (size.get("x"), size.get("y"), size.get("z"))

    check(actual_pos == expected["region_position"], f"Region position mismatch: {actual_pos}")
    check(actual_size == expected["region_size"], f"Region size mismatch: {actual_size}")
    check(metadata.get("RegionCount") == 1, "RegionCount mismatch")
    check(metadata.get("TotalVolume") == expected["volume"], "TotalVolume mismatch")
    check(metadata.get("TotalBlocks") == len(expected["expected_non_air"]), "TotalBlocks mismatch")

    palette = region.get("BlockStatePalette") or []
    palette_names = [entry.get("Name") for entry in palette]
    check(palette_names == expected["palette_names"], "Palette mismatch")

    width, height, length = expected["region_size"]
    count = width * height * length
    nbits = bits_needed(len(palette_names))
    unpacked = unpack_palette_indices(region.get("BlockStates") or [], count, nbits)

    actual_non_air = {}
    rx, ry, rz = expected["region_position"]
    for index, pidx in enumerate(unpacked):
        if pidx == 0:
            continue

        ly = index // (width * length)
        rem = index % (width * length)
        lz = rem // width
        lx = rem % width

        sx, sy, sz = rx + lx, ry + ly, rz + lz
        if pidx >= len(palette_names):
            errors.append(f"Palette index out of range at {(sx, sy, sz)}")
            continue
        actual_non_air[(sx, sy, sz)] = palette_names[pidx]

    exact_map = actual_non_air == expected["expected_non_air"]
    marker = (0, -1, 0)
    marker_block = config["registration"]["block"]

    check(exact_map, "Read-back block map differs from generated source map")
    check(actual_non_air.get(marker) == marker_block, "Registration marker missing or wrong")

    digest = hashlib.sha256(OUT_FILE.read_bytes()).hexdigest()

    report = {
        "schema_version": 1,
        "export_id": config["export_id"],
        "status": "valid" if not errors else "invalid",
        "file": str(OUT_FILE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": digest,
        "format": {
            "litematica_version": root.get("Version"),
            "subversion": root.get("SubVersion"),
            "minecraft_data_version": root.get("MinecraftDataVersion"),
            "gzip": True,
            "nbt_endianness": "big"
        },
        "region": {
            "name": region_name,
            "position": list(actual_pos),
            "size": list(actual_size),
            "volume": count,
            "non_air_blocks": len(actual_non_air),
            "palette_size": len(palette_names),
            "bits_per_block": nbits
        },
        "registration": {
            "player_feet_origin": [0, 0, 0],
            "marker_block_position": [0, -1, 0],
            "marker_block": marker_block,
            "verified": actual_non_air.get(marker) == marker_block
        },
        "checks": {
            "region_position": actual_pos == expected["region_position"],
            "region_size": actual_size == expected["region_size"],
            "palette": palette_names == expected["palette_names"],
            "exact_block_map": exact_map,
            "registration_marker": actual_non_air.get(marker) == marker_block
        },
        "errors": errors
    }

    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "export_id": config["export_id"],
        "file": report["file"],
        "sha256": digest,
        "source_block_plan": config["source_block_plan"],
        "source_frame": config["source_frame"],
        "region": report["region"],
        "palette": palette_names,
        "placement": {
            "instruction": "Stand on the yellow registration block and set schematic placement origin to the player feet block position.",
            "origin_relative_marker": [0, -1, 0],
            "rotation": 0,
            "mirror": "none"
        }
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if errors:
        raise ValueError("Litematic read-back validation failed: " + "; ".join(errors))

    return report


def main() -> int:
    expected = build_litematic()
    report = validate_litematic(expected)

    print("EarthForge Redfield POC 001 L0 Litematic generated and validated.")
    print(f"  File          : {report['file']}")
    print(f"  SHA256        : {report['sha256']}")
    print(f"  Region pos    : {report['region']['position']}")
    print(f"  Region size   : {report['region']['size']}")
    print(f"  Non-air blocks: {report['region']['non_air_blocks']}")
    print(f"  Palette size  : {report['region']['palette_size']}")
    print(f"  Marker        : {report['registration']['marker_block_position']} {report['registration']['marker_block']}")
    print("  Read-back     : PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
