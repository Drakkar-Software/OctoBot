#!/usr/bin/env bash
# Computes which add-on channel to build and what version to publish it under.
#
# Deliberately NOT using home-assistant/actions/helpers/info@master: that action
# reads `version:` from the committed config.yaml. For octobot that field only ever
# holds a "0.0.0" placeholder here — bump-version.sh stamps the real value afterwards,
# from this script's `version` output, on every tag push. For octobot-latest `version`
# here is only the Docker image tag (traceability) — config.yaml's version is a
# deliberate manual bump instead, see homeassistant/octobot-latest/config.yaml.
#
# Inputs (env): REF (github.ref)
# Output: appends addon/version/image_name/registry_prefix/architectures/name/description
#         to $GITHUB_OUTPUT (or stdout, when run locally).
set -euo pipefail

out="${GITHUB_OUTPUT:-/dev/stdout}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # homeassistant/

if [[ "$REF" == refs/tags/* ]]; then
  addon="octobot"
  version="${REF##refs/tags/}"
else
  addon="octobot-latest"
  base="$(grep -Po '^VERSION\s*=\s*"\K[^"]+' "$here/../octobot/__init__.py")"
  base="${base%%-*}"; base="${base%%+*}"   # 3.0.0-beta1 -> 3.0.0
  # Date-based, not a run counter: monotonic by construction, no dependency on
  # github.run_number (which is per-workflow-*file* and silently resets if
  # main.yml is ever renamed/recreated, which would make a rebuild look older
  # than the last real one).
  version="${base}-dev.$(date -u +%Y%m%d%H%M)"
fi

# Docker tag charset guard — catch an illegal tag (e.g. '+') before spending a
# 20-minute build. AwesomeVersion also ignores SemVer build metadata, so a
# scheme using '+' would silently never be offered as an update either way.
if [[ ! "$version" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$ ]]; then
  echo "::error::'$version' is not a valid Docker tag" >&2
  exit 1
fi

cfg="$here/${addon}/config.yaml"
image="$(yq -r '.image' "$cfg")"

{
  echo "addon=${addon}"
  echo "version=${version}"
  echo "image_name=${image##*/}"
  echo "registry_prefix=${image%/*}"
  echo "architectures=$(yq -o=json -I=0 '.arch' "$cfg")"   # matrix action needs a JSON array
  echo "name=$(yq -r '.name' "$cfg")"
  echo "description=$(yq -r '.description' "$cfg")"
} >> "$out"
