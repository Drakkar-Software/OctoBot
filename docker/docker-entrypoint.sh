#!/bin/bash

# Exit immediately if a command exits with a non-zero status 
set -e

# Save OctoBot config
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json >/dev/null
fi

# Trigger AWS env loading
python aws.py

# Mount s3fs
bash s3fs.sh

# Mount efs
bash efs.sh

# Start cloudflared tunnel
bash tunnel.sh

# Disable set -e 
set +e

# Start OctoBot
./OctoBot
