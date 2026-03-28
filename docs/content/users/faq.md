---
title: FAQ
description: Frequently asked questions about using OctoBot. Troubleshooting, common issues, and tips.
keywords: [octobot, faq, troubleshooting, help, common issues]
sidebar_position: 90
---

# Frequently Asked Questions

## General

### What is OctoBot?

OctoBot is an open-source cryptocurrency trading bot that supports multiple exchanges, strategies, and cryptocurrencies.

### Is OctoBot free?

Yes. OctoBot is open-source and free to use. [OctoBot Cloud](https://www.octobot.cloud) offers optional managed hosting.

### Which exchanges are supported?

OctoBot supports 20+ exchanges including Binance, Bybit, OKX, Kraken, Bitget, Coinex, Gate.io, and more. See the [exchanges reference](/users/exchanges/) for the full list.

## Troubleshooting

### OctoBot won't start

- Ensure Python 3.13+ is installed: `python --version`
- Check logs in the `logs/` directory
- Try reinstalling: `pip install --upgrade --force-reinstall octobot`

### Exchange connection fails

- Verify your API keys are correct and have trading permissions
- Check that your IP is whitelisted if the exchange requires it
- Ensure your system clock is synchronized (NTP)

### Web interface is not accessible

- Check that port 5001 is not blocked by a firewall
- If running in Docker, ensure the port is mapped: `-p 5001:5001`
