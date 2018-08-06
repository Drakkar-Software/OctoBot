#!/bin/sh

pyinstaller start.py --onfile

BUILD_DIR="dist"
MESSAGE=$(git log --format=%B -n 1 $TRAVIS_COMMIT)

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git clone -b ${TRAVIS_BRANCH} --single-branch git://${GH_REPO} ${GH_REPO_NAME}

rm -rf ./${GH_REPO_NAME}/${BUILD_DIR}
cp -rf ./${BUILD_DIR} ./${GH_REPO_NAME}
cd ./${GH_REPO_NAME}

git add -f ./${BUILD_DIR}
git commit -a -m "TRAVIS : binary push - ${TRAVIS_OS_NAME}"

git remote remove origin
git remote add origin https://${GH_TOKEN}@${GH_REPO}.git
git push origin ${TRAVIS_BRANCH}
