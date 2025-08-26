#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

csv = Path("/case/results/summary.csv")
out = Path("/case/results/summary_table.txt")

df = pd.read_csv(csv)
df.to_string(open(out,"w"), index=False)
print(f"[ok] wrote {out}")
