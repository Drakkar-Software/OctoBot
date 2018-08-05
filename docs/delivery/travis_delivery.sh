#!/bin/sh

pyinstaller start.py

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git pull travis-builds
git checkout travis-builds

git add --force dist/
git commit -a -m "TRAVIS : binary push"

git remote remove origin
git remote add origin https://${GH_TOKEN}@${GH_REF}.git
git push origin HEAD:travis-builds