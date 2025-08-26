#!/usr/bin/env python3
import argparse, csv, math, subprocess
from pathlib import Path

ROOT = Path("/case")
RESULTS = ROOT/"results"
CSV_PATH = RESULTS/"summary.csv"
EVAL = ROOT/"scripts"/"evaluate.py"

def read_rows():
    rows=[]
    if not CSV_PATH.exists(): return rows
    with open(CSV_PATH,"r",newline="") as f:
        r=csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

def L_over_D(row):
    try:
        Cd=float(row["Cd"]); Cl=float(row["Cl"])
        return Cl/(abs(Cd)+1e-12)
    except: return float("-inf")

def passes(row, disp_lim, stress_lim):
    try:
        d=float(row["max_disp_m"]); s=float(row["max_stress_Pa"])
        return (d<=disp_lim) and (s<=stress_lim)
    except: return False

def has_row(rows, aoa, t, v, cfg_hash=""):
    for r in rows:
        try:
            if (abs(float(r.get("aoa_deg","nan"))-aoa)<1e-9 and
                abs(float(r.get("thickness_m","nan"))-t)<1e-12 and
                abs(float(r.get("speed_mps","nan"))-v)<1e-6 and
                (cfg_hash=="" or (r.get("config_hash") or "").strip()==cfg_hash)):
                return True
        except:
            continue
    return False

def run_eval(aoa,t,v,config=None):
    cmd=["python3", str(EVAL),
         "--aoa_deg", f"{aoa}",
         "--thickness", f"{t}",
         "--speed_mps", f"{v}"]
    if config: cmd += ["--config", config]
    print("[RUN]"," ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main():
    ap=argparse.ArgumentParser(description="Joint search over AoA and thickness to maximize L/D under constraints")
    ap.add_argument("--speed_mps", type=float, default=69.44)
    ap.add_argument("--aoa_min", type=float, default=8.0)
    ap.add_argument("--aoa_max", type=float, default=18.0)
    ap.add_argument("--aoa_step", type=float, default=1.0)
    ap.add_argument("--t_list", type=float, nargs="+", default=[0.0015,0.0020,0.0025,0.0030])
    ap.add_argument("--disp_limit_m", type=float, default=0.010)
    ap.add_argument("--stress_limit_pa", type=float, default=700e6)
    ap.add_argument("--config_hash", type=str, default="")
    ap.add_argument("--config_path", type=str, default="", help="optional explicit config file for evaluate.py")
    args=ap.parse_args()

    # Build AoA grid
    aoas=[]
    a=args.aoa_min
    while a<=args.aoa_max+1e-9:
        aoas.append(round(a,3))
        a+=args.aoa_step

    # Evaluate missing points
    rows = read_rows()
    for t in args.t_list:
        for aoa in aoas:
            if has_row(rows, aoa, t, args.speed_mps, cfg_hash=args.config_hash.strip()):
                print(f"[skip] aoa={aoa}°, t={t} m already present")
                continue
            run_eval(aoa, t, args.speed_mps, config=args.config_path if args.config_path else None)
    rows = read_rows()

    # Pick best: prefer PASS, then max L/D
    best=None
    for r in rows:
        try:
            if abs(float(r.get("speed_mps","nan"))-args.speed_mps)>1e-6: continue
            if float(r.get("thickness_m","nan")) not in args.t_list: continue
            aoa=float(r.get("aoa_deg","nan"))
            if aoa<args.aoa_min-1e-9 or aoa>args.aoa_max+1e-9: continue
        except: 
            continue
        ok = passes(r, args.disp_limit_m, args.stress_limit_pa)
        score = L_over_D(r)
        cand = dict(row=r, ok=ok, score=score)
        if (best is None) or ((cand["ok"], cand["score"]) > (best["ok"], best["score"])):
            best = cand

    if not best:
        print("[warn] No valid results in the searched set."); return

    r = best["row"]
    print("\n=== Best design (constraints-first, then L/D) ===")
    print(f"AoA: {r.get('aoa_deg')} deg | t: {r.get('thickness_m')} m | speed: {r.get('speed_mps')} m/s")
    print(f"L/D: {L_over_D(r):.3f} | PASS: {best['ok']}")
    print(f"Cd: {r.get('Cd')} | Cl: {r.get('Cl')}")
    print(f"disp: {r.get('max_disp_m')} m | stress: {r.get('max_stress_Pa')} Pa")
    print(f"FEA: {r.get('fea_outbase')} | timestamp: {r.get('timestamp')}")
    # mini table (sorted by t then AoA)
    subset=[]
    for r2 in rows:
        try:
            if abs(float(r2.get('speed_mps','nan'))-args.speed_mps)>1e-6: continue
            if float(r2.get('thickness_m','nan')) not in args.t_list: continue
            aoa=float(r2.get('aoa_deg','nan'))
            if aoa<args.aoa_min-1e-9 or aoa>args.aoa_max+1e-9: continue
        except:
            continue
        subset.append(r2)
    subset.sort(key=lambda q:(float(q.get('thickness_m','inf')), float(q.get('aoa_deg','inf'))))
    print("\n t [m]   AoA [deg]   Cd        Cl        L/D     disp [m]    stress [Pa]")
    for q in subset:
        try:
            print(f"{float(q['thickness_m']):7.4f}   {float(q['aoa_deg']):9.1f}  "
                  f"{float(q['Cd']):.6f}  {float(q['Cl']):.6f}  {L_over_D(q):6.3f}  "
                  f"{float(q['max_disp_m']):.6e}  {float(q['max_stress_Pa']):.6e}")
        except: 
            continue

if __name__=="__main__":
    main()
