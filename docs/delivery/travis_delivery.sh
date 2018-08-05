#!/bin/sh

pyinstaller start.py

LAST_COMMIT_MESSAGE="$(git log --no-merges -1 --pretty=%B)"
git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git add --force dist/
git commit -a -m "TRAVIS : binary push"
git remote remove origin
git remote add origin https://${GH_TOKEN}@${GH_REF}.git
git push origin HEAD:travis-builds