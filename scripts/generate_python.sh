#!/bin/bash
set -e

HOME=~/
rootDir="$(dirname "$0")/.."
echo "${rootDir}"

# Artifact naming
artifactPrefix="symbol"
artifactName="catbuffer"

# Artifact versioning for uploading to PyPI (PEP 440 compliant)
# Examples
#   1.2.0.dev1    # Development release
#   1.2.0a1       # Alpha Release
#   1.2.0b1       # Beta Release
#   1.2.0rc1      # Release Candidate
#   1.2.0         # Final Release
#   1.2.0.post1   # Post Release
# Insert UTC datetime for snapshots and dev testing releases,
# so we don't need to bump the artifact version or the prerelease version suffix.
# Note: Leading zeros are dropped in HHMMSS during package build version normalization.
#   1.2.0.YYYYMMDD.HHMMSS.dev1
artifactVersion="0.0.2"
prereleaseVersion="a1"
prereleaseDateTime=".$(date -u +'%Y%m%d.%H%M%S')"  # UTC time
upload=true   # convenient var to disable uploading of the artifact
repo="pypi"

if [[ -z $1 ]]; then
  # upload=false  # uncomment to disable upload to pypi for snapshots
  artifactVersion="${artifactVersion}${prereleaseDateTime}${prereleaseVersion}"
elif [[ $1 == "release" ]]; then
  artifactVersion="${artifactVersion}${prereleaseVersion}"
elif [[ $1 == "test" ]] || [[ $2 == "test" ]]; then
  repo="testpypi"
  REPO_URL="https://test.pypi.org/legacy/"
  artifactVersion="${artifactVersion}${prereleaseDateTime}${prereleaseVersion}"
fi
echo "artifactVersion=${artifactVersion}"
echo "repo=${repo}"

artifactProjectName="${artifactPrefix}-${artifactName}-python"
artifactBuildDir="${rootDir}/build/${artifactProjectName}"
artifactSrcDir="${artifactBuildDir}/src"
artifactPackageDir="${artifactSrcDir}/${artifactPrefix}_${artifactName}"
artifactTestDir="${artifactBuildDir}/test"
artifactDistDir="${artifactBuildDir}/dist"

rm -rf "${rootDir}/catbuffer/_generated/python"
rm -rf "${artifactBuildDir}"

PYTHONPATH=".:${PYTHONPATH}" python3 "catbuffer/main.py" \
  --schema catbuffer/schemas/all.cats \
  --include catbuffer/schemas \
  --output "catbuffer/_generated" \
  --generator python \
  --copyright catbuffer/HEADER.inc

mkdir -p "${artifactPackageDir}"
cp "$rootDir/catbuffer/_generated/python/"* "${artifactPackageDir}"
touch "${artifactPackageDir}/__init__.py"
cp "$rootDir/LICENSE" "${artifactBuildDir}"
cp "$rootDir/.pylintrc" "${artifactBuildDir}"
cp "$rootDir/generators/python/README.md" "${artifactBuildDir}"
cp "$rootDir/generators/python/setup.py" "${artifactBuildDir}"
cp "$rootDir/generators/python/.pypirc" "${HOME}"
sed -i -e "s/#artifactName/$artifactName/g" "${artifactBuildDir}/setup.py"
sed -i -e "s/#artifactVersion/$artifactVersion/g" "${artifactBuildDir}/setup.py"

mkdir -p "${artifactTestDir}"
PYTEST_CACHE="$rootDir/test/python/.pytest_cache/"
if [ -d "$PYTEST_CACHE" ]; then rm -Rf "$PYTEST_CACHE"; fi
cp -r "$rootDir/test/python/" "${artifactTestDir}"

# Build
cd "${artifactBuildDir}"
echo "Building..."
PYTHONPATH=".:${PYTHONPATH}" python3 setup.py sdist bdist_wheel build
# Test
echo "Testing..."
PYTHONPATH="./src:${PYTHONPATH}" pytest -v --color=yes --exitfirst --showlocals --durations=5
# Linter
echo "Linting..."
PYTHONPATH="./src:${PYTHONPATH}" pylint --rcfile .pylintrc --load-plugins pylint_quotes symbol_catbuffer
# Deploy
if [[ $upload == true ]]; then
  # Log intention
  if [[ $1 == "publish" ]]; then
    echo "Publishing python artifact[$artifactName $artifactVersion] to $repo"
  else
    echo "Releasing python artifact[$artifactName $artifactVersion] to $repo"
  fi
  # Do upload
  if [[ $repo == "pypi" ]]; then
    if [[ -n ${PYPI_USER} ]] && [[ -n ${PYPI_PASS} ]]; then
      echo "variable PYPI_USER and PYPI_PASS are already set"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload -u "$PYPI_USER" -p "$PYPI_PASS" dist/*
    else
      echo "variable PYPI_USER and/or PYPI_PASS not set - manual upload"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload --repository $repo dist/*
    fi
  else
    if [[ -n ${TEST_PYPI_USER} ]] && [[ -n ${TEST_PYPI_PASS} ]]; then
      echo "variable TEST_PYPI_USER and TEST_PYPI_PASS are already set"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload --repository-url $REPO_URL -u "$TEST_PYPI_USER" -p "$TEST_PYPI_PASS" dist/*
    else
      echo "variable TEST_PYPI_USER and/or TEST_PYPI_PASS not set - manual upload"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload --repository $repo dist/*
    fi
  fi
fi