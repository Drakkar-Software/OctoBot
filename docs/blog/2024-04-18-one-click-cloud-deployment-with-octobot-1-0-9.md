---
title: "One Click Cloud Deployment with OctoBot 1.0.9"
description: "OctoBot 1.0.9 is released ! Deploy your OctoBot from the DigitalOcean marketplace, create your custom crypto baskets, use the improved TradingView Trading Mode"
slug: "one-click-cloud-deployment-with-octobot-1-0-9"
date: "2024-04-18"
authors: ["paul"]
tags: ["Tradingview", "Hosting", "Release"]
image: "/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-1.0.9-ditigtalocean-1-click-deployment-custom-crypto-baskets.png"
---



# One Click Cloud Deployment with OctoBot 1.0.9

![octobot 1.0.9 ditigtalocean 1 click deployment custom crypto baskets](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-1.0.9-ditigtalocean-1-click-deployment-custom-crypto-baskets.png)

## One Click Cloud Deployment

Running your OctoBot trading robot on the cloud has never been **easier and cheaper**! OctoBot is now available as a 1-Click Droplet on the <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">official DigitalOcean marketplace</a>.

<!--truncate-->

<div style={{textAlign: "center"}}>
  ![octobot on the digitalocean
  marketplace](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/octobot-on-the-digitalocean-marketplace.png)
</div>
Using DigitalOcean, you can now run simply your own OctoBot trading bot on the
cloud and have it available and automating your trading strategies 100% of the
time.

<div style={{textAlign: "center"}}>
  **[Deploy your OctoBot](/guides/octobot-installation/cloud-install-octobot-on-digitalocean)**
</div>

Having your OctoBot up and running on DigitalOcean only takes **1 click** and starting from as cheap as **$6 per month** when using the minimal setup.

## Introducing OctoBot 1.0.9

We're glad to announce the release of OctoBot 1.0.9. This version notably adds support for the above mentioned [DigitalOcean One Click Deployment](/guides/octobot-installation/cloud-install-octobot-on-digitalocean) and also adds custom crypto baskets into OctoBot and improves the existing trading modes while fixing many issues.

### Crypto Baskets

Similarly to [OctoBot cloud crypto baskets](https://www.octobot.cloud/features/crypto-basket), you can now create your own crypto baskets using OctoBot and the new [Index Trading Mode](/guides/octobot-trading-modes/index-trading-mode).

<div style={{textAlign: "center"}}>
  <div>
    ![crypto
    basket](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/crypto-basket.png)
  </div>
</div>

When using the Index Trading Mode, your OctoBot will split your reference market holdings into the different coins of your traded pairs. You can also define a rebalance interval and threshold to customize the way your OctoBot should behave when coins held in your basket change in value.

And of course, you can use backtesting to optimize the content of your baskets!

### Improved trading modes

Both the DCA and TradingView trading mode have been improved in OctoBot 1.0.9.

**DCA Trading Mode**

The [DCA Trading Mode](/guides/octobot-trading-modes/dca-trading-mode) now supports an additional parameter. By setting the `Max asset holding` of your DCA strategies, you can limit the exposure to a given asset. This is especially useful when using a evaluator-based DCA as it prevents your DCA bot from building an excessive exposure to a given asset when buying conditions are repeating.

**TradingView Trading Mode**

<div style={{textAlign: "center"}}>
  <div>
    ![tradingview logo showing octobot tradingview trading
    mode](/images/blog/one-click-cloud-deployment-with-octobot-1-0-9/tradingview-logo-showing-octobot-tradingview-trading-mode.png)
  </div>
</div>

Limit and stop orders created by the [TradingView Trading Mode](/guides/octobot-trading-modes/tradingview-trading-mode) are now much more flexible.

The TradingView Trading Mode now supports [relative pricing](/guides/octobot-trading-modes/order-price-syntax) for limit and stop orders. This means that you can configure your TradingView alerts to trigger for example:

- A BTC/USDT buy order at -10% of the current price
- An ETH/BTC sell order at the current price + 0.01 BTC
- A BTC/USDT stop loss at the price of 35000 USDT

### Exchanges improvements

- **Coinbase**: OctoBot now support both the legacy and updated Coinbase API key format
- **MEXC**: Trading on MEXC is now much more stable
- **All exchanges**: The order flow inside OctoBot as been improved. This fixes many issues related to order synchronization as well as errors on order creation.

<div style={{textAlign: "center"}}>
  **[Update your OctoBot](/guides/octobot-installation/install-octobot-on-your-computer)**
</div>

### Full changelog

Find the full changelog of OctoBot 1.0.9 on the OctoBot <a href="https://github.com/Drakkar-Software/OctoBot/blob/master/CHANGELOG.md" rel="nofollow">GitHub repository</a>.

## Final words

We would like to thank the OctoBot community for their great support and improvement ideas as well as reporting many of the issues that have been fixed in 1.0.9.
