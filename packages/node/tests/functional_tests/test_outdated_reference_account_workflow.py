#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
from __future__ import annotations

import asyncio
import decimal
import logging
import time

import mock
import pytest

from .util import authenticator_mocks as authenticator_mocks_module
from .util import grid_workflow as grid_workflow_module
from .util import price_mocks as price_mocks_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot.community.authentication as community_authentication_module
import octobot_flow.entities as octobot_flow_entities
import octobot_node.config
import octobot_node.scheduler
import octobot_node.scheduler.workflows_util as workflows_util_module
import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module

from tests.scheduler import temp_dbos_scheduler

_T_ENQUEUE_SECONDS = 5.0
_T_POLL_SECONDS = workflow_common_module.functional_timeout_seconds(25.0)


@pytest.mark.asyncio
class TestOutdatedReferenceAccountWorkflow:
    async def test_skips_stale_signal_then_executes_fresh_signal_from_internal_channel(
        self,
        temp_dbos_scheduler,
        caplog,
    ):
        """
        Copy automation on the simulator exchange: stale TradingSignal is rejected as outdated,
        workflow postpones and waits; a fresh signal drives a real mirror limit order.
        """
        import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel_module
        import octobot_node.scheduler.internal_trading_signals as internal_trading_signals_module

        from .util import outdated_reference_workflow as outdated_reference_workflow_module

        fresh_order_price_decimal = decimal.Decimal(str(outdated_reference_workflow_module.FRESH_ORDER_PRICE))
        stale_order_price_decimal = decimal.Decimal(str(outdated_reference_workflow_module.STALE_ORDER_PRICE))

        # Step 0 — Pin BTC/USDC close and mock only exchange/infra providers; DBOS + flow run for real.
        patched_fetch_tickers = price_mocks_module.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: outdated_reference_workflow_module.FRESH_MARKET_PRICE,
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_price(
            lambda: outdated_reference_workflow_module.FRESH_MARKET_PRICE,
        )
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=outdated_reference_workflow_module.COPY_ACCOUNT_ID,
            usdc_total=2000.0,
            account_name="Outdated reference functional copy account",
        )
        copy_user_action = outdated_reference_workflow_module.build_create_copy_follower_user_action()
        automation_id = user_action_assertions_module.resolve_create_automation_metadata_id(copy_user_action)
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        def _functional_seed_strategy_for_outdated_reference_test(_wallet_address, stored_item_id):
            if stored_item_id == grid_workflow_module.SIMULATOR_COPY_FOLLOWER_STORED_STRATEGY_ID:
                return grid_workflow_module.seeded_copy_follower_strategy_for_functional_wallet(
                    copy_master_strategy_id=outdated_reference_workflow_module.MASTER_STRATEGY_ID,
                )
            raise AssertionError(f"unexpected strategy id for functional seed: {stored_item_id!r}")

        await internal_trading_signals_module.subscribe_internal_trading_signal_consumer()
        try:
            # Step 0 (continued) — Subscribe internal trading-signal consumer and seed account trading state.
            with (
                mock.patch.object(
                    community_authentication_module.CommunityAuthentication,
                    "instance",
                    return_value=authentication_instance,
                ),
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
                            return_value=workflow_common_module.protocol_exchange_config_for_grid_functional(),
                        ),
                    ),
                ),
                mock.patch(
                    "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                    return_value=mock.Mock(
                        get_item=mock.Mock(
                            side_effect=_functional_seed_strategy_for_outdated_reference_test,
                        ),
                    ),
                ),
                mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
                mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
            ):
                caplog.set_level(logging.INFO)
                workflow_common_module.seed_empty_account_trading_state(
                    user_id,
                    outdated_reference_workflow_module.COPY_ACCOUNT_ID,
                )

                stale_signal = outdated_reference_workflow_module.build_stale_trading_signal()
                fresh_signal = outdated_reference_workflow_module.build_fresh_trading_signal()

                stale_delivery_task = asyncio.create_task(
                    outdated_reference_workflow_module.deliver_trading_signal_when_pending(
                        temp_dbos_scheduler,
                        automation_id,
                        stale_signal,
                        _T_POLL_SECONDS,
                    )
                )

                # Step 1 — Enqueue AUTOMATION_CREATE for copy follower; expect COMPLETED create result.
                try:
                    await asyncio.wait_for(
                        workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                            temp_dbos_scheduler,
                            copy_user_action,
                            user_id,
                        ),
                        timeout=_T_ENQUEUE_SECONDS,
                    )
                except TimeoutError as exc:
                    raise AssertionError("execute_user_action timed out enqueueing copy workflow") from exc

                await stale_delivery_task

                await user_action_assertions_module.assert_user_action_selector_completed_automation_create(
                    user_id=user_id,
                    user_action_id=copy_user_action.id,
                    expected_workflow_id=None,
                )

                # Step 2 — Stale signal delivered while copy workflow was pending; expect outdated skip log.
                stale_skip_deadline = time.monotonic() + _T_POLL_SECONDS
                while time.monotonic() < stale_skip_deadline:
                    if outdated_reference_workflow_module.caplog_contains_outdated_skip(caplog):
                        break
                    await asyncio.sleep(workflow_common_module.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS)
                else:
                    pytest.fail(
                        "Timed out waiting for outdated reference account skip log "
                        f"({outdated_reference_workflow_module.OUTDATED_SKIP_LOG_SUBSTRING!r})"
                    )

                await outdated_reference_workflow_module.poll_state_reader_until(
                    temp_dbos_scheduler,
                    automation_id,
                    lambda reader: stale_order_price_decimal
                    not in outdated_reference_workflow_module.sell_limit_prices_from_reader(reader),
                    _T_POLL_SECONDS,
                    "stale sell limit not mirrored",
                )

                # Step 3 — Send fresh TradingSignal after child workflow is pending again; expect mirror at fresh price.
                await outdated_reference_workflow_module.deliver_trading_signal_when_pending(
                    temp_dbos_scheduler,
                    automation_id,
                    fresh_signal,
                    _T_POLL_SECONDS,
                )
                fresh_reader = await outdated_reference_workflow_module.poll_state_reader_until(
                    temp_dbos_scheduler,
                    automation_id,
                    lambda reader: fresh_order_price_decimal
                    in outdated_reference_workflow_module.sell_limit_prices_from_reader(reader),
                    _T_POLL_SECONDS,
                    "fresh sell limit mirrored",
                )

                # Step 4 — Assert stale price never mirrored, fresh order present, automation still healthy.
                sell_prices = outdated_reference_workflow_module.sell_limit_prices_from_reader(fresh_reader)
                assert stale_order_price_decimal not in sell_prices
                assert sell_prices.count(fresh_order_price_decimal) == 1
                assert outdated_reference_workflow_module.caplog_contains_outdated_skip(caplog)
        finally:
            await trading_signals_channel_module.shutdown_internal_trading_signal_channel()
