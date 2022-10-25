#!/bin/bash

export TUNNEL_LOGFILE=/root/cloudflared.log
export TUNNEL_LOGLEVEL=info

# start cloudflared if token is provided
# https://developers.cloudflare.com/cloudflare-one/tutorials/cli/
if [[ -n "$CLOUDFLARE_TOKEN" ]]; then
  cloudflared tunnel --url http://localhost:5001 --no-autoupdate run --token $CLOUDFLARE_TOKEN &
fi
