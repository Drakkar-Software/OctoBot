---
title: "Golden Cross Strategy"
description: "Learn to automate a Bitcoin Death and Golden Cross Strategy using TradingView alerts and OctoBot with paper or real trading on any exchange."
sidebar_position: 2
---



# Automating a TradingView Death and Golden Cross Strategy

With this tutorial, you will learn how to trade with Death and Golden Crosses using two <a href="https://www.investopedia.com/terms/e/ema.asp" rel="nofollow">Exponential Moving Averages</a> (or EMA).  
The concept is to:

- Buy when the short term EMA crosses up the long term EMA. This is a <a href="https://www.investopedia.com/terms/g/goldencross.asp" rel="nofollow">Golden Cross</a> and is usually a bullish sign.
- Sell when the short term EMA crosses down the long term EMA. This is a <a href="https://www.investopedia.com/terms/d/deathcross.asp" rel="nofollow">Death Cross</a> and is usually a bearish sign.

## 1. Automatically identifying Death and Golden Crosses

### 1.1 Select your traded market

First, we want to visually see our Death and Golden Crosses. Let's go to <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> and select the trading pair, exchange and time frame we want to trade.

<div style="text-align: center">

![tradingview select btcusdt market](/images/guides/trading-view/tradingview-select-btcusdt-market.png)

</div>

For this tutorial, we will trade BTC/USDT on Binance using the 5 minutes time frame. Of course, any other value would also work.  
Note: Trading on Death and Golden Crosses is usually more profitable on longer time frames. In this tutorial the 5 minutes time frame is only meant as an example.

### 1.2 Add the EMA indicators

Then we will add the Exponential Moving Average indicator twice:

1. Once for the long term EMA
2. Once for the short term EMA

<div style="text-align: center">

![tradingview adding ema indicator](/images/guides/trading-view/tradingview-adding-ema-indicator.png)

</div>

### 1.3 Configure the EMA indicators

Click on the `Settings` of both of your EMA indicators and set the `Length` value according to how you wish to configure your Death and Golden Crosses.

<div style="text-align: center">

![tradingview configuring ema indicator](/images/guides/trading-view/tradingview-configuring-ema-indicator.png)

</div>

In this example, we will use the following values:

1. `21` for the Length of the long term EMA
2. `9` for the Length of the short term EMA

Note: you can also configure the `Style` of those EMA to make them easier to visualize on the chart

### 1.4 Visualize the Strategy

Death and Golden crosses happen when the long and short term EMA are crossing. We can now easily see what it would look like.

<div style="text-align: center">

![tradingview ema indicator visualization with golden and death crosses](/images/guides/trading-view/tradingview-ema-indicator-visualization-with-golden-and-death-crosses.png)

</div>

Our strategy is ready, the only remaining step is to create an OctoBot to trade when those crosses happen.

## 2. Creating OctoBot automations to buy and sell

### 2.1 Create a TradingView OctoBot

Let's open a new tab and go to <a href="https://www.octobot.cloud/dashboard" rel="nofollow">OctoBot cloud</a> to start a new TradingView OctoBot

<div style="text-align: center">

![start new tradingview octobot from explorer](/images/guides/trading-view/start-new-tradingview-octobot-from-explorer.png)

</div>

**[Start a bot](https://www.octobot.cloud)**

For this tutorial, we will start a bot on Binance. If you are unsure about how to start a TradingView OctoBot, check out the `Create your TradingView OctoBot` section of the [TradingView trading tutorial](../tradingview-trading-tutorial#1-create-your-tradingview-octobot).

### 2.2 Create your BUY automation

When a Golden Cross happens, we want our OctoBot to buy. For this tutorial, we will buy using 50% of our portfolio's USDT holdings.

<div style="text-align: center">

![octobot automation create buy btc](/images/guides/trading-view/octobot-automation-create-buy-btc.png)

</div>

### 2.3 Create your SELL automation

When a Death Cross occurs, we want our OctoBot to sell. For this tutorial, we will sell all of our portfolio's BTC holdings.

<div style="text-align: center">

![octobot automation create sell btc](/images/guides/trading-view/octobot-automation-create-sell-btc.png)

</div>

Note: in this tutorial, we are keeping things simple by using market orders, selling everything at once and having only one type of BUY and SELL automation.  
Since there is no limit the the automations you can create, you customize this strategy as much as you want by creating other BUY and SELL automations.

## 3. Binding automations to trigger on Crosses

Note: the following steps are assuming that you already configured your TradingView Alerts webhook URL. If it is not the case, please follow the [Configure the webhook URL guide](../tradingview-trading-tutorial#25-configure-the-webhook-url).

### 3.1 Buying on Golden Crosses

Open the connection panel of your BUY automation and copy its automation identifier.

<div style="text-align: center">

![octobot open automation connection panel](/images/guides/trading-view/octobot-open-automation-connection-panel.png)

</div>

<div style="text-align: center">

![octobot automation identifier](/images/guides/trading-view/octobot-automation-identifier.png)

</div>

Going back to your TradingView tab, create a new alert

<div style="text-align: center">

![creating an alert from tradingview](/images/guides/trading-view/creating-an-alert-from-tradingview.png)

</div>

<div style="text-align: center">

![tradingview create golden cross alert](/images/guides/trading-view/tradingview-create-golden-cross-alert.png)

</div>

In this alert, pay attention to:

- Select `Crossing Up` as wall as EMA 9 and 21 as Condition: this is our Golden Cross.
- Select `Once Per Bar Close` as Trigger to check for Golden Crosses on each candle close.
- Give a meaningful name to your alert to easily identify it later on.
- Replace the full Message value by your BUY automation identifier from the OctoBot tab.

Great ! Your TradingView strategy will not send an alert triggering your OctoBot BUY automation when a Golden Cross is identified according to your EMA settings.

### 3.2 Selling on Death Crosses

Similarly to the Golden Cross configuration:

1. On your OctoBot tab, open your SELL automation connection panel.
2. On the TradingView tab, create a seconds alert to identify Death Crosses and configure it to trigger your SELL automation.

<div style="text-align: center">

![tradingview create death cross alert](/images/guides/trading-view/tradingview-create-death-cross-alert.png)

</div>

In this alert, remember to:

- Select `Crossing Down` as wall as EMA 9 and 21 as Condition: this is our Death Cross.
- Select `Once Per Bar Close` as Trigger to check for Death Crosses on each candle close.
- Give a meaningful name to your alert to easily identify it later on.
- Replace the full Message value by your SELL automation identifier from the OctoBot tab.

## The strategy is ready

And that's it !
We just created an EMA Death and Golden Cross strategy on TradingView and automated its trading using OctoBot. Everytime a Death or Golden cross happen on TradingView, our OctoBot will buy or sell BTC accordingly.

![tradingview ema strategy illustration with 2 buy and 2 sell](/images/guides/trading-view/tradingview-ema-strategy-illustration-with-2-buy-and-2-sell.png)

![octobot tradingview trading side of ema strategy illustration with 2 buy and 2 sell](/images/guides/trading-view/octobot-tradingview-trading-side-of-ema-strategy-illustration-with-2-buy-and-2-sell.png)

Of course, you can use this configuration to trade any pair(s) on any exchange using your real funds or risk free with [simulated funds](../paper-trading-a-strategy).

**[Start your TradingView OctoBot](https://www.octobot.cloud)**

We hope this tutorial was clear enough. Please let is know if there is something we should improve.

:::info
  Warning: The strategy presented in this tutorial is only meant for educational
  purposes and is not financial advice.
:::
