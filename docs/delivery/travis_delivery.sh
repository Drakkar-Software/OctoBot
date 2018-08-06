#!/bin/sh

pyinstaller start.py --onefile

REPO="OctoBot"
BUILD_DIR="dist"
BRANCH_TO_PUSH="travis-builds"
GH_REPO="github.com/${GH_REF}.git"
MESSAGE=$(git log --format=%B -n 1 $TRAVIS_COMMIT)

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git clone git://${GH_REPO} ${BRANCH_TO_PUSH}
cp -r ./${BUILD_DIR} ${REPO}/${BUILD_DIR}
cd ${REPO}

git add -f ./${BUILD_DIR}
git commit -a -m "TRAVIS : binary push"
git remote add origin https://${GH_TOKEN}@${GH_REF}.git
git push origin ${BRANCH_TO_PUSH}
