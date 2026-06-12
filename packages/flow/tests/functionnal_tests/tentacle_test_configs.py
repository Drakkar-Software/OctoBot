import decimal
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Evaluator.TA.trend_evaluator.trend as trend_evaluator
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading


def _dsl_compatible_tentacle_config(config: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return {
        config_key: float(config_value) if isinstance(config_value, decimal.Decimal) else config_value
        for config_key, config_value in config.items()
        if config_value is not None
    }


def binanceus_dca_tentacle_config(**overrides: typing.Any) -> dict[str, typing.Any]:
    config = dict(
        dca_trading.DCATradingMode.get_default_config(
            buy_amount="8t%",
            exit_limit_orders_price_percent=1.75,
            entry_limit_orders_price_percent=1.5,
            secondary_entry_orders_count=1,
            secondary_entry_orders_amount="7%t",
            secondary_entry_orders_price_percent=1.0,
            secondary_exit_orders_price_percent=0.7,
            enable_stop_loss=False,
            use_init_entry_orders=True,
            use_secondary_entry_orders=True,
            use_take_profit_exit_orders=True,
            trigger_mode=dca_trading.TriggerMode.ALWAYS_TRIGGER_LONG,
            max_asset_holding_percent=50,
        )
    )
    config.update(
        {
            dca_trading.DCATradingMode.ENABLE_HEALTH_CHECK: True,
            dca_trading.DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS: False,
            dca_trading.DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_COUNT: 0,
            dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT: 50,
        }
    )
    config.update(overrides)
    return _dsl_compatible_tentacle_config(config)


def binanceus_dca_maximum_evaluators_config(**overrides: typing.Any) -> dict[str, typing.Any]:
    config = binanceus_dca_tentacle_config(
        **{
            dca_trading.DCATradingModeProducer.TRIGGER_MODE: (
                dca_trading.TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED.value
            ),
            dca_trading.DCATradingModeConsumer.USE_INIT_ENTRY_ORDERS: False,
            dca_trading.DCATradingMode.TIME_FRAMES: [commons_enums.TimeFrames.TWO_HOURS.value],
            "dag_reset_to_action_id": "action_init",
        }
    )
    config.update(overrides)
    return _dsl_compatible_tentacle_config(config)


def dma_evaluator_config(
    *,
    long_period_length: int = 10,
    short_period_length: int = 5,
) -> dict[str, typing.Any]:
    return trend_evaluator.DoubleMovingAverageTrendEvaluator.get_default_config(
        long_period_length=long_period_length,
        short_period_length=short_period_length,
    )


def rsi_evaluator_config(
    *,
    period_length: int = 12,
    long_threshold: float = 50,
    short_threshold: float = 70,
    trend_change_identifier: bool = False,
) -> dict[str, typing.Any]:
    return momentum_evaluator.RSIMomentumEvaluator.get_default_config(
        period_length=period_length,
        long_threshold=long_threshold,
        short_threshold=short_threshold,
        trend_change_identifier=trend_change_identifier,
    )


def strategy_evaluator_config(
    *,
    time_frames: list[str] | None = None,
    required_candles_count: int = 15,
) -> dict[str, typing.Any]:
    resolved_time_frames = time_frames
    if resolved_time_frames is None:
        resolved_time_frames = [commons_enums.TimeFrames.TWO_HOURS.value]
    config = mixed_strategies_evaluator.SimpleStrategyEvaluator.get_default_config(
        time_frames=resolved_time_frames,
    )
    config[commons_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT] = required_candles_count
    config[mixed_strategies_evaluator.SimpleStrategyEvaluator.BACKGROUND_SOCIAL_EVALUATORS] = []
    return config


def grid_trading_mode_tentacle_config(
    pair_settings: list[dict[str, typing.Any]],
) -> dict[str, typing.Any]:
    return {
        grid_trading.GridTradingMode.CONFIG_PAIR_SETTINGS: pair_settings,
    }


def grid_trading_mode_profile_tentacle(
    *,
    symbol: str,
    spread: float,
    increment: float,
    buy_count: int,
    sell_count: int,
) -> dict[str, typing.Any]:
    return {
        "name": grid_trading.GridTradingMode.get_name(),
        "config": grid_trading_mode_tentacle_config(
            [
                grid_trading.GridTradingMode.get_default_pair_config(
                    symbol,
                    spread,
                    increment,
                    buy_count,
                    sell_count,
                    False,
                    False,
                    False,
                )
            ]
        ),
    }
