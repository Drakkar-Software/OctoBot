---
title: "Supported Exchanges"
description: "Discover the many exchanges supported by OctoBot. Trade on Binance, OKX, Kucoin, Bybit, Crypto.com, HTX, Coinbase, Bitget, HollaEx, BingX, MEXC and many more."
sidebar_position: 7
---

# Exchanges in OctoBot

:::info
  For users of the open source OctoBot.
:::

## Officially supported exchanges

- [Binance](exchanges/binance)
- [OKX](exchanges/okx)
- [Kucoin](exchanges/kucoin)
- [Coinbase](exchanges/coinbase)
- [Binance US](exchanges/binance-us)
- [Bybit](exchanges/bybit)
- [Crypto.com](exchanges/cryptocom)
- [HTX](exchanges/htx)
- [Bitget](exchanges/bitget)
- [Hyperliquid](exchanges/hyperliquid)
- [BingX](exchanges/bingx)
- [MEXC](exchanges/mexc)
- [CoinEx](exchanges/coinex)
- [BitMart](exchanges/bitmart)
- [HollaEx](exchanges/hollaex)
- [Phemex](exchanges/phemex)
- [GateIO](exchanges/gateio)
- [Ascendex](exchanges/ascendex)

## Partner exchanges - Support OctoBot

As the OctoBot team, **our goal is to keep providing the [open source OctoBot](/guides/octobot-installation/install-octobot-on-your-computer) for free**. However developing and maintaining the project comes at a cost. Therefore we rely on exchanges partnerships to propose the most convenient way to support OctoBot.

By using OctoBot on real trading with our partner exchanges, you contribute to support the project and it won't cost you any money.

## Community tested exchanges

- [Kraken](exchanges/kraken)
- [Bitstamp](exchanges/bitstamp)
- [Bitfinex](exchanges/bitfinex)
- [Poloniex](exchanges/poloniex)

## Exchanges support

OctoBot uses <a href="https://github.com/ccxt/ccxt" rel="nofollow">ccxt</a> to connect to exchanges. In theory, any exchange that is <a href="https://github.com/ccxt/ccxt/wiki/Exchange-Markets" rel="nofollow">supported on ccxt</a> should work. However only partner, and officially supported exchanges are regularly tested by the OctoBot Team.

Using an exchange that is not a partner or officially supported **is at your own risks**.

### REST

The REST technology is a HTTP polling based interface where exchanges have to be frequently requested to refresh OctoBot's databases.
It:

- is **slower**: it might take a few seconds to update prices and orders
- can handle a **limited** amount of requests per seconds due to exchanges restrictions. Therefore only a limited amount of trading pairs can be handled simultaneously when using a REST interface.

The REST technology is the default connection on any exchange.

### Websocket

The websocket technology allows for permanent channels between exchanges and OctoBot from which exchanges directly push updated information to OctoBot.
It:

- is **almost instantaneous**: updates are directly pushed to OctoBot when updated on the exchange
- is **limitless** regarding the amount trading pairs that can be handled simultaneously

The websocket technology is automatically enabled on each exchange when supported.
