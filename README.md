# racewing-opt

Parametric wing: geometry → OpenFOAM (RANS) → pressure mapping → CalculiX shell FEA.

## Quick start (developer)
```bash
docker run --rm -it -v "$PWD":/case -w /case opencfd/openfoam-default:latest bash
source /usr/lib/openfoam/*/etc/bashrc 2>/dev/null || source /opt/*/etc/bashrc 2>/dev/null || true
python3 scripts/generate_geometry.py --aoa_deg 3 --out of_case/constant/triSurface/wing.stl
bash scripts/run_cfd.sh of_case
# export wing patch pressure then run FEA:
python3 scripts/map_and_run_fea.py --surface-vtk of_case/postProcessing/wingSurf/<TIME>/wingPatch.vtp --outbase fea/run_t2p5 --thickness 0.0025

