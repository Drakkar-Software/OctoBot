---
title: "Index trading mode"
description: "Invest in the multiple crypto at the same time and create your own crypto index using the Index trading mode."
sidebar_position: 3
---


# Index Trading Mode

The Index Trading Mode (or IndexTradingMode) is designed to maintain your portfolio using a predefined cryptocurrencies configuration.

<div style="text-align: center">
  <div>
    ![index trading illustrated by a crypto basket](/images/guides/crypto-basket.png)
  </div>
</div>

Similarly to [OctoBot cloud's crypto baskets](https://www.octobot.cloud/features/crypto-basket), The Index Trading Mode enables you to easily invest in sets of cryptocurrencies.

## The Index Trading Mode can

- Evenly split your reference market holdings into the different coins of your traded pairs
- Check and adapt your portfolio if a crypto:
  - Takes a larger part of your portfolio than expected
  - Takes a smaller part of your portfolio than expected
  - Is missing from your portfolio
- Check and adapt your portfolio whevener you want when starting your OctoBot or by checking your portfolio or a regular basis

## The way funds are dispatched
When starting a OctoBot with the Index Trading Mode, your OctoBot will:
1. Value all the assets configured in your profile traded pairs and compute your portfolio holdings ratios
2. If a crypto from the traded pairs is missing from your portfolio or present with the wrong ratio, a rebalance is triggered.
3. If a rebalance is triggered, then your funds are converted to the reference market and then split into the configured coins

## Using OctoBot cloud crypto baskets
When using the [Premium OctoBot Extension](/guides/octobot-configuration/premium-octobot-extension), you can use every crypto basket available OctoBot cloud directly from your open source OctoBot.

<div style="text-align: center">
  <div>
    ![index trading illustrated by a crypto basket](/images/guides/trading-modes/octobot-open-source-using-crypto-baskets-from-premium-extension.png)
  </div>
</div>

This way, when an OctoBot cloud crypto basket gets updated, for example if the top 20 of the crypto market changes or if a new coin joins the AI crypto basket, then your open source OctoBot will also automatically update its basket.

## Configuring rebalances
### Trigger period
Your OctoBot can check the content of your portfolio on a regular basis to make sure it is still representative of the configured index.

The `Trigger period` is the number of days for your OctoBot to wait before rechecking the content of your portfolio against the index ideal content.

### Rebalance cap
When checking the content of your portfolio, the ideal index content will never be exactly matched. As crypto prices change all the time, there will always be minor differences between your holdings and the theoretical holdings of your index. 

The `Rebalance cap` defines a value in `%` from which to consider a holding ratio out of sync with the target ratio of an index.

**Example with a 4 crypto index: BTC, ETH, SOL and AVAX:**

Ideally, the portfolio would contain exactly 25% of each.  
However, if the price of AVAX increases by 10%, it might now take 28% of the portfolio instead of the ideal 25%. In this case, during the next portfolio rebalance check, 2 outcomes are possible:
- A. `Rebalance cap` is 3% or lower: As the AVAX holding ratio is 3% higher than the ideal 25%, a rebalance is triggered, therefore distributing the AVAX gains into BTC, ETH and SOL
- B. `Rebalance cap` is higher than 3%: the AVAX holding ratio is still within the ideal ratio plus/minus the `Rebalance cap`: no rebalance is required, nothing happens.
