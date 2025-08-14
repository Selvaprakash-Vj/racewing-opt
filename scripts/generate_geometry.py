#!/usr/bin/env python3
import numpy as np, argparse

def rot2d(xy, deg, origin_x=0.075):  # rotate about 25% chord (0.25*chord) by default
    th = np.deg2rad(deg)
    R = np.array([[np.cos(th), -np.sin(th)],
                  [np.sin(th),  np.cos(th)]])
    xy_shift = xy - np.array([origin_x, 0.0])
    return xy_shift @ R.T + np.array([origin_x, 0.0])

def naca4(m=0.0, p=0.0, t=12.0, n=121):
    x = np.linspace(0,1,n)
    yt = 5*t/100*(0.2969*np.sqrt(np.clip(x,1e-9,1)) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
    up = np.c_[x,  yt]
    lo = np.c_[x, -yt]
    return up, lo

def write_ascii_stl(path, V, F, name="wing"):
    with open(path,"w") as f:
        f.write(f"solid {name}\n")
        for (i,j,k) in F:
            v1,v2,v3 = V[i],V[j],V[k]
            n = np.cross(v2-v1, v3-v1); n/= (np.linalg.norm(n)+1e-12)
            f.write(f" facet normal {n[0]} {n[1]} {n[2]}\n  outer loop\n")
            for v in (v1,v2,v3):
                f.write(f"   vertex {v[0]} {v[1]} {v[2]}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")

def build_wing(chord=0.3, span=0.8, thickness=12.0, aoa_deg=0.0, n=121, gurney_h=0.0):
    up, lo = naca4(t=thickness, n=n)
    # rotate airfoil in 2D about 25% chord
    up_r = rot2d(up, aoa_deg, origin_x=0.25)
    lo_r = rot2d(lo, aoa_deg, origin_x=0.25)
    # optional Gurney flap at TE, height as fraction of chord (upwards)
    if gurney_h > 0:
        h = gurney_h
        # add a tiny vertical tab at x=1
        gf = np.array([[1.0,0.0],[1.0, h]])
        # stitch into lower surface near TE
        lo_r = np.vstack([lo_r[:-1], gf, lo_r[-1:]])
        up_r = np.vstack([up_r])

    # scale to 3D
    up3 = np.c_[up_r[:,0]*chord, up_r[:,1]*chord, np.zeros(len(up_r))]
    lo3 = np.c_[lo_r[:,0]*chord, lo_r[:,1]*chord, np.zeros(len(lo_r))]
    # extrude to +/- span/2
    def extrude(strip,z): s = strip.copy(); s[:,2]=z; return s
    upA, upB = extrude(up3,-span/2), extrude(up3, span/2)
    loA, loB = extrude(lo3, span/2), extrude(lo3,-span/2)  # reverse to keep normals outward

    V=[]; F=[]
    def add_strip(a,b):
        start=len(V); V.extend(a); V.extend(b)
        na=len(a)
        for i in range(na-1):
            i0=start+i; i1=start+i+1; j0=start+na+i; j1=start+na+i+1
            F.append((i0,j0,i1)); F.append((i1,j0,j1))
    add_strip(upA,upB)    # top
    add_strip(loB,loA)    # bottom
    # LE, TE, tips
    add_strip(np.vstack([upA[0], loA[-1]]), np.vstack([upB[0], loB[-1]]))  # LE
    add_strip(np.vstack([loA[0], upA[-1]]), np.vstack([loB[0], upB[-1]]))  # TE
    add_strip(upA[::-1], loA[::-1])  # left tip
    add_strip(loB, upB)              # right tip
    return np.asarray(V,float), np.asarray(F,int)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--chord", type=float, default=0.30)
    ap.add_argument("--span", type=float, default=0.80)
    ap.add_argument("--thickness_pct", type=float, default=12.0)
    ap.add_argument("--aoa_deg", type=float, default=0.0)
    ap.add_argument("--gurney_chord_frac", type=float, default=0.0)  # e.g. 0.01 = 1% chord
    args=ap.parse_args()
    V,F = build_wing(chord=args.chord, span=args.span, thickness=args.thickness_pct,
                     aoa_deg=args.aoa_deg, gurney_h=args.gurney_chord_frac)
    write_ascii_stl(args.out, V, F, name="wing")
    print(f"[ok] STL: {args.out}  verts={len(V)} tris={len(F)}  AoA={args.aoa_deg}deg  Gurney={args.gurney_chord_frac*100:.1f}%c")
