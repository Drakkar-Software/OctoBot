---
title: Updating OctoBot
description: How to update OctoBot to the latest version. Covers pip, Docker, and binary update methods.
keywords: [octobot, update, upgrade, version]
sidebar_position: 2
---

# Updating OctoBot

## pip

```bash
pip install --upgrade octobot
```

## Docker

```bash
docker pull drakkarsoftware/octobot:stable
docker stop octobot && docker rm octobot
docker run -d --name octobot -p 5001:5001 -v $(pwd)/user:/octobot/user drakkarsoftware/octobot:stable
```

## Binary

Download the latest binary from [GitHub Releases](https://github.com/Drakkar-Software/OctoBot/releases) and replace your existing binary.

Your `user/` directory containing configuration and data is preserved across updates.
