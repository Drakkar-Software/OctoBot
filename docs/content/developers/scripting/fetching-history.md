---
title: "Historical data"
description: "Learn how to fetch and reuse exchange historical market trading data with python using OctoBot script."
sidebar_position: 14
---



# Fetching trading data

In order to run a backtest, OctoBot script requires historical
trading data, which is at least candles history.

## Fetching new data

When using OctoBot script, historical data can be fetched using:
`await obs.get_data(symbol, time frame)`

Where:

- symbol: the trading symbol to fetch data from. It can also be a list of symbols
- time frame: the time frame to fetch (1h, 4h, 1d, etc). It can also be a list of time frames

Optional arguments:

- start_timestamp: the unix timestamp to start fetching data from. Use <a href="https://www.epochconverter.com/" rel="nofollow">this converter</a> if you are unsure what you should use.
- exchange: the exchange to fetch data from. Default is "binance"
- exchange_type: the exchange trading type to fetch data from. Default is "spot", "future" is also possible on supported exchanges

```python
data = await obs.get_data("BTC/USDT", "1d", start_timestamp=1505606400)
```

## Re-using fetched data

Calling `data = await obs.get_data` will save the downloaded data into the `backtesting/data` local folder.
If you want to speedup subsequent calls, you can provide the `data_file` optional argument to read
data from this file instead of downloading historical data. This also makes it possible to run a
script while being offline.

You can get the name of the downloaded backtesting file by accessing
`data.data_files[0]`

```python
data = await obs.get_data("BTC/USDT", "1d", start_timestamp=1505606400)
# print the name of the downloaded data file
print(data.data_files[0])
```

```python
datafile = "ExchangeHistoryDataCollector_1671754854.5234916.data"
# will not download historical data as a local data_file is provided
data = await obs.get_data("BTC/USDT", "1d", start_timestamp=1505606400, data_file=datafile)
```
