---
title: "Free open source market making bot"
description: "Improve your token's exchange liquidity for free using the open source market making OctoBot. Install it, configure it and run it on your computer."
sidebar_position: 2
---

# Free open source market making bot

The free open source [OctoBot Market Making](https://github.com/Drakkar-Software/OctoBot-Market-Making) is a distribution of the open source cryptocurrency trading robot [OctoBot](https://github.com/Drakkar-Software/OctoBot). This automation software can be installed and used for free to automate simple market making strategies and is the backbone of all strategies of this platform.

![free open source octobot market making dashboard with buy and sell orders](/images/guides/free-open-source-octobot-market-making-dashboard-with-buy-and-sell-orders.png)

The cloud version of OctoBot Market Making, available on [market-making.octobot.cloud](https://market-making.octobot.cloud), is an advanced version of the OctoBot Market Making distribution, adding multiple functionalities such as:

- Advanced market making strategies
- Tailored configurations
- Liquidity monitoring

## Installing the free OctoBot Market Making

### Using Docker

```shell
docker pull drakkarsoftware/octobot:marketmaking-stable
```

### Using Python

```shell
git clone https://github.com/Drakkar-Software/OctoBot-Market-Making
cd OctoBot-Market-Making
python -m pip install -Ur requirements.txt
python start.py
```

## Configuring the OctoBot Market Making distribution

The OctoBot Market Making distribution supports more than 15 exchanges and its market making strategy can be configured in the following way.

![free open source octobot market making strategy configuration](/images/guides/free-open-source-octobot-market-making-strategy-configuration.png)

- **Exchange liquidity configuration**: Set how many bids and asks must be included in your strategy and the price range your orders should cover.
- **Order book maintenance**: The bot will automatically replace filled orders and adapts the order book according to the up-to-date price of your traded pair.
- **Arbitrage protection**: OctoBot Market Making protects your funds from arbitrage by using the most liquid exchange prices.

## Testing a market making strategy with virtual funds

![free open source octobot market making paper-trading configuration](/images/guides/free-open-source-octobot-market-making-paper-trading-configuration.png)

OctoBot Market Making comes with a built-in trading simulator to test strategies with virtual funds.

Configure your market making strategy and test it risk-free with paper money before connecting your bot to a real exchange account.
