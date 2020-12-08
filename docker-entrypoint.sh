#!/bin/bash

if [[ -n "${OCTOBOT_CONFIG}" ]]; then
  echo "$OCTOBOT_CONFIG" | tee /octobot/user/config.json > /dev/null
fi

./OctoBot
