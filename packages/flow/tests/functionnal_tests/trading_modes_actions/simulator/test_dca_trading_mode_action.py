import contextlib
import decimal
import time
import typing

import mock
import pytest

import octobot_commons.constants as common_constants
import octobot_commons.str_util as str_util
import octobot_commons.enums as common_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchanges.util.exchange_data as exchange_data
import octobot_flow.jobs
import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.repositories.community
import octobot_flow.repositories.exchange
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools

import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Evaluator.TA.trend_evaluator.trend as trend_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    assert_emitted_signal_account_allocation_ratios,
    automation_state_dict,
    current_time,
    d_order_price,
    empty_copy_exchange_account_action,
    resolved_actions,
    set_emit_signals_metadata,
    trading_signal_emission_patches,
)

BTC_USDC = "BTC/USDC"
ETH_USDC = "ETH/USDC"
TRADED_SYMBOLS = (BTC_USDC, ETH_USDC)
BTC_BASE_ASSET = symbol_util.parse_symbol(BTC_USDC).base
ETH_BASE_ASSET = symbol_util.parse_symbol(ETH_USDC).base
QUOTE_ASSET = symbol_util.parse_symbol(BTC_USDC).quote
_FIXED_BTC_USDC_CLOSE = 100000.0
_FIXED_ETH_USDC_CLOSE = 2000.0
D_ENTRY_LIMIT_PERCENT = decimal.Decimal("0.015")
D_SECONDARY_ENTRY_STEP_PERCENT = decimal.Decimal("0.01")
D_EXIT_LIMIT_PERCENT = decimal.Decimal("0.0175")
PRICE_TOLERANCE = decimal.Decimal("0.5")

SIMULATOR_COPY_DCA_FUNCTIONAL_TEST_COMMUNITY_WALLET_ADDRESS = (
    "simulator-copy-dca-functional-test-wallet-address"
)

DCA_TRADING_MODE_DSL_OPERATOR = str_util.camel_to_snake(dca_trading.DCATradingMode.get_name())
DMA_EVALUATOR_DSL_OPERATOR = str_util.camel_to_snake(trend_evaluator.DoubleMovingAverageTrendEvaluator.get_name())
RSI_EVALUATOR_DSL_OPERATOR = str_util.camel_to_snake(momentum_evaluator.RSIMomentumEvaluator.get_name())
STRATEGY_EVALUATOR_DSL_OPERATOR = str_util.camel_to_snake(mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name())

# BinanceUS smart-DCA product shape: BTC/USDC + ETH/USDC, fixed ticker closes patched in tests.
BINANCEUS_DCA_TENTACLE_CONFIG = {
    "trigger_mode": dca_trading.TriggerMode.ALWAYS_TRIGGER_LONG.value,
    "use_stop_losses": False,
    "buy_order_amount": "8t%",
    "enable_health_check": True,
    "use_init_entry_orders": True,
    "minutes_before_next_buy": 10080,
    "use_market_entry_orders": False,
    "max_asset_holding_percent": 50,
    "use_secondary_exit_orders": False,
    "use_secondary_entry_orders": True,
    "secondary_exit_orders_count": 0,
    "use_take_profit_exit_orders": True,
    "secondary_entry_orders_count": 1,
    "secondary_entry_orders_amount": "7%t",
    "exit_limit_orders_price_percent": 1.75,
    "entry_limit_orders_price_percent": 1.5,
    "secondary_exit_orders_price_percent": 0.7,
    "secondary_entry_orders_price_percent": 1,
    dca_trading.DCATradingMode.TRADING_PAIRS: [BTC_USDC, ETH_USDC],
}

BINANCEUS_DCA_MAXIMUM_EVALUATORS_CONFIG = {
    **BINANCEUS_DCA_TENTACLE_CONFIG,
    "trigger_mode": dca_trading.TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED.value,
    "use_init_entry_orders": False,
    "time_frames": [common_enums.TimeFrames.TWO_HOURS.value],
    "dag_reset_to_action_id": "action_init",
}

BINANCEUS_DCA_MAXIMUM_EVALUATORS_FROM_STRATEGY_SYMBOLS_CONFIG = {
    **BINANCEUS_DCA_MAXIMUM_EVALUATORS_CONFIG,
    dca_trading.DCATradingMode.TRADING_PAIRS: [],
}

DMA_EVALUATOR_CONFIG = {
    "long_period_length": 10,
    "short_period_length": 5,
}

RSI_EVALUATOR_CONFIG = {
    "period_length": 12,
    "long_threshold": 50,
    "short_threshold": 70,
    "trend_change_identifier": False,
}

STRATEGY_EVALUATOR_CONFIG = {
    "background_social_evaluators": [],
    "required_time_frames": [common_enums.TimeFrames.TWO_HOURS.value],
    "required_candles_count": 15,
}


def _close_to_decimal(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    if isinstance(close, decimal.Decimal):
        return close
    return decimal.Decimal(str(close))


def initial_buy_price(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    close_decimal = _close_to_decimal(close)
    return close_decimal * (decimal.Decimal("1") - D_ENTRY_LIMIT_PERCENT)


def secondary_buy_price(close: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    close_decimal = _close_to_decimal(close)
    return close_decimal * (
        decimal.Decimal("1") - D_ENTRY_LIMIT_PERCENT - D_SECONDARY_ENTRY_STEP_PERCENT
    )


def take_profit_price(entry_price: decimal.Decimal) -> decimal.Decimal:
    return entry_price * (decimal.Decimal("1") + D_EXIT_LIMIT_PERCENT)


def _dsl_evaluator_action(
    action_id: str,
    operator_name: str,
    dependency_action_id: str,
    evaluator_config: dict,
    extra_dependencies: typing.Optional[list[dict]] = None,
    symbols: tuple[str, ...] = TRADED_SYMBOLS,
) -> dict:
    config_parts = ", ".join(
        f"{key}={dsl_interpreter.format_parameter_value(value)}"
        for key, value in evaluator_config.items()
    )
    unresolved_placeholder = common_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    injected_parameter_names = []
    injected_dependency_parts = []
    for dependency in (extra_dependencies or []):
        parameter_name = dependency.get("parameter")
        if parameter_name and parameter_name not in injected_parameter_names:
            injected_parameter_names.append(parameter_name)
            injected_dependency_parts.append(f"{parameter_name}={unresolved_placeholder}")
    if operator_name == STRATEGY_EVALUATOR_DSL_OPERATOR:
        dsl_parameters = f"time_frames=['{common_enums.TimeFrames.TWO_HOURS.value}']"
    else:
        symbols_list = ", ".join(f"'{symbol}'" for symbol in symbols)
        dsl_parameters = (
            f"symbols=[{symbols_list}], time_frames=['{common_enums.TimeFrames.TWO_HOURS.value}']"
        )
    if config_parts:
        dsl_parameters = f"{dsl_parameters}, {config_parts}"
    if injected_dependency_parts:
        dsl_parameters = f"{dsl_parameters}, {', '.join(injected_dependency_parts)}"
    dependencies = [{"action_id": dependency_action_id}]
    if extra_dependencies:
        dependencies.extend(extra_dependencies)
    return {
        "id": action_id,
        "dsl_script": f"{operator_name}({dsl_parameters})",
        "dependencies": dependencies,
    }


def _evaluator_results(action) -> list[dict]:
    if action.result is None:
        return []
    if isinstance(action.result, list):
        return action.result
    return [action.result]


def _evaluator_result_for_symbol(action, symbol: str) -> dict:
    matching_results = [
        evaluator_result
        for evaluator_result in _evaluator_results(action)
        if evaluator_result.get("symbol") == symbol
    ]
    assert len(matching_results) == 1, (
        f"Expected one evaluator result for {symbol}, got {matching_results}"
    )
    return matching_results[0]


def _single_evaluator_result(action) -> dict:
    evaluator_results = _evaluator_results(action)
    assert len(evaluator_results) == 1, (
        f"Expected one evaluator result, got {evaluator_results}"
    )
    return evaluator_results[0]


def _assert_evaluator_results_for_traded_symbols(
    action,
    *,
    eval_note: float,
    evaluator_name: str,
    time_frame: str = common_enums.TimeFrames.TWO_HOURS.value,
) -> None:
    assert len(_evaluator_results(action)) == len(TRADED_SYMBOLS)
    for traded_symbol in TRADED_SYMBOLS:
        evaluator_result = _evaluator_result_for_symbol(action, traded_symbol)
        assert evaluator_result["eval_note"] == eval_note
        assert evaluator_result["evaluator_name"] == evaluator_name
        assert evaluator_result["time_frame"] == time_frame


def _maximum_evaluators_dca_action(
    dependency_action_id: str,
    *,
    dca_config: dict | None = None,
) -> dict:
    resolved_dca_config = dca_config or BINANCEUS_DCA_MAXIMUM_EVALUATORS_CONFIG
    config_parts = ", ".join(
        f"{key}={dsl_interpreter.format_parameter_value(value)}"
        for key, value in resolved_dca_config.items()
    )
    unresolved_placeholder = common_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    return {
        "id": "action_dca",
        "dsl_script": (
            f"{DCA_TRADING_MODE_DSL_OPERATOR}({config_parts}, "
            f"_dynamic_dependencies={unresolved_placeholder})"
        ),
        "dependencies": [
            {"action_id": dependency_action_id},
            {"action_id": "action_strategy", "parameter": "_dynamic_dependencies"},
        ],
    }


def _assert_dag_action(
    actions_dag,
    action_id: str,
    *,
    completed: bool,
    error_status: str = octobot_flow.enums.ActionErrorStatus.NO_ERROR.value,
    result_is_none: typing.Optional[bool] = None,
    previous_result_is_none: typing.Optional[bool] = None,
    result_eval_note: typing.Optional[int] = None,
) -> None:
    action = actions_dag.get_actions_by_id()[action_id]
    assert action.error_status == error_status
    assert action.is_completed() == completed
    if result_is_none is not None:
        assert (action.result is None) == result_is_none
    if previous_result_is_none is not None:
        assert (action.previous_execution_result is None) == previous_result_is_none
    if result_eval_note is not None:
        assert _single_evaluator_result(action)["eval_note"] == result_eval_note


def _assert_dag_snapshot(actions_dag, expected: dict[str, dict]) -> None:
    for action_id, assertion_kwargs in expected.items():
        _assert_dag_action(actions_dag, action_id, **assertion_kwargs)


def dca_trading_mode_action(dependency_action: dict) -> dict:
    config_parts = ", ".join(
        f"{key}={dsl_interpreter.format_parameter_value(value)}"
        for key, value in BINANCEUS_DCA_TENTACLE_CONFIG.items()
    )
    return {
        "id": "action_1",
        "dsl_script": f"{DCA_TRADING_MODE_DSL_OPERATOR}({config_parts})",
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


def _dca_reference_storage_order(
    order_id: str,
    side: str,
    price: float,
    amount: float,
    symbol: str = BTC_USDC,
) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: order_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: side,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: price,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value: trading_enums.OrderStatus.OPEN.value,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
            trading_enums.ExchangeConstantsOrderColumns.REMAINING.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: time.time(),
            trading_enums.ExchangeConstantsOrderColumns.SELF_MANAGED.value: False,
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "test-exchange",
            trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: True,
            trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: False,
            trading_enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value: True,
        }
    }


def _dca_reference_buy_storage_order_with_chained_take_profit(
    buy_order_id: str,
    buy_price: float,
    amount: float,
    symbol: str,
) -> dict:
    buy_order_storage = _dca_reference_storage_order(
        buy_order_id,
        trading_enums.TradeOrderSide.BUY.value,
        buy_price,
        amount,
        symbol,
    )
    take_profit_sell_price = float(
        take_profit_price(decimal.Decimal(str(buy_price)))
    )
    chained_sell_order_storage = _dca_reference_storage_order(
        f"{buy_order_id}_tp",
        trading_enums.TradeOrderSide.SELL.value,
        take_profit_sell_price,
        amount,
        symbol,
    )
    buy_order_storage[trading_enums.StoredOrdersAttr.CHAINED_ORDERS.value] = [
        chained_sell_order_storage
    ]
    return buy_order_storage


def copied_account_from_content_and_storage_orders(
    *,
    updated_at: float,
    content: dict,
    orders_storage: list,
) -> protocol_models.CopiedAccount:
    copied_assets = [
        protocol_models.CopiedAsset(
            name=name,
            total=float(balance[common_constants.PORTFOLIO_TOTAL]),
            available=float(balance[common_constants.PORTFOLIO_AVAILABLE]),
            ratio=float(balance[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO]),
        )
        for name, balance in sorted(content.items(), key=lambda item: item[0])
    ]
    orders = [trading_personal_data.to_protocol_order(row) for row in orders_storage]
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=updated_at,
        copied_assets=copied_assets,
        orders=orders,
        positions=[],
    )


def fetch_ohlcv_side_effect_for_declining_closes(
    get_start_close_for_symbol: typing.Callable[[str], typing.Union[int, float]],
    decline_per_candle: typing.Union[float, typing.Callable[[str], float]],
):
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        time_frame_seconds = common_enums.TimeFramesMinutes[common_enums.TimeFrames(time_frame)] * 60
        candle_count = max(int(limit or 1), 15)
        start_close = float(get_start_close_for_symbol(symbol))
        symbol_decline_per_candle = (
            decline_per_candle(symbol)
            if callable(decline_per_candle)
            else decline_per_candle
        )
        local_time = time.time()
        current_candle_open_time = local_time - (local_time % time_frame_seconds)
        first_candle_open_time = current_candle_open_time - (candle_count - 1) * time_frame_seconds
        times = [float(first_candle_open_time + index * time_frame_seconds) for index in range(candle_count)]
        closes = [
            start_close - (symbol_decline_per_candle * index)
            for index in range(candle_count)
        ]
        if candle_count >= 2:
            closes[-1] = closes[-2] - (symbol_decline_per_candle * 10)
        return exchange_data.MarketDetails(
            symbol=symbol,
            time_frame=time_frame,
            close=closes,
            open=closes,
            high=closes,
            low=closes,
            volume=[0.0] * candle_count,
            time=times,
        )

    return patched_fetch_ohlcv


def fetch_ohlcv_side_effect_for_close_prices(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        time_frame_seconds = common_enums.TimeFramesMinutes[common_enums.TimeFrames(time_frame)] * 60
        close_price = float(get_close_price_for_symbol(symbol))
        candle_count = max(int(limit or 1), 1)
        local_time = time.time()
        current_candle_open_time = local_time - (local_time % time_frame_seconds)
        first_candle_open_time = current_candle_open_time - (candle_count - 1) * time_frame_seconds
        times = [float(first_candle_open_time + index * time_frame_seconds) for index in range(candle_count)]
        closes = [close_price] * candle_count
        ohlc = [close_price] * candle_count
        return exchange_data.MarketDetails(
            symbol=symbol,
            time_frame=time_frame,
            close=closes,
            open=ohlc,
            high=ohlc,
            low=ohlc,
            volume=[0.0] * candle_count,
            time=times,
        )

    return patched_fetch_ohlcv


def tickers_repository_fetch_tickers_close_override(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    orig_get_all = exchanges_test_tools.get_all_currencies_price_ticker
    orig_get_one = exchanges_test_tools.get_price_ticker
    close_col = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value

    async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
        tickers = await orig_get_all(exchange_manager, **kwargs)
        for symbol in (BTC_USDC, ETH_USDC):
            close_value = get_close_price_for_symbol(symbol)
            if symbol in tickers:
                tickers[symbol] = {**tickers[symbol], close_col: close_value}
            else:
                tickers[symbol] = {close_col: close_value}
        return tickers

    async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
        if symbol in (BTC_USDC, ETH_USDC):
            return {close_col: get_close_price_for_symbol(symbol)}
        return await orig_get_one(exchange_manager, symbol, **kwargs)

    async def patched_fetch_tickers(self, symbols):
        if symbols == []:
            return {}
        if isinstance(symbols, list) and len(symbols) == 1:
            return {
                symbols[0]: await patched_get_price_ticker(self.exchange_manager, symbols[0])
            }
        return await patched_get_all_currencies_price_ticker(self.exchange_manager, symbols=None)

    return patched_fetch_tickers


class _ExchangePriceMockCalls:
    def __init__(self) -> None:
        self.fetch_tickers_await_count = 0
        self.fetch_ohlcv_await_count = 0


@contextlib.contextmanager
def patch_dca_simulator_exchange_prices(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    """
    Patch tickers/OHLCV repositories with fixed closes and track call counts.
    """
    patched_fetch_tickers_impl = tickers_repository_fetch_tickers_close_override(
        get_close_price_for_symbol
    )
    patched_fetch_ohlcv_impl = fetch_ohlcv_side_effect_for_close_prices(
        get_close_price_for_symbol
    )
    exchange_price_mock_calls = _ExchangePriceMockCalls()

    async def tracked_fetch_tickers(self, symbols):
        exchange_price_mock_calls.fetch_tickers_await_count += 1
        return await patched_fetch_tickers_impl(self, symbols)

    async def tracked_fetch_ohlcv(
        self,
        symbol: str,
        time_frame: str,
        limit: int,
        tickers: dict[str, dict[str, typing.Any]],
    ):
        exchange_price_mock_calls.fetch_ohlcv_await_count += 1
        return await patched_fetch_ohlcv_impl(symbol, time_frame, limit, tickers)

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=tracked_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            new=tracked_fetch_ohlcv,
        ),
    ):
        yield exchange_price_mock_calls


def _assert_exchange_price_mocks_called(
    exchange_price_mock_calls: _ExchangePriceMockCalls,
) -> None:
    assert exchange_price_mock_calls.fetch_tickers_await_count >= 1
    assert exchange_price_mock_calls.fetch_ohlcv_await_count >= 1


def _base_asset_from_symbol(symbol: str) -> str:
    return symbol_util.parse_symbol(symbol).base


def _open_order_documents_from_dump(automation_dump: dict) -> list[dict]:
    return automation_dump["automation"]["exchange_account_elements"]["orders"]["open_orders"]


def _open_orders_from_dump(automation_dump: dict) -> list[dict]:
    return [
        order[trading_constants.STORAGE_ORIGIN_VALUE]
        for order in _open_order_documents_from_dump(automation_dump)
    ]


def _chained_order_origins_from_document(order_document: dict) -> list[dict]:
    chained_order_documents = order_document.get(
        trading_enums.StoredOrdersAttr.CHAINED_ORDERS.value, []
    )
    return [
        chained_order_document[trading_constants.STORAGE_ORIGIN_VALUE]
        for chained_order_document in chained_order_documents
    ]


def _buy_order_documents_for_symbol(
    open_order_documents: list[dict],
    symbol: str,
) -> list[dict]:
    symbol_column = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    side_column = trading_enums.ExchangeConstantsOrderColumns.SIDE.value
    return [
        order_document
        for order_document in open_order_documents
        if order_document[trading_constants.STORAGE_ORIGIN_VALUE][symbol_column] == symbol
        and order_document[trading_constants.STORAGE_ORIGIN_VALUE][side_column]
        == trading_enums.TradeOrderSide.BUY.value
    ]


def _portfolio_content_from_dump(automation_dump: dict) -> dict:
    return automation_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]


def _sorted_orders_by_side(open_orders: list[dict], side: str) -> list[dict]:
    price_column = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    return sorted(
        [
            order
            for order in open_orders
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == side
        ],
        key=lambda order: order[price_column],
    )


def _sorted_orders_by_side_and_symbol(
    open_orders: list[dict],
    side: str,
    symbol: str,
) -> list[dict]:
    symbol_column = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    return _sorted_orders_by_side(
        [order for order in open_orders if order[symbol_column] == symbol],
        side,
    )


def _default_close_prices_by_symbol() -> dict[str, float]:
    return {
        BTC_USDC: _FIXED_BTC_USDC_CLOSE,
        ETH_USDC: _FIXED_ETH_USDC_CLOSE,
    }


def _assert_dca_buy_ladder_prices(
    buy_orders: list[dict],
    *,
    close: typing.Union[int, float, decimal.Decimal],
) -> tuple[decimal.Decimal, decimal.Decimal]:
    assert len(buy_orders) == 2
    price_column = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    expected_initial = initial_buy_price(close)
    expected_secondary = secondary_buy_price(close)
    buy_prices = [d_order_price(order[price_column]) for order in buy_orders]
    highest_buy_price = max(buy_prices)
    lowest_buy_price = min(buy_prices)
    assert abs(highest_buy_price - expected_initial) <= PRICE_TOLERANCE
    assert abs(lowest_buy_price - expected_secondary) <= PRICE_TOLERANCE
    return lowest_buy_price, highest_buy_price


def _assert_dca_chained_take_profit_orders_for_symbol(
    open_order_documents: list[dict],
    symbol: str,
) -> None:
    price_column = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    side_column = trading_enums.ExchangeConstantsOrderColumns.SIDE.value
    symbol_column = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    buy_order_documents = _buy_order_documents_for_symbol(open_order_documents, symbol)
    assert len(buy_order_documents) == 2
    for buy_order_document in buy_order_documents:
        buy_order = buy_order_document[trading_constants.STORAGE_ORIGIN_VALUE]
        buy_price = d_order_price(buy_order[price_column])
        chained_sell_orders = _chained_order_origins_from_document(buy_order_document)
        assert len(chained_sell_orders) == 1
        chained_sell_order = chained_sell_orders[0]
        assert chained_sell_order[side_column] == trading_enums.TradeOrderSide.SELL.value
        assert chained_sell_order[symbol_column] == symbol
        expected_take_profit_price = take_profit_price(buy_price)
        assert abs(
            d_order_price(chained_sell_order[price_column]) - expected_take_profit_price
        ) <= PRICE_TOLERANCE


def _assert_trading_signal_dca_chained_take_profit_orders_for_symbol(
    buy_orders: list[protocol_models.Order],
    symbol: str,
) -> None:
    assert len(buy_orders) == 2
    for buy_order in buy_orders:
        assert buy_order.chained_orders is not None
        assert len(buy_order.chained_orders) == 1
        chained_sell_order = buy_order.chained_orders[0]
        assert chained_sell_order.side == protocol_models.Side.SELL
        assert chained_sell_order.symbol == symbol
        expected_take_profit_price = take_profit_price(d_order_price(buy_order.price))
        assert abs(
            d_order_price(chained_sell_order.price) - expected_take_profit_price
        ) <= PRICE_TOLERANCE


def _assert_copied_account_buy_chained_take_profit_orders(
    account: protocol_models.CopiedAccount,
) -> None:
    order_list = account.orders or []
    top_level_sell_orders = [
        order for order in order_list if order.side == protocol_models.Side.SELL
    ]
    assert len(top_level_sell_orders) == 0
    for traded_symbol in TRADED_SYMBOLS:
        buy_orders_for_symbol = sorted(
            [
                order
                for order in order_list
                if order.side == protocol_models.Side.BUY and order.symbol == traded_symbol
            ],
            key=lambda order: order.price,
        )
        _assert_trading_signal_dca_chained_take_profit_orders_for_symbol(
            buy_orders_for_symbol, traded_symbol
        )


def _portfolio_asset_total(portfolio_content: dict, base_asset: str) -> float:
    return portfolio_content.get(base_asset, {}).get(common_constants.PORTFOLIO_TOTAL, 0)


def _signal_copied_assets_by_name(
    account: protocol_models.CopiedAccount,
) -> dict[str, protocol_models.CopiedAsset]:
    return {asset.name: asset for asset in (account.copied_assets or [])}


def _assert_trading_signal_dca_account_metadata(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    account = trading_signal.account
    assert isinstance(account.updated_at, float)
    assert current_time <= account.updated_at <= time.time()
    assert account.positions in (None, [])
    assert account.historical_snapshots in (None, [])


def _assert_trading_signal_dca_after_entry_placement(
    trading_signal: octobot_flow.entities.TradingSignal,
) -> None:
    assets = _signal_copied_assets_by_name(trading_signal.account)
    assert list(sorted(assets.keys())) == [QUOTE_ASSET]
    assert float(assets[QUOTE_ASSET].total) == 1000
    assert float(assets[QUOTE_ASSET].available) < 900
    assert_emitted_signal_account_allocation_ratios(trading_signal.account)
    order_list = trading_signal.account.orders or []
    buy_orders_btc = sorted(
        [
            order
            for order in order_list
            if order.side == protocol_models.Side.BUY and order.symbol == BTC_USDC
        ],
        key=lambda order: order.price,
    )
    buy_orders_eth = sorted(
        [
            order
            for order in order_list
            if order.side == protocol_models.Side.BUY and order.symbol == ETH_USDC
        ],
        key=lambda order: order.price,
    )
    assert len(buy_orders_btc) == 2
    assert len(buy_orders_eth) == 2
    _assert_dca_buy_ladder_prices(
        [
            {
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: order.price,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            }
            for order in buy_orders_btc
        ],
        close=_FIXED_BTC_USDC_CLOSE,
    )
    _assert_dca_buy_ladder_prices(
        [
            {
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: order.price,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            }
            for order in buy_orders_eth
        ],
        close=_FIXED_ETH_USDC_CLOSE,
    )
    top_level_sell_orders = [
        order for order in order_list if order.side == protocol_models.Side.SELL
    ]
    assert len(top_level_sell_orders) == 0
    _assert_trading_signal_dca_chained_take_profit_orders_for_symbol(
        buy_orders_btc, BTC_USDC
    )
    _assert_trading_signal_dca_chained_take_profit_orders_for_symbol(
        buy_orders_eth, ETH_USDC
    )
    _assert_trading_signal_dca_account_metadata(trading_signal)


def _assert_trading_signal_dca_after_buy_fill(
    trading_signal: octobot_flow.entities.TradingSignal,
    *,
    filled_base_asset: str,
) -> None:
    assets = _signal_copied_assets_by_name(trading_signal.account)
    assert filled_base_asset in assets
    assert list(sorted(assets.keys())) == sorted([filled_base_asset, QUOTE_ASSET])
    assert float(assets[filled_base_asset].total) > 0.001
    assert float(assets[QUOTE_ASSET].available) < float(assets[QUOTE_ASSET].total)
    assert_emitted_signal_account_allocation_ratios(trading_signal.account)
    order_list = trading_signal.account.orders or []
    buy_orders = [order for order in order_list if order.side == protocol_models.Side.BUY]
    sell_orders = [order for order in order_list if order.side == protocol_models.Side.SELL]
    # ALWAYS_TRIGGER_LONG re-places both symbol ladders on the fill automation run.
    assert len(buy_orders) == 4
    assert len(sell_orders) >= 1
    _assert_trading_signal_dca_account_metadata(trading_signal)


def _automation_state_with_metadata(
    all_actions: list[dict],
    emit_signals: bool,
) -> dict:
    automation_state = automation_state_dict(resolved_actions(all_actions))
    set_emit_signals_metadata(automation_state, emit_signals)
    if emit_signals:
        automation_state["automation"]["metadata"]["strategy_id"] = (
            functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID
        )
    return automation_state


async def _bootstrap_dca_with_open_buy_orders(init_action: dict) -> dict:
    """Run init + DCA DSL actions and return the automation dump with open buy ladders."""
    all_actions = [init_action, dca_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
        await automation_job.run()
    after_init_execution_dump = automation_job.dump()
    async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
        await automation_job.run()
    return automation_job.dump()


@pytest.fixture
def init_action():
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {
                    "automation_id": "automation_1",
                },
                "exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            QUOTE_ASSET: {
                                common_constants.PORTFOLIO_AVAILABLE: 1000.0,
                                common_constants.PORTFOLIO_TOTAL: 1000.0,
                            },
                        },
                    },
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": functionnal_tests.EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {
                    "unit": QUOTE_ASSET,
                },
            },
        },
    }


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_dca_init_from_empty_state_always_long_and_fill_buy_orders(
    init_action: dict,
    emit_signals: bool,
):
    """
    From USDC-only portfolio: start DCA on BTC/USDC + ETH/USDC, assert entry ladders,
    then drop price to fill the lowest buy and verify chained take-profit sells.
    """
    simulated_close_by_symbol = _default_close_prices_by_symbol()

    with patch_dca_simulator_exchange_prices(
        lambda symbol: simulated_close_by_symbol[symbol]
    ) as exchange_price_mock_calls:
        with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
            all_actions = [init_action, dca_trading_mode_action(init_action)]
            automation_state = _automation_state_with_metadata(all_actions, emit_signals)

            # 1. run init action (USDC portfolio + exchange account setup)
            async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
                await automation_job.run()
            after_init_execution_dump = automation_job.dump()

            # 2. run DCA trading mode action (ALWAYS_TRIGGER_LONG places both symbol buy ladders)
            async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_dca_execution_dump = automation_job.dump()

            # 3. assert USDC-only portfolio, two buy limits per symbol, chained TPs, no open sells yet
            after_dca_portfolio = _portfolio_content_from_dump(after_dca_execution_dump)
            assert list(after_dca_portfolio.keys()) == [QUOTE_ASSET]
            assert after_dca_portfolio[QUOTE_ASSET][common_constants.PORTFOLIO_TOTAL] == 1000
            assert after_dca_portfolio[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE] < 900

            open_after_dca_documents = _open_order_documents_from_dump(after_dca_execution_dump)
            open_after_dca = _open_orders_from_dump(after_dca_execution_dump)
            buy_after_dca = _sorted_orders_by_side(
                open_after_dca, trading_enums.TradeOrderSide.BUY.value
            )
            buy_after_dca_btc = _sorted_orders_by_side_and_symbol(
                open_after_dca, trading_enums.TradeOrderSide.BUY.value, BTC_USDC
            )
            buy_after_dca_eth = _sorted_orders_by_side_and_symbol(
                open_after_dca, trading_enums.TradeOrderSide.BUY.value, ETH_USDC
            )
            sell_after_dca = _sorted_orders_by_side(
                open_after_dca, trading_enums.TradeOrderSide.SELL.value
            )
            assert len(buy_after_dca) == 4
            assert len(buy_after_dca_btc) == 2
            assert len(buy_after_dca_eth) == 2
            assert len(sell_after_dca) == 0
            _assert_dca_buy_ladder_prices(buy_after_dca_btc, close=_FIXED_BTC_USDC_CLOSE)
            _assert_dca_buy_ladder_prices(buy_after_dca_eth, close=_FIXED_ETH_USDC_CLOSE)
            _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, BTC_USDC)
            _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, ETH_USDC)

            # 4. move market below the lowest buy limit to trigger a fill (typically ETH/USDC)
            lowest_buy_order = min(
                buy_after_dca,
                key=lambda order: d_order_price(
                    order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
                ),
            )
            fill_symbol = lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
            lowest_buy = d_order_price(
                lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
            )
            simulated_close_by_symbol[fill_symbol] = float(lowest_buy - decimal.Decimal("10"))

            async with octobot_flow.jobs.AutomationJob(after_dca_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_fill_dump = automation_job.dump()

            # 5. assert filled symbol holdings increased, other symbol unchanged; check both ladders
            after_fill_portfolio = _portfolio_content_from_dump(after_fill_dump)
            filled_base_asset = _base_asset_from_symbol(fill_symbol)
            for traded_symbol in TRADED_SYMBOLS:
                base_asset = _base_asset_from_symbol(traded_symbol)
                before_total = _portfolio_asset_total(after_dca_portfolio, base_asset)
                after_total = _portfolio_asset_total(after_fill_portfolio, base_asset)
                if traded_symbol == fill_symbol:
                    assert after_total > before_total
                else:
                    assert after_total == before_total
            assert (
                after_fill_portfolio[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE]
                < after_dca_portfolio[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE]
            )

            open_after_fill = _open_orders_from_dump(after_fill_dump)
            buy_after_fill = _sorted_orders_by_side(
                open_after_fill, trading_enums.TradeOrderSide.BUY.value
            )
            sell_after_fill = _sorted_orders_by_side(
                open_after_fill, trading_enums.TradeOrderSide.SELL.value
            )
            # ALWAYS_TRIGGER_LONG re-places both symbol ladders on the fill automation run.
            assert len(buy_after_fill) == 4
            assert len(sell_after_fill) >= 1
            for traded_symbol in TRADED_SYMBOLS:
                buy_after_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                    open_after_fill, trading_enums.TradeOrderSide.BUY.value, traded_symbol
                )
                sell_after_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                    open_after_fill, trading_enums.TradeOrderSide.SELL.value, traded_symbol
                )
                assert len(buy_after_fill_for_symbol) == 2
                _assert_dca_buy_ladder_prices(
                    buy_after_fill_for_symbol, close=simulated_close_by_symbol[traded_symbol]
                )
                if traded_symbol == fill_symbol:
                    assert len(sell_after_fill_for_symbol) >= 1
                else:
                    assert len(sell_after_fill_for_symbol) == 0

            # 6. when enabled, verify emitted trading signals after entry placement and after buy fill
            if emit_signals:
                assert insert_trading_signal_mock.await_count == 2
                _assert_trading_signal_dca_after_entry_placement(
                    insert_trading_signal_mock.await_args_list[0].args[0],
                )
                _assert_trading_signal_dca_after_buy_fill(
                    insert_trading_signal_mock.await_args_list[1].args[0],
                    filled_base_asset=filled_base_asset,
                )
            else:
                insert_trading_signal_mock.assert_not_awaited()

            _assert_exchange_price_mocks_called(exchange_price_mock_calls)


@pytest.mark.asyncio
async def test_simulator_dca_fill_buy_then_sell_orders(init_action: dict):
    """
    Bootstrap open DCA buy ladders, fill the lowest buy, then raise price to fill
    chained take-profit sells and verify portfolio moves at each step.
    """
    simulated_close_by_symbol = _default_close_prices_by_symbol()

    with patch_dca_simulator_exchange_prices(
        lambda symbol: simulated_close_by_symbol[symbol]
    ) as exchange_price_mock_calls:
        # 1. bootstrap init + DCA with both symbol buy ladders open
        after_dca_dump = await _bootstrap_dca_with_open_buy_orders(init_action)
        portfolio_after_dca = _portfolio_content_from_dump(after_dca_dump)
        assert list(portfolio_after_dca.keys()) == [QUOTE_ASSET]
        assert portfolio_after_dca[QUOTE_ASSET][common_constants.PORTFOLIO_TOTAL] == 1000
        assert portfolio_after_dca[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE] < 900

        open_after_dca_documents = _open_order_documents_from_dump(after_dca_dump)
        open_after_dca = _open_orders_from_dump(after_dca_dump)
        buy_after_dca = _sorted_orders_by_side(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value
        )
        buy_after_dca_btc = _sorted_orders_by_side_and_symbol(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value, BTC_USDC
        )
        buy_after_dca_eth = _sorted_orders_by_side_and_symbol(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value, ETH_USDC
        )
        sell_after_dca = _sorted_orders_by_side(
            open_after_dca, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(buy_after_dca) == 4
        assert len(buy_after_dca_btc) == 2
        assert len(buy_after_dca_eth) == 2
        assert len(sell_after_dca) == 0
        _assert_dca_buy_ladder_prices(buy_after_dca_btc, close=_FIXED_BTC_USDC_CLOSE)
        _assert_dca_buy_ladder_prices(buy_after_dca_eth, close=_FIXED_ETH_USDC_CLOSE)
        _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, BTC_USDC)
        _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, ETH_USDC)
        lowest_buy_order = min(
            buy_after_dca,
            key=lambda order: d_order_price(
                order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
            ),
        )
        fill_symbol = lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
        filled_base_asset = _base_asset_from_symbol(fill_symbol)
        lowest_buy = d_order_price(
            lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        )

        # 2. drop price to fill the lowest buy and open chained take-profit sells
        simulated_close_by_symbol[fill_symbol] = float(lowest_buy - decimal.Decimal("10"))
        async with octobot_flow.jobs.AutomationJob(after_dca_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_buy_fill_dump = automation_job.dump()

        portfolio_after_buy_fill = _portfolio_content_from_dump(after_buy_fill_dump)
        for traded_symbol in TRADED_SYMBOLS:
            base_asset = _base_asset_from_symbol(traded_symbol)
            before_total = _portfolio_asset_total(portfolio_after_dca, base_asset)
            after_total = _portfolio_asset_total(portfolio_after_buy_fill, base_asset)
            if traded_symbol == fill_symbol:
                assert after_total > before_total
            else:
                assert after_total == before_total
        assert (
            portfolio_after_buy_fill[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE]
            < portfolio_after_dca[QUOTE_ASSET][common_constants.PORTFOLIO_AVAILABLE]
        )

        open_after_buy_fill = _open_orders_from_dump(after_buy_fill_dump)
        buy_after_buy_fill = _sorted_orders_by_side(
            open_after_buy_fill, trading_enums.TradeOrderSide.BUY.value
        )
        sell_after_buy_fill = _sorted_orders_by_side(
            open_after_buy_fill, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(buy_after_buy_fill) == 4
        assert len(sell_after_buy_fill) >= 1
        for traded_symbol in TRADED_SYMBOLS:
            buy_after_buy_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_buy_fill, trading_enums.TradeOrderSide.BUY.value, traded_symbol
            )
            sell_after_buy_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_buy_fill, trading_enums.TradeOrderSide.SELL.value, traded_symbol
            )
            assert len(buy_after_buy_fill_for_symbol) == 2
            _assert_dca_buy_ladder_prices(
                buy_after_buy_fill_for_symbol, close=simulated_close_by_symbol[traded_symbol]
            )
            if traded_symbol == fill_symbol:
                assert len(sell_after_buy_fill_for_symbol) >= 1
            else:
                assert len(sell_after_buy_fill_for_symbol) == 0
        highest_sell = d_order_price(
            sell_after_buy_fill[-1][trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        )

        # 3. raise price above take-profit sells to complete the round trip
        simulated_close_by_symbol[fill_symbol] = float(highest_sell + decimal.Decimal("100"))
        async with octobot_flow.jobs.AutomationJob(after_buy_fill_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_sell_fill_dump = automation_job.dump()

        portfolio_after_sell_fill = _portfolio_content_from_dump(after_sell_fill_dump)
        for traded_symbol in TRADED_SYMBOLS:
            base_asset = _base_asset_from_symbol(traded_symbol)
            before_total = _portfolio_asset_total(portfolio_after_buy_fill, base_asset)
            after_total = _portfolio_asset_total(portfolio_after_sell_fill, base_asset)
            if traded_symbol == fill_symbol:
                assert after_total < before_total
            else:
                assert after_total == before_total
        assert (
            portfolio_after_sell_fill[QUOTE_ASSET][common_constants.PORTFOLIO_TOTAL]
            > portfolio_after_buy_fill[QUOTE_ASSET][common_constants.PORTFOLIO_TOTAL]
        )

        open_after_sell_fill = _open_orders_from_dump(after_sell_fill_dump)
        buy_after_sell_fill = _sorted_orders_by_side(
            open_after_sell_fill, trading_enums.TradeOrderSide.BUY.value
        )
        sell_after_sell_fill = _sorted_orders_by_side(
            open_after_sell_fill, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(buy_after_sell_fill) == 4
        assert len(sell_after_sell_fill) == 0
        for traded_symbol in TRADED_SYMBOLS:
            buy_after_sell_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_sell_fill, trading_enums.TradeOrderSide.BUY.value, traded_symbol
            )
            sell_after_sell_fill_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_sell_fill, trading_enums.TradeOrderSide.SELL.value, traded_symbol
            )
            assert len(buy_after_sell_fill_for_symbol) == 2
            _assert_dca_buy_ladder_prices(
                buy_after_sell_fill_for_symbol, close=simulated_close_by_symbol[traded_symbol]
            )
            assert len(sell_after_sell_fill_for_symbol) == 0

        _assert_exchange_price_mocks_called(exchange_price_mock_calls)


def _dca_buy_signal_reference_account(
    close_by_symbol: dict[str, float] | None = None,
) -> protocol_models.CopiedAccount:
    """Reference copied account for BTC/USDC + ETH/USDC buy ladders in a community signal."""
    if close_by_symbol is None:
        close_by_symbol = _default_close_prices_by_symbol()
    btc_close = close_by_symbol[BTC_USDC]
    eth_close = close_by_symbol[ETH_USDC]
    btc_order_amount = 0.004
    eth_order_amount = 0.1
    content = {
        BTC_BASE_ASSET: {
            common_constants.PORTFOLIO_TOTAL: decimal.Decimal("0.005"),
            common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0.005"),
            copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.34"),
        },
        ETH_BASE_ASSET: {
            common_constants.PORTFOLIO_TOTAL: decimal.Decimal("0.05"),
            common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0.05"),
            copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.33"),
        },
        QUOTE_ASSET: {
            common_constants.PORTFOLIO_TOTAL: decimal.Decimal("1000"),
            common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("850"),
            copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.33"),
        },
    }
    orders_storage = [
        _dca_reference_buy_storage_order_with_chained_take_profit(
            "dca_ref_b0",
            float(initial_buy_price(btc_close)),
            btc_order_amount,
            BTC_USDC,
        ),
        _dca_reference_buy_storage_order_with_chained_take_profit(
            "dca_ref_b1",
            float(secondary_buy_price(btc_close)),
            btc_order_amount,
            BTC_USDC,
        ),
        _dca_reference_buy_storage_order_with_chained_take_profit(
            "dca_ref_e0",
            float(initial_buy_price(eth_close)),
            eth_order_amount,
            ETH_USDC,
        ),
        _dca_reference_buy_storage_order_with_chained_take_profit(
            "dca_ref_e1",
            float(secondary_buy_price(eth_close)),
            eth_order_amount,
            ETH_USDC,
        ),
    ]
    return copied_account_from_content_and_storage_orders(
        updated_at=time.time(),
        content=content,
        orders_storage=orders_storage,
    )


def _dca_sell_signal_reference_account(
    entry_close_by_symbol: dict[str, float],
    *,
    portfolio_content: dict,
) -> protocol_models.CopiedAccount:
    """Reference copied account for BTC/USDC + ETH/USDC take-profit sell ladders."""
    content = {}
    for asset_name, balance in portfolio_content.items():
        asset_content = {
            common_constants.PORTFOLIO_TOTAL: decimal.Decimal(
                str(balance[common_constants.PORTFOLIO_TOTAL])
            ),
            common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal(
                str(balance[common_constants.PORTFOLIO_AVAILABLE])
            ),
        }
        allocation_ratio = balance.get(copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO)
        if allocation_ratio is not None:
            asset_content[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = decimal.Decimal(
                str(allocation_ratio)
            )
        else:
            asset_content[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = decimal.Decimal(
                "0.34"
            )
        content[asset_name] = asset_content
    orders_storage = []
    for traded_symbol, order_id_prefix, default_order_amount in (
        (BTC_USDC, "dca_ref_bs", 0.004),
        (ETH_USDC, "dca_ref_es", 0.1),
    ):
        base_asset = _base_asset_from_symbol(traded_symbol)
        base_available = float(
            portfolio_content[base_asset][common_constants.PORTFOLIO_AVAILABLE]
        )
        order_amount = min(default_order_amount, base_available / 2.2)
        assert order_amount > 0
        symbol_close = entry_close_by_symbol[traded_symbol]
        orders_storage.extend(
            [
                _dca_reference_storage_order(
                    f"{order_id_prefix}0",
                    trading_enums.TradeOrderSide.SELL.value,
                    float(take_profit_price(initial_buy_price(symbol_close))),
                    order_amount,
                    traded_symbol,
                ),
                _dca_reference_storage_order(
                    f"{order_id_prefix}1",
                    trading_enums.TradeOrderSide.SELL.value,
                    float(take_profit_price(secondary_buy_price(symbol_close))),
                    order_amount,
                    traded_symbol,
                ),
            ]
        )
    return copied_account_from_content_and_storage_orders(
        updated_at=time.time(),
        content=content,
        orders_storage=orders_storage,
    )


def _lowest_buy_price_for_symbol(open_orders: list[dict], symbol: str) -> decimal.Decimal:
    buy_orders_for_symbol = _sorted_orders_by_side_and_symbol(
        open_orders, trading_enums.TradeOrderSide.BUY.value, symbol
    )
    price_column = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    return d_order_price(buy_orders_for_symbol[0][price_column])


def _highest_buy_price_for_symbol(open_orders: list[dict], symbol: str) -> decimal.Decimal:
    buy_orders_for_symbol = _sorted_orders_by_side_and_symbol(
        open_orders, trading_enums.TradeOrderSide.BUY.value, symbol
    )
    price_column = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    return d_order_price(buy_orders_for_symbol[-1][price_column])


def _price_to_fill_only_initial_buy_for_symbol(
    open_orders: list[dict],
    symbol: str,
    close: typing.Union[int, float, decimal.Decimal],
) -> float:
    """
    Market price strictly below the initial (higher) buy limit and above the
    secondary buy so only one limit buy fills per symbol.
    """
    highest_buy = _highest_buy_price_for_symbol(open_orders, symbol)
    secondary_buy = secondary_buy_price(close)
    fill_price = highest_buy - decimal.Decimal("1")
    assert fill_price > secondary_buy, (
        f"Fill price {fill_price} must stay above secondary buy {secondary_buy} for {symbol}"
    )
    return float(fill_price)


async def _run_automation_job_dump(
    automation_dump: dict,
    trading_signals: list,
    community_auth_details: octobot_flow.entities.UserAuthentication,
) -> dict:
    async with octobot_flow.jobs.AutomationJob(
        automation_dump, [], trading_signals, community_auth_details
    ) as automation_job:
        await automation_job.run()
    return automation_job.dump()


@pytest.mark.asyncio
async def test_simulator_copy_dca_buy_signal_then_sell_signal(init_action: dict):
    """
    Copy BTC/USDC + ETH/USDC buy ladders from a community signal, fill mirrored buys
    on both symbols, apply a dual-symbol sell signal, then raise prices stepwise to
    verify portfolio moves on both symbols.
    """
    community_auth_details = octobot_flow.entities.UserAuthentication(
        wallet_address=SIMULATOR_COPY_DCA_FUNCTIONAL_TEST_COMMUNITY_WALLET_ADDRESS,
    )
    simulated_close_by_symbol = _default_close_prices_by_symbol()
    entry_close_by_symbol = dict(simulated_close_by_symbol)

    buy_signal_account = _dca_buy_signal_reference_account(entry_close_by_symbol)
    _assert_copied_account_buy_chained_take_profit_orders(buy_signal_account)

    fetch_trading_signals_mock = mock.AsyncMock()
    fetch_trading_signals_mock.return_value = [
        octobot_flow.entities.TradingSignal(
            strategy_id=functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID,
            account=buy_signal_account,
        )
    ]

    with contextlib.ExitStack() as patch_stack:
        exchange_price_mock_calls = patch_stack.enter_context(
            patch_dca_simulator_exchange_prices(
                lambda symbol: simulated_close_by_symbol[symbol]
            )
        )
        patch_stack.enter_context(
            mock.patch.object(
                octobot_flow.repositories.community.TradingSignalsRepository,
                "fetch_trading_signals",
                fetch_trading_signals_mock,
            )
        )

        copy_action = empty_copy_exchange_account_action()
        all_actions = [init_action, copy_action]
        automation_state = automation_state_dict(resolved_actions(all_actions))

        # 1. run init action
        after_init_dump = await _run_automation_job_dump(
            automation_state, [], community_auth_details
        )

        # 2. run copy action: mirror buy ladders for both symbols from community signal
        after_copy_dump = await _run_automation_job_dump(
            after_init_dump, [], community_auth_details
        )
        assert fetch_trading_signals_mock.await_count == 1

        portfolio_after_copy = _portfolio_content_from_dump(after_copy_dump)
        for traded_symbol in TRADED_SYMBOLS:
            base_asset = _base_asset_from_symbol(traded_symbol)
            assert _portfolio_asset_total(portfolio_after_copy, base_asset) > 0
        open_after_copy = _open_orders_from_dump(after_copy_dump)
        buy_after_copy = _sorted_orders_by_side(
            open_after_copy, trading_enums.TradeOrderSide.BUY.value
        )
        sell_after_copy = _sorted_orders_by_side(
            open_after_copy, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(buy_after_copy) == 4
        assert len(sell_after_copy) == 0
        for traded_symbol in TRADED_SYMBOLS:
            buy_after_copy_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_copy, trading_enums.TradeOrderSide.BUY.value, traded_symbol
            )
            assert len(buy_after_copy_for_symbol) == 2
            _assert_dca_buy_ladder_prices(
                buy_after_copy_for_symbol, close=entry_close_by_symbol[traded_symbol]
            )

        # 3. fill only the initial buy on each symbol (copy does not chain TPs)
        for traded_symbol in TRADED_SYMBOLS:
            simulated_close_by_symbol[traded_symbol] = _price_to_fill_only_initial_buy_for_symbol(
                open_after_copy,
                traded_symbol,
                entry_close_by_symbol[traded_symbol],
            )
        after_buy_fills_dump = await _run_automation_job_dump(
            after_copy_dump, [], community_auth_details
        )
        portfolio_after_buy_fills = _portfolio_content_from_dump(after_buy_fills_dump)
        assert (
            _portfolio_asset_total(portfolio_after_buy_fills, QUOTE_ASSET)
            < _portfolio_asset_total(portfolio_after_copy, QUOTE_ASSET)
        )
        open_after_buy_fills = _open_orders_from_dump(after_buy_fills_dump)
        sell_after_buy_fills = _sorted_orders_by_side(
            open_after_buy_fills, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(sell_after_buy_fills) == 0
        for traded_symbol in TRADED_SYMBOLS:
            buy_after_buy_fills_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_buy_fills, trading_enums.TradeOrderSide.BUY.value, traded_symbol
            )
            sell_after_buy_fills_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_buy_fills, trading_enums.TradeOrderSide.SELL.value, traded_symbol
            )
            assert len(buy_after_buy_fills_for_symbol) == 2
            _assert_dca_buy_ladder_prices(
                buy_after_buy_fills_for_symbol, close=entry_close_by_symbol[traded_symbol]
            )
            assert len(sell_after_buy_fills_for_symbol) == 0

        # 4. apply sell trading signal: mirror take-profit sell ladders for both symbols
        for traded_symbol in TRADED_SYMBOLS:
            simulated_close_by_symbol[traded_symbol] = entry_close_by_symbol[traded_symbol]
        sell_trading_signal = octobot_flow.entities.TradingSignal(
            strategy_id=functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID,
            account=_dca_sell_signal_reference_account(
                entry_close_by_symbol,
                portfolio_content=portfolio_after_buy_fills,
            ),
        )
        after_sell_signal_copy_dump = await _run_automation_job_dump(
            after_buy_fills_dump,
            [sell_trading_signal],
            community_auth_details,
        )
        assert fetch_trading_signals_mock.await_count == 1

        portfolio_after_sell_signal = _portfolio_content_from_dump(after_sell_signal_copy_dump)
        open_after_sell_signal = _open_orders_from_dump(after_sell_signal_copy_dump)
        sell_after_sell_signal = _sorted_orders_by_side(
            open_after_sell_signal, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(sell_after_sell_signal) >= 2
        for traded_symbol in TRADED_SYMBOLS:
            sell_after_sell_signal_for_symbol = _sorted_orders_by_side_and_symbol(
                open_after_sell_signal, trading_enums.TradeOrderSide.SELL.value, traded_symbol
            )
            assert len(sell_after_sell_signal_for_symbol) >= 1

        # 5. raise price above each sell limit in turn to fill mirrored sells on both symbols
        after_sell_fill_dump = after_sell_signal_copy_dump
        for _ in range(len(sell_after_sell_signal)):
            open_sell_orders = _sorted_orders_by_side(
                _open_orders_from_dump(after_sell_fill_dump),
                trading_enums.TradeOrderSide.SELL.value,
            )
            if not open_sell_orders:
                break
            next_sell_order = open_sell_orders[0]
            next_sell_symbol = next_sell_order[
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
            ]
            next_sell_price = d_order_price(
                next_sell_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
            )
            for traded_symbol in TRADED_SYMBOLS:
                if traded_symbol == next_sell_symbol:
                    simulated_close_by_symbol[traded_symbol] = float(
                        next_sell_price + decimal.Decimal("50")
                    )
                else:
                    simulated_close_by_symbol[traded_symbol] = entry_close_by_symbol[
                        traded_symbol
                    ]
            after_sell_fill_dump = await _run_automation_job_dump(
                after_sell_fill_dump, [], community_auth_details
            )

        # 6. assert both base assets decreased after mirrored sell fills
        portfolio_after_sell_fill = _portfolio_content_from_dump(after_sell_fill_dump)
        for traded_symbol in TRADED_SYMBOLS:
            base_asset = _base_asset_from_symbol(traded_symbol)
            before_total = _portfolio_asset_total(portfolio_after_sell_signal, base_asset)
            after_total = _portfolio_asset_total(portfolio_after_sell_fill, base_asset)
            assert after_total < before_total

        assert fetch_trading_signals_mock.await_count >= 1
        _assert_exchange_price_mocks_called(exchange_price_mock_calls)


@pytest.mark.asyncio
async def test_simulator_dca_init_from_empty_state_2_evaluators_1_strategy_and_fill_buy_orders(
    init_action: dict,
):
    """
    DCA in MAXIMUM_EVALUATORS_SIGNALS_BASED mode on BTC/USDC + ETH/USDC with empty trading_pairs:
    symbols come from strategy evaluator dynamic dependencies; evaluators and strategy must
    return -1 before entry orders are placed; no orders exist until DCA runs; per-symbol
    buy ladders are placed; DAG resets after DCA recall and evaluators run again.
    """
    simulated_close_by_symbol = _default_close_prices_by_symbol()
    declining_ohlcv = fetch_ohlcv_side_effect_for_declining_closes(
        lambda symbol: simulated_close_by_symbol[symbol],
        lambda symbol: simulated_close_by_symbol[symbol] * 0.005,
    )
    fixed_close_ohlcv = fetch_ohlcv_side_effect_for_close_prices(
        lambda symbol: simulated_close_by_symbol[symbol],
    )
    ohlcv_fetch_mode = {"use_declining_for_history": True}

    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        tickers: dict[str, dict[str, typing.Any]],
    ):
        # Evaluator steps need declining history; DCA entry pricing uses flat ticker closes.
        if ohlcv_fetch_mode["use_declining_for_history"] and (
            limit is None or int(limit) != 1
        ):
            return await declining_ohlcv(symbol, time_frame, limit, tickers)
        return await fixed_close_ohlcv(symbol, time_frame, limit, tickers)

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=tickers_repository_fetch_tickers_close_override(
                lambda symbol: simulated_close_by_symbol[symbol]
            ),
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        all_actions = [
            init_action,
            _dsl_evaluator_action(
                "action_dma",
                DMA_EVALUATOR_DSL_OPERATOR,
                init_action["id"],
                DMA_EVALUATOR_CONFIG,
            ),
            _dsl_evaluator_action(
                "action_rsi",
                RSI_EVALUATOR_DSL_OPERATOR,
                init_action["id"],
                RSI_EVALUATOR_CONFIG,
            ),
            _dsl_evaluator_action(
                "action_strategy",
                STRATEGY_EVALUATOR_DSL_OPERATOR,
                init_action["id"],
                STRATEGY_EVALUATOR_CONFIG,
                extra_dependencies=[
                    {
                        "action_id": "action_dma",
                        "parameter": "_dynamic_dependencies",
                    },
                    {
                        "action_id": "action_rsi",
                        "parameter": "_dynamic_dependencies",
                    },
                ],
            ),
            _maximum_evaluators_dca_action(
                init_action["id"],
                dca_config=BINANCEUS_DCA_MAXIMUM_EVALUATORS_FROM_STRATEGY_SYMBOLS_CONFIG,
            ),
        ]
        automation_state = automation_state_dict(resolved_actions(all_actions))

        # Step 1 — init: only action_init completed; DSL actions pending
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
            await automation_job.run()
        after_init_dump = automation_job.dump()
        actions_dag = automation_job.automation_state.automation.actions_dag
        _assert_dag_snapshot(actions_dag, {
            "action_init": {"completed": True, "result_is_none": True, "previous_result_is_none": True},
            "action_dma": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
            "action_rsi": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
            "action_strategy": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
            "action_dca": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
        })
        executable_action_ids = {
            action.id for action in actions_dag.get_executable_actions()
        }
        assert executable_action_ids == {"action_dma", "action_rsi"}

        # Step 2 — evaluators: both TA actions completed with -1; strategy/DCA pending
        async with octobot_flow.jobs.AutomationJob(after_init_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_evaluators_dump = automation_job.dump()
        actions_dag = automation_job.automation_state.automation.actions_dag
        _assert_dag_snapshot(actions_dag, {
            "action_init": {"completed": True, "result_is_none": True, "previous_result_is_none": True},
            "action_dma": {"completed": True, "result_is_none": False, "previous_result_is_none": True},
            "action_rsi": {"completed": True, "result_is_none": False, "previous_result_is_none": True},
            "action_strategy": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
            "action_dca": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
        })
        _assert_evaluator_results_for_traded_symbols(
            actions_dag.get_actions_by_id()["action_dma"],
            eval_note=-1,
            evaluator_name=trend_evaluator.DoubleMovingAverageTrendEvaluator.get_name(),
        )
        _assert_evaluator_results_for_traded_symbols(
            actions_dag.get_actions_by_id()["action_rsi"],
            eval_note=-1,
            evaluator_name=momentum_evaluator.RSIMomentumEvaluator.get_name(),
        )
        assert {action.id for action in actions_dag.get_executable_actions()} == {"action_strategy"}

        # Step 3 — strategy: strategy completed with -1; DCA pending
        async with octobot_flow.jobs.AutomationJob(after_evaluators_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_strategy_dump = automation_job.dump()
        actions_dag = automation_job.automation_state.automation.actions_dag
        _assert_dag_snapshot(actions_dag, {
            "action_init": {"completed": True, "result_is_none": True, "previous_result_is_none": True},
            "action_dma": {"completed": True, "result_is_none": False, "previous_result_is_none": True},
            "action_rsi": {"completed": True, "result_is_none": False, "previous_result_is_none": True},
            "action_strategy": {
                "completed": True,
                "result_is_none": False,
                "previous_result_is_none": True,
            },
            "action_dca": {"completed": False, "result_is_none": True, "previous_result_is_none": True},
        })
        _assert_evaluator_results_for_traded_symbols(
            actions_dag.get_actions_by_id()["action_strategy"],
            eval_note=-1,
            evaluator_name=mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name(),
        )
        assert {action.id for action in actions_dag.get_executable_actions()} == {"action_dca"}
        assert _open_orders_from_dump(after_strategy_dump) == []

        # Step 4 — DCA: orders placed; DAG reset on dependents; 2h recall scheduled
        ohlcv_fetch_mode["use_declining_for_history"] = False
        async with octobot_flow.jobs.AutomationJob(after_strategy_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_dca_dump = automation_job.dump()
        actions_dag = automation_job.automation_state.automation.actions_dag
        _assert_dag_snapshot(actions_dag, {
            "action_init": {"completed": True, "result_is_none": True, "previous_result_is_none": True},
            "action_dma": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
            "action_rsi": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
            "action_strategy": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
            "action_dca": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
        })
        dca_action = actions_dag.get_actions_by_id()["action_dca"]
        assert isinstance(dca_action.previous_execution_result, dict)
        assert dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            dca_action.previous_execution_result
        )
        recall_wrapper = dsl_interpreter.ReCallingOperatorResult.from_dict(
            dca_action.previous_execution_result[dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        assert recall_wrapper.reset_to_id == "action_init"
        two_hours_seconds = (
            common_enums.TimeFramesMinutes[common_enums.TimeFrames.TWO_HOURS]
            * common_constants.MINUTE_TO_SECONDS
        )
        assert abs(recall_wrapper.last_execution_result["waiting_time"] - two_hours_seconds) < 20
        assert {action.id for action in actions_dag.get_executable_actions()} == {"action_dma", "action_rsi"}
        assert not actions_dag.completed_all_actions()

        allowed_execution_time = 20
        schedule_delay = (
            after_dca_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_dca_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert two_hours_seconds - allowed_execution_time < schedule_delay < two_hours_seconds + allowed_execution_time

        open_after_dca_documents = _open_order_documents_from_dump(after_dca_dump)
        open_after_dca = _open_orders_from_dump(after_dca_dump)
        buy_after_dca = _sorted_orders_by_side(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value
        )
        buy_after_dca_btc = _sorted_orders_by_side_and_symbol(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value, BTC_USDC
        )
        buy_after_dca_eth = _sorted_orders_by_side_and_symbol(
            open_after_dca, trading_enums.TradeOrderSide.BUY.value, ETH_USDC
        )
        sell_after_dca = _sorted_orders_by_side(
            open_after_dca, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(buy_after_dca) == 4
        assert len(buy_after_dca_btc) == 2
        assert len(buy_after_dca_eth) == 2
        assert len(sell_after_dca) == 0
        _assert_dca_buy_ladder_prices(buy_after_dca_btc, close=_FIXED_BTC_USDC_CLOSE)
        _assert_dca_buy_ladder_prices(buy_after_dca_eth, close=_FIXED_ETH_USDC_CLOSE)
        _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, BTC_USDC)
        _assert_dca_chained_take_profit_orders_for_symbol(open_after_dca_documents, ETH_USDC)

        # Step 5 — post-DCA recall: evaluators run again before strategy is re-evaluated
        ohlcv_fetch_mode["use_declining_for_history"] = True
        async with octobot_flow.jobs.AutomationJob(after_dca_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_re_evaluators_dump = automation_job.dump()
        actions_dag = automation_job.automation_state.automation.actions_dag
        _assert_dag_snapshot(actions_dag, {
            "action_init": {"completed": True, "result_is_none": True, "previous_result_is_none": True},
            "action_dma": {"completed": True, "result_is_none": False, "previous_result_is_none": False},
            "action_rsi": {"completed": True, "result_is_none": False, "previous_result_is_none": False},
            "action_strategy": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
            "action_dca": {"completed": False, "result_is_none": True, "previous_result_is_none": False},
        })
        dma_action = actions_dag.get_actions_by_id()["action_dma"]
        rsi_action = actions_dag.get_actions_by_id()["action_rsi"]
        assert dma_action.executed_at is not None
        assert rsi_action.executed_at is not None
        _assert_evaluator_results_for_traded_symbols(
            dma_action,
            eval_note=-1,
            evaluator_name=trend_evaluator.DoubleMovingAverageTrendEvaluator.get_name(),
        )
        _assert_evaluator_results_for_traded_symbols(
            rsi_action,
            eval_note=-1,
            evaluator_name=momentum_evaluator.RSIMomentumEvaluator.get_name(),
        )
        assert {action.id for action in actions_dag.get_executable_actions()} == {"action_strategy"}

        # Step 6 — fill: drop price below lowest buy to trigger a fill
        lowest_buy_order = min(
            buy_after_dca,
            key=lambda order: d_order_price(
                order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
            ),
        )
        fill_symbol = lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
        lowest_buy = d_order_price(
            lowest_buy_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        )
        simulated_close_by_symbol[fill_symbol] = float(lowest_buy - decimal.Decimal("10"))

        ohlcv_fetch_mode["use_declining_for_history"] = False
        async with octobot_flow.jobs.AutomationJob(after_dca_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_fill_dump = automation_job.dump()

        after_fill_portfolio = _portfolio_content_from_dump(after_fill_dump)
        after_dca_portfolio = _portfolio_content_from_dump(after_dca_dump)
        for traded_symbol in TRADED_SYMBOLS:
            base_asset = _base_asset_from_symbol(traded_symbol)
            before_total = _portfolio_asset_total(after_dca_portfolio, base_asset)
            after_total = _portfolio_asset_total(after_fill_portfolio, base_asset)
            if traded_symbol == fill_symbol:
                assert after_total > before_total
            else:
                assert after_total == before_total

        open_after_fill = _open_orders_from_dump(after_fill_dump)
        sell_after_fill = _sorted_orders_by_side(
            open_after_fill, trading_enums.TradeOrderSide.SELL.value
        )
        assert len(sell_after_fill) >= 1
