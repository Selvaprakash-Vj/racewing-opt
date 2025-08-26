#!/usr/bin/env python3
"""
Append a small rectangular Gurney flap to an **ASCII** STL wing.

Assumptions (matching your coords now):
- Flow is +X (streamwise); trailing edge is at max X of the STL.
- Downforce is along −Y (we set liftDir = (0 -1 0)); flap extrudes **downward (−Y)**.
- Span is Z; we extend the tab across the full Z-span of the STL.
- STL must be ASCII; if binary is detected, we fail gracefully.

Usage:
  add_gurney_to_stl.py --in wing.stl --out wing.stl --height_mm 10 --thick_mm 3 [--inset_mm 0]
"""
import argparse, sys
from pathlib import Path
import base64, struct

def read_ascii_stl_points(fn):
    p = Path(fn)
    txt = p.read_text(errors="ignore")
    if not txt.lstrip().lower().startswith("solid"):
        raise RuntimeError("Binary STL detected or file doesn't start with 'solid' — ASCII only.")
    import re
    pts=[]
    for m in re.finditer(r'vertex\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)', txt, flags=re.I):
        x,y,z = map(float, m.groups())
        pts.append((x,y,z))
    if not pts:
        raise RuntimeError("No vertices found in ASCII STL.")
    xs=[x for x,_,_ in pts]; ys=[y for _,y,_ in pts]; zs=[z for _,_,z in pts]
    bounds = (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))
    return txt, bounds

def write_ascii_stl_with_append(in_txt, out_fn, append_triangles):
    # Strip trailing endsolid so we can append
    txt = in_txt.rstrip()
    lower = txt.lower()
    if not lower.endswith("endsolid") and "endsolid" not in lower:
        txt = txt + "\nendsolid\n"
        lower = txt.lower()
    idx = lower.rfind("endsolid")
    body = txt[:idx].rstrip()
    tail = txt[idx:].splitlines()[-1] if idx >= 0 else "endsolid"
    facets=[]
    for tri in append_triangles:
        (x1,y1,z1),(x2,y2,z2),(x3,y3,z3)=tri
        facets.append(
            "  facet normal 0 0 0\n"
            "    outer loop\n"
            f"      vertex {x1} {y1} {z1}\n"
            f"      vertex {x2} {y2} {z2}\n"
            f"      vertex {x3} {y3} {z3}\n"
            "    endloop\n"
            "  endfacet"
        )
    out = body + "\n" + "\n".join(facets) + "\n" + tail + "\n"
    Path(out_fn).write_text(out)

def make_gurney_prism_tris(x0, z0, z1, y_base, h, tx):
    """
    Rectangular tab:
      - thickness tx along +X:  x in [x0, x0+tx]
      - span along Z:           z in [z0, z1]
      - height along −Y:        y in [y_base-h, y_base]
    """
    y_top = y_base
    y_bot = y_base + h  # upward (+Y)
    A = (x0,    y_top, z0)  # top, inner
    B = (x0+tx, y_top, z0)  # top, outer
    C = (x0+tx, y_top, z1)
    D = (x0,    y_top, z1)
    E = (x0,    y_bot, z0)  # bottom (down), inner
    F = (x0+tx, y_bot, z0)
    G = (x0+tx, y_bot, z1)
    H = (x0,    y_bot, z1)
    tris=[]
    # top face (y = y_top)
    tris += [(A,B,C),(A,C,D)]
    # bottom face (y = y_bot)
    tris += [(E,G,F),(E,H,G)]
    # front face (x = x0+tx)
    tris += [(B,F,G),(B,G,C)]
    # back face (x = x0)
    tris += [(A,E,H),(A,H,D)]
    # left face (z = z0)
    tris += [(A,E,F),(A,F,B)]
    # right face (z = z1)
    tris += [(D,G,H),(D,C,G)]
    return tris

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--height_mm", type=float, required=True, help="Gurney height (mm), extruded in −Y")
    ap.add_argument("--thick_mm", type=float, default=3.0, help="tab thickness (mm) in +X")
    ap.add_argument("--inset_mm", type=float, default=0.0, help="shift in X from TE (positive = downstream)")
    args = ap.parse_args()

    if args.height_mm <= 0 or args.thick_mm <= 0:
        # pass-through
        Path(args.out).write_text(Path(args.inp).read_text())
        print("[info] zero/negative height or thickness → no flap appended")
        return

    txt, (xmin,xmax,ymin,ymax,zmin,zmax) = read_ascii_stl_points(args.inp)
    h  = args.height_mm/1000.0
    tx = args.thick_mm/1000.0
    x0 = xmax + args.inset_mm/1000.0
    y_base = ymax  # anchor at top (suction side)
    z0, z1 = zmin, zmax

    tris = make_gurney_prism_tris(x0, z0, z1, y_base, h, tx)
    write_ascii_stl_with_append(txt, args.out, tris)
    print(f"[ok] appended Gurney: height={args.height_mm} mm down, thick={args.thick_mm} mm, TE x≈{xmax:.6g}")

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"[err] {e}", file=sys.stderr)
        sys.exit(1)
