import asyncio
import mock

import pytest

from .util import authenticator_mocks as authenticator_mocks_module
from .util import grid_workflow as grid_sim_util
from .util import price_mocks as price_mocks_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot.community.authentication as community_authentication_module
import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
import octobot_node.config as octobot_node_config

from tests.scheduler import temp_dbos_scheduler


_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = workflow_common_module.functional_timeout_seconds(20.0)
_T_SIGNAL_SECONDS = workflow_common_module.functional_timeout_seconds(20.0)
_POST_SIGNAL_POLL_SECONDS = 0.05

_GRID_ACCOUNT_ID = "functional_signal_account"
_GRID_AUTOMATION_DISPLAY_NAME = "test_signal_priority_automation"
_GRID_AUTOMATION_CONFIGURATION_ID = "d4e5f6a7-b8c9-4012-d345-6789abcdef01"


@pytest.mark.asyncio
class TestSignalAutomationPriorityEndToEnd:
    async def test_list_of_signal_scripts_buy_then_cancel(self, temp_dbos_scheduler):
        # 1. Set up mocks (community auth, tickers/OHLCV, sync providers, node crypto keys)
        patched_fetch_tickers = price_mocks_module.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_price(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_GRID_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Signal priority functional account",
        )
        create_user_action = grid_sim_util.build_create_grid_user_action(
            account_id=_GRID_ACCOUNT_ID,
            name=_GRID_AUTOMATION_DISPLAY_NAME,
            automation_id=_GRID_AUTOMATION_CONFIGURATION_ID,
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
                        return_value=grid_sim_util.seeded_grid_strategy_for_functional_wallet(
                            stored_strategy_id=grid_sim_util.SIMULATOR_GRID_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
        ):
            # 2. Seed account and create grid automation via automation_create user action
            workflow_common_module.seed_empty_account_trading_state(user_id, _GRID_ACCOUNT_ID)
            parent_automation_id = _GRID_AUTOMATION_CONFIGURATION_ID
            await asyncio.wait_for(
                workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler,
                    create_user_action,
                    user_id,
                ),
                timeout=_T_ENQUEUE_SECONDS,
            )
            await user_action_assertions_module.assert_user_action_selector_completed_automation_create(
                user_id=user_id,
                user_action_id=create_user_action.id,
                expected_workflow_id=None,
            )

            # 3. Wait for grid baseline (exactly one trade, open orders present)
            await workflow_common_module.wait_for_latest_automation_exchange_elements_until(
                temp_dbos_scheduler,
                parent_automation_id,
                lambda elements: grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                    *workflow_common_module.buy_sell_trade_counts_from_exchange_elements(elements),
                ),
                _T_GRID_SECONDS,
                "simulator grid baseline",
                user_id=user_id,
                account_id=_GRID_ACCOUNT_ID,
                require_account_trading_open_orders=True,
            )

            # 4. Send automation_signal user action with two signal scripts (buy + cancel)
            signal_user_action = workflow_common_module.build_actions_signal_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-signal-priority-functional",
                signal_payload=[
                    {"script": "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.00001"},
                    {"script": "SYMBOL=BTC/USDC\nSIGNAL=cancel"},
                ],
            )
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        signal_user_action,
                        user_id,
                    ),
                    timeout=_T_SIGNAL_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action signal actions timed out") from exc

            # 5. Assert user action completed
            await user_action_assertions_module.assert_user_action_selector_completed_automation_signal(
                user_id=user_id,
                user_action_id=signal_user_action.id,
            )

            # 6. Poll until open buy/sell counts are zero
            final_elements = await workflow_common_module.wait_for_latest_automation_exchange_elements_until(
                temp_dbos_scheduler,
                parent_automation_id,
                lambda elements: workflow_common_module.buy_sell_trade_counts_from_exchange_elements(elements)[0] == 0
                and workflow_common_module.buy_sell_trade_counts_from_exchange_elements(elements)[1] == 0,
                _T_SIGNAL_SECONDS,
                "open orders cleared after signal cancel",
            )
            final_buy_count, final_sell_count, _ = workflow_common_module.buy_sell_trade_counts_from_exchange_elements(
                final_elements,
            )
            assert final_buy_count == 0
            assert final_sell_count == 0
