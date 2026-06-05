import decimal
import os
import time
import typing

import pytest

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.logging as common_logging
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models
import octobot_flow.jobs
import octobot_flow.entities
import octobot_flow.enums
import octobot_trading.modes.mode_dsl_factory as mode_dsl_factory

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    assert_emitted_signal_account_allocation_ratios,
    automation_state_dict,
    AUTHENTICATED_TEST_GROUP,
    current_time,
    d_order_price,
    fetch_last_price,
    resolved_actions,
    set_emit_signals_metadata,
    trading_signal_emission_patches,
)

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

import tests.functionnal_tests.trading_modes_actions.simulator.test_grid_trading_mode_action as grid_simulator_tests

increment = 5000
spread = 10000
D_INCREMENT = decimal.Decimal(str(increment))
D_SPREAD = decimal.Decimal(str(spread))
# Exchange price rounding (e.g. Binance tick) — ladder spacing is still flat increment/spread.
_GRID_PRICE_TOLERANCE = decimal.Decimal("0.5")


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
            f"grid_trading_mode(pair_settings={dsl_interpreter.format_parameter_value(grid_pair_settings)}, {mode_dsl_factory.ENABLE_INITIAL_PORTFOLIO_OPTIMIZATION}=True)"
        ),
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


def _signal_copied_assets_by_name(
    account: protocol_models.CopiedAccount,
) -> dict[str, protocol_models.CopiedAsset]:
    return {a.name: a for a in (account.copied_assets or [])}


def _assert_grid_ladder_prices_protocol(
    buy_orders: list[protocol_models.Order],
    sell_orders: list[protocol_models.Order],
) -> None:
    lowest_buy_price = d_order_price(buy_orders[0].price)
    assert len(buy_orders) == len(sell_orders) == 2
    assert abs(d_order_price(buy_orders[1].price) - (lowest_buy_price + D_INCREMENT)) <= _GRID_PRICE_TOLERANCE
    assert (
        abs(d_order_price(sell_orders[0].price) - (lowest_buy_price + D_INCREMENT + D_SPREAD))
        <= _GRID_PRICE_TOLERANCE
    )
    assert (
        abs(d_order_price(sell_orders[1].price) - (lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT))
        <= _GRID_PRICE_TOLERANCE
    )


def _btc_usdc_limit_open_order_values(open_orders_origin_values: list[dict]) -> list[dict]:
    """
    Keep only limit orders on BTC/USDC. Rebalancing can leave market orders in open_orders
    briefly (or as filled-but-still-open rows), which would break the 2×2 grid ladder count.
    """
    sym_col = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    type_col = trading_enums.ExchangeConstantsOrderColumns.TYPE.value
    limit_type = trading_enums.TradeOrderType.LIMIT.value
    return [
        o
        for o in open_orders_origin_values
        if o.get(sym_col) == "BTC/USDC" and o.get(type_col) == limit_type
    ]


def _assert_grid_ladder_prices(
    buy_orders: list[dict],
    sell_orders: list[dict],
    price_col: str,
) -> None:
    lowest_buy_price = d_order_price(buy_orders[0][price_col])
    assert len(buy_orders) == len(sell_orders) == 2
    assert abs(d_order_price(buy_orders[1][price_col]) - (lowest_buy_price + D_INCREMENT)) <= _GRID_PRICE_TOLERANCE
    assert (
        abs(d_order_price(sell_orders[0][price_col]) - (lowest_buy_price + D_INCREMENT + D_SPREAD))
        <= _GRID_PRICE_TOLERANCE
    )
    assert (
        abs(d_order_price(sell_orders[1][price_col]) - (lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT))
        <= _GRID_PRICE_TOLERANCE
    )


def _assert_nonempty_btc_usdc_portfolio(portfolio_content: dict) -> None:
    assert "BTC" in portfolio_content
    assert "USDC" in portfolio_content
    assert portfolio_content["USDC"]["total"] > 0
    assert portfolio_content["BTC"]["total"] > 0


def _assert_btc_usdc_balances_unchanged(before: dict, after: dict) -> None:
    """A no-op second run must not move BTC/USDC; other assets are ignored (exchange free/total can flap between fetches)."""
    for asset in ("BTC", "USDC"):
        assert before[asset] == after[asset]


def _assert_trading_signal_authenticated_grid_account_metadata(
    trading_signal: octobot_flow.entities.TradingSignal,
) -> None:
    account = trading_signal.account
    assert isinstance(account.updated_at, float)
    assert current_time <= account.updated_at <= time.time()
    assert account.positions in (None, [])
    assert account.historical_snapshots in (None, [])


def _assert_trading_signal_authenticated_grid_initial_placement(
    trading_signal: octobot_flow.entities.TradingSignal, is_sub_portfolio: bool
) -> None:
    """
    Same structure as simulator grid signal checks: BTC/USDC content, allocation ratios,
    four BTC/USDC limit orders in a 2×2 ladder (live price — use tolerance on prices).
    """
    content = _signal_copied_assets_by_name(trading_signal.account)
    expected_assets = ["BTC", "USDC"]
    if is_sub_portfolio:
        assert list(sorted(content.keys())) == expected_assets
    else:
        assert all(asset in content for asset in expected_assets)
    assert float(content["USDC"].total) > 0
    assert float(content["BTC"].total) > 0
    if is_sub_portfolio:
        assert_emitted_signal_account_allocation_ratios(trading_signal.account)
    else:
        for asset in expected_assets:
            assert asset in content
            assert float(content[asset].ratio) > 0
    ladder_orders = [
        order
        for order in (trading_signal.account.orders or [])
        if order.symbol == "BTC/USDC" and order.type == protocol_models.OrderType.LIMIT
    ]
    assert len(ladder_orders) == 4
    buy_orders = sorted(
        [
            order
            for order in ladder_orders
            if order.side == protocol_models.Side.BUY
        ],
        key=lambda order: order.price,
    )
    sell_orders = sorted(
        [
            order
            for order in ladder_orders
            if order.side == protocol_models.Side.SELL
        ],
        key=lambda order: order.price,
    )
    _assert_grid_ladder_prices_protocol(buy_orders, sell_orders)
    _assert_trading_signal_authenticated_grid_account_metadata(trading_signal)


def _btc_usdc_open_order_count(automation_dump: dict, portfolio_type: str) -> int:
    sym_col = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    return sum(
        1
        for order in automation_dump["automation"][portfolio_type]["orders"]["open_orders"]
        if order[trading_constants.STORAGE_ORIGIN_VALUE].get(sym_col) == "BTC/USDC"
    )


async def _cancel_all_btc_usdc_orders_for_test(automation_dump: dict) -> None:
    common_logging.get_logger("Tests").info("*** Cancelling all BTC/USDC orders ***")
    cancel_grid_orders_actions = resolved_actions(
        [
            {
                "id": "action_cancel_grid",
                "dsl_script": "cancel_order('BTC/USDC')",
            }
        ]
    )
    async with octobot_flow.jobs.AutomationJob(automation_dump, [], [], {}) as automations_job:
        automations_job.automation_state.upsert_automation_actions(cancel_grid_orders_actions)
        await automations_job.run()
    cancel_action = automations_job.automation_state.automation.actions_dag.actions[-1]
    assert isinstance(cancel_action, octobot_flow.entities.AbstractActionDetails)
    assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
    assert isinstance(cancel_action.result, dict)
    assert "cancelled_orders" in cancel_action.result
    assert len(cancel_action.result["cancelled_orders"]) >= 4

    after_cancel_dump = automations_job.dump()
    assert _btc_usdc_open_order_count(after_cancel_dump, "exchange_account_elements") == 0


def _live_grid_reference_account(btc_usdc_close: float) -> protocol_models.CopiedAccount:
    """
    Same shape as the simulator grid_reference_account fixture: 2×2 BTC/USDC limits and half/half
    portfolio ratios, with ladder prices anchored to the current market close.
    """
    lowest_buy = btc_usdc_close - (spread / 2) - increment * 2 + 12.12
    order_amount = 0.004
    content = {
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
    }
    orders_storage = [
        grid_simulator_tests._grid_reference_storage_order(
            "grid_ref_b0", trading_enums.TradeOrderSide.BUY.value, lowest_buy, order_amount
        ),
        grid_simulator_tests._grid_reference_storage_order(
            "grid_ref_b1",
            trading_enums.TradeOrderSide.BUY.value,
            lowest_buy + increment,
            order_amount,
        ),
        grid_simulator_tests._grid_reference_storage_order(
            "grid_ref_s0",
            trading_enums.TradeOrderSide.SELL.value,
            lowest_buy + increment + spread,
            order_amount,
        ),
        grid_simulator_tests._grid_reference_storage_order(
            "grid_ref_s1",
            trading_enums.TradeOrderSide.SELL.value,
            lowest_buy + increment + spread + increment,
            order_amount,
        ),
    ]
    return grid_simulator_tests.copied_account_from_content_and_storage_orders(
        updated_at=time.time(),
        content=content,
        orders_storage=orders_storage,
        positions=[],
    )


@pytest.fixture
def init_action():
    if not os.environ.get("BINANCE_KEY") or not os.environ.get("BINANCE_SECRET"):
        pytest.skip(
            "BINANCE_KEY and BINANCE_SECRET must be set in the .env file to run this test, skipping..."
        )
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
                "auth_details": {
                    "api_key": os.environ["BINANCE_KEY"],
                    "api_secret": os.environ["BINANCE_SECRET"],
                },
                "portfolio": {
                    "unit": "USDC",
                },
            },
        },
    }


@pytest.mark.asyncio
@pytest.mark.xdist_group(name=AUTHENTICATED_TEST_GROUP)
async def test_authenticated_grid_init_from_empty_state(init_action: dict):
    """
    Same flow as the simulator grid test, but against a real authenticated account: current market price
    anchors the ladder (no ticker/ohlcv mocks).
    Requires spot USD/BTC balance sufficient for the grid on the configured exchange.
    """
    all_actions = [init_action, grid_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    emit_signals = True # always True in this test in order to test signal emission as well
    set_emit_signals_metadata(automation_state, emit_signals)

    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
        trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock,
    ):
        # 1. run init action
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
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

        # 2. run grid trading mode action (orders may exist on the exchange after this completes)
        cleanup_dump: typing.Optional[dict] = None
        try:
            async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            cleanup_dump = automation_job.dump()

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

            after_grid_execution_dump = cleanup_dump
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

            # check portfolio and open grid orders (balances depend on the live account)
            after_grid_portfolio_content = after_grid_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_execution_dump, dict)
            _assert_nonempty_btc_usdc_portfolio(after_grid_portfolio_content)

            after_grid_reference_account_portfolio_content = after_grid_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_reference_account_portfolio_content, dict)
            _assert_nonempty_btc_usdc_portfolio(after_grid_reference_account_portfolio_content)

            price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
            order_portfolio_types = ["exchange_account_elements"]
            for portfolio_type in order_portfolio_types:
                open_orders_origin_values = [
                    order[trading_constants.STORAGE_ORIGIN_VALUE]
                    for order in after_grid_execution_dump["automation"][portfolio_type]["orders"][
                        "open_orders"
                    ]
                ]
                ladder_orders = _btc_usdc_limit_open_order_values(open_orders_origin_values)
                buy_orders = sorted(
                    [
                        o
                        for o in ladder_orders
                        if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                        == trading_enums.TradeOrderSide.BUY.value
                    ],
                    key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
                )
                sell_orders = sorted(
                    [
                        o
                        for o in ladder_orders
                        if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                        == trading_enums.TradeOrderSide.SELL.value
                    ],
                    key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
                )
                _assert_grid_ladder_prices(buy_orders, sell_orders, price_col)

            trades = after_grid_execution_dump["automation"]["exchange_account_elements"]["trades"]
            assert len(trades) >= 1
            trade_id_column = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
            exchange_id_column = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            symbol_column = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
            for trade in trades:
                assert trade.get(trade_id_column) or trade.get(exchange_id_column)
                assert trade.get(symbol_column)

            # 3. trigger again: nothing to do
            async with octobot_flow.jobs.AutomationJob(cleanup_dump, [], [], {}) as automation_job:
                await automation_job.run()
            cleanup_dump = automation_job.dump()

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
                cleanup_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
                - cleanup_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
            )
            assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

            after_second_call_portfolio_content = cleanup_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            _assert_btc_usdc_balances_unchanged(
                after_grid_portfolio_content,
                after_second_call_portfolio_content,
            )
            after_second_call_reference_account_portfolio_content = cleanup_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            _assert_btc_usdc_balances_unchanged(
                after_grid_reference_account_portfolio_content,
                after_second_call_reference_account_portfolio_content,
            )

            assert insert_trading_signal_mock.await_count == 2
            for await_args in insert_trading_signal_mock.await_args_list:
                _assert_trading_signal_authenticated_grid_initial_placement(await_args.args[0], is_sub_portfolio=False)
        finally:
            if cleanup_dump is not None:
                await _cancel_all_btc_usdc_orders_for_test(cleanup_dump)

        login_mock.assert_not_called()
        assert insert_bot_logs_mock.await_count == 3 # called once per grid trading mode iteration


@pytest.mark.asyncio
@pytest.mark.xdist_group(name=AUTHENTICATED_TEST_GROUP)
async def test_authenticated_copy_grid(init_action: dict):
    """
    Same flow as test_simulator_copy_grid: init, then copy a synthetic reference BTC/USDC grid onto the
    account, then a no-op second copy run. Uses live BTC/USDC price to build valid limit prices (no mocks).
    emit_signals=False. Requires spot USDC/BTC balance sufficient for mirrored limits on the exchange.
    """
    btc_close = await fetch_last_price("BTC/USDC")
    grid_reference_account = _live_grid_reference_account(btc_close)
    reference_market = init_action["config"]["exchange_account_details"]["portfolio"]["unit"]
    all_actions = [
        init_action,
        functionnal_tests.copy_exchange_account_action(reference_market, grid_reference_account),
    ]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    emit_signals = False
    set_emit_signals_metadata(automation_state, emit_signals)

    allowed_execution_time = 20

    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
        trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock,
    ):
        cleanup_dump: typing.Optional[dict] = None
        try:
            async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
                await automation_job.run()
            after_init_execution_dump = automation_job.dump()

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

            async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_initial_copy_execution_dump = automation_job.dump()
            cleanup_dump = after_initial_copy_execution_dump

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

            assert (
                after_initial_copy_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
                >= current_time
            )
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
            _assert_nonempty_btc_usdc_portfolio(after_initial_portfolio_content)

            after_initial_reference_account_portfolio_content = after_initial_copy_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_initial_reference_account_portfolio_content, dict)
            _assert_nonempty_btc_usdc_portfolio(after_initial_reference_account_portfolio_content)

            open_orders_origin_values = [
                order[trading_constants.STORAGE_ORIGIN_VALUE]
                for order in after_initial_copy_execution_dump["automation"]["exchange_account_elements"]["orders"][
                    "open_orders"
                ]
            ]
            ladder_orders = _btc_usdc_limit_open_order_values(open_orders_origin_values)
            price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
            buy_orders = sorted(
                [
                    order
                    for order in ladder_orders
                    if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.BUY.value
                ],
                key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            sell_orders = sorted(
                [
                    order
                    for order in ladder_orders
                    if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.SELL.value
                ],
                key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            _assert_grid_ladder_prices(buy_orders, sell_orders, price_col)

            async with octobot_flow.jobs.AutomationJob(after_initial_copy_execution_dump, [], [], {}) as automation_job:
                await automation_job.run()
            after_second_call_execution_dump = automation_job.dump()
            cleanup_dump = after_second_call_execution_dump

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
            _assert_btc_usdc_balances_unchanged(
                after_initial_portfolio_content,
                after_second_call_portfolio_content,
            )
            after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"][
                "exchange_account_elements"
            ]["portfolio"]["content"]
            _assert_btc_usdc_balances_unchanged(
                after_initial_reference_account_portfolio_content,
                after_second_call_reference_account_portfolio_content,
            )

            second_open_orders_origin_values = [
                order[trading_constants.STORAGE_ORIGIN_VALUE]
                for order in after_second_call_execution_dump["automation"]["exchange_account_elements"]["orders"][
                    "open_orders"
                ]
            ]
            second_ladder_orders = _btc_usdc_limit_open_order_values(second_open_orders_origin_values)
            second_buy_orders = sorted(
                [
                    order
                    for order in second_ladder_orders
                    if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.BUY.value
                ],
                key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            second_sell_orders = sorted(
                [
                    order
                    for order in second_ladder_orders
                    if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    == trading_enums.TradeOrderSide.SELL.value
                ],
                key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            )
            assert [d_order_price(order[price_col]) for order in second_buy_orders] == [
                d_order_price(order[price_col]) for order in buy_orders
            ]
            assert [d_order_price(order[price_col]) for order in second_sell_orders] == [
                d_order_price(order[price_col]) for order in sell_orders
            ]

            insert_trading_signal_mock.assert_not_awaited()
        finally:
            if cleanup_dump is not None:
                await _cancel_all_btc_usdc_orders_for_test(cleanup_dump)

        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called() # not called in copy action
