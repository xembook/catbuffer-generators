#!/bin/bash
set -e

rootDir="$(dirname $0)/.."

ARTIFACT_NAME="catbuffer-java"
RELEASE_VERSION="0.0.21"
SNAPSHOT_VERSION="${RELEASE_VERSION}-SNAPSHOT"
CURRENT_VERSION="$SNAPSHOT_VERSION"
if [[ $1 == "release" ]]; then
  CURRENT_VERSION="$RELEASE_VERSION"
fi

rm -rf "${rootDir}/catbuffer/_generated/java"
rm -rf "$rootDir/build/java/$ARTIFACT_NAME"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator java \
  --copyright catbuffer/HEADER.inc

if [[ $1 == "release" ]]; then
  ARTIFACT_VERSION="${ARTIFACT_VERSION%$SNAPSHOT_PREFIX}"
fi

mkdir -p "$rootDir/build/java/$ARTIFACT_NAME/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/catbuffer/_generated/java/"* "$rootDir/build/java/$ARTIFACT_NAME/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/generators/java/build.gradle" "$rootDir/build/java/$ARTIFACT_NAME/"
cp "$rootDir/generators/java/settings.gradle" "$rootDir/build/java/$ARTIFACT_NAME/"

sed -i -e "s/#artifactName/$ARTIFACT_NAME/g" "$rootDir/build/java/$ARTIFACT_NAME/settings.gradle"
sed -i -e "s/#artifactVersion/$CURRENT_VERSION/g" "$rootDir/build/java/$ARTIFACT_NAME/build.gradle"

if [[ $1 == "release" ]]; then
  echo "Releasing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" publish closeAndReleaseRepository
elif [[ $1 == "publish" ]]; then
  echo "Publishing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" publish
else
  echo "Installing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" install
fi
