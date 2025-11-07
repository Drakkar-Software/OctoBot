#!/bin/bash

export TUNNEL_LOGFILE=/root/cloudflared.log
export TUNNEL_LOGLEVEL=info

# load env file
ENV_FILE=.env
if [[ -f "$ENV_FILE" ]]; then
    source $ENV_FILE
fi

# start cloudflared if token is provided
# https://developers.cloudflare.com/cloudflare-one/tutorials/cli/
if [[ -n "$CLOUDFLARE_TOKEN" ]]; then
  # Install cloudflared if not already installed
  # Add cloudflare gpg key and add cloudflare repo in apt repositories (from https://pkg.cloudflare.com/index.html)
  mkdir -p /usr/share/keyrings
  chmod 0755 /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
  echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared buster main' | tee /etc/apt/sources.list.d/cloudflared.list
  apt-get update
  apt-get install -y --no-install-recommends cloudflared

  # Start cloudflared tunnel
  cloudflared tunnel --url http://localhost:5001 --no-autoupdate run --token $CLOUDFLARE_TOKEN &
fi
