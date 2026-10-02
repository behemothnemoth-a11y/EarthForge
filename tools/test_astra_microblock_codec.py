#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod); return mod


def main():
    codec=load(ROOT/"pipeline/export/litematic_codec.py","codec")
    astra=load(ROOT/"pipeline/microblocks/astra_microblock_codec.py","astra")
    patterns=[
        astra.thin_cornice("east","minecraft:bricks"),
        astra.vertical_mullion("west","minecraft:smooth_sandstone"),
        astra.transom("east","minecraft:stone_bricks"),
        astra.pilaster("west","minecraft:bricks"),
        astra.mixed_frame("east","minecraft:smooth_sandstone","minecraft:red_terracotta")
    ]
    # Astra 0.7.0 requires a supported solid `original`; air would make
    # volume_v4 fail runtime palette resolution and fall back to legacy stone.
    try:
        astra.MicroVolume("minecraft:air")
        raise AssertionError("minecraft:air original unexpectedly accepted")
    except ValueError:
        pass

    writer=codec.NBTWriter()
    for i,v in enumerate(patterns):
        payload=astra.tile_entity_payload(writer,(i,0,0),v)
        # Parse payload by wrapping it as an unnamed root compound.
        raw=bytes([codec.TAG_COMPOUND])+b"\x00\x00"+payload
        parsed=codec.NBTReader(raw).root()
        assert parsed["id"]==astra.BLOCK_ENTITY_ID
        assert parsed["volume_v4"]["version"]==2
        decoded=astra.decode_volume_v4(parsed["volume_v4"])
        assert decoded==v.cells
    print("ASTRA_DIRECT_NBT_PASS",len(patterns))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
