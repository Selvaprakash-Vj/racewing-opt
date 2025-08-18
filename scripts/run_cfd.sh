#!/usr/bin/env bash
set -e -o pipefail
CASE=${1:-of_case}

# Load OpenFOAM (keep -u off while sourcing)
set +u
source /usr/lib/openfoam/*/etc/bashrc 2>/dev/null || { echo "[err] could not source OpenFOAM bashrc" >&2; exit 2; }
set -u

CASE="$(realpath "$CASE")"
mkdir -p "$CASE/logs"
echo "[info] CASE=$CASE"

# Run solver, stream to screen + log
set +e
simpleFoam -case "$CASE" 2>&1 | tee "$CASE/logs/simpleFoam.log"
rc=${PIPESTATUS[0]}
set -e
if [[ $rc -ne 0 ]]; then
  echo "[err] simpleFoam failed — see $CASE/logs/simpleFoam.log"
  tail -n 80 "$CASE/logs/simpleFoam.log" || true
  exit 1
fi
echo "[ok] simpleFoam finished"

# Latest written time (int or decimal)
LT=$(ls -1 "$CASE" | egrep '^[0-9]+(\.[0-9]+)?$' | sort -g | tail -1 || true)

# Use ABSOLUTE dict path for postProcess
if [[ -n "${LT:-}" && -f "$CASE/system/post.fo" ]]; then
  echo "[info] postProcess time=$LT, dict=$CASE/system/post.fo"
  postProcess -case "$CASE" -time "$LT" -dict "$CASE/system/post.fo" -func wingSurf -field p || echo "[warn] postProcess failed"
else
  echo "[warn] no time dirs or missing $CASE/system/post.fo — skipping postProcess"
fi

echo "[ok] CFD done. See $CASE/logs and $CASE/postProcessing/"
