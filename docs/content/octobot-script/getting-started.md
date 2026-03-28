---
title: "Start scripting"
description: "Harness the power of the OctoBot framework within your own python scripted trading strategies while keeping it as simple as a TradingView Pine Script."
sidebar_position: 17
---



# OctoBot script

:::info
For users of <a href="https://github.com/Drakkar-Software/OctoBot-script" rel="nofollow">OctoBot script</a>.
:::

## The script-based trading framework using OctoBot

> OctoBot script is in early alpha version

OctoBot script allows you to harness the power of the OctoBot framework while keeping it as simple as a TradingView Pine Script.

With OctoBot script, automate your trading strategies using your own highly optimized scripts

- Whether it is from your scripted strategy ideas, like on <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> Pine Script
- Or using an advanced AI based strategy

## Install OctoBot script from pip

> OctoBot script requires **Python 3.10**

```{.sourceCode .bash}
python3 -m pip install OctoBot wheel appdirs==1.4.4
python3 -m pip install octobot-script
```

## Script example: RSI strategy

In this example, OctoBot script allows to quickly create a <a href="https://www.investopedia.com/terms/r/rsi.asp" rel="nofollow">RSI</a>
based trading strategy including:

- a take profit at 25% profits
- a stop loss at 15% loss

```python


async def rsi_test():
    async def strategy(ctx):
        # Will be called at each candle.
        if run_data["entries"] is None:
            # Compute entries only once per backtest.
            closes = await obs.Close(ctx, max_history=True)
            times = await obs.Time(ctx, max_history=True, use_close_time=True)
            rsi_v = tulipy.rsi(closes, period=ctx.tentacle.trading_config["period"])
            delta = len(closes) - len(rsi_v)
            # Populate entries with timestamps of candles where RSI is
            # below the "rsi_value_buy_threshold" configuration.
            run_data["entries"] = {
                times[index + delta]
                for index, rsi_val in enumerate(rsi_v)
                if rsi_val < ctx.tentacle.trading_config["rsi_value_buy_threshold"]
            }
            await obs.plot_indicator(ctx, "RSI", times[delta:], rsi_v, run_data["entries"])
        if obs.current_live_time(ctx) in run_data["entries"]:
            # Uses pre-computed entries times to enter positions when relevant.
            # Also, instantly set take profits and stop losses.
            # Position exists could also be set separately.
            await obs.market(ctx, "buy", amount="10%", stop_loss_offset="-15%", take_profit_offset="25%")

    # Configuration that will be passed to each run.
    # It will be accessible under "ctx.tentacle.trading_config".
    config = {
        "period": 10,
        "rsi_value_buy_threshold": 28,
    }

    # Read and cache candle data to make subsequent backtesting runs faster.
    data = await obs.get_data("BTC/USDT", "1d", start_timestamp=1505606400)
    run_data = {
        "entries": None,
    }
    # Run a backtest using the above data, strategy and configuration.
    res = await obs.run(data, strategy, config)
    print(res.describe())
    # Generate and open report including indicators plots
    await res.plot(show=True)
    # Stop data to release local databases.
    await data.stop()


# Call the execution of the script inside "asyncio.run" as
# OctoBot script runs using the python asyncio framework.
asyncio.run(rsi_test())
```

## Generated report

![octobot pro report btc usdt with chart trades portfolio value and rsi](/images/guides/octobot-pro/octobot-pro-report-btc-usdt-with-chart-trades-portfolio-value-and-rsi.jpg)

## Join the community

We recently created a telegram channel dedicated to OctoBot script.

<a href="https://t.me/+366CLLZ2NC0xMjFk" rel="nofollow">Telegram News</a>
