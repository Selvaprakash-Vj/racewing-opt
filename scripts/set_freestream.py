#!/usr/bin/env python3
import argparse, math, re
from pathlib import Path
CASE = Path("/case/of_case")
U_FILE = CASE / "0" / "U"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoa_deg", type=float, required=True, help="AoA in degrees (rotate in XY; Uy=+sin, Uz=0)")
    ap.add_argument("--speed_mps", type=float, required=True)
    args = ap.parse_args()
    a = math.radians(args.aoa_deg)
    Ux = args.speed_mps*math.cos(a)
    Uy = args.speed_mps*math.sin(a)
    Uz = 0.0
    txt = U_FILE.read_text()
    txt = re.sub(r'(internalField\s+uniform\s*)\([^)]*\)', rf'\1({Ux:.6f} {Uy:.6f} {Uz:.6f})', txt, flags=re.I)
    def repl_inlet(m):
        block = m.group(0)
        block = re.sub(r'(value\s+uniform\s*)\([^)]*\)', rf'\1({Ux:.6f} {Uy:.6f} {Uz:.6f})', block, flags=re.I)
        return block
    txt = re.sub(r'inlet\s*\{[^}]*\}', repl_inlet, txt, flags=re.I|re.S)
    U_FILE.write_text(txt)
    print(f"[ok] freestream set → AoA={args.aoa_deg}°, speed={args.speed_mps} m/s; U=({Ux:.6f},{Uy:.6f},{Uz:.6f})")
if __name__ == "__main__":
    main()
