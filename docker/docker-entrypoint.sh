#!/bin/bash

# Save OctoBot config
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json >/dev/null
fi

# Trigger AWS env loading
python aws.py

# Mount s3fs
bash s3fs.sh

# Start cloudflared tunnel
bash tunnel.sh

# Start OctoBot
./OctoBot
