#!/bin/bash
set -e

rootDir="$(dirname $0)/.."

ARTIFACT_NAME="catbuffer-java"
RELEASE_VERSION="$(head -n 1 ${rootDir}/version.txt)"
OPERATION="$1"
SNAPSHOT_VERSION="${RELEASE_VERSION}-SNAPSHOT"
CURRENT_VERSION="$SNAPSHOT_VERSION"
if [[ $OPERATION == "release" ]]; then
  CURRENT_VERSION="$RELEASE_VERSION"
fi

echo "Building Java version $CURRENT_VERSION, operation $OPERATION"

rm -rf "${rootDir}/catbuffer/_generated/java"
rm -rf "$rootDir/build/java/$ARTIFACT_NAME"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator java \
  --copyright catbuffer/HEADER.inc

if [[ $OPERATION == "release" ]]; then
  ARTIFACT_VERSION="${ARTIFACT_VERSION%$SNAPSHOT_PREFIX}"
fi

mkdir -p "$rootDir/build/java/$ARTIFACT_NAME/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/catbuffer/_generated/java/"* "$rootDir/build/java/$ARTIFACT_NAME/src/main/java/io/nem/symbol/catapult/builders/"
cp "$rootDir/generators/java/build.gradle" "$rootDir/build/java/$ARTIFACT_NAME/"
cp "$rootDir/generators/java/settings.gradle" "$rootDir/build/java/$ARTIFACT_NAME/"

sed -i -e "s/#artifactName/$ARTIFACT_NAME/g" "$rootDir/build/java/$ARTIFACT_NAME/settings.gradle"
sed -i -e "s/#artifactVersion/$CURRENT_VERSION/g" "$rootDir/build/java/$ARTIFACT_NAME/build.gradle"

if [[ $OPERATION == "release" ]]; then
  echo "Releasing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" publish closeAndReleaseRepository
elif [[ $OPERATION == "publish" ]]; then
  echo "Publishing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" publish
else
  echo "Installing artifact $CURRENT_VERSION"
  $rootDir/gradlew -p "$rootDir/build/java/$ARTIFACT_NAME/" install
fi
