#!/bin/bash
set -e

rootDir="$(dirname $0)/.."
bash "$rootDir/scripts/generate_all.sh" java

SNAPSHOT_PREFIX="-SNAPSHOT"
artifactName="catbuffer"
artifactVersion="0.0.3-SNAPSHOT"

if [[ $1 == "release" ]]; then
  artifactVersion="${artifactVersion%$SNAPSHOT_PREFIX}"
fi

rm -rf "$rootDir/build/java/$artifactName"
mkdir -p "$rootDir/build/java/$artifactName/src/main/java/io/nem/catapult/builders/"
cp "$rootDir/catbuffer/_generated/java/"* "$rootDir/build/java/$artifactName/src/main/java/io/nem/catapult/builders/"
cp "$rootDir/generators/java/build.gradle" "$rootDir/build/java/$artifactName/"
cp "$rootDir/generators/java/settings.gradle" "$rootDir/build/java/$artifactName/"

sed -i -e "s/#artifactName/$artifactName/g" "$rootDir/build/java/$artifactName/settings.gradle"
sed -i -e "s/#artifactVersion/$artifactVersion/g" "$rootDir/build/java/$artifactName/build.gradle"

if [[ $1 == "release" ]]; then
  echo "Releasing artifact $artifactVersion"
  $rootDir/gradlew -p "$rootDir/build/java/$artifactName/" publish closeAndReleaseRepository
else
  echo "Installing artifact $artifactVersion"
  $rootDir/gradlew -p "$rootDir/build/java/$artifactName/" install
fi
