---
title: Getting Started
description: Install and run OctoBot, the open-source cryptocurrency trading bot. Step-by-step guide for setup, configuration, and first trade.
keywords: [octobot, install, setup, getting started, crypto trading bot]
sidebar_position: 1
---

# Getting Started with OctoBot

OctoBot is an open-source cryptocurrency trading bot designed to be **multi-strategy**, **multi-exchange**, and **multi-cryptocurrency**.

## Installation

### Using pip

```bash
pip install octobot
```

### Using Docker

```bash
docker run -d --name octobot -p 5001:5001 drakkarsoftware/octobot:stable
```

### Using the binary

Download the latest binary for your platform from the [GitHub Releases](https://github.com/Drakkar-Software/OctoBot/releases) page.

## Running OctoBot

```bash
OctoBot
```

OctoBot starts with a web interface accessible at `http://localhost:5001`.

## First Steps

1. **Open the web interface** at `http://localhost:5001`
2. **Connect an exchange** with your API keys
3. **Select a trading profile** or configure your own
4. **Start trading** and monitor from the dashboard

## Configuration

OctoBot can be configured through:
- The **web interface** at `http://localhost:5001`
- Configuration files in the `user/` directory
- Environment variables

## Next Steps

- [Installation options](/users/installation/methods) - Detailed install guides for every platform
- [Configuration guide](/users/configuration/overview) - Customize OctoBot to your needs
- [Supported exchanges](/users/exchanges/) - See which exchanges are available

## Resources

- [OctoBot Cloud](https://www.octobot.cloud) - Managed OctoBot hosting
- [Discord Community](https://discord.gg/vHkcb8W) - Get help and chat
- [Telegram](https://t.me/OctoBot_Project) - Community discussions
