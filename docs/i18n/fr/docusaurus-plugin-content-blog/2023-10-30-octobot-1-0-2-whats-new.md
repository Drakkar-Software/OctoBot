---
title: "OctoBot 1.0.2 - Les nouveautés"
description: "Discover what's new in OctoBot - Chatgpt strategy upgrade, improved TradingView integration and more"
slug: "octobot-1-0-2-whats-new"
date: "2023-10-30"
authors: ["guillaume"]
tags: ["Tradingview", "Chatgpt", "Release", "DCA", "Backtesting"]
image: "/images/blog/octobot-1-0-2-whats-new/cover.png"
---



# OctoBot 1.0.2 - Les nouveautés

:::info
  La traduction française de cette page est en cours.
:::

![cover](/images/blog/octobot-1-0-2-whats-new/cover.png)

## Présentation d'OctoBot 1.0.2

We're thrilled to announce the release of OctoBot 1.0.2, an upgraded version with many improved features, thanks to the great feedback we received from you all.

## Refonte de la stratégie ChatGPT

In OctoBot 1.0.2, we've revamped the ChatGPT strategy. Until now, you couldn't run a [backtesting](/guides/octobot-usage/backtesting) on a chatgpt profile due to the excessive prompt, costing around $2 for 6 months history, hence we disallowed it.
However, with the new update, you can run backtesting on some gpt settings because we've already computed the prompt against some exchanges pairs historical data which are downloaded from our servers.

We've also shifted from Daily Trading mode to a smart DCA trading mode in the chatgpt profile. The previous mode was no longer suited to the current market, hence we updated it to DCA trading mode to develop more accurate sell orders following a chatgpt entry signal.

Additionally, we've introduced a new prompt setting. You can now ask chatgpt with pure candle history (without any TA indicator) and include the number of candles you want.

![chatgpt settings](/images/blog/octobot-1-0-2-whats-new/gpt-evaluator-settings.png)

## Amélioration de la connexion à TradingView

We've also made noteworthy improvements to the TradingView connection, thanks to some valuable feedback from our OctoBot users who use the TradingView integration.
It's now possible to send a cancel order signal to cancel all current open orders for a symbol, or only to cancel an open order on a specific side using the param SIDE. More details on this can be found at [this link](/guides/octobot-interfaces/tradingview/alert-format#canceling-orders).

Special thanks to @KidCharlemagne, an active member of our OctoBot <a href="https://discord.com/invite/vHkcb8W" rel="nofollow">Discord community</a>, for helping with the complete refactor of the TradingView [configuration guide](/guides/octobot-interfaces/tradingview). It's clearer now, with ample examples.

![TradingView guide](/images/blog/octobot-1-0-2-whats-new/tv-guides.png)

## Correction de bugs

We've also squashed some bugs in this release. After careful checks, we discovered an issue in the OctoBot [backtesting engine](/guides/octobot-usage/backtesting) that allowed for premature filling of open orders.

## Conclusion

We can't wait to hear your thoughts on this new version.
Please use this <a href="https://feedback.octobot.cloud/open-source" rel="nofollow">feedback link</a> to share your suggestions and what you'd like to see in our next release.
