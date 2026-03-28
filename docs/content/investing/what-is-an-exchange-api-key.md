---
title: "What are API Keys ?"
description: "Wondering what an exchange API Key is and why you should use it with a trading software ? Here is the simple explanation."
sidebar_position: 34
---

# What is an exchange API Key

In cryptocurrencies trading, API Keys are the go-to solution to allow trading software to create and cancel orders on your exchange account in a secure manner. It also presents the advantage of not requiring to disclose your exchange email or password.

## API Keys on OctoBot
On OctoBot, your API Keys are used to execute a strategy, which means to:
- fetch your current portfolio balance
- fetch, create and cancel trading orders on your account

## Permissions
API Keys can be configured with permissions. This is an additional security layer that is preventing any unwanted behavior. For example, if you have not activated withdrawals on an API Key, the exchange will never let any software proceed to withdrawal when using this API Key.

For this reason, only **reading and trading permissions are required** for OctoBot to be able to execute a strategy. No other permission is required.

**We strongly recommend that you do not add any other permission to any API Key given to any trading software, whether it is OctoBot or not.**

## How to create your exchange account API Keys
To help you connect your exchange account to OctoBot using API Keys, we created detailed step by step guides:
- [Binance connection guide](connect-your-binance-account-to-octobot)
- [Kucoin connection guide](connect-your-kucoin-account-to-octobot)
- [Coinbase connection guide](connect-your-coinbase-account-to-octobot)
