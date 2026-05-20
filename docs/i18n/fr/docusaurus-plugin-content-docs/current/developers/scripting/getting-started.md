---
title: "Commencer le scripting"
description: "Exploitez la puissance du framework OctoBot au sein de vos propres stratégies de trading scriptées en Python tout en gardant la simplicité d'un Pine Script TradingView."
sidebar_position: 17
---



# OctoBot Script

:::note
  Pour les utilisateurs d'
  <a href="https://github.com/Drakkar-Software/OctoBot-script" rel="nofollow">OctoBot Script</a>
  .
:::

:::info
  La traduction française de cette page est en cours.
:::

## Le framework de trading par script basé sur OctoBot

> OctoBot Script est dans une version alpha

OctoBot Script vous permet d'exploiter la puissance du framework OctoBot tout en gardant la simplicité d'un Pine Script TradingView.

With OctoBot Script, automatisez vos stratégies de trading en utilisant vos scripts hautement optimisés

- Que ce soit à partir de vos idées de stratégies scriptées, comme sur le Pine Script de <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a>
- Ou en utilisant une stratégie avancée basée sur l'IA

## Installer OctoBot Script depuis pip

> OctoBot Script nécessite **Python 3.10**

```{.sourceCode .bash}
python3 -m pip install OctoBot wheel appdirs==1.4.4
python3 -m pip install octobot-script
```

## Exemple de script: une strategie RSI

Dans cet exemple, OctoBot script permet de créer rapidement une stratégie de trading basée sur le <a href="https://www.investopedia.com/terms/r/rsi.asp" rel="nofollow">RSI</a> comprenant:

- une prise de profit à 25% de gains
- un stop loss à 15% de perte

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

## Rapport généré

![rapport octobot pro avec btc usdt avec graphiques de trades et portfolio et rsi](/images/guides/octobot-pro/octobot-pro-report-btc-usdt-with-chart-trades-portfolio-value-and-rsi.jpg)

## Rejoignez la communauté

Nous avons récemment créé un canal Telegram dédié au script OctoBot.

<a href="https://t.me/+366CLLZ2NC0xMjFk" rel="nofollow">Telegram News</a>
