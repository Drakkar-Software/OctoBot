import contextlib
import decimal
import logging
import typing

import mock
import pytest
import time

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.repositories.community
import octobot_flow.repositories.exchange
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    assert_emitted_signal_account_allocation_ratios,
    automation_state_dict,
    copy_exchange_account_action,
    current_time,
    d_order_price,
    empty_copy_exchange_account_action,
    resolved_actions,
    set_emit_signals_metadata,
    trading_signal_emission_patches,
)

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

increment = 200
spread = 600
D_INCREMENT = decimal.Decimal(str(increment))
D_SPREAD = decimal.Decimal(str(spread))
# Stable quote for mirrored grid limits (test patches tickers to this close).
_FIXED_BTC_USDC_CLOSE = 100000.0
GRID_REFERENCE_LOWEST_BUY = _FIXED_BTC_USDC_CLOSE - (spread / 2) - increment * 2 + 12.12

# Placeholder wallet address for community `UserAuthentication` (tests mock Starfish paths).
SIMULATOR_COPY_GRID_FUNCTIONAL_TEST_COMMUNITY_WALLET_ADDRESS = "simulator-copy-grid-functional-test-wallet-address"

grid_pair_settings = [
    grid_trading.GridTradingMode.get_default_pair_config(
        "BTC/USDC",
        spread,
        increment,
        2,
        2,
        False,
        False,
        False,
    )
]


def grid_trading_mode_action(dependency_action: dict):
    return {
        "id": "action_1",
        "dsl_script": (
            f"grid_trading_mode(pair_settings={dsl_interpreter.format_parameter_value(grid_pair_settings)})"
        ),
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


def _grid_reference_storage_order(order_id: str, side: str, price: float, amount: float) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: order_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDC",
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: side,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: price,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value: trading_enums.OrderStatus.OPEN.value,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
            trading_enums.ExchangeConstantsOrderColumns.REMAINING.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: time.time(),
            trading_enums.ExchangeConstantsOrderColumns.SELF_MANAGED.value: False,
        }
    }


def fetch_ohlcv_side_effect_for_close_price(
    get_close_price: typing.Callable[[], typing.Union[int, float]],
):
    """
    Async side effect for octobot_flow.repositories.exchange.OhlcvRepository.fetch_ohlcv:
    every candle uses get_close_price() for open, high, low, and close.
    """
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        time_frame_seconds = common_enums.TimeFramesMinutes[common_enums.TimeFrames(time_frame)] * 60
        close_price = float(get_close_price())
        n = max(int(limit or 1), 1)
        local_time = time.time()
        current_candle_open_time = local_time - (local_time % time_frame_seconds)
        first_candle_open_time = current_candle_open_time - (n - 1) * time_frame_seconds
        times = [float(first_candle_open_time + i * time_frame_seconds) for i in range(n)]
        closes = [close_price] * n
        ohlc = [close_price] * n
        return exchange_data.MarketDetails(
            symbol=symbol,
            time_frame=time_frame,
            close=closes,
            open=ohlc,
            high=ohlc,
            low=ohlc,
            volume=[0.0] * n,
            time=times,
        )

    return patched_fetch_ohlcv


def tickers_repository_fetch_tickers_btc_usdc_close_override(
    get_btc_usdc_close: typing.Callable[[], typing.Union[int, float]],
    *,
    btc_usdc_symbol: str = "BTC/USDC",
):
    """
    TickersRepository.fetch_tickers replacement for tests: forces BTC/USDC close from get_btc_usdc_close()
    and does not use the process-wide ticker cache on the fetch path.
    """
    orig_get_all = exchanges_test_tools.get_all_currencies_price_ticker
    orig_get_one = exchanges_test_tools.get_price_ticker
    close_col = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value

    async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
        tickers = await orig_get_all(exchange_manager, **kwargs)
        c = get_btc_usdc_close()
        if btc_usdc_symbol in tickers:
            tickers[btc_usdc_symbol] = {**tickers[btc_usdc_symbol], close_col: c}
        else:
            tickers[btc_usdc_symbol] = {close_col: c}
        return tickers

    async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
        if symbol == btc_usdc_symbol:
            return {close_col: get_btc_usdc_close()}
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


def _assert_trading_signal_grid_account_metadata(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    account = trading_signal.account
    assert isinstance(account.updated_at, float)
    assert current_time <= account.updated_at <= time.time()
    assert account.positions == []
    assert account.historical_snapshots == []


def _assert_signal_orders_two_by_two_grid_ladder(
    orders: list[dict],
) -> None:
    open_orders_origin_values = [
        order[trading_constants.STORAGE_ORIGIN_VALUE] for order in orders
    ]
    buy_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.BUY.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    sell_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.SELL.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    assert len(buy_orders) == len(sell_orders) == 2
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    lowest_buy_price = d_order_price(buy_orders[0][price_col])
    assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
    assert d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
    assert d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT


def _assert_trading_signal_grid_simulator_initial_placement(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    content = trading_signal.account.content
    assert list(sorted(content.keys())) == ["BTC", "USDC"]
    assert 450 < float(content["USDC"][common_constants.PORTFOLIO_TOTAL]) < 550
    assert float(content["USDC"][common_constants.PORTFOLIO_AVAILABLE]) < 200
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_TOTAL]) < 0.02
    assert float(content["BTC"][common_constants.PORTFOLIO_AVAILABLE]) < 0.001
    assert_emitted_signal_account_allocation_ratios(content)
    assert len(trading_signal.account.orders) == 4
    _assert_signal_orders_two_by_two_grid_ladder(trading_signal.account.orders)
    _assert_trading_signal_grid_account_metadata(trading_signal)


def _assert_trading_signal_grid_after_sell_fill_and_mirror(
    trading_signal: octobot_flow.entities.TradingSignal,
    *,
    lowest_buy_price: decimal.Decimal,
    first_sell_price: decimal.Decimal,
    second_sell_price: decimal.Decimal,
) -> None:
    btc_usdc = "BTC/USDC"
    content = trading_signal.account.content
    assert list(sorted(content.keys())) == ["BTC", "USDC"]
    # After a sell fill, quote is mostly reserved for open buy limits (small free USDC).
    assert float(content["USDC"][common_constants.PORTFOLIO_AVAILABLE]) < 50
    assert 450 < float(content["USDC"][common_constants.PORTFOLIO_TOTAL]) < 800
    assert float(content["BTC"][common_constants.PORTFOLIO_AVAILABLE]) < 0.001
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_TOTAL]) < 0.02
    assert_emitted_signal_account_allocation_ratios(content)
    final_open = [
        order[trading_constants.STORAGE_ORIGIN_VALUE] for order in trading_signal.account.orders
    ]
    buy_orders = sorted(
        [
            order
            for order in final_open
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.BUY.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    sell_orders = sorted(
        [
            order
            for order in final_open
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.SELL.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    assert len(buy_orders) == 3
    assert len(sell_orders) == 1
    expected_mirror_buy_price = first_sell_price - (D_SPREAD - D_INCREMENT)
    expected_remaining_sell_price = second_sell_price
    for order in buy_orders:
        assert order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == trading_enums.TradeOrderType.LIMIT.value
        assert order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.OPEN.value
        assert order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == btc_usdc
        assert 0.0024 <= float(order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]) <= 0.0026
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    assert d_order_price(buy_orders[0][price_col]) == lowest_buy_price
    assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
    assert d_order_price(buy_orders[2][price_col]) == expected_mirror_buy_price
    assert d_order_price(sell_orders[0][price_col]) == expected_remaining_sell_price
    assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == trading_enums.TradeOrderType.LIMIT.value
    assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.OPEN.value
    assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == btc_usdc
    assert 0.0024 <= float(sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]) <= 0.0026
    _assert_trading_signal_grid_account_metadata(trading_signal)


def _assert_trading_signal_grid_copy_reference_shape(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    content = trading_signal.account.content
    assert list(sorted(content.keys())) == ["BTC", "USDC"]
    assert 450 < float(content["USDC"][common_constants.PORTFOLIO_TOTAL]) < 550
    assert 100 < float(content["USDC"][common_constants.PORTFOLIO_AVAILABLE]) < 150
    assert 0.0045 < float(content["BTC"][common_constants.PORTFOLIO_TOTAL]) < 0.055
    assert float(content["BTC"][common_constants.PORTFOLIO_AVAILABLE]) < 0.0015
    assert_emitted_signal_account_allocation_ratios(content)
    assert len(trading_signal.account.orders) == 4
    open_orders_origin_values = [
        order[trading_constants.STORAGE_ORIGIN_VALUE] for order in trading_signal.account.orders
    ]
    buy_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.BUY.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    sell_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.SELL.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    assert len(buy_orders) == len(sell_orders) == 2
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    lowest_buy_price = d_order_price(buy_orders[0][price_col])
    assert lowest_buy_price == d_order_price(GRID_REFERENCE_LOWEST_BUY)
    assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
    assert d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
    assert d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT
    _assert_trading_signal_grid_account_metadata(trading_signal)


@pytest.fixture
def grid_reference_account():
    """Spot snapshot matching a BTC/USDC grid: half USDC / half BTC by ratio, with 2+2 open limits."""
    lowest_buy = GRID_REFERENCE_LOWEST_BUY
    order_amount = 0.004
    return copy_entities.Account(
        updated_at=time.time(),
        content={
            "BTC": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("0.01"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("0.002"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
            "USDC": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("1000"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("200"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
        },
        orders=[
            _grid_reference_storage_order(
                "grid_ref_b0", trading_enums.TradeOrderSide.BUY.value, lowest_buy, order_amount
            ),
            _grid_reference_storage_order(
                "grid_ref_b1",
                trading_enums.TradeOrderSide.BUY.value,
                lowest_buy + increment,
                order_amount,
            ),
            _grid_reference_storage_order(
                "grid_ref_s0",
                trading_enums.TradeOrderSide.SELL.value,
                lowest_buy + increment + spread,
                order_amount,
            ),
            _grid_reference_storage_order(
                "grid_ref_s1",
                trading_enums.TradeOrderSide.SELL.value,
                lowest_buy + increment + spread + increment,
                order_amount,
            ),
        ],
        positions=[],
        # no historical snapshots
    )


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
                            "USDC": {
                                "available": 1000.0,
                                "total": 1000.0,
                            }
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
                    "unit": "USDC",
                },
            },
        },
    }


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_grid_init_from_empty_state(init_action: dict, emit_signals: bool):
    patched_fetch_tickers = tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: _FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = fetch_ohlcv_side_effect_for_close_price(lambda: _FIXED_BTC_USDC_CLOSE)

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
            all_actions = [init_action, grid_trading_mode_action(init_action)]
            automation_state = automation_state_dict(resolved_actions(all_actions))
            set_emit_signals_metadata(automation_state, emit_signals)

            # 1. run init action
            async with octobot_flow.AutomationJob(automation_state, [], [], {}) as automation_job:
                await automation_job.run()
            after_init_execution_dump = automation_job.dump()

            # check bot actions execution
            assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
            for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
                assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.result is None
                if index == 0:
                    assert action.executed_at and action.executed_at >= current_time
                    assert action.previous_execution_result is None
                else:
                    assert action.executed_at is None
                    assert action.previous_execution_result is None

            # 2. run grid trading mode action
            async with octobot_flow.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_grid_execution_dump = automation_job.dump()
            assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
            for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
                assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.result is None
                if index == 0:
                    assert action.executed_at is not None
                    assert action.previous_execution_result is None
                else:
                    # action is reset: this is a trading mode action: it will be executed again at the next execution
                    assert action.executed_at is None
                    assert isinstance(action.previous_execution_result, dict)

            # scheduled next execution time at 1h after the current execution (1h is the default time when unspecified)
            assert after_grid_execution_dump["automation"]["execution"]["previous_execution"][
                "triggered_at"
            ] >= current_time
            one_hour = (
                common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR]
                * common_constants.MINUTE_TO_SECONDS
            )
            allowed_execution_time = 20
            schedule_delay = (
                after_grid_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
                - after_grid_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
            )
            assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

            # ensure trades are saved
            assert len(after_grid_execution_dump["automation"]["exchange_account_elements"]["trades"]) == 1

            # check portfolio and open grid orders
            after_grid_portfolio_content = after_grid_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_execution_dump, dict)
            assert list(sorted(after_grid_portfolio_content.keys())) == ["BTC", "USDC"]
            # applied portfolio optimizations and created grid open orders
            assert 450 < after_grid_portfolio_content["USDC"]["total"] < 550 # USDC holding split in half
            assert after_grid_portfolio_content["USDC"]["available"] < 200
            assert 0.001 < after_grid_portfolio_content["BTC"]["total"] < 0.02
            assert after_grid_portfolio_content["BTC"]["available"] < 0.001

            after_grid_reference_account_portfolio_content = after_grid_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_reference_account_portfolio_content, dict)
            assert list(sorted(after_grid_reference_account_portfolio_content.keys())) == ["BTC", "USDC"]
            assert 450 < after_grid_reference_account_portfolio_content["USDC"]["total"] < 550  # USDC holding split in half
            assert after_grid_reference_account_portfolio_content["USDC"]["available"] < 200
            assert 0.001 < after_grid_reference_account_portfolio_content["BTC"]["total"] < 0.02
            assert after_grid_reference_account_portfolio_content["BTC"]["available"] < 0.001

            order_portfolio_types = ["exchange_account_elements"]
            for portfolio_type in order_portfolio_types:
                open_orders_origin_values = [
                    order[trading_constants.STORAGE_ORIGIN_VALUE]
                    for order in after_grid_execution_dump["automation"][portfolio_type]["orders"][
                        "open_orders"
                    ]
                ]
                buy_orders = sorted([
                    o for o in open_orders_origin_values if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
                ], key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])
                sell_orders = sorted([
                    o for o in open_orders_origin_values if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.SELL.value
                ], key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])
                assert len(buy_orders) == len(sell_orders) == 2
                # check order prices are according to the grid settings
                price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
                lowest_buy_price = d_order_price(buy_orders[0][price_col])
                assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
                assert d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
                assert d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT

            # 3. trigger again: nothing to do
            async with octobot_flow.AutomationJob(after_grid_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_second_call_execution_dump = automation_job.dump()
            assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
            for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
                assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.result is None
                if index == 0:
                    assert action.executed_at is not None
                    assert action.previous_execution_result is None
                else:
                    assert action.executed_at is None
                    assert isinstance(action.previous_execution_result, dict)

            schedule_delay = (
                after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
                - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
            )
            assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

            # ensure trades are not erased
            assert len(after_grid_execution_dump["automation"]["exchange_account_elements"]["trades"]) == 1

            after_second_call_portfolio_content = after_second_call_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert after_second_call_portfolio_content == after_grid_portfolio_content
            after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert after_second_call_reference_account_portfolio_content == after_grid_reference_account_portfolio_content

            if emit_signals:
                assert insert_trading_signal_mock.await_count == 2
                for await_args in insert_trading_signal_mock.await_args_list:
                    _assert_trading_signal_grid_simulator_initial_placement(await_args.args[0])
            else:
                insert_trading_signal_mock.assert_not_awaited()


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_grid_init_and_fill_sell_order(init_action: dict, emit_signals: bool):
    """
    Initialize a grid at a fixed BTC/USDC price, move the market above the first sell limit so it fills,
    then run the automation again from the saved state: staggered/grid mode should place a mirror buy
    at (first_sell_price - (spread - increment)).
    """
    btc_usdc = "BTC/USDC"
    simulated_close = {"value": _FIXED_BTC_USDC_CLOSE}
    patched_fetch_tickers = tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: simulated_close["value"]
    )
    patched_fetch_ohlcv = fetch_ohlcv_side_effect_for_close_price(lambda: simulated_close["value"])

    with (
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
            all_actions = [
                init_action,
                grid_trading_mode_action(init_action),
            ]
            automation_state = automation_state_dict(resolved_actions(all_actions))
            set_emit_signals_metadata(automation_state, emit_signals)

            async with octobot_flow.AutomationJob(automation_state, [], [], {}) as automation_job:
                await automation_job.run()
            after_init_execution_dump = automation_job.dump()

            async with octobot_flow.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_grid_execution_dump = automation_job.dump()

            open_after_grid = [
                order[trading_constants.STORAGE_ORIGIN_VALUE]
                for order in after_grid_execution_dump["automation"]["exchange_account_elements"]["orders"][
                    "open_orders"
                ]
            ]
            buy_after_grid = sorted(
                [
                    o
                    for o in open_after_grid
                    if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.BUY.value
                ],
                key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            sell_after_grid = sorted(
                [
                    o
                    for o in open_after_grid
                    if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.SELL.value
                ],
                key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            assert len(buy_after_grid) == len(sell_after_grid) == 2
            price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
            lowest_buy_price = d_order_price(buy_after_grid[0][price_col])
            first_sell_price = d_order_price(sell_after_grid[0][price_col])
            second_sell_price = d_order_price(sell_after_grid[1][price_col])
            assert d_order_price(buy_after_grid[1][price_col]) == lowest_buy_price + D_INCREMENT
            assert first_sell_price == lowest_buy_price + D_INCREMENT + D_SPREAD
            assert second_sell_price == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT

            # Between first and second sell so the lowest sell limit fills but price stays inside the grid upper bound.
            simulated_close["value"] = float(first_sell_price + D_INCREMENT / decimal.Decimal("2"))

            async with octobot_flow.AutomationJob(after_grid_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
                final_dump = automation_job.dump()
                for action in automation_job.automation_state.automation.actions_dag.actions:
                    assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
                    assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value

            final_open = [
                order[trading_constants.STORAGE_ORIGIN_VALUE]
                for order in final_dump["automation"]["exchange_account_elements"]["orders"]["open_orders"]
            ]
            buy_orders = sorted(
                [
                    o
                    for o in final_open
                    if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
                ],
                key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            sell_orders = sorted(
                [
                    o
                    for o in final_open
                    if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.SELL.value
                ],
                key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            assert len(buy_orders) == 3
            assert len(sell_orders) == 1

            expected_mirror_buy_price = first_sell_price - (D_SPREAD - D_INCREMENT)
            expected_remaining_sell_price = second_sell_price

            for o in buy_orders:
                assert o[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == trading_enums.TradeOrderType.LIMIT.value
                assert o[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.OPEN.value
                assert o[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == btc_usdc
                # even mirrored order amount is close to the amount of initial orders
                assert 0.0024 <= o[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] <= 0.0026
            price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
            assert d_order_price(buy_orders[0][price_col]) == lowest_buy_price
            assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
            assert d_order_price(buy_orders[2][price_col]) == expected_mirror_buy_price
            assert d_order_price(sell_orders[0][price_col]) == expected_remaining_sell_price

            assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == trading_enums.TradeOrderType.LIMIT.value
            assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.OPEN.value
            assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == btc_usdc
            assert 0.0024 <= sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] <= 0.0026

            if emit_signals:
                assert insert_trading_signal_mock.await_count == 2
                _assert_trading_signal_grid_simulator_initial_placement(
                    insert_trading_signal_mock.await_args_list[0].args[0]
                )
                _assert_trading_signal_grid_after_sell_fill_and_mirror(
                    insert_trading_signal_mock.await_args_list[1].args[0],
                    lowest_buy_price=lowest_buy_price,
                    first_sell_price=first_sell_price,
                    second_sell_price=second_sell_price,
                )
            else:
                insert_trading_signal_mock.assert_not_awaited()


@pytest.mark.parametrize("start_as_uninitialized_copy_keyword", [
    False,
    True,
])
@pytest.mark.parametrize("emit_signals", [
    False,
    True,
])
@pytest.mark.asyncio
async def test_simulator_copy_grid(
    init_action: dict,
    grid_reference_account: copy_entities.Account,
    emit_signals: bool,
    start_as_uninitialized_copy_keyword: bool,
):
    """
    Copy a reference spot account shaped like a BTC/USDC grid (portfolio + 2/2 open limits)
    onto the client after init, then ensure a no-op second run keeps portfolio and ladder intact.

    When start_as_uninitialized_copy_keyword is True, the copy action is stored with empty reference_market /
    reference_account until a fetched trading signal fills the DSL; otherwise the reference account
    is embedded in the action from the start.
    """
    community_auth_details = octobot_flow.entities.UserAuthentication(
        wallet_address=SIMULATOR_COPY_GRID_FUNCTIONAL_TEST_COMMUNITY_WALLET_ADDRESS,
    )
    patched_fetch_tickers = tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: _FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = fetch_ohlcv_side_effect_for_close_price(lambda: _FIXED_BTC_USDC_CLOSE)

    fetch_trading_signals_mock = mock.AsyncMock()
    if start_as_uninitialized_copy_keyword:
        fetch_trading_signals_mock.return_value = [
            octobot_flow.entities.TradingSignal(
                strategy_id=functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID,
                account=grid_reference_account,
            )
        ]

    with contextlib.ExitStack() as patch_stack:
        patch_stack.enter_context(
            mock.patch.object(
                octobot_flow.repositories.exchange.TickersRepository,
                "fetch_tickers",
                new=patched_fetch_tickers,
            )
        )
        patch_stack.enter_context(
            mock.patch.object(
                octobot_flow.repositories.exchange.OhlcvRepository,
                "fetch_ohlcv",
                side_effect=patched_fetch_ohlcv,
            )
        )
        patch_stack.enter_context(
            mock.patch.object(
                octobot_flow.repositories.community.TradingSignalsRepository,
                "fetch_trading_signals",
                fetch_trading_signals_mock,
            )
        )
        insert_trading_signal_mock = patch_stack.enter_context(
            trading_signal_emission_patches(emit_signals, mock_authenticator=False)
        )

        reference_market = init_action["config"]["exchange_account_details"]["portfolio"]["unit"]
        if start_as_uninitialized_copy_keyword:
            copy_action = empty_copy_exchange_account_action()
        else:
            copy_action = copy_exchange_account_action(reference_market, grid_reference_account)
        all_actions = [
            init_action,
            copy_action,
        ]
        automation_state = automation_state_dict(resolved_actions(all_actions))
        set_emit_signals_metadata(automation_state, emit_signals)

        # 1. run init action
        async with octobot_flow.AutomationJob(
            automation_state, [], [], community_auth_details
        ) as automation_job:
            await automation_job.run()
        after_init_execution_dump = automation_job.dump()

        # check bot actions execution
        assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.result is None
            if index == 0:
                assert action.executed_at and action.executed_at >= current_time
                assert action.previous_execution_result is None
            else:
                assert action.executed_at is None
                assert action.previous_execution_result is None

        # 2. run copy exchange account action (rebalance + mirror reference grid orders)
        async with octobot_flow.AutomationJob(
            after_init_execution_dump, [], [], community_auth_details
        ) as automation_job:
            await automation_job.run()
        after_initial_copy_execution_dump = automation_job.dump()
        assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.result is None
            if index == 0:
                assert action.executed_at is not None
                assert action.previous_execution_result is None
            else:
                assert action.executed_at is None
                assert isinstance(action.previous_execution_result, dict)

        if start_as_uninitialized_copy_keyword:
            assert fetch_trading_signals_mock.await_count == 1
            fetch_call = fetch_trading_signals_mock.await_args
            assert functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID in fetch_call.args[0]
            assert fetch_call.args[1] == copy_constants.DEFAULT_MISSED_SIGNALS_GRACE_ABORT_THRESHOLD
        else:
            fetch_trading_signals_mock.assert_not_awaited()

        # scheduled next execution: default copy interval (4h)
        assert (
            after_initial_copy_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
            >= current_time
        )
        allowed_execution_time = 20
        schedule_delay = (
            after_initial_copy_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_initial_copy_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert (
            copy_constants.DEFAULT_COPY_WAITING_TIME - allowed_execution_time
            < schedule_delay
            < copy_constants.DEFAULT_COPY_WAITING_TIME + allowed_execution_time
        )

        after_initial_portfolio_content = after_initial_copy_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert isinstance(after_initial_copy_execution_dump, dict)
        assert list(sorted(after_initial_portfolio_content.keys())) == ["BTC", "USDC"]
        assert 450 < after_initial_portfolio_content["USDC"]["total"] < 550
        assert 100 < after_initial_portfolio_content["USDC"]["available"] < 150
        assert 0.0045 < after_initial_portfolio_content["BTC"]["total"] < 0.055
        assert after_initial_portfolio_content["BTC"]["available"] < 0.0015
        logging.getLogger("test_simulator_copy_grid").info(
            f"after_copy_portfolio_content: {after_initial_portfolio_content}"
        )

        after_initial_reference_account_portfolio_content = after_initial_copy_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert isinstance(after_initial_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_reference_account_portfolio_content.keys())) == ["BTC", "USDC"]
        assert 450 < after_initial_reference_account_portfolio_content["USDC"]["total"] < 550
        assert 100 < after_initial_reference_account_portfolio_content["USDC"]["available"] < 150
        assert 0.0045 < after_initial_reference_account_portfolio_content["BTC"]["total"] < 0.055
        assert after_initial_reference_account_portfolio_content["BTC"]["available"] < 0.0015

        open_orders_origin_values = [
            order[trading_constants.STORAGE_ORIGIN_VALUE]
            for order in after_initial_copy_execution_dump["automation"]["exchange_account_elements"]["orders"][
                "open_orders"
            ]
        ]
        buy_orders = sorted(
            [
                o
                for o in open_orders_origin_values
                if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
            ],
            key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
        )
        sell_orders = sorted(
            [
                o
                for o in open_orders_origin_values
                if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                == trading_enums.TradeOrderSide.SELL.value
            ],
            key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
        )
        assert len(buy_orders) == len(sell_orders) == 2
        price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
        lowest_buy_price = d_order_price(buy_orders[0][price_col])
        assert lowest_buy_price == d_order_price(GRID_REFERENCE_LOWEST_BUY)
        assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
        assert d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
        assert d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT

        # 3. trigger again: portfolio and mirrored grid should be unchanged
        async with octobot_flow.AutomationJob(
            after_initial_copy_execution_dump, [], [], community_auth_details
        ) as automation_job:
            await automation_job.run()
        after_second_call_execution_dump = automation_job.dump()
        assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.result is None
            if index == 0:
                assert action.executed_at is not None
                assert action.previous_execution_result is None
            else:
                assert action.executed_at is None
                assert isinstance(action.previous_execution_result, dict)

        schedule_delay = (
            after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert (
            copy_constants.DEFAULT_COPY_WAITING_TIME - allowed_execution_time
            < schedule_delay
            < copy_constants.DEFAULT_COPY_WAITING_TIME + allowed_execution_time
        )

        after_second_call_portfolio_content = after_second_call_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert after_second_call_portfolio_content == after_initial_portfolio_content
        after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert after_second_call_reference_account_portfolio_content == after_initial_reference_account_portfolio_content

        second_open_orders_origin_values = [
            order[trading_constants.STORAGE_ORIGIN_VALUE]
            for order in after_second_call_execution_dump["automation"]["exchange_account_elements"]["orders"][
                "open_orders"
            ]
        ]
        second_buy_orders = sorted(
            [
                o
                for o in second_open_orders_origin_values
                if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
            ],
            key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
        )
        second_sell_orders = sorted(
            [
                o
                for o in second_open_orders_origin_values
                if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                == trading_enums.TradeOrderSide.SELL.value
            ],
            key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
        )
        price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
        assert [d_order_price(o[price_col]) for o in second_buy_orders] == [
            d_order_price(o[price_col]) for o in buy_orders
        ]
        assert [d_order_price(o[price_col]) for o in second_sell_orders] == [
            d_order_price(o[price_col]) for o in sell_orders
        ]

        if start_as_uninitialized_copy_keyword:
            assert fetch_trading_signals_mock.call_count == 1
        else:
            fetch_trading_signals_mock.assert_not_called()

        if emit_signals:
            assert insert_trading_signal_mock.await_count == 2
            for await_args in insert_trading_signal_mock.await_args_list:
                _assert_trading_signal_grid_copy_reference_shape(await_args.args[0])
        else:
            insert_trading_signal_mock.assert_not_awaited()
