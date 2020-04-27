#!/bin/bash
set -e

rootDir="$(dirname $0)/.."

SNAPSHOT_PREFIX="-SNAPSHOT"
artifactName="catbuffer-typescript"
artifactVersion="0.0.13"

rm -rf "${rootDir}/catbuffer/_generated/typescript"
rm -rf "$rootDir/build/typescript/$artifactName"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator typescript \
  --copyright catbuffer/HEADER.inc

if [[ $1 == "release" ]]; then
  artifactVersion="${artifactVersion%$SNAPSHOT_PREFIX}"
fi

mkdir -p "$rootDir/build/typescript/$artifactName/src/"
cp "$rootDir/catbuffer/_generated/typescript/"* "$rootDir/build/typescript/$artifactName/src/"
cp "$rootDir/generators/typescript/.npmignore" "$rootDir/build/typescript/$artifactName/"
cp "$rootDir/generators/typescript/package.json" "$rootDir/build/typescript/$artifactName/"
cp "$rootDir/generators/typescript/README.md" "$rootDir/build/typescript/$artifactName/"
cp "$rootDir/generators/typescript/tsconfig.json" "$rootDir/build/typescript/$artifactName/"
sed -i -e "s/#artifactName/$artifactName/g" "$rootDir/build/typescript/$artifactName/package.json"
sed -i -e "s/#artifactVersion/$artifactVersion/g" "$rootDir/build/typescript/$artifactName/package.json"

npm install --prefix "$rootDir/build/typescript/$artifactName/"
npm run build --prefix "$rootDir/build/typescript/$artifactName/"

if [[ $1 == "release" ]]; then
  echo "Releasing artifact $artifactVersion"
  cd "$rootDir/build/typescript/$artifactName/" && npm publish
elif [[ $1 == "publish" ]]; then
  echo "Publishing artifact $artifactVersion"
  cd "$rootDir/build/typescript/$artifactName/" && npm publish
fi
