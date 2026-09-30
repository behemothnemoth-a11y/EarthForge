from __future__ import annotations


def merge(dst, src, overwrite=True):
    for i, value in enumerate(src.cells):
        if value is None:
            continue
        if overwrite or dst.cells[i] is None:
            dst.cells[i] = value
    return dst


def empty(astra):
    return astra.MicroVolume()


def fill_face(astra, material, x0, x1):
    v=astra.MicroVolume()
    return v.fill_box(x0,0,0,x1,16,16,material)


def floor_skin(astra, material, thickness=2):
    v=astra.MicroVolume()
    return v.fill_box(0,0,0,16,thickness,16,material)


def roof_skin(astra, material, thickness=3, setback_cells=2):
    v=astra.MicroVolume()
    # Roof starts slightly behind the front face. For an east-facing facade the
    # missing east strip prevents the roof from visually merging with parapet.
    return v.fill_box(0,0,0,16-setback_cells,thickness,16,material)


def side_skin(astra, face, material, thickness=3):
    v=astra.MicroVolume()
    if face=="west": return v.fill_box(0,0,0,thickness,16,16,material)
    if face=="north": return v.fill_box(0,0,0,16,16,thickness,material)
    if face=="south": return v.fill_box(0,0,16-thickness,16,16,16,material)
    if face=="east": return v.fill_box(16-thickness,0,0,16,16,16,material)
    raise ValueError(face)


def brick_field(astra, material, body_thickness):
    return fill_face(astra,material,16-body_thickness,16)


def reveal_opening(astra, wall, trim, reveal_depth, border=2):
    """Deep open opening: brick returns run from inner plane to the outer face."""
    v=astra.MicroVolume()
    inner=16-reveal_depth
    # left/right returns in local z
    v.fill_box(inner,0,0,16,16,border,wall)
    v.fill_box(inner,0,16-border,16,16,16,wall)
    # sill/header returns
    v.fill_box(inner,0,0,16,border,16,wall)
    v.fill_box(inner,16-border,0,16,16,16,wall)
    # pale inner edge, deliberately behind the outer face
    v.fill_box(inner,1,1,inner+2,15,3,trim)
    v.fill_box(inner,1,13,inner+2,15,15,trim)
    return v


def recessed_lattice(astra, material, setback, vertical=True, horizontal=True, thickness=1):
    v=astra.MicroVolume()
    x0=max(0,16-setback-1)
    x1=min(16,x0+2)
    if vertical:
        z0=8-thickness
        z1=8+thickness
        v.fill_box(x0,0,z0,x1,16,z1,material)
    if horizontal:
        y0=8-thickness
        y1=8+thickness
        v.fill_box(x0,y0,0,x1,y1,16,material)
    return v


def external_surround(astra, material, projection, border=2):
    """Lives in the exterior host. West edge x=0 touches the facade."""
    v=astra.MicroVolume()
    x1=max(1,min(16,projection))
    v.fill_box(0,0,0,x1,border,16,material)
    v.fill_box(0,16-border,0,x1,16,16,material)
    v.fill_box(0,0,0,x1,16,border,material)
    v.fill_box(0,0,16-border,x1,16,16,material)
    return v


def sill_header(astra, material, projection, sill=True, header=True):
    v=astra.MicroVolume()
    x1=max(1,min(16,projection))
    if sill:
        v.fill_box(0,0,0,x1,3,16,material)
    if header:
        v.fill_box(0,13,0,x1,16,16,material)
    return v


def storefront_reveal(astra, green, shadow, reveal_depth, opening_kind="display"):
    v=astra.MicroVolume()
    inner=16-reveal_depth
    # Strong green outside returns; darker inner shadow plane.
    v.fill_box(inner,0,0,16,16,2,green)
    v.fill_box(inner,0,14,16,16,16,green)
    v.fill_box(inner,0,0,16,2,16,green)
    v.fill_box(inner,14,0,16,16,16,green)
    # Shadow trim deeper in opening.
    v.fill_box(inner,2,2,inner+2,14,4,shadow)
    v.fill_box(inner,2,12,inner+2,14,14,shadow)
    if opening_kind=="door":
        # threshold only; center remains open
        v.fill_box(inner,0,2,16,2,14,shadow)
    return v


def recessed_door(astra, wood, trim, handle, setback, half):
    v=astra.MicroVolume()
    # Door plane is intentionally deep inside the host.
    x0=max(0,16-setback-2)
    x1=min(16,x0+3)
    if half=="lower":
        v.fill_box(x0,0,2,x1,16,14,wood)
        v.fill_box(x0,2,4,x1,6,12,trim)
        v.fill_box(x0,7,12,x1,9,14,handle)
    else:
        v.fill_box(x0,0,2,x1,3,14,wood)
        v.fill_box(x0,13,2,x1,16,14,wood)
        v.fill_box(x0,0,7,x1,16,9,wood)
        v.fill_box(x0,3,2,x1,5,14,trim)
    return v


def projecting_fascia(astra, green, trim, projection):
    v=astra.MicroVolume()
    x1=max(1,min(16,projection))
    v.fill_box(0,3,0,x1,13,16,green)
    v.fill_box(0,1,0,min(16,x1+2),3,16,trim)
    v.fill_box(0,13,0,min(16,x1+2),15,16,trim)
    return v


def pilaster(astra, material, projection, width=5):
    v=astra.MicroVolume()
    x1=max(1,min(16,projection))
    z0=(16-width)//2
    return v.fill_box(0,0,z0,x1,16,z0+width,material)


def awning(astra, green, trim, projection):
    v=astra.MicroVolume()
    x1=max(2,min(16,projection))
    # sloped-look stepped section
    v.fill_box(0,10,0,x1-4,13,16,green)
    v.fill_box(0,9,0,x1-1,11,16,green)
    v.fill_box(x1-3,8,0,x1,13,16,trim)
    return v


def cornice_band(astra, brick, trim, projection, stage):
    v=astra.MicroVolume()
    p=max(1,min(16,projection))
    if stage==0:
        v.fill_box(0,2,0,max(2,p-5),5,16,trim)
    elif stage==1:
        v.fill_box(0,5,0,max(3,p-3),9,16,brick)
        v.fill_box(0,7,0,max(4,p-1),10,16,trim)
    elif stage==2:
        v.fill_box(0,10,0,p,13,16,trim)
        v.fill_box(0,13,0,max(3,p-2),16,16,trim)
    else:
        raise ValueError(stage)
    return v


def bracket(astra, trim, projection):
    v=astra.MicroVolume()
    p=max(4,min(16,projection))
    v.fill_box(0,0,5,p-3,7,11,trim)
    v.fill_box(0,6,6,p,12,10,trim)
    return v


def parapet_field(astra, brick, trim, setback, cap=True):
    v=astra.MicroVolume()
    # Because this is the building host, x starts behind the outer wall plane.
    x0=max(0,setback)
    v.fill_box(x0,0,0,16,16,16,brick)
    if cap:
        v.fill_box(max(0,x0-2),13,0,16,16,16,trim)
    return v


def roundel(astra, brick, trim, setback):
    v=parapet_field(astra,brick,trim,setback,True)
    x0=max(0,setback-2)
    cy=8; cz=8
    for y in range(16):
        for z in range(16):
            d=(y-cy)*(y-cy)+(z-cz)*(z-cz)
            if 9 <= d <= 23:
                v.fill_box(x0,y,z,16,y+1,z+1,trim)
    return v


def rear_opening(astra, wall, trim, depth=6):
    v=astra.MicroVolume()
    # West face opening; wall returns project eastward into the host.
    v.fill_box(0,0,0,depth,16,2,wall)
    v.fill_box(0,0,14,depth,16,16,wall)
    v.fill_box(0,0,0,depth,2,16,wall)
    v.fill_box(0,14,0,depth,16,16,wall)
    v.fill_box(depth-2,1,1,depth,15,3,trim)
    v.fill_box(depth-2,1,13,depth,15,15,trim)
    return v
