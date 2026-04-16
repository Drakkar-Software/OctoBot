import pytest
import logging
import json
import mock
import decimal
import copy
import time

import octobot_copy.entities as copy_entities
import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_trading.dsl as trading_dsl
import octobot_trading.exchanges.exchange_channels as exchange_channels
import octobot_copy.rebalancing as rebalancing
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums
import octobot_copy.constants as copy_constants

import tentacles.Trading.Mode.index_trading_mode as index_trading_mode

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    assert_emitted_signal_account_allocation_ratios,
    automation_state_dict,
    copy_exchange_account_action,
    current_time,
    resolved_actions,
    set_emit_signals_metadata,
    trading_signal_emission_patches,
)

import octobot_copy.enums as rebalancer_enums

index_content = [
    {
        rebalancer_enums.DistributionKeys.NAME: "BTC",
        rebalancer_enums.DistributionKeys.VALUE: 1,
    },
    {
        rebalancer_enums.DistributionKeys.NAME: "ETH",
        rebalancer_enums.DistributionKeys.VALUE: 1,
    },
]

index_content_btc_sol = [
    {
        rebalancer_enums.DistributionKeys.NAME: "BTC",
        rebalancer_enums.DistributionKeys.VALUE: 1,
    },
    {
        rebalancer_enums.DistributionKeys.NAME: "SOL",
        rebalancer_enums.DistributionKeys.VALUE: 1,
    },
]


def _replace_index_trading_mode_dsl_in_dump(automation_dump: dict, new_index_content: list) -> None:
    for action in automation_dump["automation"]["actions_dag"]["actions"]:
        if action.get("id") != "action_1":
            continue
        action["dsl_script"] = (
            f"index_trading_mode(index_content={json.dumps(new_index_content)}, rebalance_trigger_min_percent=5)"
        )
        action.pop("resolved_dsl_script", None)
        return
    raise AssertionError("action_1 not found in automation dump")


def index_trading_mode_action(dependency_action: dict):
    return {
        "id": "action_1",
        "dsl_script": f"index_trading_mode(index_content={json.dumps(index_content)}, rebalance_trigger_min_percent=5)",
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


def _assert_trading_signal_account_fields(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    """
    Matches octobot_flow.logic.actions.account_copy_util.reference_exchange_elements_to_account:
    updated_at from time.time(), orders from exchange elements' open_orders (empty in these tests),
    positions and historical_snapshots default to empty (not set by the helper).
    """
    account = trading_signal.account
    assert isinstance(account.updated_at, float)
    assert current_time <= account.updated_at <= time.time()
    assert account.orders == []
    assert account.positions == []
    assert account.historical_snapshots == []


def _assert_trading_signal_btc_eth_usdt_index_portfolio(
    trading_signal: octobot_flow.entities.TradingSignal,
    *,
    allow_zero_ratio_assets: frozenset[str] = frozenset(),
) -> None:
    content = trading_signal.account.content
    assert list(sorted(content.keys())) == ["BTC", "ETH", "USDT"]
    assert 0 < float(content["USDT"][common_constants.PORTFOLIO_AVAILABLE]) < 5
    assert 0.1 < float(content["ETH"][common_constants.PORTFOLIO_AVAILABLE]) < 0.4
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_AVAILABLE]) < 0.01
    assert 0 < float(content["USDT"][common_constants.PORTFOLIO_TOTAL]) < 5
    assert 0.1 < float(content["ETH"][common_constants.PORTFOLIO_TOTAL]) < 0.4
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_TOTAL]) < 0.01
    assert_emitted_signal_account_allocation_ratios(content, allow_zero_ratio_assets=allow_zero_ratio_assets)
    _assert_trading_signal_account_fields(trading_signal)


def _assert_trading_signal_btc_eth_sol_usdt_after_btc_sol_rebalance(
    trading_signal: octobot_flow.entities.TradingSignal,
    *,
    allow_zero_ratio_assets: frozenset[str] = frozenset(),
) -> None:
    content = trading_signal.account.content
    assert list(sorted(content.keys())) == ["BTC", "ETH", "SOL", "USDT"]
    assert 0 < float(content["USDT"][common_constants.PORTFOLIO_AVAILABLE]) < 5
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_AVAILABLE]) < 0.02
    assert 0.5 < float(content["SOL"][common_constants.PORTFOLIO_AVAILABLE]) < 20
    assert 0 < float(content["ETH"][common_constants.PORTFOLIO_AVAILABLE]) < 0.001
    assert 0 < float(content["USDT"][common_constants.PORTFOLIO_TOTAL]) < 5
    assert 0.001 < float(content["BTC"][common_constants.PORTFOLIO_TOTAL]) < 0.02
    assert 0.5 < float(content["SOL"][common_constants.PORTFOLIO_TOTAL]) < 20
    assert 0 < float(content["ETH"][common_constants.PORTFOLIO_TOTAL]) < 0.001
    assert_emitted_signal_account_allocation_ratios(
        content,
        allow_negligible_ratio_assets=allow_zero_ratio_assets,
    )
    _assert_trading_signal_account_fields(trading_signal)


@pytest.fixture
def index_reference_account():
    return copy_entities.Account(
        updated_at=time.time(),
        content={
            "BTC": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("1"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
            "ETH": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("20"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("20"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.4999"),
            },
            "USDT": {
                common_constants.PORTFOLIO_TOTAL: decimal.Decimal("10"),
                common_constants.PORTFOLIO_AVAILABLE: decimal.Decimal("10"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.0001"),
            },
        },
        orders=[],
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
                            "USDT": {
                                "available": 1000.0,
                                "total": 1000.0,
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
                    "unit": "USDT",
                },
            },
        },
    }


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_index_init_from_empty_state(init_action: dict, emit_signals: bool):
    all_actions = [init_action, index_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    set_emit_signals_metadata(automation_state, emit_signals)

    with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
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

        # 2. run index trading mode action
        async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
            await automation_job.run()
        after_initial_rebalance_execution_dump = automation_job.dump()
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
        assert after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        one_hour = common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR] * common_constants.MINUTE_TO_SECONDS
        allowed_execution_time = 20
        schedule_delay = (
            after_initial_rebalance_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time
        # check portfolio content
        after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_execution_dump, dict)
        assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01
        logging.getLogger("test_update_simulated_basket_bot").info(f"after_execution_portfolio_content: {after_initial_rebalance_portfolio_content}")

        after_initial_rebalance_reference_account_portfolio_content = after_initial_rebalance_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_rebalance_reference_account_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_reference_account_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_reference_account_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_reference_account_portfolio_content["BTC"]["available"] < 0.01

        # 3. trigger again: nothing to do
        async with octobot_flow.AutomationJob(after_initial_rebalance_execution_dump, [], {}) as automation_job:
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
                # action is reset: this is a trading mode action: it will be executed again at the next execution
                assert action.executed_at is None
                assert isinstance(action.previous_execution_result, dict)

        # ensure schedule delay is the same as the first call
        schedule_delay = (
            after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

        # portfolio already follows the index content: ensure portfolio content is the same as the first call
        after_second_call_portfolio_content = after_second_call_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert after_second_call_portfolio_content == after_initial_rebalance_portfolio_content
        after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"]["exchange_account_elements"][
            "portfolio"
        ]["content"]
        assert after_second_call_reference_account_portfolio_content == after_initial_rebalance_reference_account_portfolio_content

        if emit_signals:
            assert insert_trading_signal_mock.await_count == 2
            for await_args in insert_trading_signal_mock.await_args_list:
                trading_signal_arg = await_args.args[0]
                _assert_trading_signal_btc_eth_usdt_index_portfolio(trading_signal_arg)
        else:
            insert_trading_signal_mock.assert_not_awaited()


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_index_rebalance_after_index_content_switch_btc_eth_to_btc_sol(
    init_action: dict,
    emit_signals: bool,
):
    all_actions = [init_action, index_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    set_emit_signals_metadata(automation_state, emit_signals)

    with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
        # 1. run init action
        async with octobot_flow.AutomationJob(automation_state, [], {}) as automation_job:
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

        # 2. first index run: BTC + ETH (base index_content)
        async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
            await automation_job.run()
        after_btc_eth_execution_dump = automation_job.dump()

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

        after_btc_eth_portfolio = after_btc_eth_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert list(sorted(after_btc_eth_portfolio.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_btc_eth_portfolio["USDT"]["available"] < 5
        assert 0.1 < after_btc_eth_portfolio["ETH"]["available"] < 0.4
        assert 0.001 < after_btc_eth_portfolio["BTC"]["available"] < 0.01
        assert "SOL" not in after_btc_eth_portfolio

        after_btc_eth_reference_portfolio = after_btc_eth_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert list(sorted(after_btc_eth_reference_portfolio.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_btc_eth_reference_portfolio["USDT"]["available"] < 5
        assert 0.1 < after_btc_eth_reference_portfolio["ETH"]["available"] < 0.4
        assert 0.001 < after_btc_eth_reference_portfolio["BTC"]["available"] < 0.01
        assert "SOL" not in after_btc_eth_reference_portfolio

        one_hour = common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR] * common_constants.MINUTE_TO_SECONDS
        allowed_execution_time = 20

        # 3. switch index definition to BTC + SOL and rebalance
        dump_after_index_switch = copy.deepcopy(after_btc_eth_execution_dump)
        _replace_index_trading_mode_dsl_in_dump(dump_after_index_switch, index_content_btc_sol)
        async with octobot_flow.AutomationJob(dump_after_index_switch, [], {}) as automation_job:
            await automation_job.run()
        after_btc_sol_execution_dump = automation_job.dump()

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

        # portfolio should be updated to BTC + SOL, ETH should be removed
        after_btc_sol_portfolio = after_btc_sol_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert list(sorted(after_btc_sol_portfolio.keys())) == ["BTC", "ETH", "SOL", "USDT"]
        assert 0 < after_btc_sol_portfolio["USDT"]["available"] < 5
        assert 0.001 < after_btc_sol_portfolio["BTC"]["available"] < 0.02
        assert 0.5 < after_btc_sol_portfolio["SOL"]["available"] < 20
        assert 0 < after_btc_sol_portfolio["ETH"]["available"] < 0.001 # sold close to all ETH

        after_btc_sol_reference_portfolio = after_btc_sol_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert list(sorted(after_btc_sol_reference_portfolio.keys())) == ["BTC", "ETH", "SOL", "USDT"]
        assert 0 < after_btc_sol_reference_portfolio["USDT"]["available"] < 5
        assert 0.001 < after_btc_sol_reference_portfolio["BTC"]["available"] < 0.02
        assert 0.5 < after_btc_sol_reference_portfolio["SOL"]["available"] < 20
        assert 0 < after_btc_sol_reference_portfolio["ETH"]["available"] < 0.001  # sold close to all ETH

        schedule_delay = (
            after_btc_sol_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_btc_sol_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

        # 4. trigger again: portfolio already matches BTC + SOL index
        async with octobot_flow.AutomationJob(after_btc_sol_execution_dump, [], {}) as automation_job:
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

        after_second_call_portfolio = after_second_call_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert after_second_call_portfolio == after_btc_sol_portfolio
        after_second_call_reference_portfolio = after_second_call_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert after_second_call_reference_portfolio == after_btc_sol_reference_portfolio

        if emit_signals:
            assert insert_trading_signal_mock.await_count == 3
            _assert_trading_signal_btc_eth_usdt_index_portfolio(insert_trading_signal_mock.await_args_list[0].args[0])
            _assert_trading_signal_btc_eth_sol_usdt_after_btc_sol_rebalance(insert_trading_signal_mock.await_args_list[1].args[0])
            _assert_trading_signal_btc_eth_sol_usdt_after_btc_sol_rebalance(insert_trading_signal_mock.await_args_list[2].args[0])
        else:
            insert_trading_signal_mock.assert_not_awaited()


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_index_with_added_traded_pairs(init_action: dict, emit_signals: bool):
    all_actions = [init_action, index_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    set_emit_signals_metadata(automation_state, emit_signals)

    with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
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

        # 2. run index trading mode action
        with (
            mock.patch.object(
                index_trading_mode.IndexTradingMode, "get_dsl_dependencies",
                # ETH/USDT won't be identified as dependency but is in index config: it will be added dynamically
                return_value=[trading_dsl.SymbolDependency(symbol="BTC/USDT")]
            ) as mock_get_dsl_dependencies,
            mock.patch.object(
                rebalancing.BaseRebalanceActionsPlanner, "_get_supported_distribution",
                return_value=rebalancing.get_uniform_distribution(["BTC", "ETH"])
            ) as mock_get_supported_distribution,
            mock.patch.object(
                rebalancing.BaseRebalanceActionsPlanner, "_get_filtered_traded_coins",
                return_value=["BTC", "ETH"]
            ) as mock_get_filtered_traded_coins,
            mock.patch.object(
                exchange_channels, "create_minimal_dynamic_symbols_env_producers_if_needed",
                mock.AsyncMock(wraps=exchange_channels.create_minimal_dynamic_symbols_env_producers_if_needed)
            ) as mock_create_minimal_dynamic_symbols_env_producers_if_needed,
        ):
            async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
                await automation_job.run()
            assert mock_get_dsl_dependencies.call_count > 1
            # ensure the ETH/USDC pairs is really added as a dynamic symbol
            mock_create_minimal_dynamic_symbols_env_producers_if_needed.assert_awaited_once()
            expected_call_count = 1
            assert mock_get_supported_distribution.call_count == expected_call_count
            assert mock_get_filtered_traded_coins.call_count == expected_call_count
            after_initial_rebalance_execution_dump = automation_job.dump()
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

        after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_execution_dump, dict)
        assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01

        after_initial_rebalance_reference_account_portfolio_content = after_initial_rebalance_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_rebalance_reference_account_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_reference_account_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_reference_account_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_reference_account_portfolio_content["BTC"]["available"] < 0.01

        if emit_signals:
            assert insert_trading_signal_mock.await_count == 1
            _assert_trading_signal_btc_eth_usdt_index_portfolio(
                insert_trading_signal_mock.await_args_list[0].args[0],
                allow_zero_ratio_assets=frozenset({"ETH"}),
            )
        else:
            insert_trading_signal_mock.assert_not_awaited()


@pytest.mark.parametrize("emit_signals", [False, True])
@pytest.mark.asyncio
async def test_simulator_copy_index(
    init_action: dict,
    index_reference_account: copy_entities.Account,
    emit_signals: bool,
):
    reference_market = init_action["config"]["exchange_account_details"]["portfolio"]["unit"]
    all_actions = [
        init_action,
        copy_exchange_account_action(reference_market, index_reference_account)
    ]
    automation_state = automation_state_dict(resolved_actions(all_actions))
    set_emit_signals_metadata(automation_state, emit_signals)

    with trading_signal_emission_patches(emit_signals) as insert_trading_signal_mock:
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

        # 2. run copy exchange account action
        async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
            await automation_job.run()
        after_initial_rebalance_execution_dump = automation_job.dump()
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

        # scheduled next execution time 4h after the current execution (4h is the default time when unspecified when copying an account)
        assert after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        allowed_execution_time = 20
        schedule_delay = (
            after_initial_rebalance_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert copy_constants.DEFAULT_COPY_WAITING_TIME - allowed_execution_time < schedule_delay < copy_constants.DEFAULT_COPY_WAITING_TIME + allowed_execution_time
        # check portfolio content
        after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_execution_dump, dict)
        assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01
        logging.getLogger("test_update_simulated_basket_bot").info(f"after_execution_portfolio_content: {after_initial_rebalance_portfolio_content}")

        after_initial_rebalance_reference_account_portfolio_content = after_initial_rebalance_execution_dump["automation"][
            "exchange_account_elements"
        ]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_rebalance_reference_account_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_reference_account_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_reference_account_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_reference_account_portfolio_content["BTC"]["available"] < 0.01

        # 3. trigger again: nothing to do
        async with octobot_flow.AutomationJob(after_initial_rebalance_execution_dump, [], {}) as automation_job:
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
                # action is reset: this is a trading mode action: it will be executed again at the next execution
                assert action.executed_at is None
                assert isinstance(action.previous_execution_result, dict)

        # ensure schedule delay is the same as the first call
        schedule_delay = (
            after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
            - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
        )
        assert copy_constants.DEFAULT_COPY_WAITING_TIME - allowed_execution_time < schedule_delay < copy_constants.DEFAULT_COPY_WAITING_TIME + allowed_execution_time

        # portfolio already follows the index content: ensure portfolio content is the same as the first call
        after_second_call_portfolio_content = after_second_call_execution_dump["automation"]["exchange_account_elements"]["portfolio"]["content"]
        assert after_second_call_portfolio_content == after_initial_rebalance_portfolio_content
        after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"]["exchange_account_elements"][
            "portfolio"
        ]["content"]
        assert after_second_call_reference_account_portfolio_content == after_initial_rebalance_reference_account_portfolio_content

        if emit_signals:
            assert insert_trading_signal_mock.await_count == 2
            for await_args in insert_trading_signal_mock.await_args_list:
                _assert_trading_signal_btc_eth_usdt_index_portfolio(await_args.args[0])
        else:
            insert_trading_signal_mock.assert_not_awaited()
