#!/usr/bin/env python3
"""
Plot + report generator for rear-wing optimization.
- Picks the true best design at 69.44 m/s (by L/D, with basic sanity filters).
- Highlights Gurney height (parsed from notes).
- Produces:
    - L/D vs AoA @ 69.44 m/s  (all designs)
    - L/D vs AoA @ 69.44 m/s  (Gurney=6 mm only, if present)
    - Displacement vs Speed for best config
    - Stress vs Speed for best config
- Writes /case/results/report.md with best & worst tables.
"""

import pandas as pd, numpy as np, matplotlib.pyplot as plt, datetime as _dt, re
from pathlib import Path

ROOT = Path("/case")
RES  = ROOT / "results"
PLOTS = RES / "plots"
CSV  = RES / "summary.csv"

PLOTS.mkdir(parents=True, exist_ok=True)

def _parse_gurney_mm(notes: str) -> float:
    """Pull 'gurney=<num>mm' from notes; 0.0 if absent."""
    if not notes: return 0.0
    m = re.search(r"gurney\s*=\s*([0-9.]+)\s*mm", str(notes), flags=re.I)
    try:
        return float(m.group(1)) if m else 0.0
    except Exception:
        return 0.0

def _load_df():
    if not CSV.exists():
        raise SystemExit(f"[err] {CSV} not found")
    df = pd.read_csv(CSV)
    # numeric coercions
    for c in ["aoa_deg","thickness_m","speed_mps","Cd","Cl","max_disp_m","max_stress_Pa"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # derived
    df["L_over_D"] = df["Cl"] / (df["Cd"].abs() + 1e-12)
    df["gurney_mm"] = df.get("notes","").map(_parse_gurney_mm)
    return df

def _clean_at_speed(df, speed=69.44, tol=0.05):
    q = df[df["speed_mps"].sub(speed).abs() <= tol].copy()
    # Basic sanity filters: drop absurd/failed values
    q = q[np.isfinite(q["Cd"]) & np.isfinite(q["Cl"]) & np.isfinite(q["L_over_D"])]
    q = q[(q["Cd"].abs() < 1.0) & (q["Cl"].abs() < 5.0)]
    return q

def _pick_best_at_speed(df, speed=69.44):
    q = _clean_at_speed(df, speed)
    if q.empty:
        return None
    q = q.sort_values("L_over_D", ascending=False)
    return q.iloc[0].to_dict()

def _ld_vs_aoa_plot(df, path_png, title):
    if df.empty:
        return False
    g = df.groupby("aoa_deg", as_index=False)["L_over_D"].max().sort_values("aoa_deg")
    plt.figure(figsize=(6.5,4.0))
    plt.plot(g["aoa_deg"], g["L_over_D"], marker="o")
    plt.xlabel("AoA (deg)")
    plt.ylabel("L/D")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path_png, dpi=160)
    plt.close()
    print(f"[ok] wrote {path_png}")
    return True

def _xy_plot(x, y, xlabel, ylabel, title, path_png):
    if len(x) == 0:
        return False
    plt.figure(figsize=(6.5,4.0))
    plt.plot(x, y, marker="o")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path_png, dpi=160)
    plt.close()
    print(f"[ok] wrote {path_png}")
    return True

def _speed_rows_for_config(df, aoa, thick, gurney_mm):
    q = df[
        (df["aoa_deg"].sub(aoa).abs() <= 1e-6) &
        (df["thickness_m"].sub(thick).abs() <= 1e-9) &
        (df["gurney_mm"].sub(gurney_mm).abs() <= 1e-6)
    ].copy()
    q = q[np.isfinite(q["speed_mps"])].sort_values("speed_mps")
    return q

def main():
    df = _load_df()

    # ===== 1) Find true best at 69.44 m/s =====
    best = _pick_best_at_speed(df, 69.44)
    if not best:
        print("[warn] no valid rows at 69.44 m/s")
        return

    best_aoa   = float(best["aoa_deg"])
    best_t     = float(best["thickness_m"])
    best_ld    = float(best["L_over_D"])
    best_cd    = float(best["Cd"])
    best_cl    = float(best["Cl"])
    best_gurn  = float(best.get("gurney_mm", 0.0))

    # ===== 2) Plots =====
    at69 = _clean_at_speed(df, 69.44)

    # 2a) L/D vs AoA (all)
    png_all = PLOTS / "LD_vs_AoA_at_69p44ms.png"
    _ld_vs_aoa_plot(at69, png_all, "L/D vs AoA @ 69.44 m/s (all)")

    # 2b) L/D vs AoA for Gurney=6 mm (only if present)
    at69_g6 = at69[at69["gurney_mm"].sub(6.0).abs() <= 1e-6].copy()
    png_g6 = PLOTS / "LD_vs_AoA_at_69p44ms_Gurney6mm.png"
    if not at69_g6.empty:
        _ld_vs_aoa_plot(at69_g6, png_g6, "L/D vs AoA @ 69.44 m/s (Gurney = 6 mm)")

    # 2c) Speed envelopes for BEST config (disp/stress)
    env = _speed_rows_for_config(df, best_aoa, best_t, best_gurn)
    disp_png = PLOTS / "Disp_vs_Speed_best.png"
    stress_png = PLOTS / "Stress_vs_Speed_best.png"
    if not env.empty:
        _xy_plot(env["speed_mps"], env["max_disp_m"],
                 "Speed (m/s)", "Max displacement (m)",
                 f"Displacement vs Speed (AoA={best_aoa:.1f}°, t={best_t:g} m, G={best_gurn:g} mm)",
                 disp_png)
        _xy_plot(env["speed_mps"], env["max_stress_Pa"],
                 "Speed (m/s)", "Max stress (Pa)",
                 f"Stress vs Speed (AoA={best_aoa:.1f}°, t={best_t:g} m, G={best_gurn:g} mm)",
                 stress_png)

    # ===== 3) Tables: Top & Worst @ 69.44 =====
    rank = at69.sort_values("L_over_D", ascending=False).copy()
    topN = rank.head(12).copy()
    botN = rank.tail(12).copy()

    show_cols = ["timestamp","aoa_deg","thickness_m","speed_mps","Cd","Cl","L_over_D","max_disp_m","max_stress_Pa","notes"]
    for col in show_cols:
        if col not in topN.columns: topN[col] = ""
        if col not in botN.columns: botN[col] = ""
    top_txt = topN[show_cols].to_string(index=False)
    bot_txt = botN[show_cols].to_string(index=False)

    # ===== 4) Write report.md =====
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# Rear Wing Optimization Report")
    lines.append("")
    lines.append(f"_Generated: {ts}_")
    lines.append("")
    lines.append("## Best at 69.44 m/s (by L/D with sanity filters)")
    lines.append("")
    lines.append(f"- **AoA**: {best_aoa:.1f}°")
    lines.append(f"- **Thickness**: {best_t:g} m")
    lines.append(f"- **Gurney**: {best_gurn:g} mm")
    lines.append(f"- **L/D**: {best_ld:.3f}")
    lines.append(f"- **Cd / Cl**: {best_cd:.6f} / {best_cl:.6f}")
    if "max_disp_m" in df.columns and "max_stress_Pa" in df.columns:
        lines.append(f"- **Max disp**: {pd.to_numeric(pd.Series([best.get('max_disp_m', np.nan)])).iloc[0]:.6g} m")
        lines.append(f"- **Max stress**: {pd.to_numeric(pd.Series([best.get('max_stress_Pa', np.nan)])).iloc[0]:.3e} Pa")
    lines.append("")
    lines.append("## Plots")
    lines.append("")
    lines.append(f"- L/D vs AoA @ 69.44 m/s (all): `{png_all}`")
    if not at69_g6.empty:
        lines.append(f"- L/D vs AoA @ 69.44 m/s (Gurney=6 mm): `{png_g6}`")
    if not env.empty:
        lines.append(f"- Displacement vs Speed (best): `{disp_png}`")
        lines.append(f"- Stress vs Speed (best): `{stress_png}`")
    lines.append("")
    lines.append("## Top designs @ 69.44 m/s (by L/D)")
    lines.append("")
    lines.append("```")
    lines.append(top_txt)
    lines.append("```")
    lines.append("")
    lines.append("## Worst designs @ 69.44 m/s (by L/D)")
    lines.append("")
    lines.append("```")
    lines.append(bot_txt)
    lines.append("```")

    (RES / "report.md").write_text("\n".join(lines))
    print(f"[ok] wrote {(RES / 'report.md')}")
    print("[done] plot_results complete.")

if __name__ == "__main__":
    main()
