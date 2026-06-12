import decimal
import typing

import octobot_commons.enums as commons_enums
import octobot_copy.enums as copy_enums
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config
import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading


def tentacle_action_id(tentacle_name: str, instance_index: int = 1) -> str:
    return f"{trading_tentacles_config.normalize_tentacle_name(tentacle_name)}_{instance_index}"


def _dsl_compatible_tentacle_config(config: dict[str, typing.Any]) -> dict[str, typing.Any]:
    return {
        config_key: float(config_value) if isinstance(config_value, decimal.Decimal) else config_value
        for config_key, config_value in config.items()
        if config_value is not None
    }


def dca_tentacle_config(**overrides: typing.Any) -> dict[str, typing.Any]:
    config = dict(
        dca_trading.DCATradingMode.get_default_config(
            buy_amount="8%t",
            exit_limit_orders_price_percent=1.75,
            entry_limit_orders_price_percent=1.5,
            secondary_entry_orders_count=1,
            secondary_entry_orders_amount="7%t",
            secondary_entry_orders_price_percent=1.0,
            enable_stop_loss=False,
            use_init_entry_orders=True,
            use_secondary_entry_orders=True,
            use_take_profit_exit_orders=True,
            trigger_mode=dca_trading.TriggerMode.TIME_BASED,
            max_asset_holding_percent=50,
        )
    )
    config[dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT] = 50
    config[dca_trading.DCATradingMode.TRADING_PAIRS] = ["BTC/USDT"]
    config.update(overrides)
    return _dsl_compatible_tentacle_config(config)


def rsi_evaluator_configuration(
    symbols: list[str],
    *,
    period_length: int = 12,
    long_threshold: float = 50,
    short_threshold: float = 70,
    trend_change_identifier: bool = False,
    include_in_construction_candle: bool = False,
) -> protocol_models.EvaluatorConfiguration:
    return protocol_models.EvaluatorConfiguration(
        name=momentum_evaluator.RSIMomentumEvaluator.get_name(),
        config=momentum_evaluator.RSIMomentumEvaluator.get_default_config(
            period_length=period_length,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            trend_change_identifier=trend_change_identifier,
        ),
        symbols=symbols,
        include_in_construction_candle=include_in_construction_candle,
    )


def ema_evaluator_configuration(
    symbols: list[str],
    *,
    period_length: int = 10,
    price_threshold_percent: float = 1.0,
    reverse_signal: bool = False,
    include_in_construction_candle: bool = False,
) -> protocol_models.EvaluatorConfiguration:
    return protocol_models.EvaluatorConfiguration(
        name=momentum_evaluator.EMAMomentumEvaluator.get_name(),
        config=momentum_evaluator.EMAMomentumEvaluator.get_default_config(
            period_length=period_length,
            price_threshold_percent=price_threshold_percent,
            reverse_signal=reverse_signal,
        ),
        symbols=symbols,
        include_in_construction_candle=include_in_construction_candle,
    )


def simple_strategy_evaluator_configuration(
    time_frames: list[str],
) -> protocol_models.StrategyEvaluatorConfiguration:
    return protocol_models.StrategyEvaluatorConfiguration(
        name=mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name(),
        config=mixed_strategies_evaluator.SimpleStrategyEvaluator.get_default_config(
            time_frames=time_frames,
        ),
        time_frames=time_frames,
    )


def trading_tentacles_configuration(
    *,
    name: str,
    config: dict[str, typing.Any],
    symbols: list[str] | None = None,
    strategies: list[protocol_models.StrategyEvaluatorConfiguration] | None = None,
    evaluators: list[protocol_models.EvaluatorConfiguration] | None = None,
) -> protocol_models.TradingTentaclesConfiguration:
    return protocol_models.TradingTentaclesConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.TRADING_TENTACLES,
        name=name,
        config=config,
        symbols=symbols,
        strategies=strategies,
        evaluators=evaluators,
    )


def minimal_dca_trading_configuration(**overrides) -> protocol_models.TradingTentaclesConfiguration:
    symbols = overrides.pop("symbols", ["BTC/USDT"])
    strategies = overrides.pop("strategies", [])
    evaluators = overrides.pop("evaluators", [])
    entry_order_amount = overrides.pop("entry_order_amount", "10%t")
    config = dca_tentacle_config()
    config[trading_constants.CONFIG_BUY_ORDER_AMOUNT] = entry_order_amount
    config[dca_trading.DCATradingMode.TRADING_PAIRS] = list(symbols)
    config.update(overrides)
    return trading_tentacles_configuration(
        name=dca_trading.DCATradingMode.get_name(),
        config=config,
        symbols=list(symbols),
        strategies=strategies,
        evaluators=evaluators,
    )


def functional_dca_trading_configuration() -> protocol_models.TradingTentaclesConfiguration:
    traded_symbols = ["BTC/USDC", "ETH/USDC"]
    return trading_tentacles_configuration(
        name=dca_trading.DCATradingMode.get_name(),
        config=dca_tentacle_config(
            **{
                dca_trading.DCATradingModeProducer.TRIGGER_MODE: (
                    dca_trading.TriggerMode.ALWAYS_TRIGGER_LONG.value
                ),
                dca_trading.DCATradingMode.TRADING_PAIRS: traded_symbols,
            }
        ),
        symbols=traded_symbols,
    )


def maximum_evaluators_trading_configuration(
    *,
    strategies: list[protocol_models.StrategyEvaluatorConfiguration] | None = None,
    evaluators: list[protocol_models.EvaluatorConfiguration] | None = None,
    traded_symbols: list[str] | None = None,
    time_frame: str = commons_enums.TimeFrames.ONE_HOUR.value,
) -> protocol_models.TradingTentaclesConfiguration:
    resolved_traded_symbols = traded_symbols
    if resolved_traded_symbols is None:
        resolved_traded_symbols = ["BTC/USDC", "ETH/USDC"]
    resolved_strategies = strategies
    if resolved_strategies is None:
        resolved_strategies = [
            simple_strategy_evaluator_configuration(time_frames=[time_frame]),
        ]
    resolved_evaluators = evaluators
    if resolved_evaluators is None:
        resolved_evaluators = [
            rsi_evaluator_configuration(resolved_traded_symbols),
            ema_evaluator_configuration(resolved_traded_symbols),
        ]
    return trading_tentacles_configuration(
        name=dca_trading.DCATradingMode.get_name(),
        config=dca_tentacle_config(
            **{
                dca_trading.DCATradingModeProducer.TRIGGER_MODE: (
                    dca_trading.TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED.value
                ),
                dca_trading.DCATradingModeConsumer.USE_INIT_ENTRY_ORDERS: False,
                dca_trading.DCATradingMode.TRADING_PAIRS: [],
                dca_trading.DCATradingMode.TIME_FRAMES: [time_frame],
            }
        ),
        strategies=resolved_strategies,
        evaluators=resolved_evaluators,
    )


def grid_trading_configuration(
    *,
    symbol: str = "BTC/USDT",
    spread: float = 6,
    increment: float = 2,
    buy_count: int = 2,
    sell_count: int = 2,
    enable_trailing_up: bool = False,
    enable_trailing_down: bool = False,
    order_by_order_trailing: bool = False,
) -> protocol_models.TradingTentaclesConfiguration:
    pair_settings = [
        grid_trading.GridTradingMode.get_default_pair_config(
            symbol,
            spread,
            increment,
            buy_count,
            sell_count,
            enable_trailing_up,
            enable_trailing_down,
            order_by_order_trailing,
        )
    ]
    return trading_tentacles_configuration(
        name=grid_trading.GridTradingMode.get_name(),
        config={
            grid_trading.GridTradingMode.CONFIG_PAIR_SETTINGS: pair_settings,
        },
        symbols=[symbol],
    )


def index_trading_configuration(
    *,
    coins: list[tuple[str, float]],
    rebalance_trigger_min_percent: float,
) -> protocol_models.TradingTentaclesConfiguration:
    index_content = [
        {
            copy_enums.DistributionKeys.NAME: coin_name,
            copy_enums.DistributionKeys.VALUE: coin_ratio,
        }
        for coin_name, coin_ratio in coins
    ]
    return trading_tentacles_configuration(
        name=index_trading.IndexTradingMode.get_name(),
        config={
            index_trading.IndexTradingModeProducer.INDEX_CONTENT: index_content,
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: (
                rebalance_trigger_min_percent
            ),
        },
    )


def evaluator_configuration_with_symbols(symbols: list[str]) -> protocol_models.EvaluatorConfiguration:
    return rsi_evaluator_configuration(symbols)
