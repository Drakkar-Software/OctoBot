#!/bin/bash

##### OctoBot config #####
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json >/dev/null
fi

python aws.py

bash tunnel.sh

./OctoBot
