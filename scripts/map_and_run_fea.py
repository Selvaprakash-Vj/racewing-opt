#!/usr/bin/env python3
import argparse, os, sys, subprocess, numpy as np

def read_surface_with_vtk(path):
    try:
        import vtk
    except Exception:
        print("[err] Need python VTK. If missing, try: apt-get install -y python3-vtk9", file=sys.stderr)
        raise

    # choose reader
    if path.lower().endswith(".vtp"):
        reader = vtk.vtkXMLPolyDataReader()
    elif path.lower().endswith(".vtk"):
        reader = vtk.vtkPolyDataReader()
    else:
        raise ValueError("Unsupported surface format (use .vtp or .vtk)")

    reader.SetFileName(path)
    reader.Update()
    poly = reader.GetOutput()
    if poly is None or poly.GetNumberOfPoints()==0 or poly.GetNumberOfPolys()==0:
        raise ValueError("Empty surface")

    # points
    npts = poly.GetNumberOfPoints()
    P = np.array([poly.GetPoint(i) for i in range(npts)], dtype=float)

    # triangles
    polys = poly.GetPolys()
    polys.InitTraversal()
    ids = vtk.vtkIdList()
    faces = []
    while polys.GetNextCell(ids):
        if ids.GetNumberOfIds()==3:
            faces.append([ids.GetId(0), ids.GetId(1), ids.GetId(2)])
    F = np.asarray(faces, dtype=int)
    if F.size == 0:
        raise ValueError("No triangular faces found")

    # pressure: try point-data first, else cell-data
    p_arr = poly.GetPointData().GetArray("p")
    if p_arr is not None:
        p_pt = np.array([p_arr.GetTuple1(i) for i in range(npts)], dtype=float)
        p_elem = p_pt[F].mean(axis=1)  # avg to faces
    else:
        p_cd = poly.GetCellData().GetArray("p")
        if p_cd is None:
            raise ValueError("Pressure 'p' not found in PointData or CellData")
        # one value per cell (triangle)
        p_elem = np.array([p_cd.GetTuple1(i) for i in range(F.shape[0])], dtype=float)

    return P, F, p_elem

def uniquify_vertices(verts, faces, tol=1e-9):
    key = np.round(verts/tol)*tol
    uniq, idx = np.unique(key, axis=0, return_inverse=True)
    return uniq, idx[faces]

def write_ccx_inp(outbase, V, F, p_elem, t_shell=2.0e-3, E=70e9, nu=0.3, rho=1600.0):
    fn = outbase + ".inp"
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    with open(fn,"w") as f:
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
        minx, maxx = V[:,0].min(), V[:,0].max()
        clamp_limit = minx + 0.01*(maxx-minx)
        root_nodes = np.where(V[:,0] <= clamp_limit)[0] + 1
        f.write("*NSET, NSET=MOUNT\n")
        for i in range(0,len(root_nodes),16):
            f.write(",".join(map(str,root_nodes[i:i+16]))+"\n")
        f.write("*BOUNDARY\nMOUNT, 1, 6\n")
        f.write("*STEP\n*STATIC\n")
        f.write("*DLOAD\n")
        for eid, pr in enumerate(p_elem, start=1):
            f.write(f"{eid},P,{ -float(pr):.9g}\n")  # minus: outward +p -> inward load
        f.write("*NSET, NSET=ALL, GENERATE\n1,{N},1\n*NODE PRINT, NSET=ALL\nU\n")
        f.write("*EL PRINT, ELSET=ALL_SHELL\nS\n")
        f.write("*END STEP\n")
    return fn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface-vtk", required=True, help=".vtp/.vtk of wing patch with 'p' in PointData or CellData")
    ap.add_argument("--outbase", default="fea/run1")
    ap.add_argument("--thickness", type=float, default=2.0e-3)
    args = ap.parse_args()

    P,F,p_elem = read_surface_with_vtk(args.surface_vtk)
    V,F2 = uniquify_vertices(P, F)
    inp = write_ccx_inp(args.outbase, V, F2, p_elem, t_shell=args.thickness)

    try:
        subprocess.run(["ccx", os.path.basename(args.outbase)],
                       cwd=os.path.dirname(args.outbase), check=True)
        print(f"[ok] CalculiX done. See {args.outbase}.dat / .frd")
    except FileNotFoundError:
        print("[err] ccx not found. Install 'calculix-ccx'.", file=sys.stderr); sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("[err] CalculiX failed:", e, file=sys.stderr); sys.exit(e.returncode)

if __name__ == "__main__":
    main()
