---
title: Installation Methods
description: All ways to install OctoBot - pip, Docker, binary, and from source. Choose the method that fits your setup.
keywords: [octobot, install, pip, docker, binary, linux, windows, macos]
sidebar_position: 1
---

# Installation Methods

## Python (pip)

Requires Python 3.13+.

```bash
pip install octobot
OctoBot
```

## Docker

The recommended method for servers and always-on setups.

```bash
docker run -d \
  --name octobot \
  -p 5001:5001 \
  -v $(pwd)/user:/octobot/user \
  drakkarsoftware/octobot:stable
```

Available tags: `stable`, `latest` (dev), `staging`.

## Binary

Pre-built binaries are available for:
- **Linux** x64 and arm64
- **macOS** arm64
- **Windows** x64

Download from [GitHub Releases](https://github.com/Drakkar-Software/OctoBot/releases).

## From Source

```bash
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot
pip install -e .
OctoBot
```
