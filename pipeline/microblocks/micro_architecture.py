from __future__ import annotations

from typing import Iterable

def merge(dst, src, overwrite=True):
    for i, value in enumerate(src.cells):
        if value is None:
            continue
        if overwrite or dst.cells[i] is None:
            dst.cells[i] = value
    return dst


def empty(astra):
    return astra.MicroVolume()


def face_panel(astra, face: str, material: str, thickness: int = 3):
    v = astra.MicroVolume()
    if face == "east":
        return v.fill_box(16-thickness,0,0,16,16,16,material)
    if face == "west":
        return v.fill_box(0,0,0,thickness,16,16,material)
    if face == "south":
        return v.fill_box(0,0,16-thickness,16,16,16,material)
    if face == "north":
        return v.fill_box(0,0,0,16,16,thickness,material)
    raise ValueError(face)


def floor_skin(astra, material: str, thickness: int = 2, top=False):
    v=astra.MicroVolume()
    if top:
        return v.fill_box(0,16-thickness,0,16,16,16,material)
    return v.fill_box(0,0,0,16,thickness,16,material)


def roof_skin(astra, material: str, thickness: int = 4):
    return floor_skin(astra,material,thickness,top=False)


def thin_front_panel(astra, material: str, thickness: int = 3):
    return face_panel(astra,"east",material,thickness)


def frame_segment(astra, trim: str, kind: str, depth: int = 3, border: int = 2, lattice: str | None = None):
    # East-facing building facade. Window remains open.
    v=astra.MicroVolume()
    x0=16-depth
    x1=16
    if kind in ("bottom","full"):
        v.fill_box(x0,0,0,x1,border,16,trim)
    if kind in ("top","full"):
        v.fill_box(x0,16-border,0,x1,16,16,trim)
    v.fill_box(x0,0,0,x1,16,border,trim)
    v.fill_box(x0,0,16-border,x1,16,16,trim)

    mat=lattice or trim
    mid0=7
    mid1=9
    v.fill_box(x0,0,mid0,x1,16,mid1,mat)
    return v


def storefront_window(astra, green: str, trim: str, upper: bool = False, depth: int = 3):
    v=frame_segment(astra,green,"full",depth=depth,border=2,lattice=green)
    # Pale sill / header accent.
    x0=16-depth
    if upper:
        v.fill_box(x0,0,0,16,2,16,trim)
        v.fill_box(x0,14,0,16,16,16,trim)
    else:
        v.fill_box(x0,14,0,16,16,16,trim)
    return v


def door_panel(astra, wood: str, trim: str, handle: str, half: str):
    v=astra.MicroVolume()
    x0=12
    # Outer frame.
    v.fill_box(x0,0,0,16,16,2,trim)
    v.fill_box(x0,0,14,16,16,16,trim)
    if half=="lower":
        v.fill_box(x0,0,2,16,16,14,wood)
        # Recessed central panel.
        v.fill_box(14,3,5,16,12,11,wood)
        # Handle.
        v.fill_box(15,7,12,16,9,14,handle)
    elif half=="upper":
        # Open upper center, wood rails.
        v.fill_box(x0,0,2,16,3,14,wood)
        v.fill_box(x0,13,2,16,16,14,wood)
        v.fill_box(x0,0,7,16,16,9,wood)
    else:
        raise ValueError(half)
    return v


def sign_band(astra, green: str, trim: str):
    v=astra.MicroVolume()
    v.fill_box(12,3,0,16,13,16,green)
    v.fill_box(11,1,0,16,3,16,trim)
    v.fill_box(11,13,0,16,15,16,trim)
    return v


def awning(astra, green: str, trim: str, depth_cells: int = 12):
    v=astra.MicroVolume()
    # Host is immediately outside building; west side connects to facade.
    v.fill_box(0,9,0,depth_cells,12,16,green)
    v.fill_box(depth_cells-2,8,0,depth_cells,13,16,trim)
    return v


def cornice(astra, brick: str, trim: str):
    v=astra.MicroVolume()
    # East face backed by brick; sandstone projects in layers.
    v.fill_box(13,0,0,16,16,16,brick)
    v.fill_box(10,2,0,16,5,16,trim)
    v.fill_box(8,7,0,16,10,16,trim)
    v.fill_box(10,13,0,16,16,16,trim)
    return v


def bracket(astra, trim: str):
    v=astra.MicroVolume()
    v.fill_box(10,0,5,16,8,11,trim)
    v.fill_box(8,6,6,16,12,10,trim)
    return v


def parapet_panel(astra, brick: str, trim: str, cap=True):
    v=face_panel(astra,"east",brick,3)
    if cap:
        v.fill_box(10,13,0,16,16,16,trim)
    return v


def roundel_panel(astra, brick: str, trim: str):
    v=parapet_panel(astra,brick,trim,cap=True)
    x0=10
    cy,cz=8,8
    for y in range(16):
        for z in range(16):
            d=(y-cy)*(y-cy)+(z-cz)*(z-cz)
            if 10 <= d <= 22:
                v.fill_box(x0,y,z,16,y+1,z+1,trim)
    return v


def rear_window(astra, brick: str, trim: str):
    # West-facing rear frame; open center.
    v=face_panel(astra,"west",brick,3)
    # Carve-like behavior is achieved by rebuilding only border material.
    v=astra.MicroVolume()
    v.fill_box(0,0,0,3,16,2,trim)
    v.fill_box(0,0,14,3,16,16,trim)
    v.fill_box(0,0,0,3,2,16,trim)
    v.fill_box(0,14,0,3,16,16,trim)
    return v


def rear_door(astra, wood: str, trim: str):
    v=astra.MicroVolume()
    v.fill_box(0,0,0,4,16,16,wood)
    v.fill_box(0,0,0,4,16,2,trim)
    v.fill_box(0,0,14,4,16,16,trim)
    v.fill_box(0,14,0,4,16,16,trim)
    return v
