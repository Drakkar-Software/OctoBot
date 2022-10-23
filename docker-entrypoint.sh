#!/bin/bash

# OctoBot user config from env
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json > /dev/null
fi

##### CLOUDFLARED #####
export TUNNEL_LOGFILE=/root/cloudflared.log
export TUNNEL_LOGLEVEL=info

# start cloudflared if token is provided
if [[ -n "$CLOUDFLARE_TOKEN" ]]; then
  cloudflared tunnel --url http://localhost:5001 --no-autoupdate run --token $CLOUDFLARE_TOKEN &
fi

./OctoBot
