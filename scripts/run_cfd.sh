#!/usr/bin/env bash
set -euo pipefail

CASE="${1:-of_case}"

# --- Robust OpenFOAM env: only source if not already available ---
if ! command -v blockMesh >/dev/null 2>&1; then
  set +u +e
  # try common locations quietly
  if [ -f /usr/lib/openfoam/openfoam2506/etc/bashrc ]; then
    . /usr/lib/openfoam/openfoam2506/etc/bashrc >/dev/null 2>&1
  elif [ -f /opt/openfoam8/etc/bashrc ]; then
    . /opt/openfoam8/etc/bashrc >/dev/null 2>&1
  elif [ -f /opt/OpenFOAM/OpenFOAM-*/etc/bashrc ]; then
    . /opt/OpenFOAM/OpenFOAM-*/etc/bashrc >/dev/null 2>&1
  fi
  set -e
fi

mkdir -p "$CASE/logs"
LOG="$CASE/logs/simpleFoam.log"
MESH_LOG="$CASE/logs/mesh.log"

echo "[info] CASE=$(realpath "$CASE")"
echo "[info] Meshing: blockMesh → surfaceFeatureExtract → snappyHexMesh -overwrite → checkMesh"

{
  blockMesh -case "$CASE"
  surfaceFeatureExtract -case "$CASE"
  snappyHexMesh -overwrite -case "$CASE"
  checkMesh -case "$CASE" -allTopology -allGeometry
  echo "[ok] Meshing done"
} | tee "$MESH_LOG"

echo "[info] running simpleFoam (startFrom/startTime from controlDict)"
set +e
simpleFoam -case "$CASE" | tee "$LOG"
rc=${PIPESTATUS[0]}
set -e
if [[ $rc -ne 0 ]]; then
  echo "[err] simpleFoam failed — see $LOG"
  exit 1
fi
echo "[ok] simpleFoam finished"

# post-process surfaces (wing pressure to VTP)
PP_LOG="$CASE/logs/postProcess.log"
DICT="$CASE/system/post.fo"
TIMEARG="-latestTime"
if [[ -f "$DICT" ]]; then
  echo "[info] postProcess (latestTime), dict=$DICT"
  set +e
  postProcess -case "$CASE" $TIMEARG -dict "$DICT" -func wingSurf -field p | tee "$PP_LOG"
  rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -eq 0 ]]; then
    echo "[ok] postProcess surfaces done"
  else
    echo "[warn] postProcess failed (see $PP_LOG)"
  fi
else
  echo "[warn] no $DICT; skipping postProcess"
fi

echo "[ok] CFD done. See $CASE/logs and $CASE/postProcessing/"
