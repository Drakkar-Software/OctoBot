#!/usr/bin/env bash
# Stamps the just-published version into homeassistant/<addon>/config.yaml and
# pushes it directly to master — the branch Supervisor actually clones (see
# supervisor/store/git.py::_clone, which omits the branch arg entirely unless
# the user's repository URL has a '#branch' suffix, so it defaults to the repo's
# default branch).
#
# Only ever invoked for ADDON=octobot (a tag push, i.e. a real OctoBot release) —
# see the `if:` guard on this step in ha-publish. octobot-latest's version is a
# deliberate manual bump instead; see homeassistant/octobot-latest/config.yaml.
#
# Runs from a checkout of THIS repo (core OctoBot repo doubles as the add-on
# distribution repo per the user's decision to accept the larger Supervisor
# clone rather than maintain a separate thin repo).
#
# Inputs (env): ADDON, NEW_VERSION
set -euo pipefail

# Assumes CWD is the repo root (true for a plain `actions/checkout@v6` step with
# no working-directory override), same as the git commands below.
cfg_rel="homeassistant/${ADDON}/config.yaml"

git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# Retry loop: a concurrency group (see ha-publish) already serializes concurrent
# runs of this step against each other, but an unrelated human push to master in
# between fetch and push is still possible - retry rather than fail the run.
for attempt in 1 2 3 4 5; do
  git fetch origin master
  git reset --hard origin/master

  # Explicit double-quote style: a bare 1.10 would otherwise parse as a float.
  V="$NEW_VERSION" yq -i '.version = strenv(V) | .version style="double"' "$cfg_rel"

  if git diff --quiet -- "$cfg_rel"; then
    echo "already at ${NEW_VERSION}, nothing to commit"
    exit 0
  fi

  git add "$cfg_rel"
  git commit -m "ci(ha): bump ${ADDON} add-on to ${NEW_VERSION} [skip ci]"
  if git push origin HEAD:master; then
    exit 0
  fi
  echo "push race on attempt ${attempt}, retrying"
  sleep $((attempt * 5))
done

echo "::error::could not push ${ADDON} version bump to master"
exit 1
