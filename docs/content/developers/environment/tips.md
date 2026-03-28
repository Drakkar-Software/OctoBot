---
title: "Developer tips"
description: "Profit from our tips to get you quickly started as an OctoBot developer. Explore the SQLite backtesting files using SQLite browser and test your strategies."
sidebar_position: 9
---



# Developer tips

## Backtesting data

[Backtesting](/guides/octobot-usage/backtesting) data files are sqlite database files. When using the regular data collector, these files contain every historical candles the requested exchange is willing to give. You can use a <a href="https://sqlitebrowser.org/" rel="nofollow">SQLite browser</a> to explore these files.

## Strategy tests

To quickly check tentacles strategy tests states or develop a new tentacles strategy test, change the following lines in **octobot/tests/functional_tests/strategy_evaluators_tests/abstract_strategy_test.py**:

```python
def _handle_results(self, independent_backtesting, profitability):
    exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
    for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
        _, run_profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
        actual = round(run_profitability, 3)
        # uncomment this print for building tests
        # print(f"results: rounded run profitability {actual} market profitability: {market_average_profitability}"
        #       f" expected: {profitability} [result: {actual ==  profitability}]")
        assert actual == profitability
```

into

```python
def _handle_results(self, independent_backtesting, profitability):
    exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
    for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
        _, run_profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
        actual = round(run_profitability, 3)
        # uncomment this print for building tests
        print(f"results: rounded run profitability {actual} market profitability: {market_average_profitability}"
              f" expected: {profitability} [result: {actual ==  profitability}]")
        # assert actual == profitability
```

This will not stop tests on failure and display the current tests results as well as expected values.
