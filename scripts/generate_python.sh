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
artifactVersion="0.0.3"  # Release (production) version
prereleaseVersion="a1"   # Appended to Release version for Pre-releases
prereleaseDateTime=".$(date -u +'%Y%m%d.%H%M%S')"  # UTC time; appended to Release version for Pre-releases
snapshot=true
repo="pypi"
upload=true   # convenient var to disable uploading of the artifact

if [[ -z $1 ]]; then  # Use prerelease+snapshot(datetime) version
  upload=false  # upload is set to false for zero arguments
  echo "Zero arguments: Disable upload to PyPI"
  artifactVersion="${artifactVersion}${prereleaseDateTime}${prereleaseVersion}"
elif [[ $1 == "publish" ]]; then  # Use prerelease version
  artifactVersion="${artifactVersion}${prereleaseVersion}"
elif [[ $1 == "test" ]] || [[ $2 == "test" ]]; then # Use prerelease+snapshot(datetime) version
  repo="testpypi"
  REPO_URL="https://test.pypi.org/legacy/"
  artifactVersion="${artifactVersion}${prereleaseDateTime}${prereleaseVersion}"
elif [[ $1 == "release" ]]; then
  snapshot=false
fi

echo "artifactName=${artifactName}"
echo "artifactVersion=${artifactVersion}"
echo "snapshot=${snapshot}"
echo "repo=${repo}"

GIT_USER_ID="$(cut -d'/' -f1 <<<"$TRAVIS_REPO_SLUG")"
GIT_REPO_ID="$(cut -d'/' -f2 <<<"$TRAVIS_REPO_SLUG")"
echo "Travis Repo Slug: $TRAVIS_REPO_SLUG"
echo "Git User ID: $GIT_USER_ID"
echo "Git Repo ID: $GIT_REPO_ID"
if [[ $upload == true ]] && [[ $repo == "pypi" ]] && [[ -n $TRAVIS_REPO_SLUG ]] && [[ $GIT_USER_ID != 'nemtech' ]]; then
  upload=false
  echo "User is not 'nemtech': Disable upload to PyPI"
fi

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
  if [[ $1 == "release" ]]; then
    echo "Releasing python artifact[$artifactName $artifactVersion] to $repo"
  else
    echo "Publishing python artifact[$artifactName $artifactVersion] to $repo"
  fi
  # Do upload
  if [[ $repo == "pypi" ]]; then
    if [[ -n ${PYPI_USER} ]] && [[ -n ${PYPI_PASS} ]]; then
      echo "PYPI_USER and PYPI_PASS are already set: Uploading to PyPI"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload -u "$PYPI_USER" -p "$PYPI_PASS" dist/*
    else
      echo "PYPI_USER and/or PYPI_PASS not set: Cancelled upload to PyPI"
    fi
  else
    if [[ -n ${TEST_PYPI_USER} ]] && [[ -n ${TEST_PYPI_PASS} ]]; then
      echo "TEST_PYPI_USER and TEST_PYPI_PASS are already set: Uploading to PyPI"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload --repository-url $REPO_URL -u "$TEST_PYPI_USER" -p "$TEST_PYPI_PASS" dist/*
    else
      echo "TEST_PYPI_USER and/or TEST_PYPI_PASS not set: Initiated manual upload"
      PYTHONPATH=".:${PYTHONPATH}" python3 -m twine upload --repository $repo dist/*
    fi
  fi
fi