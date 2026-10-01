#!/usr/bin/env bash
# Builds homeassistant/Dockerfile.HA on top of a given core OctoBot image and
# asserts the behaviours rootfs/entrypoint.sh exists to provide — the entire
# reason the HA wrapper exists over running the base image directly:
#
#   1. the container answers on :8000/app (Node web interface)
#   2. /data/tentacles is wiped on every boot (tentacles are never persisted)
#   3. the running process's cwd is /data (so user/logs/backtesting persist
#      under HA's /data volume, not the base image's /octobot/* VOLUMEs)
#   4. ENABLE_NODE_API reflects options.json, and NODE_EXTERNAL_HOST stays
#      unset when the option is absent/empty
#
# Usage: homeassistant/tests/smoke.sh <base-image-ref>
# No registry access required if <base-image-ref> is already loaded locally
# (docker/build-push-action's `load: true` in the docker job's PR path does this).
set -euo pipefail

BASE_FROM="${1:?usage: smoke.sh <base-image-ref>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # homeassistant/
IMG="octobot-ha-smoketest"
CONTAINER="octobot-ha-smoketest"
DATA_DIR="$(mktemp -d)"
FAIL=0

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$DATA_DIR"
}
trap cleanup EXIT

check() {
  local desc="$1" got="$2" want="$3"
  if [[ "$got" == "$want" ]]; then
    echo "OK   - $desc"
  else
    echo "FAIL - $desc (got: '$got', want: '$want')"
    FAIL=1
  fi
}

echo "Building $IMG from BUILD_FROM=$BASE_FROM ..."
docker build -t "$IMG" --build-arg "BUILD_FROM=$BASE_FROM" -f "$HERE/Dockerfile.HA" "$HERE"

mkdir -p "$DATA_DIR/tentacles"
touch "$DATA_DIR/tentacles/marker"          # must be gone after boot: tentacles are wiped every start
cp "$HERE/tests/options.json" "$DATA_DIR/options.json"

echo "Starting $CONTAINER ..."
docker run -d --name "$CONTAINER" -p 18000:8000 -v "$DATA_DIR:/data" "$IMG" >/dev/null

# The wrapper contract (cwd, tentacle wipe, env translation) is set up by
# rootfs/entrypoint.sh before it execs OctoBot, so these don't need to wait for
# the app to finish booting — just for the container to be up. entrypoint execs
# OctoBot as the final step, so OctoBot is PID 1 inside the container.
sleep 5

CWD="$(docker exec "$CONTAINER" readlink /proc/1/cwd)"
check "process cwd is /data" "$CWD" "/data"

check "/data/tentacles wiped on boot" "$( [[ -e "$DATA_DIR/tentacles/marker" ]] && echo present || echo absent )" "absent"

ENVIRON="$(docker exec "$CONTAINER" sh -c "tr '\0' '\n' < /proc/1/environ")"
check "ENABLE_NODE_API reflects options.json" "$(grep -c '^ENABLE_NODE_API=true$' <<<"$ENVIRON")" "1"
check "NODE_EXTERNAL_HOST unset when absent from options.json" "$(grep -c '^NODE_EXTERNAL_HOST=' <<<"$ENVIRON")" "0"

# Non-fatal: OctoBot must download a full tentacles set from tentacles.octobot.online
# before /app serves anything (tentacles are wiped above, unlike the core docker job's
# health check which mounts tentacles from the host). Also documented in DOCS.md as
# occasionally 404-ing on builds that predate the node web bundle, with :5001 as the
# fallback. A slow or missing response here is not evidence the wrapper is broken.
echo "Waiting for :8000/app (best-effort, not a hard gate) ..."
up=false
for _ in $(seq 1 60); do
  if curl -sf -o /dev/null "http://127.0.0.1:18000/app"; then
    up=true
    break
  fi
  sleep 3
done
if [[ "$up" == "true" ]]; then
  echo "OK   - answers on :8000/app"
else
  echo "WARN - never answered on :8000/app within 180s (non-fatal, see comment above)"
  docker logs "$CONTAINER" || true
fi

exit "$FAIL"
