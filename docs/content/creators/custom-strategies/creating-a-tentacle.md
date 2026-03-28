---
title: Creating a Tentacle
description: How to build a custom OctoBot tentacle - trading mode, evaluator, or exchange connector.
keywords: [octobot, tentacle, custom, plugin, development, strategy]
sidebar_position: 1
---

# Creating a Custom Tentacle

Tentacles are OctoBot's plugin system. You can create custom trading modes, evaluators, and exchange connectors.

## Tentacle Structure

A tentacle is a Python module that follows a specific directory layout:

```
MyCustomEvaluator/
  __init__.py
  my_custom_evaluator.py
  resources/
    MyCustomEvaluator.md    # Documentation
```

## Creating an Evaluator

```python
import octobot_commons.enums as commons_enums
import octobot_evaluators.evaluators as evaluators


class MyCustomEvaluator(evaluators.TAEvaluator):
    """A custom technical analysis evaluator."""

    async def ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle,
        inc_in_construction_data,
    ):
        # Your analysis logic here
        evaluation = 0.5  # -1 (sell) to +1 (buy)
        await self.evaluation_completed(
            cryptocurrency, symbol, time_frame,
            eval_note=evaluation,
        )
```

## Creating a Trading Mode

Trading modes define the complete trading logic. Extend `AbstractTradingMode` and implement the order creation logic.

## Installing Custom Tentacles

Place your tentacle in the `tentacles/` directory and install:

```bash
OctoBot tentacles --install --location ./my_tentacle_package.zip --all
```

## Testing

Test your tentacle using backtesting to validate it works correctly before live trading.
