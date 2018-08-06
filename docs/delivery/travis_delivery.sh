#!/bin/sh

pyinstaller start.py --onefile

BUILD_DIR="dist"
MESSAGE=$(git log --format=%B -n 1 $TRAVIS_COMMIT)

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git clone git://${GH_REPO} ${TRAVIS_BRANCH}
cp -r ./${BUILD_DIR} ${GH_REPO_NAME}/${BUILD_DIR}
cd ${REPO}

git add -f ./${BUILD_DIR}
git commit -a -m "TRAVIS : binary push"
git remote add origin https://${GH_TOKEN}@${GH_REF}.git
git push origin ${TRAVIS_BRANCH}
