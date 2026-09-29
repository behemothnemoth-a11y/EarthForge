from __future__ import annotations

import gzip
import hashlib
import math
from pathlib import Path
import struct
import time
from typing import Dict, List, Tuple

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

Coord = Tuple[int, int, int]


def _u16_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) > 65535:
        raise ValueError("NBT string too long")
    return struct.pack(">H", len(raw)) + raw


class NBTWriter:
    def header(self, tag_type: int, name: str) -> bytes:
        return bytes([tag_type]) + _u16_string(name)

    def tag_int(self, name: str, value: int) -> bytes:
        return self.header(TAG_INT, name) + struct.pack(">i", int(value))

    def tag_long(self, name: str, value: int) -> bytes:
        return self.header(TAG_LONG, name) + struct.pack(">q", int(value))

    def tag_string(self, name: str, value: str) -> bytes:
        return self.header(TAG_STRING, name) + _u16_string(value)

    def tag_int_array(self, name: str, values: List[int]) -> bytes:
        return self.header(TAG_INT_ARRAY, name) + struct.pack(">i", len(values)) + b"".join(
            struct.pack(">i", int(v)) for v in values
        )

    def tag_long_array(self, name: str, values: List[int]) -> bytes:
        return self.header(TAG_LONG_ARRAY, name) + struct.pack(">i", len(values)) + b"".join(
            struct.pack(">q", int(v)) for v in values
        )

    def tag_list_compounds(self, name: str, payloads: List[bytes]) -> bytes:
        return (
            self.header(TAG_LIST, name)
            + bytes([TAG_COMPOUND])
            + struct.pack(">i", len(payloads))
            + b"".join(payloads)
        )

    def tag_compound(self, name: str, payload: bytes) -> bytes:
        return self.header(TAG_COMPOUND, name) + payload + bytes([TAG_END])

    def root(self, payload: bytes) -> bytes:
        return bytes([TAG_COMPOUND]) + _u16_string("") + payload + bytes([TAG_END])


def _payload(entries: List[bytes]) -> bytes:
    return b"".join(entries)


def _vec3(w: NBTWriter, x: int, y: int, z: int) -> bytes:
    return _payload([w.tag_int("x", x), w.tag_int("y", y), w.tag_int("z", z)])


def _palette_entry(w: NBTWriter, name: str) -> bytes:
    return w.tag_string("Name", name) + bytes([TAG_END])


def bits_needed(palette_size: int) -> int:
    return max(2, math.ceil(math.log2(max(2, palette_size))))


def pack_indices(values: List[int], nbits: int) -> List[int]:
    arr = [0] * math.ceil(len(values) * nbits / 64)
    mask = (1 << nbits) - 1
    u64 = (1 << 64) - 1

    for index, value in enumerate(values):
        start = index * nbits
        a = start >> 6
        b = ((index + 1) * nbits - 1) >> 6
        bit = start & 63

        arr[a] |= (value & mask) << bit
        arr[a] &= u64

        if a != b:
            shift = 64 - bit
            arr[b] |= (value >> shift)
            arr[b] &= u64

    return [v - (1 << 64) if v & (1 << 63) else v for v in arr]


def unpack_indices(values: List[int], count: int, nbits: int) -> List[int]:
    arr = [v & ((1 << 64) - 1) for v in values]
    mask = (1 << nbits) - 1
    out = []

    for index in range(count):
        start = index * nbits
        a = start >> 6
        b = ((index + 1) * nbits - 1) >> 6
        bit = start & 63

        if a == b:
            value = (arr[a] >> bit) & mask
        else:
            shift = 64 - bit
            value = ((arr[a] >> bit) | (arr[b] << shift)) & mask

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
            kind = self.byte()
            return [self.payload(kind) for _ in range(self.i32())]
        if tag_type == TAG_COMPOUND:
            out = {}
            while True:
                child = self.byte()
                if child == TAG_END:
                    break
                name = self.string()
                out[name] = self.payload(child)
            return out
        if tag_type == TAG_INT_ARRAY:
            return [self.i32() for _ in range(self.i32())]
        if tag_type == TAG_LONG_ARRAY:
            return [self.i64() for _ in range(self.i32())]
        raise ValueError(f"Unsupported NBT tag {tag_type}")

    def root(self) -> dict:
        if self.byte() != TAG_COMPOUND:
            raise ValueError("Root is not compound")
        self.string()
        root = self.payload(TAG_COMPOUND)
        if self.pos != len(self.data):
            raise ValueError("Trailing bytes after NBT root")
        return root


def write_gzip(path: Path, raw: bytes) -> None:
    with path.open("wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, compresslevel=9, mtime=0) as gz:
            gz.write(raw)


def write_single_region_litematic(
    path: Path,
    blocks: Dict[Coord, str],
    bounds: Tuple[int, int, int, int, int, int],
    region_name: str,
    schematic_name: str,
    description: str,
    data_version: int = 4903,
    version: int = 6,
    subversion: int = 1,
    author: str = "EarthForge",
) -> dict:
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    length = max_z - min_z + 1
    volume = width * height * length

    palette = ["minecraft:air"]
    for block in sorted(set(blocks.values())):
        if block != "minecraft:air" and block not in palette:
            palette.append(block)
    pindex = {name: i for i, name in enumerate(palette)}

    states = [0] * volume
    for (x, y, z), block in blocks.items():
        if not (min_x <= x <= max_x and min_y <= y <= max_y and min_z <= z <= max_z):
            raise ValueError(f"Block outside bounds: {(x, y, z)}")
        lx = x - min_x
        ly = y - min_y
        lz = z - min_z
        index = ly * width * length + lz * width + lx
        states[index] = pindex[block]

    nbits = bits_needed(len(palette))
    packed = pack_indices(states, nbits)

    w = NBTWriter()
    now = int(time.time() * 1000)

    region = _payload([
        w.tag_compound("Position", _vec3(w, min_x, min_y, min_z)),
        w.tag_compound("Size", _vec3(w, width, height, length)),
        w.tag_list_compounds("BlockStatePalette", [_palette_entry(w, b) for b in palette]),
        w.tag_list_compounds("Entities", []),
        w.tag_list_compounds("TileEntities", []),
        w.tag_list_compounds("PendingBlockTicks", []),
        w.tag_list_compounds("PendingFluidTicks", []),
        w.tag_long_array("BlockStates", packed),
    ])

    metadata = _payload([
        w.tag_compound("EnclosingSize", _vec3(w, width, height, length)),
        w.tag_string("Author", author),
        w.tag_string("Description", description),
        w.tag_string("Name", schematic_name),
        w.tag_string("Software", "EarthForge_0.2"),
        w.tag_int("RegionCount", 1),
        w.tag_long("TimeCreated", now),
        w.tag_long("TimeModified", now),
        w.tag_int("TotalBlocks", len(blocks)),
        w.tag_int("TotalVolume", volume),
        w.tag_int_array("PreviewImageData", []),
    ])

    root_payload = _payload([
        w.tag_int("Version", version),
        w.tag_int("SubVersion", subversion),
        w.tag_int("MinecraftDataVersion", data_version),
        w.tag_compound("Metadata", metadata),
        w.tag_compound("Regions", w.tag_compound(region_name, region)),
    ])

    raw = w.root(root_payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_gzip(path, raw)

    return {
        "palette": palette,
        "bits_per_block": nbits,
        "region_position": [min_x, min_y, min_z],
        "region_size": [width, height, length],
        "volume": volume,
        "non_air_blocks": len(blocks),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def read_back_block_map(path: Path, region_name: str) -> tuple[dict, dict]:
    with gzip.open(path, "rb") as fh:
        root = NBTReader(fh.read()).root()

    region = root["Regions"][region_name]
    pos = region["Position"]
    size = region["Size"]
    min_x, min_y, min_z = pos["x"], pos["y"], pos["z"]
    width, height, length = size["x"], size["y"], size["z"]

    palette = [entry["Name"] for entry in region["BlockStatePalette"]]
    nbits = bits_needed(len(palette))
    states = unpack_indices(region["BlockStates"], width * height * length, nbits)

    blocks = {}
    for index, pidx in enumerate(states):
        if pidx == 0:
            continue
        ly = index // (width * length)
        rem = index % (width * length)
        lz = rem // width
        lx = rem % width
        blocks[(min_x + lx, min_y + ly, min_z + lz)] = palette[pidx]

    meta = {
        "root": root,
        "palette": palette,
        "bits_per_block": nbits,
        "region_position": [min_x, min_y, min_z],
        "region_size": [width, height, length],
    }
    return blocks, meta
