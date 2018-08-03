#!/bin/sh

LAST_COMMIT_MESSAGE="$(git log --no-merges -1 --pretty=%B)"
git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git checkout travis-builds
git add --force dist/
git commit -a -m "TEST"
git remote remove origin
git remote add origin https://${GITHUB_TOKEN}@github.com/Drakkar-Software/OctoBot.git
git push origin --tags HEAD:master