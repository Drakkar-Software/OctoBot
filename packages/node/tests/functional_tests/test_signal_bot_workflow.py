import asyncio
import mock

import pytest

from .util import authenticator_mocks as authenticator_mocks_module
from .util import price_mocks as price_mocks_module
from .util import signal_bot_workflow as signal_bot_sim_util
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot.community.authentication as community_authentication_module
import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
import octobot_node.config as octobot_node_config

from tests.scheduler import temp_dbos_scheduler


_T_ENQUEUE_SECONDS = 5.0
_T_SIGNAL_SECONDS = workflow_common_module.functional_timeout_seconds(20.0)
_T_IDLE_SECONDS = workflow_common_module.functional_timeout_seconds(20.0)

_GRID_ACCOUNT_ID = "functional_signal_bot_account"
_GRID_AUTOMATION_DISPLAY_NAME = "test_signal_bot_workflow_automation"
_GRID_AUTOMATION_CONFIGURATION_ID = "d4e5f6a7-b8c9-4012-d345-6789abcdef04"


@pytest.mark.asyncio
class TestSignalBotWorkflowEndToEnd:
    async def test_start_signal_buy_cancel_stop_lifecycle(self, temp_dbos_scheduler):
        patched_fetch_tickers = price_mocks_module.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: 100000.0,
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_price(
            lambda: 100000.0,
        )
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_GRID_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Signal bot functional account",
        )
        create_user_action = signal_bot_sim_util.build_create_signal_bot_user_action(
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
                        return_value=signal_bot_sim_util.seeded_signal_bot_strategy_for_functional_wallet(
                            stored_strategy_id=signal_bot_sim_util.SIMULATOR_SIGNAL_BOT_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
        ):
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

            await signal_bot_sim_util.wait_for_signal_exchange_context_ready(
                temp_dbos_scheduler,
                parent_automation_id,
                user_id,
                _T_IDLE_SECONDS,
            )

            signal_user_action = workflow_common_module.build_actions_signal_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-signal-bot-functional",
                signal_payload=[
                    {
                        "script": (
                            "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.00001\n"
                            "TAKE_PROFIT_PRICE=10%"
                        ),
                    },
                    {"script": "SYMBOL=BTC/USDC\nSIGNAL=cancel"},
                ],
            )
            await asyncio.wait_for(
                workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler,
                    signal_user_action,
                    user_id,
                ),
                timeout=_T_SIGNAL_SECONDS,
            )
            await user_action_assertions_module.assert_user_action_selector_completed_automation_signal(
                user_id=user_id,
                user_action_id=signal_user_action.id,
                expected_signal_execution_result_count=2,
            )

            stop_user_action = workflow_common_module.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-signal-bot-stop",
            )
            await asyncio.wait_for(
                workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler,
                    stop_user_action,
                    user_id,
                ),
                timeout=_T_SIGNAL_SECONDS,
            )
            await user_action_assertions_module.assert_user_action_selector_completed_automation_stop(
                user_id=user_id,
                user_action_id=stop_user_action.id,
            )
