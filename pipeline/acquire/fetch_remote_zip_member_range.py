#!/usr/bin/env python3
"""Fetch one member from a very large remote ZIP using HTTP byte ranges.

EarthForge uses this for public GIS archives where downloading the entire
county-scale ZIP would be wasteful. Supports standard and ZIP64 central
directories plus stored/deflated members.
"""
from __future__ import annotations

import argparse
import binascii
import struct
import time
import urllib.request
import zlib
from pathlib import Path

UA = "EarthForge/0.1 (selective remote ZIP member fetch)"
RANGE_VALIDATORS: dict[str, str] = {}

def request_bytes(url: str, start: int, end: int) -> bytes:
    last_status = None
    for attempt in range(5):
        headers = {
            "Range": f"bytes={start}-{end}",
            "User-Agent": f"{UA} range-attempt/{attempt}",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        validator = RANGE_VALIDATORS.get(url)
        if validator:
            headers["If-Range"] = validator
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=180) as response:
            last_status = response.status
            if response.status == 206:
                return response.read()
        time.sleep(0.35 * (attempt + 1))
    raise RuntimeError(f"Expected HTTP 206 after retries, got {last_status}")

def remote_size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        length = response.headers.get("Content-Length")
        ranges = response.headers.get("Accept-Ranges", "")
        if length is None:
            raise RuntimeError("Remote ZIP did not report Content-Length")
        if "bytes" not in ranges.lower():
            raise RuntimeError("Remote server does not advertise byte ranges")
        validator = response.headers.get("Last-Modified")
        if validator:
            RANGE_VALIDATORS[url] = validator
        return int(length)

def find_zip64_directory(url: str, total: int) -> tuple[int, int]:
    tail_size = min(total, 256 * 1024)
    tail_start = total - tail_size
    tail = request_bytes(url, tail_start, total - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("ZIP end-of-central-directory record not found")

    disk, cd_disk, disk_entries, entries, cd_size, cd_offset, _ = struct.unpack_from(
        "<4H2IH", tail, eocd + 4
    )
    if cd_offset != 0xFFFFFFFF and cd_size != 0xFFFFFFFF:
        return cd_offset, cd_size

    locator = tail.rfind(b"PK\x06\x07", 0, eocd)
    if locator < 0:
        raise RuntimeError("ZIP64 locator not found")
    _, zip64_offset, _ = struct.unpack_from("<IQI", tail, locator + 4)
    record = request_bytes(url, zip64_offset, zip64_offset + 95)
    if record[:4] != b"PK\x06\x06":
        raise RuntimeError("ZIP64 end record signature not found")
    values = struct.unpack_from("<2H2I4Q", record, 12)
    _, _, _, _, _, _, size64, offset64 = values
    return offset64, size64

def parse_zip64_extra(
    extra: bytes,
    compressed: int,
    uncompressed: int,
    local_offset: int,
) -> tuple[int, int, int]:
    pos = 0
    c64, u64, o64 = compressed, uncompressed, local_offset
    while pos + 4 <= len(extra):
        header_id, size = struct.unpack_from("<HH", extra, pos)
        data = extra[pos + 4 : pos + 4 + size]
        pos += 4 + size
        if header_id != 0x0001:
            continue
        dp = 0
        if uncompressed == 0xFFFFFFFF:
            u64 = struct.unpack_from("<Q", data, dp)[0]
            dp += 8
        if compressed == 0xFFFFFFFF:
            c64 = struct.unpack_from("<Q", data, dp)[0]
            dp += 8
        if local_offset == 0xFFFFFFFF:
            o64 = struct.unpack_from("<Q", data, dp)[0]
        break
    return c64, u64, o64

def find_member(url: str, member: str) -> dict:
    total = remote_size(url)
    cd_offset, cd_size = find_zip64_directory(url, total)
    central = request_bytes(url, cd_offset, cd_offset + cd_size - 1)
    pos = 0
    target = member.replace("\\", "/").lower()
    while pos + 46 <= len(central):
        if central[pos : pos + 4] != b"PK\x01\x02":
            raise RuntimeError(f"Bad central-directory signature at {pos}")
        values = struct.unpack_from("<6H3I5H2I", central, pos + 4)
        (
            _made, _need, flag, method, _time, _date, crc,
            compressed, uncompressed, name_len, extra_len, comment_len,
            _disk, _int_attr, _ext_attr, local_offset,
        ) = values
        name_raw = central[pos + 46 : pos + 46 + name_len]
        encoding = "utf-8" if flag & 0x800 else "cp437"
        name = name_raw.decode(encoding)
        extra_start = pos + 46 + name_len
        extra = central[extra_start : extra_start + extra_len]
        c64, u64, o64 = parse_zip64_extra(
            extra, compressed, uncompressed, local_offset
        )
        if name.replace("\\", "/").lower() == target:
            return {
                "name": name,
                "method": method,
                "flag": flag,
                "crc": crc,
                "compressed": c64,
                "uncompressed": u64,
                "local_offset": o64,
                "remote_size": total,
            }
        pos += 46 + name_len + extra_len + comment_len
    raise FileNotFoundError(member)
def extract_member(url: str, info: dict, output: Path) -> None:
    local_offset = info["local_offset"]
    header = request_bytes(url, local_offset, local_offset + 65535)
    if header[:4] != b"PK\x03\x04":
        raise RuntimeError("Bad local-file-header signature")
    (
        _need, _flag, method, _time, _date, _crc, _compressed, _uncompressed,
        name_len, extra_len,
    ) = struct.unpack_from("<5H3I2H", header, 4)
    data_offset = local_offset + 30 + name_len + extra_len
    compressed = request_bytes(
        url, data_offset, data_offset + info["compressed"] - 1
    )
    if method == 0:
        raw = compressed
    elif method == 8:
        raw = zlib.decompress(compressed, -15)
    else:
        raise RuntimeError(f"Unsupported ZIP compression method {method}")

    if len(raw) != info["uncompressed"]:
        raise RuntimeError(
            f"Size mismatch: got {len(raw)}, expected {info['uncompressed']}"
        )
    crc = binascii.crc32(raw) & 0xFFFFFFFF
    if crc != info["crc"]:
        raise RuntimeError(f"CRC mismatch: {crc:08x} != {info['crc']:08x}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("member")
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"SKIP existing {args.output}")
        return 0

    info = find_member(args.url, args.member)
    print(
        f"Found {info['name']}: "
        f"{info['compressed']:,} compressed / {info['uncompressed']:,} bytes"
    )
    extract_member(args.url, info, args.output)
    print(f"WROTE {args.output} ({args.output.stat().st_size:,} bytes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
