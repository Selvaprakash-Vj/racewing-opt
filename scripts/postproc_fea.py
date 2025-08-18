import os, math

def _try_float(x):
    try: return float(x)
    except: return None

def _is_int(x):
    try:
        int(x); return True
    except:
        return False

def _parse_dat_for_results(path):
    """Return (max_disp or None, max_vm or None) from .dat"""
    max_disp = None
    max_vm   = None
    if not os.path.exists(path): 
        return None, None

    with open(path, "r", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if not parts: 
                continue

            # Element stress lines: "<elemId> <ip> <sxx> <syy> <szz> <sxy> <syz> <szx> ..."
            if len(parts) >= 8 and _is_int(parts[0]) and _is_int(parts[1]):
                nums = list(map(_try_float, parts[2:8]))
                if all(n is not None for n in nums):
                    sxx, syy, szz, sxy, syz, szx = nums
                    vm = math.sqrt(0.5*((sxx-syy)**2 + (syy-szz)**2 + (szz-sxx)**2
                                        + 6.0*(sxy*sxy + syz*syz + szx*szx)))
                    if (max_vm is None) or (vm > max_vm):
                        max_vm = vm
                    continue

            # Node displacement lines (if present): "<nodeId> U1 U2 U3 ..."
            if len(parts) >= 4 and _is_int(parts[0]):
                u1 = _try_float(parts[1]); u2 = _try_float(parts[2]); u3 = _try_float(parts[3])
                if None not in (u1, u2, u3):
                    mag = math.sqrt(u1*u1 + u2*u2 + u3*u3)
                    if (max_disp is None) or (mag > max_disp):
                        max_disp = mag
                    continue

    return max_disp, max_vm

def _parse_frd_for_displacements(path):
    """
    Very lightweight FRD reader: look for lines with nodeId and three floats.
    This is robust enough for CalculiX FRD nodal U blocks.
    Returns max displacement magnitude or None.
    """
    if not os.path.exists(path): 
        return None
    max_disp = None
    with open(path, "r", errors="ignore") as f:
        for line in f:
            # Typical nodal lines: "   123   1.23E-04  -4.56E-05  7.89E-06"
            parts = line.strip().split()
            if len(parts) >= 4 and _is_int(parts[0]):
                u1 = _try_float(parts[1]); u2 = _try_float(parts[2]); u3 = _try_float(parts[3])
                if None not in (u1, u2, u3):
                    mag = math.sqrt(u1*u1 + u2*u2 + u3*u3)
                    if (max_disp is None) or (mag > max_disp):
                        max_disp = mag
    return max_disp

def extract_results(dat_path: str):
    """
    Returns (max_disp_m, max_stress_Pa).
    Strategy:
      1) Parse .dat for stresses and (if present) node displacements
      2) If displacement missing, fall back to sibling .frd
    """
    max_disp, max_vm = _parse_dat_for_results(dat_path)
    if max_disp is None:
        frd_path = dat_path[:-4] + ".frd" if dat_path.endswith(".dat") else dat_path + ".frd"
        max_disp = _parse_frd_for_displacements(frd_path)
    return max_disp, max_vm
