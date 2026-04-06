import decimal
import os
import typing

import pytest

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.logging as common_logging
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums
import octobot_trading.modes.mode_dsl_factory as mode_dsl_factory

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    resolved_actions,
    automation_state_dict,
    set_init_action_run_mode,
    AUTHENTICATED_TEST_GROUP,
    d_order_price,
)

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

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
    async with octobot_flow.AutomationJob(automation_dump, [], {}) as automations_job:
        automations_job.automation_state.upsert_automation_actions(cancel_grid_orders_actions)
        await automations_job.run()
    cancel_action = automations_job.automation_state.automation.actions_dag.actions[-1]
    assert isinstance(cancel_action, octobot_flow.entities.AbstractActionDetails)
    assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
    assert isinstance(cancel_action.result, dict)
    assert "cancelled_orders" in cancel_action.result
    assert len(cancel_action.result["cancelled_orders"]) >= 4

    after_cancel_dump = automations_job.dump()
    assert _btc_usdc_open_order_count(after_cancel_dump, "client_exchange_account_elements") == 0 #todo
    assert _btc_usdc_open_order_count(after_cancel_dump, "reference_exchange_account_elements") == 0


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
                "client_exchange_account_elements": {
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
async def test_authenticated_grid_init_from_empty_state_copying_reference_account(init_action: dict):
    """
    Same flow as the simulator grid test with UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY, but against a
    real authenticated account: current market price anchors the ladder (no ticker/ohlcv mocks).
    Requires spot USD/BTC balance sufficient for the grid on the configured exchange.
    """
    run_mode = octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY
    all_actions = [set_init_action_run_mode(init_action, run_mode), grid_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))

    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        # 1. run init action
        async with octobot_flow.AutomationJob(automation_state, [], {}) as automation_job:
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
            async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
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
                "client_exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_execution_dump, dict)
            _assert_nonempty_btc_usdc_portfolio(after_grid_portfolio_content)

            after_grid_reference_account_portfolio_content = after_grid_execution_dump["automation"][
                "reference_exchange_account_elements"
            ]["portfolio"]["content"]
            assert isinstance(after_grid_reference_account_portfolio_content, dict)
            _assert_nonempty_btc_usdc_portfolio(after_grid_reference_account_portfolio_content)

            price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
            order_portfolio_types = ["client_exchange_account_elements", "reference_exchange_account_elements"]
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

            # raise NotImplementedError("TODO Not implemented")

            # 3. trigger again: nothing to do
            async with octobot_flow.AutomationJob(cleanup_dump, [], {}) as automation_job:
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
                "client_exchange_account_elements"
            ]["portfolio"]["content"]
            _assert_btc_usdc_balances_unchanged(
                after_grid_portfolio_content,
                after_second_call_portfolio_content,
            )
            after_second_call_reference_account_portfolio_content = cleanup_dump["automation"][
                "reference_exchange_account_elements"
            ]["portfolio"]["content"]
            _assert_btc_usdc_balances_unchanged(
                after_grid_reference_account_portfolio_content,
                after_second_call_reference_account_portfolio_content,
            )

        finally:
            if cleanup_dump is not None:
                await _cancel_all_btc_usdc_orders_for_test(cleanup_dump)

        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()
