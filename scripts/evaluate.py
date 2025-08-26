#!/usr/bin/env python3
import argparse, subprocess, os, sys, csv, datetime, re, hashlib, math, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "of_case"
POST = CASE / "postProcessing"
SCRIPTS = ROOT / "scripts"

# Make scripts/ importable (for postproc_fea)
sys.path.insert(0, str(SCRIPTS.resolve()))
from postproc_fea import extract_results  # parses max disp & stress from .dat


def _parse_gurney_mm_from_notes(notes: str) -> float:
    """
    Pull 'gurney=<num>mm' from a notes string; return 0.0 if absent.
    Robust to spaces (e.g., 'gurney = 6 mm').
    """
    try:
        m = re.search(r'gurney\s*=\s*([0-9.]+)\s*mm', notes or "", flags=re.I)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return 0.0


def run(cmd, **kw):
    print("[RUN]", " ".join(map(str, cmd)), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def parse_force_coeffs(log_path=str(CASE / "logs" / "simpleFoam.log")):
    """
    Parse Cd, Cl from simpleFoam.log by scanning the final forceCoeffs report.
    Returns (Cd, Cl, note). If not found, returns (0.0, 0.0, note).
    """
    Cd = Cl = None
    note = "from simpleFoam.log"
    if not os.path.exists(log_path):
        return 0.0, 0.0, "simpleFoam.log missing"

    cd_re = re.compile(r'\bCd:\s*([-+0-9.eE]+)')
    cl_re = re.compile(r'\bCl:\s*([-+0-9.eE]+)')

    with open(log_path, "r", errors="ignore") as fp:
        for line in fp:
            m = cd_re.search(line)
            if m:
                try:
                    Cd = float(m.group(1))
                except:
                    pass
            m = cl_re.search(line)
            if m:
                try:
                    Cl = float(m.group(1))
                except:
                    pass
    return (Cd or 0.0), (Cl or 0.0), note


def ensure_wing_vtp_symlink():
    """
    post.fo writes to postProcessing/surfaces/<time>/wingSurf.vtp.
    FEA expects postProcessing/wingSurf/<time>/wingPatch.vtp.
    Create that mirror (symlink or copy) if needed and return the chosen <time>.
    """
    surfaces = POST / "surfaces"
    if not surfaces.exists():
        return None
    times = []
    for p in surfaces.iterdir():
        if p.is_dir():
            try:
                times.append((float(p.name), p))
            except:
                pass
    if not times:
        return None
    lt = sorted(times)[-1][1].name
    dst_dir = POST / "wingSurf" / lt
    dst_dir.mkdir(parents=True, exist_ok=True)
    src = POST / "surfaces" / lt / "wingSurf.vtp"
    dst = dst_dir / "wingPatch.vtp"
    if src.exists() and not dst.exists():
        try:
            rel = os.path.relpath(src, dst_dir)
            os.symlink(rel, dst)
        except OSError:
            import shutil
            shutil.copy2(src, dst)
    return lt


def compute_cfg_hash(path: Path) -> str:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    except FileNotFoundError:
        return "none"


def load_config_dict(path: Path) -> dict:
    """
    Load a flat YAML refs file. Tries PyYAML if available; otherwise falls back
    to a minimal 'key: value' parser (comments & blanks ignored).
    """
    try:
        import yaml  # optional
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return {}
            return {str(k): data[k] for k in data}
    except Exception:
        cfg = {}
        try:
            for line in Path(path).read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.split("#", 1)[0].strip()
                # try to coerce numbers/bools
                try:
                    if v.lower() in ("true", "false"):
                        v = v.lower() == "true"
                    elif any(ch in v.lower() for ch in (".", "e")):
                        v = float(v)
                    else:
                        v = int(v)
                except Exception:
                    pass
                cfg[k] = v
        except FileNotFoundError:
            pass
        return cfg


def write_human_table(results_dir: Path):
    """
    Build /case/results/summary_table.txt from summary.csv *without modifying the CSV*.
    Handles mixed schemas (9/10/12/13 cols) in-memory and never crashes.
    """
    import pandas as pd, csv
    src = results_dir / "summary.csv"
    if not src.exists():
        print("[warn] no summary.csv yet; skipping table render")
        return

    TARGET = ["timestamp","aoa_deg","thickness_m","speed_mps","Cd","Cl",
              "max_disp_m","max_stress_Pa","fea_outbase",
              "config_path","config_hash","config_meta","notes"]

    rows = []
    with src.open("r", newline="") as fin:
        r = csv.reader(fin)
        try:
            header = next(r)
        except StopIteration:
            (results_dir/"summary_table.txt").write_text("(empty)")
            print(f"[ok] wrote summary_table.txt (empty)")
            return
        for row in r:
            cells = list(row)
            # Normalize per historical schemas
            if len(cells) == 9:
                cells.insert(3, "69.44")
                cells[9:9] = ["", "", ""]
            elif len(cells) == 10:
                cells[9:9] = ["", "", ""]
            elif len(cells) == 12:
                cells.insert(11, "")
            if len(cells) < len(TARGET):
                cells += [""] * (len(TARGET) - len(cells))
            elif len(cells) > len(TARGET):
                cells = cells[:len(TARGET)]
            rows.append(cells)

    import numpy as np
    df = pd.DataFrame(rows, columns=TARGET)
    for c in ["aoa_deg","thickness_m","speed_mps","Cd","Cl","max_disp_m","max_stress_Pa"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["L_over_D"] = df["Cl"] / (df["Cd"].abs() + 1e-12)

    cols = ["timestamp","aoa_deg","thickness_m","speed_mps","Cd","Cl","L_over_D",
            "max_disp_m","max_stress_Pa","fea_outbase","config_path","config_hash","config_meta","notes"]
    out = results_dir / "summary_table.txt"
    out.write_text(df[cols].to_string(index=False))
    print(f"[ok] Wrote human-readable table → {out}")


def main():
    ap = argparse.ArgumentParser(description="Evaluate geometry → CFD → FEA → append results")
    ap.add_argument("--aoa_deg", type=float, required=True)
    ap.add_argument("--thickness", type=float, required=True)
    ap.add_argument("--speed_mps", type=float, default=69.44, help="freestream speed")
    ap.add_argument("--config", type=str, default="/racewing-opt/config/refs.yaml", help="path to config YAML for run signature")
    ap.add_argument("--force", action="store_true", help="run even if identical case already exists")
    ap.add_argument("--note", type=str, default="", help="free-form note to store in CSV")
    ap.add_argument("--gurney_h_mm", type=float, default=0.0, help="Gurney flap height in mm (0=off)")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg_hash = compute_cfg_hash(cfg_path)
    cfg_meta = load_config_dict(cfg_path)
    cfg_meta_json = json.dumps(cfg_meta, sort_keys=True, separators=(",",":"))

    print("=== EVALUATE: geometry → set U → CFD → pressure → FEA ===")
    print(f"AOA={args.aoa_deg:.1f} deg | thickness={args.thickness:.4g} m | speed={args.speed_mps:.2f} m/s | cfg={cfg_hash}\n")

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    csv_path = results_dir / "summary.csv"

    # De-duplication guard (includes gurney height)
    if (not args.force) and csv_path.exists():
        with open(csv_path, "r", newline="") as fin:
            r = csv.DictReader(fin)
            for row in r:
                try:
                    a = float(row.get("aoa_deg","nan"))
                    t = float(row.get("thickness_m","nan"))
                    v = float(row.get("speed_mps","nan"))
                    ch = (row.get("config_hash") or "").strip()
                    gh_existing = _parse_gurney_mm_from_notes(row.get("notes",""))
                except Exception:
                    continue

                same_geom = (math.isclose(a, args.aoa_deg, abs_tol=1e-9)
                             and math.isclose(t, args.thickness, abs_tol=1e-12)
                             and math.isclose(v, args.speed_mps, abs_tol=1e-6))
                same_cfg  = (ch == cfg_hash)
                same_gurn = math.isclose(gh_existing, float(args.gurney_h_mm or 0.0), abs_tol=1e-6)

                if same_geom and same_cfg and same_gurn:
                    gtxt = f", gurney={gh_existing:g}mm"
                    print(f"[skip] identical design already in summary.csv → (aoa={args.aoa_deg}, t={args.thickness}, speed={args.speed_mps}, cfg={cfg_hash}{gtxt})")
                    print("       use --force to re-run anyway or change a parameter.")
                    return

    # 0) freestream
    run(["python3", str(SCRIPTS / "set_freestream.py"),
         "--aoa_deg", f"{args.aoa_deg:.3f}",
         "--speed_mps", f"{args.speed_mps:.6f}"])

    # 1) Geometry
    run(["python3","scripts/generate_geometry.py",
         "--aoa_deg", f"{args.aoa_deg:.1f}",
         "--out", str(CASE/"constant/triSurface/wing.stl")])
    if args.gurney_h_mm > 0:
        in_stl  = str(CASE/"constant/triSurface/wing.stl")
        out_stl = str(CASE/"constant/triSurface/wing.stl")
        run(["python3","scripts/add_gurney_to_stl.py",
             "--in", in_stl,
             "--out", out_stl,
             "--height_mm", f"{args.gurney_h_mm:.6g}",
             "--thick_mm", "3"])

    # 2) CFD
    run(["bash","scripts/run_cfd.sh", str(CASE)])
    Cd, Cl, note_coeff = parse_force_coeffs()

    # 3) PostProcess symlink
    lt = ensure_wing_vtp_symlink()
    vtp = str(POST / "wingSurf" / (lt or "0") / "wingPatch.vtp")
    print(f"[ok] using VTP: {vtp}")

    # 4) FEA
    ts_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outbase = Path("fea") / f"auto_run_{ts_tag}"
    outbase_abs = (ROOT / outbase).resolve()
    run([
        "python3","scripts/map_and_run_fea.py",
        "--surface-vtk", vtp,
        "--outbase", str(outbase_abs),
        "--thickness", f"{args.thickness:.9g}"
    ])

    # 5) Extract FEA
    dat_path = Path(str(outbase_abs) + ".dat")
    max_disp, max_stress = extract_results(str(dat_path))

    # 6) Append results
    header = ["timestamp","aoa_deg","thickness_m","speed_mps","Cd","Cl",
              "max_disp_m","max_stress_Pa","fea_outbase",
              "config_path","config_hash","config_meta","notes"]

    gurney_tag = f"gurney={float(args.gurney_h_mm or 0.0):g}mm"
    base_note  = args.note.strip()
    notes_field = f"{gurney_tag}"
    if base_note:
        notes_field += f", {base_note}"
    notes_field += f" | {note_coeff}"

    row = [
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        args.aoa_deg, args.thickness, args.speed_mps,
        Cd, Cl,
        max_disp if max_disp is not None else "",
        max_stress if max_stress is not None else "",
        str(outbase_abs),
        str(cfg_path), cfg_hash, cfg_meta_json,
        notes_field,
    ]

    def append_csv(path: Path, row):
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f, delimiter=',')
            if new:
                w.writerow(header)
            w.writerow(row)

    if (Cd == 0.0 and Cl == 0.0) or (max_disp is None) or (max_stress is None):
        append_csv(results_dir / "summary_pending.csv", row)
        print("\n=== DONE with warnings ===")
    else:
        append_csv(csv_path, row)
        print("\n=== DONE ===")
        print(f"[ok] Appended results → {csv_path}")
        print(f"[info] outbase: {outbase_abs}")

    # 7) Human-readable table
    try:
        write_human_table(results_dir)
    except Exception as e:
        print(f"[warn] table export failed: {e}")


if __name__ == "__main__":
    main()
