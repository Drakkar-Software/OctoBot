#!/bin/bash
set -e

OPTS=/data/options.json
enable_node_api() { python3 -c "import json;print(str(json.load(open('$OPTS')).get('enable_node_api',True)).lower())" 2>/dev/null || echo true; }
node_external_host() { python3 -c "import json;print(json.load(open('$OPTS')).get('node_external_host') or '')" 2>/dev/null || echo ""; }

export ENABLE_NODE_API="$(enable_node_api)"
export AUTO_OPEN_IN_WEB_BROWSER=false

# Optional external host (and port, if non-default) the Node sync/mobile features
# advertise — set it when OctoBot sits behind a reverse proxy or a public
# hostname. Only exported when non-empty so OctoBot keeps its own default.
NODE_EXTERNAL_HOST_VALUE="$(node_external_host)"
[ -n "$NODE_EXTERNAL_HOST_VALUE" ] && export NODE_EXTERNAL_HOST="$NODE_EXTERNAL_HOST_VALUE"

# OctoBot resolves its user/tentacles/backtesting/logs folders as plain relative
# paths against the process's current working directory (no env override exists
# for user/tentacles/backtesting). Relocating CWD to HA's persistent /data keeps
# them off the base image's inherited /octobot/{user,tentacles,logs,backtesting}
# VOLUMEs, so data survives add-on rebuilds/updates.
cd /data

# Tentacles are intentionally NOT persisted: wipe them on every start so OctoBot
# reinstalls a fresh default tentacles set each boot. user/logs/backtesting stay
# under /data and keep persisting.
rm -rf /data/tentacles

exec OctoBot "$@"
