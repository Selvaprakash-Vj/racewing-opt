#!/usr/bin/env python3
import subprocess, itertools, datetime, os, sys

AOA = [0, 3, 6, 9]
THK = [0.0020, 0.0025, 0.0030]

print(f"=== Parametric sweep started @ {datetime.datetime.now()} ===")
for a, t in itertools.product(AOA, THK):
    print(f"\n[RUN] aoa={a} deg  thickness={t} m")
    try:
        subprocess.check_call(["python3","scripts/evaluate.py","--aoa_deg",str(a),"--thickness",str(t)])
    except subprocess.CalledProcessError as e:
        print(f"[warn] case (aoa={a},thk={t}) failed: {e}")
print("\n=== Sweep done. See results/summary.csv ===")
