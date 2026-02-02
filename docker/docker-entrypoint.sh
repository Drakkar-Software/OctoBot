#!/bin/bash

# Exit immediately if a command exits with a non-zero status 
set -e

# Save OctoBot config
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json >/dev/null
fi

# Start cloudflared tunnel
bash tunnel.sh

# Disable set -e 
set +e

# Start OctoBot using the installed console script
OctoBot