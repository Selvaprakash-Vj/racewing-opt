#!/usr/bin/env bash
set -euo pipefail
caseDir="${1:-of_case}"
pushd "$caseDir" >/dev/null

# ensure logs is a directory
[ -f logs ] && rm -f logs
mkdir -p logs

# clean old mesh/results
rm -rf constant/polyMesh processor* postProcessing 2>/dev/null || true

# 1) feature edges
surfaceFeatureExtract > logs/surfaceFeatureExtract.log 2>&1 || true

# 2) base mesh
blockMesh > logs/blockMesh.log 2>&1

# 3) snap + layers
snappyHexMesh -overwrite > logs/snappyHexMesh.log 2>&1

# 4) initialise fields
rm -rf 0 2>/dev/null || true
cp -r 0.orig 0

# 5) steady RANS
simpleFoam > logs/simpleFoam.log 2>&1

popd >/dev/null
echo "[ok] CFD done. See ${caseDir}/logs and ${caseDir}/postProcessing/"
