from __future__ import annotations
import math

class FacadeCanvas:
    """
    Continuous facade voxel canvas.

    Coordinates:
      d = facade depth in 1/16 cells. 0 = nominal outer wall plane.
          negative = recessed into building; positive = projected streetward.
      y = vertical 1/16 cells.
      u = horizontal facade 1/16 cells.

    The canvas is independent of Minecraft host boundaries. That is the point:
    windows, doors, curves, slopes and moldings can cross block borders freely.
    """
    def __init__(self, width_cells, height_cells):
        self.width = width_cells
        self.height = height_cells
        self.cells = {}
        self.feature_counts = {"sloped":0, "round":0, "boxes":0}

    def set(self, d, y, u, material):
        if 0 <= y < self.height and 0 <= u < self.width:
            self.cells[(int(d), int(y), int(u))] = material

    def clear(self, d0, d1, y0, y1, u0, u1):
        for d in range(d0,d1):
            for y in range(max(0,y0), min(self.height,y1)):
                for u in range(max(0,u0), min(self.width,u1)):
                    self.cells.pop((d,y,u), None)

    def box(self, d0, d1, y0, y1, u0, u1, material):
        self.feature_counts["boxes"] += 1
        for d in range(d0,d1):
            for y in range(max(0,y0), min(self.height,y1)):
                for u in range(max(0,u0), min(self.width,u1)):
                    self.cells[(d,y,u)] = material

    def line_uy(self, d0, d1, u0, y0, u1, y1, thickness, material):
        self.feature_counts["sloped"] += 1
        steps=max(abs(u1-u0),abs(y1-y0),1)
        for i in range(steps+1):
            t=i/steps
            u=round(u0+(u1-u0)*t)
            y=round(y0+(y1-y0)*t)
            self.box(d0,d1,y-thickness,y+thickness+1,u-thickness,u+thickness+1,material)

    def line_dy(self, u0, u1, d0, y0, d1, y1, thickness, material):
        self.feature_counts["sloped"] += 1
        steps=max(abs(d1-d0),abs(y1-y0),1)
        for i in range(steps+1):
            t=i/steps
            d=round(d0+(d1-d0)*t)
            y=round(y0+(y1-y0)*t)
            self.box(d-thickness,d+thickness+1,y-thickness,y+thickness+1,u0,u1,material)

    def ring(self, d0, d1, uc, yc, r0, r1, material):
        self.feature_counts["round"] += 1
        for y in range(max(0,yc-r1-1), min(self.height,yc+r1+2)):
            for u in range(max(0,uc-r1-1), min(self.width,uc+r1+2)):
                rr=(u-uc)*(u-uc)+(y-yc)*(y-yc)
                if r0*r0 <= rr <= r1*r1:
                    self.box(d0,d1,y,y+1,u,u+1,material)

    def beveled_pilaster(self,u0,u1,y0,y1,din,dout,material):
        # Chamfered projection in the depth/horizontal section.
        self.feature_counts["sloped"] += 1
        for d in range(din,dout):
            nd=(d-din)/(max(1,dout-din-1))
            shrink=int(round(nd*1.5))
            for u in range(u0+shrink,u1-shrink):
                self.box(d,d+1,y0,y1,u,u+1,material)

    def frontmost(self):
        out={}
        for (d,y,u),material in self.cells.items():
            key=(y,u)
            if key not in out or d>out[key][0]:
                out[key]=(d,material)
        return out

    def split_to_astra_hosts(self, astra, boundary_micro_x, facade_min_z):
        """
        Convert continuous d/y/u coordinates to world-space Astra hosts.

        boundary_micro_x is the microcell coordinate of the boundary between
        the real building's front Minecraft block and the first exterior block.
        """
        hosts={}
        abs_z0=facade_min_z*16

        for (d,y,u), material in self.cells.items():
            ax=boundary_micro_x+d
            ay=y
            az=abs_z0+u

            hx=ax//16
            hy=ay//16
            hz=az//16
            lx=ax-hx*16
            ly=ay-hy*16
            lz=az-hz*16

            key=(hx,hy,hz)
            if key not in hosts:
                hosts[key]=astra.MicroVolume()
            hosts[key].set(lx,ly,lz,material)
        return hosts
