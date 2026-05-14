---
title: "Understanding the Liquidity Score"
description: "What is the Liquidity Score of a crypto market? Quickly measure your crypto market liquidity and attractiveness and attract more investors."
sidebar_position: 6
---

# Understanding the Liquidity Score

![octobot market making bot impact on liquidity score](/images/guides/octobot-market-making-bot-impact-on-liquidity-score.png)

## How the Liquidity Score works

On OctoBot Market Making, exchange trading pairs have a Liquidity Score. This value ranges from 0 to 10.

The Liquidity Score **measures how well adapted to the trading demand an order book is**.

- A lower liquidity score means that the trading pair's current order book is not sufficient to provide the necessary liquidity for this trading pair average trading activity.
- A higher liquidity score means that the order book efficiently covers the needs of the trading pair's average trading activity.

In short, a Liquidity Score below 4 can signal a market that investors might avoid due to lack of liquidity. On the other hand, a liquidity score above 6 will satisfy most investors. Finally, investors with larger capital will look for markets reflected by a liquidity score of 8 and above.

## How the Liquidity Score is computed

The liquidity score takes the following factors into account:

- The [market depth](https://www.investopedia.com/terms/m/marketdepth.asp) of the top of the order book compared to a part of the last 24 hours trading volume
- The [bid-ask spread](https://www.investopedia.com/articles/investing/082213/how-calculate-bidask-spread.asp) of the order book relatively to the asset price

As a result, the liquidity score remains relevant regardless of a market's trading volume, as it is a rating of the market's order book compared to the current trading demand in terms of trading volume.

In other words, a market with low trading activity can reach a high Liquidity Score with a relatively empty order book as long as it covers the daily trading activity requirements and displays a tight spread.
