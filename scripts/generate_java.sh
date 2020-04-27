#!/bin/bash
set -e

rootDir="$(dirname $0)/.."

SNAPSHOT_PREFIX="-SNAPSHOT"
artifactName="catbuffer-java"
artifactVersion="2.0.2-SNAPSHOT"

rm -rf "${rootDir}/catbuffer/_generated/java"
rm -rf "$rootDir/build/java/$artifactName"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator java \
  --copyright catbuffer/HEADER.inc

if [[ $1 == "release" ]]; then
  artifactVersion="${artifactVersion%$SNAPSHOT_PREFIX}"
fi

mkdir -p "$rootDir/build/java/$artifactName/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/catbuffer/_generated/java/"* "$rootDir/build/java/$artifactName/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/generators/java/build.gradle" "$rootDir/build/java/$artifactName/"
cp "$rootDir/generators/java/settings.gradle" "$rootDir/build/java/$artifactName/"

sed -i -e "s/#artifactName/$artifactName/g" "$rootDir/build/java/$artifactName/settings.gradle"
sed -i -e "s/#artifactVersion/$artifactVersion/g" "$rootDir/build/java/$artifactName/build.gradle"

if [[ $1 == "release" ]]; then
  echo "Releasing artifact $artifactVersion"
  $rootDir/gradlew -p "$rootDir/build/java/$artifactName/" publish closeAndReleaseRepository
elif [[ $1 == "publish" ]]; then
  echo "Publishing artifact $artifactVersion"
  $rootDir/gradlew -p "$rootDir/build/java/$artifactName/" publish
else
  echo "Installing artifact $artifactVersion"
  $rootDir/gradlew -p "$rootDir/build/java/$artifactName/" install
fi
