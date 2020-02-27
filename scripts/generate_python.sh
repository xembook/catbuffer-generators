#!/bin/bash
set -e

rootDir="$(dirname "$0")/.."

artifactName="catbuffer"

rm -rf "${rootDir}/catbuffer/_generated/python"
rm -rf "$rootDir/build/python/$artifactName"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator python \
  --copyright catbuffer/HEADER.inc
