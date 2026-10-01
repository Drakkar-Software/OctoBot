import contextlib
import json

import mock
import pytest

import octobot_copy.enums as rebalancer_enums
import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.jobs
import octobot_flow.repositories.community as community_repository_module

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    automation_state_dict,
    empty_copy_exchange_account_action,
    resolved_actions,
    set_emit_signals_metadata,
    trading_signal_emission_patches,
)
from tests.functionnal_tests.trading_modes_actions.simulator import coinrabbit_ticker_wise_test_util as coinrabbit_util


def _index_content():
    return [
        {rebalancer_enums.DistributionKeys.NAME: coin, rebalancer_enums.DistributionKeys.VALUE: 1}
        for coin in coinrabbit_util.INDEX_COINS
    ]


def _init_action() -> dict:
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {
                    "automation_id": "automation_coinrabbit_ticker_wise",
                },
                "exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            coinrabbit_util.REFERENCE_ASSET: {
                                "available": coinrabbit_util.INITIAL_REFERENCE_HOLDING,
                                "total": coinrabbit_util.INITIAL_REFERENCE_HOLDING,
                            },
                        },
                    },
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": coinrabbit_util.EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {
                    "unit": coinrabbit_util.REFERENCE_ASSET,
                },
            },
        },
    }


def _index_trading_mode_action(dependency_action: dict) -> dict:
    return {
        "id": "action_1",
        "dsl_script": (
            f"index_trading_mode(index_content={json.dumps(_index_content())}, "
            f"rebalance_trigger_min_percent=5)"
        ),
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


@pytest.mark.asyncio
async def test_coinrabbit_markets_expose_ticker_wise_symbols(skip_on_exchange_proxy_error):
    async with coinrabbit_util.coinrabbit_exchange_manager_context() as exchange_manager:
        await coinrabbit_util.assert_coinrabbit_markets_expose_symbols(exchange_manager)


@pytest.mark.asyncio
async def test_coinrabbit_index_trading_mode_ticker_wise_rebalance(skip_on_exchange_proxy_error):
    init_action = _init_action()
    all_actions = [init_action, _index_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    initial_reference = coinrabbit_util.INITIAL_REFERENCE_HOLDING

    async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
        await automation_job.run()
    after_init_dump = automation_job.dump()
    portfolio_after_init = (
        after_init_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
    )
    assert portfolio_after_init[coinrabbit_util.REFERENCE_ASSET]["total"] == initial_reference

    with coinrabbit_util.patch_coinrabbit_ticker_closes():
        async with octobot_flow.jobs.AutomationJob(after_init_dump, [], [], {}) as automation_job:
            await automation_job.run()
        after_index_dump = automation_job.dump()

    for action in after_index_dump["automation"]["actions_dag"]["actions"]:
        if action.get("id") == "action_1":
            assert action.get("error_status") == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            break
    else:
        pytest.fail("action_1 not found")

    portfolio_content = (
        after_index_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
    )
    for key in coinrabbit_util.EXPECTED_PORTFOLIO_KEYS_AFTER_REBALANCE:
        assert key in portfolio_content, f"missing portfolio key {key!r}: {portfolio_content.keys()}"
    assert portfolio_content["BTC@BTC"]["total"] > 0
    reference_total = portfolio_content.get(coinrabbit_util.REFERENCE_ASSET, {}).get("total", 0)
    assert reference_total < initial_reference


def _copier_init_action() -> dict:
    action = _init_action()
    action["config"]["automation"]["metadata"]["automation_id"] = "automation_coinrabbit_ticker_wise_copier"
    return action


@pytest.mark.asyncio
async def test_coinrabbit_index_signals_copied_by_copy_trading_bot(skip_on_exchange_proxy_error):
    """
    Index leader on CoinRabbit emits a trading signal after ticker-wise rebalance;
    a separate copier automation fetches that signal and rebalances to match.
    """
    leader_init = _init_action()
    leader_actions = [leader_init, _index_trading_mode_action(leader_init)]
    leader_state = automation_state_dict(resolved_actions(leader_actions))
    leader_state["automation"]["metadata"]["strategy_id"] = functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID
    set_emit_signals_metadata(leader_state, True)
    initial_reference = coinrabbit_util.INITIAL_REFERENCE_HOLDING

    with trading_signal_emission_patches(True) as insert_trading_signal_mock:
        async with octobot_flow.jobs.AutomationJob(leader_state, [], [], {}) as automation_job:
            await automation_job.run()
        after_leader_init = automation_job.dump()

        with coinrabbit_util.patch_coinrabbit_ticker_closes():
            async with octobot_flow.jobs.AutomationJob(after_leader_init, [], [], {}) as automation_job:
                await automation_job.run()

        insert_trading_signal_mock.assert_awaited_once()
        emitted_signal = insert_trading_signal_mock.await_args.args[0]
        assert emitted_signal.strategy_id == functionnal_tests.FUNCTIONAL_TEST_COPY_STRATEGY_ID

    fetch_trading_signals_mock = mock.AsyncMock(return_value=[emitted_signal])
    copier_init = _copier_init_action()
    copy_action = empty_copy_exchange_account_action()
    copier_actions = [copier_init, copy_action]
    copier_state = automation_state_dict(resolved_actions(copier_actions))

    @contextlib.asynccontextmanager
    async def _fake_maybe_authenticator(_self):
        yield mock.MagicMock()

    with contextlib.ExitStack() as patch_stack:
        patch_stack.enter_context(coinrabbit_util.patch_coinrabbit_ticker_closes())
        patch_stack.enter_context(
            mock.patch.object(
                octobot_flow.jobs.AutomationJob,
                "_maybe_authenticator",
                _fake_maybe_authenticator,
            )
        )
        patch_stack.enter_context(
            mock.patch.object(
                community_repository_module.TradingSignalsRepository,
                "fetch_trading_signals",
                fetch_trading_signals_mock,
            )
        )
        copier_auth = octobot_flow.entities.UserAuthentication(
            wallet_address="simulator-coinrabbit-copy-functional-test-wallet",
        )
        async with octobot_flow.jobs.AutomationJob(
            copier_state, [], [], copier_auth
        ) as automation_job:
            await automation_job.run()
        after_copier_init = automation_job.dump()

        async with octobot_flow.jobs.AutomationJob(
            after_copier_init, [], [], copier_auth
        ) as automation_job:
            await automation_job.run()
        after_copy_dump = automation_job.dump()

    fetch_trading_signals_mock.assert_awaited_once()
    portfolio_content = (
        after_copy_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
    )
    for key in coinrabbit_util.EXPECTED_PORTFOLIO_KEYS_AFTER_REBALANCE:
        assert key in portfolio_content, f"missing portfolio key {key!r}: {portfolio_content.keys()}"
    assert portfolio_content["BTC@BTC"]["total"] > 0
    reference_total = portfolio_content.get(coinrabbit_util.REFERENCE_ASSET, {}).get("total", 0)
    assert reference_total < initial_reference
