#!/bin/bash

##### OctoBot config #####
if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json >/dev/null
fi

bash aws.sh
bash tunnel.sh

./OctoBot
