#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CODEC = ROOT / "pipeline" / "export" / "litematic_codec.py"


def load_codec():
    spec = importlib.util.spec_from_file_location("earthforge_litematic_codec", CODEC)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main():
    c = load_codec()
    blocks = {
        (0,-1,0): "minecraft:yellow_concrete",
        (1,0,0): "minecraft:dark_oak_door[facing=west,half=lower,hinge=left,open=false,powered=false]",
        (1,1,0): "minecraft:dark_oak_door[facing=west,half=upper,hinge=left,open=false,powered=false]",
        (2,0,0): "minecraft:smooth_stone_slab[type=bottom,waterlogged=false]",
        (3,0,0): "minecraft:lantern[hanging=false]",
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.litematic"
        info = c.write_single_region_litematic(
            p, blocks, (0,-1,0,3,1,1), "TEST", "Test", "Codec test", 4903, 6, 1
        )
        back, meta = c.read_back_block_map(p, "TEST")
        expected = {k:c.canonical_state(v) for k,v in blocks.items()}
        assert back == expected, (back, expected)
        assert any("[" in x for x in meta["palette"])
    print("LITEMATIC_STATEFUL_CODEC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
