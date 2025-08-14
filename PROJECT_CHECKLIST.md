# ✅ Final Deliverables Checklist – racewing-opt

## 01_Input_Geometry/
- [ ] `baseline_wing.stl` – Base wing surface model
- [ ] `geometry_parameters.yaml` – Geometry parameters (span, chord, twist, airfoil shape)
- [ ] `README.md` – Instructions on geometry setup & parametric control

## 02_Mesh_and_CFD/
- [ ] **case_setup/** – OpenFOAM case (`0/`, `system/`, `constant/`)
- [ ] **results_raw/** – Unprocessed solver outputs + logs
- [ ] **plots/** – Lift/drag curves, Cp distributions
- [ ] **postprocessing/** – `.vtp` / `.vtk` files, surface pressure maps
- [ ] `README.md` – Steps to run CFD from scratch

## 03_FEA/
- [ ] **fea_mesh/** – `.inp` files for CalculiX runs
- [ ] **results_raw/** – `.frd`, `.dat`, `.sta` files from FEA
- [ ] **plots/** – Stress & displacement contour plots
- [ ] `README.md` – How to run FEA from mapped pressures

## 04_Materials_and_Layup/
- [ ] `cfrp_properties.yaml` – Material constants, ply layup schedule
- [ ] `README.md` – Source & validation notes

## 05_Automation_Scripts/
- [ ] `generate_geometry.py` – Creates wing STL from parameters
- [ ] `run_cfd.sh` – Runs OpenFOAM case
- [ ] `map_and_run_fea.py` – Maps CFD pressures to FEA mesh & runs CalculiX
- [ ] `evaluate.py` – Reads results & computes metrics
- [ ] `README.md` – Script usage & arguments

## 06_Optimization_History/
- [ ] Iteration CSV log of parameters & performance metrics
- [ ] Convergence plots
- [ ] `README.md` – Optimization process description

## 07_Final_Design/
- [ ] Final STL geometry
- [ ] Final CFD postprocessing plots
- [ ] Final FEA plots
- [ ] Final performance report (`PDF`)

## 08_Report_and_Docs/
- [ ] `Final_Report.pdf` – Objectives, physics, approach, results, conclusions
- [ ] `README.md` – Links to supplementary docs

## Root-level files
- [ ] `README.md` – Overview + quick start
- [ ] `config/` – Global YAML configs (bounds, refs)
- [ ] `.gitignore` – Ignore raw logs & temp files

---

### 📌 Scope for Improvement
- Parametric optimization loop
- Mesh adaptation in high-gradient areas
- Ply-by-ply composite modeling in FEA
- GPU-based CFD acceleration


