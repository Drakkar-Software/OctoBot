#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import asyncio
import pathlib
import sys
import time
import typing

import dbos
import mock
import pytest

import octobot_protocol.models as octobot_protocol_models
import octobot_trading.enums as trading_enums_module
import octobot_trading.errors as trading_errors_module

import octobot.community.authentication as community_authentication_module
import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module

from tests.scheduler import temp_dbos_scheduler

from .util import authenticator_mocks as authenticator_mocks_module
from .util import coinrabbit_dca_workflow as coinrabbit_dca_util
from .util import exchange_account_elements_access as exchange_account_elements_access_module
from .util import price_mocks as price_mocks_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

_FLOW_TESTS_ROOT = pathlib.Path(__file__).resolve().parents[3] / "flow" / "tests"
if str(_FLOW_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_FLOW_TESTS_ROOT))

from functionnal_tests.trading_modes_actions.simulator import (  # noqa: E402
    coinrabbit_ticker_wise_test_util as coinrabbit_price_util,
)

_T_ENQUEUE_SECONDS = 30.0
_T_DCA_BUY_SECONDS = 180.0
_T_STOP_SEND_SECONDS = 15.0
_T_STOP_COMPLETE_SECONDS = 30.0

_DCA_ACCOUNT_ID = "functional_coinrabbit_dca_ticker_wise_account"
_DCA_AUTOMATION_DISPLAY_NAME = "test_coinrabbit_dca_ticker_wise_automation"


@pytest.fixture
def skip_on_exchange_proxy_error(request):
    class _SkipOnExchangeProxyErrorPlugin:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self, item, call):
            outcome = yield
            report = outcome.get_result()
            if item is not request.node:
                return
            if call.when != "call" or call.excinfo is None:
                return
            if not isinstance(call.excinfo.value, trading_errors_module.ExchangeProxyError):
                return
            skip_reason = f"CoinRabbit exchange proxy unavailable: {call.excinfo.value}"
            report.outcome = "skipped"
            line_number = item.location[1] if item.location else 0
            report.longrepr = (str(item.path), line_number, f"Skipped: {skip_reason}")

    plugin = _SkipOnExchangeProxyErrorPlugin()
    request.config.pluginmanager.register(plugin)
    yield
    request.config.pluginmanager.unregister(plugin)


def _portfolio_reference_total(elements: typing.Any) -> float:
    content = exchange_account_elements_access_module.portfolio_content_from_elements(elements)
    row = content.get(coinrabbit_dca_util.REFERENCE_MARKET, {})
    if not row:
        return 0.0
    return exchange_account_elements_access_module.portfolio_row_scalar(
        row,
        "total",
    )


def _portfolio_btc_total(elements: typing.Any) -> float:
    content = exchange_account_elements_access_module.portfolio_content_from_elements(elements)
    row = content.get("BTC@BTC", {})
    if not row:
        return 0.0
    return exchange_account_elements_access_module.portfolio_row_scalar(
        row,
        "total",
    )


def _has_filled_market_buy_on_traded_symbol(elements: typing.Any) -> bool:
    symbol_key = trading_enums_module.ExchangeConstantsOrderColumns.SYMBOL.value
    side_key = trading_enums_module.ExchangeConstantsOrderColumns.SIDE.value
    type_key = trading_enums_module.ExchangeConstantsOrderColumns.TYPE.value
    status_key = trading_enums_module.ExchangeConstantsOrderColumns.STATUS.value
    for trade_row in exchange_account_elements_access_module.trades_from_elements(elements):
        payload = exchange_account_elements_access_module.order_storage_payload(trade_row)
        if payload.get(symbol_key) != coinrabbit_dca_util.TRADED_SYMBOL:
            continue
        if payload.get(side_key) == trading_enums_module.TradeOrderSide.BUY.value:
            return True
    for order_row in exchange_account_elements_access_module.open_orders_from_elements(elements):
        payload = exchange_account_elements_access_module.order_storage_payload(order_row)
        if payload.get(symbol_key) != coinrabbit_dca_util.TRADED_SYMBOL:
            continue
        if payload.get(side_key) != trading_enums_module.TradeOrderSide.BUY.value:
            continue
        order_type = payload.get(type_key)
        if order_type in (
            trading_enums_module.TradeOrderType.BUY_MARKET.value,
            trading_enums_module.TraderOrderType.BUY_MARKET.value,
        ):
            return True
        status = payload.get(status_key)
        if status in (
            trading_enums_module.OrderStatus.FILLED.value,
            trading_enums_module.OrderStatus.CLOSED.value,
        ):
            return True
    return False


class TestCoinrabbitTickerWiseDCADbosIntegration:
    @pytest.mark.asyncio
    async def test_create_dca_buy_on_ticker_wise_pair_then_stop(
        self,
        temp_dbos_scheduler,
        skip_on_exchange_proxy_error,
    ):
        close_by_symbol = coinrabbit_dca_util.default_close_prices_by_symbol()
        patched_fetch_tickers = coinrabbit_dca_util.tickers_repository_fetch_tickers_close_override(
            lambda symbol: close_by_symbol[symbol],
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_prices(
            lambda symbol: close_by_symbol[symbol],
        )
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        initial_reference = coinrabbit_dca_util.INITIAL_REFERENCE_HOLDING
        protocol_account = coinrabbit_dca_util.protocol_account_for_coinrabbit_functional(
            account_id=_DCA_ACCOUNT_ID,
            reference_total=initial_reference,
        )
        create_user_action = coinrabbit_dca_util.build_create_dca_user_action(
            account_id=_DCA_ACCOUNT_ID,
            name=_DCA_AUTOMATION_DISPLAY_NAME,
        )
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        with (
            mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ),
            coinrabbit_price_util.patch_coinrabbit_ticker_closes(close_by_symbol),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.TickersRepository,
                "fetch_tickers",
                new=patched_fetch_tickers,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.OhlcvRepository,
                "fetch_ohlcv",
                side_effect=patched_fetch_ohlcv,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(return_value=protocol_account),
                    get_exchange_config=mock.Mock(
                        return_value=coinrabbit_dca_util.protocol_exchange_config_for_coinrabbit_functional(),
                    ),
                ),
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(
                        return_value=coinrabbit_dca_util.seeded_dca_strategy_for_coinrabbit_wallet(
                            stored_strategy_id=coinrabbit_dca_util.COINRABBIT_DCA_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
        ):
            workflow_common_module.seed_empty_account_trading_state(user_id, _DCA_ACCOUNT_ID)
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        create_user_action,
                        user_id,
                    ),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action timed out enqueueing automation workflow") from exc

            await user_action_assertions_module.assert_user_action_selector_completed_automation_create(
                user_id=user_id,
                user_action_id=create_user_action.id,
                expected_workflow_id=None,
            )

            metadata_automation_id = user_action_assertions_module.resolve_create_automation_metadata_id(
                create_user_action,
            )
            parent_automation_id = await user_action_assertions_module.get_created_automation_id_from_user_action(
                user_action_id=create_user_action.id,
                user_id=user_id,
            )

            async def _enqueue_forced_trigger(user_action_id: str) -> None:
                signal_user_action = workflow_common_module.build_forced_trigger_signal_user_action(
                    automation_id=parent_automation_id,
                    user_action_id=user_action_id,
                )
                await workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler,
                    signal_user_action,
                    user_id,
                )
                await user_action_assertions_module.assert_user_action_selector_completed_automation_signal(
                    user_id=user_id,
                    user_action_id=signal_user_action.id,
                )

            await _enqueue_forced_trigger("ua-signal-coinrabbit-dca-initial")

            reference_after_init = initial_reference
            buy_deadline = time.monotonic() + _T_DCA_BUY_SECONDS
            elements_after_buy: typing.Any = None
            last_seen_elements: typing.Any = None
            forced_trigger_counter = 0
            while time.monotonic() < buy_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if automation_states_loader_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader = automation_states_loader_module.get_automation_state_reader(workflow_row)
                    if reader is None:
                        continue
                    candidate_elements = reader.state.automation.exchange_account_elements
                    last_seen_elements = candidate_elements
                    btc_total = _portfolio_btc_total(candidate_elements)
                    reference_total = _portfolio_reference_total(candidate_elements)
                    if btc_total > 0 and reference_total < reference_after_init:
                        elements_after_buy = candidate_elements
                        break
                if elements_after_buy is not None:
                    break
                forced_trigger_counter += 1
                if forced_trigger_counter % 20 == 0:
                    await _enqueue_forced_trigger(f"ua-signal-coinrabbit-dca-retry-{forced_trigger_counter}")
                await asyncio.sleep(workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS)
            else:
                last_portfolio = exchange_account_elements_access_module.portfolio_content_from_elements(
                    last_seen_elements
                )
                pytest.fail(
                    "Timed out waiting for DCA market buy on "
                    f"{coinrabbit_dca_util.TRADED_SYMBOL} with portfolio delta; "
                    f"last portfolio keys={list(last_portfolio.keys()) if last_portfolio else 'n/a'}"
                )

            assert _has_filled_market_buy_on_traded_symbol(elements_after_buy) or _portfolio_btc_total(
                elements_after_buy
            ) > 0, (
                "expected a filled/closed market buy or buy trade on "
                f"{coinrabbit_dca_util.TRADED_SYMBOL}"
            )

            stop_user_action = workflow_common_module.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-stop-coinrabbit-dca-functional",
            )
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        stop_user_action,
                        user_id,
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action stop timed out") from exc

            await user_action_assertions_module.assert_user_action_selector_completed_automation_stop(
                user_id=user_id,
                user_action_id=stop_user_action.id,
            )

            final_output_text = await workflow_common_module.wait_for_stop_success_output(
                temp_dbos_scheduler,
                metadata_automation_id,
                _T_STOP_COMPLETE_SECONDS,
            )
            assert final_output_text is not None
            parsed_final = workflow_common_module.parse_automation_workflow_output(final_output_text)
            assert parsed_final.error is None
