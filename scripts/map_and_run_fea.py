#!/usr/bin/env python3
import argparse, base64, os, re, struct, subprocess, sys, tarfile, time
from xml.etree import ElementTree as ET
from pathlib import Path

# ---------- VTP (VTK-XML) binary reader ----------
def _decode_vtk_base64(ba):
    raw = base64.b64decode(ba.strip())
    if len(raw) < 8: raise ValueError("VTP DataArray too short")
    n = struct.unpack("<Q", raw[:8])[0]
    return raw[8:8+n]

def _read_float32(ba):
    payload = _decode_vtk_base64(ba)
    n = len(payload)//4
    return list(struct.unpack("<" + "f"*n, payload))

def _read_int32(ba):
    payload = _decode_vtk_base64(ba)
    n = len(payload)//4
    return list(struct.unpack("<" + "i"*n, payload))

def read_vtp_binary(path):
    tree = ET.parse(path)
    piece = tree.getroot().find(".//Piece")
    if piece is None: raise ValueError("No <Piece> in VTP")
    npts  = int(piece.attrib["NumberOfPoints"])
    ncells= int(piece.attrib["NumberOfPolys"])

    pts_da = piece.find("./Points/DataArray")
    if pts_da is None or pts_da.attrib.get("format","") != "binary":
        raise ValueError("Points array not found or not binary")
    comps = int(pts_da.attrib.get("NumberOfComponents","3"))
    if comps != 3: raise ValueError(f"Unexpected NumberOfComponents for Points: {comps}")
    pts = _read_float32(pts_da.text); 
    if len(pts) != 3*npts: raise ValueError("Point array length mismatch")
    P = [tuple(pts[i:i+3]) for i in range(0, len(pts), 3)]

    conn_da = piece.find("./Polys/DataArray[@Name='connectivity']")
    off_da  = piece.find("./Polys/DataArray[@Name='offsets']")
    if conn_da is None or off_da is None: raise ValueError("Polys connectivity/offsets missing")
    if conn_da.attrib.get("format","") != "binary" or off_da.attrib.get("format","") != "binary":
        raise ValueError("Polys arrays not binary")
    conn = _read_int32(conn_da.text); offs = _read_int32(off_da.text)

    faces = []; prev = 0
    for o in offs:
        f = conn[prev:o]; cnt = o - prev; prev = o
        if cnt == 3: faces.append(tuple(f))
        else:
            for k in range(1, cnt-1):
                faces.append((f[0], f[k], f[k+1]))
    if not faces: raise ValueError("No faces parsed from Polys")

    # CellData 'p'
    p_cell = None
    for da in piece.findall("./CellData/DataArray"):
        if da.attrib.get("Name","") == "p":
            if da.attrib.get("format","") != "binary": raise ValueError("CellData p is not binary")
            p_vals = _read_float32(da.text)
            if len(p_vals) not in (ncells, len(faces)): p_vals = p_vals[:ncells]
            p_cell = p_vals; break
    if p_cell is None: raise ValueError("CellData array 'p' not found")

    # Expand p if faces were triangulated
    if len(p_cell) != len(offs):
        tri_faces, tri_p = [], []; prev = 0
        for i, o in enumerate(offs):
            f = conn[prev:o]; cnt = o-prev
            if cnt == 3:
                tri_faces.append(tuple(f)); tri_p.append(p_cell[i])
            else:
                for k in range(1, cnt-1):
                    tri_faces.append((f[0], f[k], f[k+1])); tri_p.append(p_cell[i])
            prev = o
        faces, p_cell = tri_faces, tri_p

    import numpy as np
    P  = np.array(P, dtype=float)
    F  = np.array(faces, dtype=int)
    pE = np.array(p_cell, dtype=float)
    return P, F, pE

# ---------- geometry cleaning ----------
def uniquify_vertices(V, F, tol=1e-12):
    import numpy as np
    key = np.round(V/tol)*tol
    uniq, idx = np.unique(key, axis=0, return_inverse=True)
    return uniq, idx[F]

# ---------- write CalculiX deck (guaranteed PRINTS to .dat) ----------
def write_ccx_inp(outbase, V, F, p_elem, t_shell=2.0e-3, E=70e9, nu=0.3, rho=1600.0):
    fn = outbase + ".inp"
    nnode = len(V)
    with open(fn, "w") as f:
        f.write("*HEADING\nWing shell from CFD pressure\n")
        f.write("*NODE\n")
        for i,(x,y,z) in enumerate(V, start=1):
            f.write(f"{i},{x:.9g},{y:.9g},{z:.9g}\n")

        f.write("*ELEMENT, TYPE=S3, ELSET=ALL_SHELL\n")
        for i,(a,b,c) in enumerate(F, start=1):
            f.write(f"{i},{a+1},{b+1},{c+1}\n")

        f.write("*MATERIAL, NAME=CFRP\n*ELASTIC\n{:.9g},{:.9g}\n".format(E,nu))
        f.write("*DENSITY\n{:.9g}\n".format(rho))
        f.write("*SHELL SECTION, ELSET=ALL_SHELL, MATERIAL=CFRP\n{:.9g}\n".format(t_shell))

        # Node sets
        f.write(f"*NSET, NSET=ALLNODES, GENERATE\n1,{nnode},1\n")

        # Clamp near-root nodes (min x + 1% chord)
        import numpy as np
        minx, maxx = V[:,0].min(), V[:,0].max()
        clamp_limit = minx + 0.01*(maxx-minx)
        root_nodes = (V[:,0] <= clamp_limit).nonzero()[0] + 1
        f.write("*NSET, NSET=MOUNT\n")
        for i in range(0,len(root_nodes),16):
            f.write(",".join(map(str,root_nodes[i:i+16]))+"\n")

        # --- STEP (all output requests INSIDE) ---
        f.write("*STEP\n*STATIC\n")

        # Print to .dat (what our parser reads)
        f.write("*NODE PRINT, NSET=ALLNODES\n")
        f.write("U\n")  # prints U1 U2 U3 per node
        f.write("*EL PRINT, ELSET=ALL_SHELL\n")
        f.write("S\n")  # prints 6 stress components

        # (optional) also write to .frd for viz
        f.write("*NODE FILE, NSET=ALLNODES\nU\n")
        f.write("*EL FILE, ELSET=ALL_SHELL\nS\n")

        # Loads + BC
        f.write("*DLOAD\n")
        for eid, p in enumerate(p_elem, start=1):
            f.write(f"{eid},P,{ -float(p):.9g}\n")
        f.write("*BOUNDARY\nMOUNT, 1, 6\n")

        f.write("*END STEP\n")
    return fn

# ---------- run ccx ----------
def run_ccx(outbase):
    try:
        subprocess.run(["ccx", os.path.basename(outbase)],
                       cwd=os.path.dirname(outbase) or ".",
                       check=True)
        return True, None
    except FileNotFoundError:
        return False, "ccx not found (install calculix-ccx)"
    except subprocess.CalledProcessError as e:
        return False, f"ccx failed: {e}"

# ---------- archive results ----------
def archive_run(outbase, backups_dir="backups"):
    os.makedirs(backups_dir, exist_ok=True)
    tag  = os.path.basename(outbase)
    stamp= time.strftime("%Y%m%d_%H%M%S")
    out  = os.path.join(backups_dir, f"fea_run_{tag}_{stamp}.tar.gz")
    base = os.path.dirname(outbase) or "."
    stem = os.path.basename(outbase)
    members = [f"{stem}.{ext}" for ext in ("inp","dat","frd","sta","cvg","12d")]
    with tarfile.open(out, "w:gz") as tar:
        for m in members:
            p = os.path.join(base, m)
            if os.path.exists(p):
                tar.add(p, arcname=m)
    print(f"[ok] archived → {out}")
    return out

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface-vtk", required=True, help="wing VTP (CellData p)")
    ap.add_argument("--outbase", default="fea/run1")
    ap.add_argument("--thickness", type=float, default=2.0e-3)
    ap.add_argument("--E", type=float, default=70e9)
    ap.add_argument("--nu", type=float, default=0.3)
    ap.add_argument("--rho", type=float, default=1600.0)
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    P,F,p_elem = read_vtp_binary(args.surface_vtk)
    V,F2 = uniquify_vertices(P, F, tol=1e-12)

    outdir = Path(os.path.dirname(args.outbase) or ".")
    outdir.mkdir(parents=True, exist_ok=True)

    _ = write_ccx_inp(args.outbase, V, F2, p_elem,
                      t_shell=args.thickness, E=args.E, nu=args.nu, rho=args.rho)
    ok, msg = run_ccx(args.outbase)
    if ok:
        print(f"[ok] CalculiX done. See {args.outbase}.dat / .frd")
        if not args.no_archive:
            archive_run(args.outbase)
    else:
        print(f"[err] {msg}", file=sys.stderr)

if __name__ == "__main__":
    main()
