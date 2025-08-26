#!/usr/bin/env python3
import argparse, csv, math, subprocess, time
from pathlib import Path

ROOT = Path("/case")
RESULTS = ROOT/"results"
CSV_PATH = RESULTS/"summary.csv"
EVAL = ROOT/"scripts"/"evaluate.py"

def get_row_key(row):
    try:
        return (float(row.get("aoa_deg","nan")),
                float(row.get("thickness_m","nan")),
                float(row.get("speed_mps","nan")),
                (row.get("config_hash") or "").strip())
    except: return None

def load_existing():
    rows = []
    if not CSV_PATH.exists(): return rows
    with open(CSV_PATH,"r",newline="") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

def find_best(rows, disp_lim, stress_lim, thickness, speed, cfg_hash=None):
    best=None
    for row in rows:
        try:
            if abs(float(row.get("thickness_m","nan"))-thickness)>1e-12: continue
            if abs(float(row.get("speed_mps","nan"))-speed)>1e-6: continue
            if cfg_hash and (row.get("config_hash") or "").strip()!=cfg_hash: continue
            Cd=float(row["Cd"]); Cl=float(row["Cl"])
            disp=float(row["max_disp_m"]); stress=float(row["max_stress_Pa"])
        except: continue
        pass_ok = (disp<=disp_lim) and (stress<=stress_lim)
        L_over_D = Cl/(abs(Cd)+1e-12)
        cand = dict(aoa=float(row["aoa_deg"]), L_over_D=L_over_D, pass_ok=pass_ok, row=row)
        if best is None or (cand["pass_ok"], cand["L_over_D"]) > (best["pass_ok"], best["L_over_D"]):
            best=cand
    return best

def run_eval(aoa, thickness, speed):
    cmd=["python3", str(EVAL),
         "--aoa_deg", f"{aoa}",
         "--thickness", f"{thickness}",
         "--speed_mps", f"{speed}"]
    print("[RUN]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main():
    ap=argparse.ArgumentParser(description="Search AoA for max L/D under constraints")
    ap.add_argument("--speed_mps", type=float, default=69.44)
    ap.add_argument("--thickness_m", type=float, default=0.0025)
    ap.add_argument("--disp_limit_m", type=float, default=0.010)
    ap.add_argument("--stress_limit_pa", type=float, default=700e6)
    ap.add_argument("--aoa_min", type=float, default=4.0)
    ap.add_argument("--aoa_max", type=float, default=16.0)
    ap.add_argument("--aoa_step", type=float, default=1.0)
    ap.add_argument("--config_hash", type=str, default="")
    args=ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    target_aoas=[]
    a=args.aoa_min
    while a<=args.aoa_max+1e-9:
        target_aoas.append(round(a,3))
        a+=args.aoa_step

    # Existing data
    rows=load_existing()
    have=set()
    for row in rows:
        k=get_row_key(row)
        if k: have.add(k)

    # Run missing AoAs
    for aoa in target_aoas:
        key=(aoa, args.thickness_m, args.speed_mps, args.config_hash.strip())
        if key in have:
            print(f"[skip] already have aoa={aoa}°, t={args.thickness_m}, V={args.speed_mps} (cfg={args.config_hash or '*'})")
            continue
        run_eval(aoa, args.thickness_m, args.speed_mps)

    # Re-load and report best
    rows=load_existing()
    best=find_best(rows, args.disp_limit_m, args.stress_limit_pa,
                   args.thickness_m, args.speed_mps, cfg_hash=args.config_hash.strip() or None)
    if best:
        row=best["row"]
        print("\n=== Best AoA (constraints-first, then L/D) ===")
        print(f"AoA: {best['aoa']} deg | L/D: {best['L_over_D']:.3f} | PASS: {best['pass_ok']}")
        print(f"Cd: {row.get('Cd')} | Cl: {row.get('Cl')}")
        print(f"disp: {row.get('max_disp_m')} m | stress: {row.get('max_stress_Pa')} Pa")
        print(f"speed: {row.get('speed_mps')} m/s | t: {row.get('thickness_m')} m")
        print(f"FEA: {row.get('fea_outbase')} | timestamp: {row.get('timestamp')}")
    else:
        print("[warn] No valid rows found for these filters.")

if __name__=="__main__":
    main()
