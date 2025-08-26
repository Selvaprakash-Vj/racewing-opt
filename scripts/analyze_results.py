#!/usr/bin/env python3
import argparse, pandas as pd, numpy as np
from pathlib import Path
import sys, csv

def load_and_normalize(src: Path):
    # Handle mixed schemas (old 9-col vs new 10-col with speed)
    cols_target = ["timestamp","aoa_deg","thickness_m","speed_mps","Cd","Cl","max_disp_m","max_stress_Pa","fea_outbase","notes"]
    if not src.exists():
        raise SystemExit("summary.csv not found")
    df_raw = pd.read_csv(src, dtype=str).fillna("")
    for c in cols_target:
        if c not in df_raw.columns:
            df_raw[c] = ""
    df = df_raw[cols_target].copy()
    # Numerics
    for c in ["aoa_deg","thickness_m","speed_mps","Cd","Cl","max_disp_m","max_stress_Pa"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def enrich(df: pd.DataFrame, disp_limit_m: float, stress_limit_pa: float):
    eps = 1e-12
    df["L_over_D"]   = df["Cl"] / (df["Cd"].abs() + eps)
    df["pass_disp"]  = df["max_disp_m"]    <= disp_limit_m
    df["pass_stress"]= df["max_stress_Pa"] <= stress_limit_pa
    df["PASS"]       = df["pass_disp"] & df["pass_stress"]
    df["PASS_rank"]  = np.where(df["PASS"], 0, 1)  # pass first
    # Safety utilization & margins
    df["disp_util_%"]    = (df["max_disp_m"] / disp_limit_m * 100).round(2)
    df["stress_util_%"]  = (df["max_stress_Pa"] / stress_limit_pa * 100).round(2)
    df["disp_margin_mm"] = ((disp_limit_m - df["max_disp_m"]) * 1e3).round(3)
    df["stress_margin_MPa"] = ((stress_limit_pa - df["max_stress_Pa"]) / 1e6).round(3)
    return df

def main():
    ap = argparse.ArgumentParser(description="Analyze summary.csv with flexible sorting and constraint checks.")
    ap.add_argument("--disp_limit_m", type=float, default=0.010, help="max allowed deflection [m]")
    ap.add_argument("--stress_limit_pa", type=float, default=700e6, help="max allowed von Mises [Pa]")
    ap.add_argument("--sort", default="L_over_D", help="column to sort by (any header, e.g., L_over_D, thickness_m, speed_mps, aoa_deg, Cd, Cl, disp_util_%, timestamp, etc.)")
    ap.add_argument("--ascending", action="store_true", help="sort ascending (default is auto: desc for L_over_D/Cl, asc otherwise)")
    ap.add_argument("--top", type=int, default=12, help="how many rows to print")
    ap.add_argument("--filter_speed", type=float, help="optional: only keep rows with this speed_mps (±0.05)")
    ap.add_argument("--filter_aoa", type=float, help="optional: only keep rows with this aoa_deg (±1e-6)")
    ap.add_argument("--filter_thickness", type=float, help="optional: only keep rows with this thickness_m (±1e-9)")
    ap.add_argument("--out_csv", default="/case/results/summary_analyzed.csv", help="write enriched CSV here")
    ap.add_argument("--out_table", default="/case/results/summary_analyzed.txt", help="write pretty table here")
    args = ap.parse_args()

    src = Path("/case/results/summary.csv")
    df  = load_and_normalize(src)
    df  = enrich(df, args.disp_limit_m, args.stress_limit_pa)

    # Optional filters
    if args.filter_speed is not None:
        df = df[np.isclose(df["speed_mps"], args.filter_speed, atol=0.05)]
    if args.filter_aoa is not None:
        df = df[np.isclose(df["aoa_deg"], args.filter_aoa, atol=1e-6)]
    if args.filter_thickness is not None:
        df = df[np.isclose(df["thickness_m"], args.filter_thickness, atol=1e-9)]

    if df.empty:
        print("[warn] No rows after filtering; nothing to analyze.")
        sys.exit(0)

    # Determine default sort direction if not explicitly set
    sort_col = args.sort
    if sort_col not in df.columns:
        # Allow friendly aliases
        aliases = {"disp":"max_disp_m", "stress":"max_stress_Pa"}
        sort_col = aliases.get(sort_col, sort_col)
        if sort_col not in df.columns:
            print(f"[warn] sort column '{args.sort}' not found. Using L_over_D.")
            sort_col = "L_over_D"

    if args.ascending:
        asc = True
    else:
        # auto direction: desc for "beneficial" metrics, asc otherwise
        asc = False if sort_col in ["L_over_D","Cl"] else True

    # Always put PASS first, then sort by chosen column
    df_sorted = df.sort_values(by=["PASS_rank", sort_col], ascending=[True, asc], kind="mergesort").reset_index(drop=True)

    # Save enriched CSV
    df_sorted.to_csv(args.out_csv, index=False)

    # Pretty table view (compact but informative)
    show = ["PASS","aoa_deg","thickness_m","speed_mps","Cd","Cl","L_over_D","config_path","config_hash",
            "max_disp_m","disp_util_%","disp_margin_mm",
            "max_stress_Pa","stress_util_%","stress_margin_MPa",
            "fea_outbase","timestamp"]
    for c in show:
        if c not in df_sorted.columns:
            df_sorted[c] = ""
    view = df_sorted[show].copy()
    view["PASS"] = view["PASS"].map({True:"✓", False:"✗"})

    with open(args.out_table, "w") as f:
        f.write(view.to_string(index=False))

    print(f"[ok] wrote analyzed CSV → {args.out_csv}")
    print(f"[ok] wrote pretty table → {args.out_table}")
    # --- Auto print best and worst N ---
    N = args.top or 5
    print(f"\n=== Top {N} designs (by {args.sort}) ===")
    print(df_sorted.head(N).to_string(index=False))
    print(f"\n=== Worst {N} designs (by {args.sort}) ===")
    print(df_sorted.tail(N).to_string(index=False))
    print("\nTop rows:")
    print(view.head(args.top).to_string(index=False))

if __name__ == "__main__":
    main()