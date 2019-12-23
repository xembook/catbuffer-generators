#!/bin/bash
set -e

rootDir="$(dirname $0)/.."

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator typescript \
  --copyright catbuffer/HEADER.inc

//TODO Typescript builds with npm and deploy artifacts to npm repositories HERE.