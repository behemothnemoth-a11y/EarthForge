#!/usr/bin/env python3
"""Reusable microcell facade authoring primitives for EarthForge.

A facade is authored in photo-view coordinates:
- u: horizontal left-to-right as seen from across the street
- y: vertical
- d: depth toward the street; negative d recesses into the building

The compiler maps those coordinates into the locked EarthForge frame for either
side of Main Street and writes directly into Astra MicroVolumes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from pipeline.microblocks.astra_microblock_codec import MicroVolume

@dataclass
class FacadePlacement:
    side: str
    front_x_micro: int
    south_z_micro: int
    north_z_micro: int
    base_y_micro: int
    ref_x_block: int
    ref_z_block: int

    @property
    def width(self) -> int:
        return abs(self.south_z_micro - self.north_z_micro)

class FacadeCanvas:
    def __init__(
        self,
        placement: FacadePlacement,
        height_micro: int,
        set_cell: Callable[[int, int, int, str | None], None],
    ):
        self.p = placement
        self.width = placement.width
        self.height = int(height_micro)
        self._set = set_cell

    def U(self, fraction: float) -> int:
        return max(0, min(self.width, round(float(fraction) * self.width)))

    def Y(self, meters: float) -> int:
        return max(0, min(self.height, round(float(meters) * 16)))

    def global_cell(self, u: int, y: int, d: int) -> tuple[int, int, int]:
        # u is always photo-left -> photo-right.
        # West facade is viewed looking west: photo-left is south.
        # East facade is viewed looking east: photo-left is north.
        if self.p.side == "west":
            z = self.p.south_z_micro - u
            x = self.p.front_x_micro + d
        elif self.p.side == "east":
            z = self.p.north_z_micro + u
            x = self.p.front_x_micro - d
        else:
            raise ValueError(self.p.side)
        sx = x - self.p.ref_x_block * 16
        sy = self.p.base_y_micro + y
        sz = z - self.p.ref_z_block * 16
        return sx, sy, sz

    def cell(self, u: int, y: int, d: int, material: str | None):
        if 0 <= u < self.width and 0 <= y < self.height:
            x, yy, z = self.global_cell(u, y, d)
            self._set(x, yy, z, material)

    def rect(self, uf0, uf1, y0m, y1m, d0, d1, material):
        u0, u1 = self.U(uf0), self.U(uf1)
        y0, y1 = self.Y(y0m), self.Y(y1m)
        for u in range(u0, u1):
            for y in range(y0, y1):
                for d in range(int(d0), int(d1)):
                    self.cell(u, y, d, material)

    def wall(self, material, thickness=3):
        self.rect(0, 1, 0, self.height / 16, -thickness + 1, 1, material)

    def clear(self, uf0, uf1, y0m, y1m, d0=-24, d1=8):
        self.rect(uf0, uf1, y0m, y1m, d0, d1, None)

    def window(
        self,
        uf0,
        uf1,
        y0m,
        y1m,
        glass,
        frame,
        recess=-5,
        frame_cells=2,
        crossbar=True,
        mullion=False,
    ):
        self.clear(uf0, uf1, y0m, y1m)
        u0, u1 = self.U(uf0), self.U(uf1)
        y0, y1 = self.Y(y0m), self.Y(y1m)
        for u in range(u0 + frame_cells, max(u0 + frame_cells, u1 - frame_cells)):
            for y in range(y0 + frame_cells, max(y0 + frame_cells, y1 - frame_cells)):
                self.cell(u, y, recess, glass)
        for u in range(u0, u1):
            for y in list(range(y0, min(y1, y0 + frame_cells))) + list(range(max(y0, y1-frame_cells), y1)):
                for d in range(recess, 2):
                    self.cell(u, y, d, frame)
        for y in range(y0, y1):
            for u in list(range(u0, min(u1, u0 + frame_cells))) + list(range(max(u0, u1-frame_cells), u1)):
                for d in range(recess, 2):
                    self.cell(u, y, d, frame)
        if crossbar and y1-y0 >= 12:
            cy=(y0+y1)//2
            for u in range(u0,u1):
                for y in range(cy-1,cy+1):
                    for d in range(recess,1): self.cell(u,y,d,frame)
        if mullion and u1-u0 >= 12:
            cu=(u0+u1)//2
            for u in range(cu-1,cu+1):
                for y in range(y0,y1):
                    for d in range(recess,1): self.cell(u,y,d,frame)

    def door(self, uf0, uf1, height_m, leaf, frame, glass=None, recess=-6):
        self.clear(uf0, uf1, 0, height_m)
        u0,u1=self.U(uf0),self.U(uf1); y1=self.Y(height_m)
        for u in range(u0+2,u1-2):
            for y in range(2,y1-2):
                self.cell(u,y,recess,leaf)
        if glass is not None:
            gy0=max(6,round(y1*.42)); gy1=y1-5
            for u in range(u0+5,u1-5):
                for y in range(gy0,gy1): self.cell(u,y,recess-1,glass)
        for u in range(u0,u1):
            for y in range(0,2):
                for d in range(recess,2):self.cell(u,y,d,frame)
            for y in range(y1-2,y1):
                for d in range(recess,2):self.cell(u,y,d,frame)
        for y in range(0,y1):
            for u in list(range(u0,min(u1,u0+2)))+list(range(max(u0,u1-2),u1)):
                for d in range(recess,2):self.cell(u,y,d,frame)

    def line(self, u0, y0, u1, y1, d0, d1, material, thickness=1):
        steps=max(abs(u1-u0),abs(y1-y0),1)
        for i in range(steps+1):
            u=round(u0+(u1-u0)*i/steps)
            y=round(y0+(y1-y0)*i/steps)
            for du in range(-thickness,thickness+1):
                for dy in range(-thickness,thickness+1):
                    for d in range(d0,d1):
                        self.cell(u+du,y+dy,d,material)
    def awning(self, uf0, uf1, y_back_m, projection, drop_cells, material, edge):
        u0,u1=self.U(uf0),self.U(uf1)
        yb=self.Y(y_back_m)
        projection=int(projection)
        for d in range(0,projection+1):
            y=yb-round(drop_cells*d/max(1,projection))
            for u in range(u0,u1):
                self.cell(u,y,d,material)
                self.cell(u,y-1,d,material)
        front_y=yb-drop_cells
        for u in range(u0,u1):
            for y in range(front_y-2,front_y+1):
                for d in range(max(0,projection-2),projection+2):
                    self.cell(u,y,d,edge)

    def gable(self, eave_m, peak_m, material, trim):
        e=self.Y(eave_m); p=self.Y(peak_m); c=self.width//2
        for u in range(self.width):
            frac=1-abs(u-c)/max(1,c)
            top=e+round((p-e)*max(0,frac))
            for y in range(e,top):
                for d in range(-2,1):self.cell(u,y,d,material)
        self.line(0,e,c,p,0,3,trim,1)
        self.line(c,p,self.width-1,e,0,3,trim,1)

    def round_column(self, uf, y0m, y1m, radius_cells, material, center_d=3):
        uc=self.U(uf); y0=self.Y(y0m); y1=self.Y(y1m); r=int(radius_cells)
        for y in range(y0,y1):
            for du in range(-r,r+1):
                for dd in range(-r,r+1):
                    if du*du+dd*dd <= r*r:
                        self.cell(uc+du,y,center_d+dd,material)

    def horizontal_seams(self, y0m, y1m, spacing_cells, material, d=2):
        y0,y1=self.Y(y0m),self.Y(y1m)
        for y in range(y0,y1,max(1,int(spacing_cells))):
            for u in range(self.width):
                self.cell(u,y,d,material)

    def vertical_seams(self, uf0, uf1, y0m, y1m, spacing_cells, material, d=2):
        u0,u1=self.U(uf0),self.U(uf1); y0,y1=self.Y(y0m),self.Y(y1m)
        for u in range(u0,u1,max(1,int(spacing_cells))):
            for y in range(y0,y1):
                self.cell(u,y,d,material)
