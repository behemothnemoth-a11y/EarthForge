from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

SIZE = 16
CELL_COUNT = 4096
GRID_WORDS = 64
HOST_STATE = "astra_microblocks:test_host[orientation=0]"
BLOCK_ENTITY_ID = "astra_microblocks:test_host"


def _signed64(value: int) -> int:
    value &= (1 << 64) - 1
    return value - (1 << 64) if value & (1 << 63) else value


def cell_index(x: int, y: int, z: int) -> int:
    if not (0 <= x < 16 and 0 <= y < 16 and 0 <= z < 16):
        raise ValueError((x, y, z))
    return x | (z << 4) | (y << 8)


class MicroVolume:
    def __init__(self, original: str = "minecraft:stone"):
        self.original = original
        self.cells: List[str | None] = [None] * CELL_COUNT

    def set(self, x: int, y: int, z: int, material: str | None):
        self.cells[cell_index(x, y, z)] = material

    def fill_box(self, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int, material: str):
        for y in range(y0, y1):
            for z in range(z0, z1):
                for x in range(x0, x1):
                    self.set(x, y, z, material)
        return self

    def occupied_count(self) -> int:
        return sum(v is not None for v in self.cells)

    def materials(self) -> List[str]:
        return sorted({v for v in self.cells if v is not None})

    def occupancy_words(self) -> List[int]:
        words = [0] * GRID_WORDS
        for i, material in enumerate(self.cells):
            if material is not None:
                words[i >> 6] |= 1 << (i & 63)
        return [_signed64(v) for v in words]

    def oak_words(self) -> List[int]:
        words = [0] * GRID_WORDS
        for i, material in enumerate(self.cells):
            if material == "minecraft:oak_planks":
                words[i >> 6] |= 1 << (i & 63)
        return [_signed64(v) for v in words]

    def volume_v4(self) -> dict:
        palette = self.materials()
        size = len(palette)
        bits = max(1, size.bit_length())
        stride = 64 // bits
        packed = [0] * ((CELL_COUNT + stride - 1) // stride)
        lookup = {mat: i + 1 for i, mat in enumerate(palette)}

        for i, material in enumerate(self.cells):
            index = 0 if material is None else lookup[material]
            packed[i // stride] |= index << ((i % stride) * bits)

        return {
            "version": 2,
            "original": self.original,
            "palette": palette,
            "bits": bits,
            "cells": [_signed64(v) for v in packed],
        }


def attached_x_range(side: str, depth: int):
    if side == "east":
        return 16 - depth, 16
    if side == "west":
        return 0, depth
    raise ValueError(side)


def thin_cornice(side: str, material: str, depth: int = 4, height: int = 4) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    return v.fill_box(x0, 0, 0, x1, height, 16, material)


def vertical_mullion(side: str, material: str, depth: int = 2, width: int = 2) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    z0 = (16 - width) // 2
    return v.fill_box(x0, 0, z0, x1, 16, z0 + width, material)


def transom(side: str, material: str, depth: int = 2, height: int = 2) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    y0 = (16 - height) // 2
    return v.fill_box(x0, y0, 0, x1, y0 + height, 16, material)


def pilaster(side: str, material: str, depth: int = 4, width: int = 6) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    z0 = (16 - width) // 2
    return v.fill_box(x0, 0, z0, x1, 16, z0 + width, material)


def sign_frame(side: str, material: str, depth: int = 2, border: int = 2) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    # Border on facade plane.
    v.fill_box(x0, 0, 0, x1, border, 16, material)
    v.fill_box(x0, 16-border, 0, x1, 16, 16, material)
    v.fill_box(x0, 0, 0, x1, 16, border, material)
    v.fill_box(x0, 0, 16-border, x1, 16, 16, material)
    return v


def entry_surround(side: str, material: str, depth: int = 6) -> MicroVolume:
    v = MicroVolume()
    x0, x1 = attached_x_range(side, depth)
    # Two narrow jamb-like strips plus a header.
    v.fill_box(x0, 0, 0, x1, 16, 4, material)
    v.fill_box(x0, 0, 12, x1, 16, 16, material)
    v.fill_box(x0, 12, 0, x1, 16, 16, material)
    return v


def mixed_frame(side: str, outer: str, inner: str) -> MicroVolume:
    v = sign_frame(side, outer, depth=3, border=3)
    x0, x1 = attached_x_range(side, 2)
    v.fill_box(x0, 6, 6, x1, 10, 10, inner)
    return v


def tile_entity_payload(writer, rel_xyz: Tuple[int,int,int], volume: MicroVolume, orientation: int = 0) -> bytes:
    rx, ry, rz = rel_xyz
    occ = volume.occupancy_words()
    oak = volume.oak_words()
    v4 = volume.volume_v4()

    volume_payload = [
        writer.tag_int("version", v4["version"]),
        writer.tag_string("original", v4["original"]),
        writer.tag_int("size", len(v4["palette"])),
    ]
    for i, material in enumerate(v4["palette"]):
        volume_payload.append(writer.tag_string(f"material_{i}", material))
    volume_payload.extend([
        writer.tag_int("bits", v4["bits"]),
        writer.tag_long_array("cells", v4["cells"]),
    ])

    entries = [
        writer.tag_string("id", BLOCK_ENTITY_ID),
        writer.tag_int("x", rx),
        writer.tag_int("y", ry),
        writer.tag_int("z", rz),
        writer.tag_int("astra_orientation", orientation),
        writer.tag_byte("grid_format_v1", 1),
    ]
    for i, word in enumerate(occ):
        entries.append(writer.tag_long(f"grid_{i}", word))
    entries.extend([
        writer.tag_long("revision", 1),
        writer.tag_byte("has_undo", 0),
        writer.tag_byte("materials_v2", 1),
    ])
    for i, word in enumerate(oak):
        entries.append(writer.tag_long(f"oak_{i}", word))
    entries.append(writer.tag_compound("volume_v4", b"".join(volume_payload)))
    return b"".join(entries) + bytes([0])


def decode_volume_v4(tag: dict) -> List[str | None]:
    if tag.get("version") != 2:
        raise ValueError("Unsupported Astra volume version")
    size = int(tag["size"])
    palette = [tag[f"material_{i}"] for i in range(size)]
    bits = int(tag["bits"])
    stride = 64 // bits
    packed = [v & ((1 << 64) - 1) for v in tag["cells"]]
    out: List[str | None] = []
    mask = (1 << bits) - 1
    for i in range(CELL_COUNT):
        index = (packed[i // stride] >> ((i % stride) * bits)) & mask
        out.append(None if index == 0 else palette[index - 1])
    return out
