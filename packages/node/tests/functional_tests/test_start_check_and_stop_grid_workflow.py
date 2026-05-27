#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at your
#  option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see https://www.gnu.org/licenses/.

import asyncio
import datetime
import mock
import time
import typing

import dbos
import pytest

import octobot_protocol.models as octobot_protocol_models

import octobot_node.scheduler

from . import grid_workflow_simulator_test_util as grid_sim_util
from tests.scheduler import temp_dbos_scheduler


IMPORTED_OCTOBOT_FLOW_GRID_DEPS = grid_sim_util.IMPORTED_OCTOBOT_FLOW_GRID_DEPS

if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    import octobot_flow.entities as octobot_flow_entities
    import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
else:
    octobot_flow_entities = None  # type: ignore
    octobot_flow_repositories_exchange_module = None  # type: ignore


_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = 20.0
_T_SIGNAL_SECONDS = 5.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 10.0
# Fast poll after stop/signal send; protocol status may flip RUNNING→COMPLETED quickly on CI.
_POST_STOP_PROTOCOL_POLL_SECONDS = 0.05

_GRID_ACCOUNT_ID = "functional_grid_account"
_GRID_AUTOMATION_DISPLAY_NAME = "test_grid_trigger_automation"


def _workflow_row_id_matches_user_action_selector_created_automation_id(
    *,
    workflow_row_id: str,
    user_action_selector_created_automation_id: str | None,
) -> None:
    assert user_action_selector_created_automation_id
    assert (
        workflow_row_id == user_action_selector_created_automation_id
        or workflow_row_id.startswith(f"{user_action_selector_created_automation_id}_")
    ), (
        f"workflow row id {workflow_row_id!r} should equal or extend user action selector created_automation_id "
        f"{user_action_selector_created_automation_id!r}"
    )


def _merge_user_actions_latest_per_id(
    user_actions: list[octobot_protocol_models.UserAction],
) -> dict[str, octobot_protocol_models.UserAction]:
    grouped: dict[str, list[octobot_protocol_models.UserAction]] = {}
    for user_action in user_actions:
        grouped.setdefault(user_action.id, []).append(user_action)
    min_utc = datetime.datetime.min.replace(tzinfo=datetime.UTC)

    def activity_stamp(user_action: octobot_protocol_models.UserAction) -> datetime.datetime:
        stamp = user_action.updated_at or user_action.created_at
        if stamp is None:
            return min_utc
        if stamp.tzinfo is None:
            return stamp.replace(tzinfo=datetime.UTC)
        return stamp

    return {
        user_action_id: max(group, key=activity_stamp)
        for user_action_id, group in grouped.items()
    }


async def _assert_user_action_selector_completed_automation_create(
    *,
    user_action_id: str,
    expected_workflow_id: str | None,
    wallet_address: str = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
) -> None:
    """Assert create user action is COMPLETED and optionally ties to a workflow row id."""
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
    by_id = _merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == octobot_protocol_models.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
    assert inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None
    if expected_workflow_id is not None:
        _workflow_row_id_matches_user_action_selector_created_automation_id(
            workflow_row_id=expected_workflow_id,
            user_action_selector_created_automation_id=inner.created_automation_id,
        )
    else:
        # ensure created_automation_id is set
        assert inner.created_automation_id
        assert len(inner.created_automation_id) > 0


async def _get_created_automation_id_from_user_action(
    *,
    user_action_id: str,
    wallet_address: str = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
) -> str:
    """Return parent workflow id from a completed create-automation user action result."""
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
    by_id = _merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
    assert inner.created_automation_id
    return inner.created_automation_id


async def _assert_user_action_selector_completed_automation_stop(
    *,
    user_action_id: str,
    wallet_address: str = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
) -> None:
    """Assert stop user action is COMPLETED with no automation result error."""
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
    by_id = _merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == octobot_protocol_models.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
    assert inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None


async def _assert_user_action_selector_completed_automation_signal(
    *,
    user_action_id: str,
    wallet_address: str = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
) -> None:
    """Assert signal user action is COMPLETED with no automation result error."""
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(wallet_address)
    by_id = _merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == octobot_protocol_models.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, octobot_protocol_models.AutomationActionResult)
    assert inner.result_type == octobot_protocol_models.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None


@pytest.mark.skipif(not IMPORTED_OCTOBOT_FLOW_GRID_DEPS, reason="octobot_flow / grid tentacle deps not available")
class TestTriggerTaskGridDbosIntegration:
    @pytest.mark.asyncio
    async def test_trigger_task_grid_simulator_two_iterations_then_stop(self, temp_dbos_scheduler):
        """
        End-to-end grid automation lifecycle on the simulator exchange.

        Flow: create automation → wait for baseline grid → forced-trigger signal (fixed price,
        no new orders) → stop automation → verify clean termination with preserved ladder.
        """
        # Step 0 — Pin BTC/USDC close so grid placement and forced iteration stay deterministic.
        patched_fetch_tickers = grid_sim_util.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE
        )
        patched_fetch_ohlcv = grid_sim_util.fetch_ohlcv_side_effect_for_close_price(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE
        )
        wallet_address = grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS
        protocol_account = grid_sim_util.protocol_account_for_functional(
            account_id=_GRID_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Start/stop functional grid account",
        )
        create_user_action = grid_sim_util.build_create_grid_user_action(
            account_id=_GRID_ACCOUNT_ID,
            name=_GRID_AUTOMATION_DISPLAY_NAME,
        )

        # Step 0 (continued) — Mock only market data and sync providers; DBOS scheduler and flow run for real.
        with (
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
                        return_value=grid_sim_util.protocol_exchange_config_for_grid_functional(),
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
        ):
            # Step 1 — Enqueue AUTOMATION_CREATE user action; expect a COMPLETED create result and a running workflow.
            try:
                await asyncio.wait_for(
                    grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        create_user_action,
                        wallet_address,
                    ),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action timed out enqueueing automation workflow") from exc

            await _assert_user_action_selector_completed_automation_create(
                user_action_id=create_user_action.id,
                expected_workflow_id=None,
            )

            # Step 2 — Poll until the simulator grid reaches baseline: 2 open buys, 2 open sells, 1 trade.
            grid_deadline = time.monotonic() + _T_GRID_SECONDS
            automation_reader_matching: typing.Any = None
            workflow_row_matching: typing.Any = None
            metadata_automation_id = create_user_action.id
            while time.monotonic() < grid_deadline:
                workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                grid_predicate_met = False
                for workflow_row in workflow_rows:
                    workflow_automation_id = grid_sim_util.workflows_util_module.get_automation_id(workflow_row)
                    if workflow_automation_id != metadata_automation_id:
                        continue
                    state_reader = grid_sim_util.workflows_util_module.get_automation_state_reader(workflow_row)
                    if state_reader is None:
                        continue
                    elements = state_reader.state.automation.exchange_account_elements
                    buy_orders, sell_orders, trade_bucket = (
                        grid_sim_util.buy_sell_trade_counts_from_exchange_elements(elements)
                    )
                    automation_reader_matching = automation_reader_matching or state_reader
                    if grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                        buy_orders,
                        sell_orders,
                        trade_bucket,
                    ):
                        automation_reader_matching = state_reader
                        workflow_row_matching = workflow_row
                        grid_predicate_met = True
                        break
                if grid_predicate_met:
                    break
                await asyncio.sleep(grid_sim_util.DEFAULT_GRID_WORKFLOW_POLL_INTERVAL_SECONDS)
            else:
                if automation_reader_matching is None:
                    pytest.fail(
                        "Timed out before any readable automation workflow state existed for automation_1"
                    )
                last_buys, last_sells, last_trades = (
                    grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                        automation_reader_matching.state.automation.exchange_account_elements
                    )
                )
                pytest.fail(
                    f"Timed out waiting for grid state (wanted 2 buy, 2 sell, 1 trade); "
                    f"last seen buys={last_buys}, sells={last_sells}, trades={last_trades}"
                )

            # Step 2 (continued) — Assert baseline counts and that protocol AutomationState mirrors exchange elements.
            elems_after_grid = automation_reader_matching.state.automation.exchange_account_elements
            buys_grid, sells_grid, trades_grid = grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                elems_after_grid
            )
            assert grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(buys_grid, sells_grid, trades_grid)

            assert workflow_row_matching is not None
            await _assert_user_action_selector_completed_automation_create(
                user_action_id=create_user_action.id,
                expected_workflow_id=workflow_row_matching.workflow_id,
            )
            protocol_state_after_step1 = await grid_sim_util.load_protocol_automation_state_for_workflow(
                grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
                workflow_row_matching,
            )
            grid_sim_util.assert_protocol_automation_matches_exchange_account_elements(
                protocol_state_after_step1,
                elems_after_grid,
                expected_automation_task_status=octobot_protocol_models.TaskStatus.RUNNING,
                expected_exchange_account_id=_GRID_ACCOUNT_ID,
            )
            grid_sim_util.assert_protocol_automation_metadata_name(
                protocol_state_after_step1,
                _GRID_AUTOMATION_DISPLAY_NAME,
            )

            # Step 3 — Enqueue AUTOMATION_SIGNAL (forced_trigger); exercises SignalAutomationActionExecutor end-to-end.
            parent_automation_id = await _get_created_automation_id_from_user_action(
                user_action_id=create_user_action.id,
                wallet_address=wallet_address,
            )
            signal_user_action = grid_sim_util.build_forced_trigger_signal_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-signal-forced-grid-functional",
            )
            try:
                await asyncio.wait_for(
                    grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        signal_user_action,
                        wallet_address,
                    ),
                    timeout=_T_SIGNAL_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action forced-trigger signal timed out") from exc

            await _assert_user_action_selector_completed_automation_signal(
                user_action_id=signal_user_action.id,
            )

            # Step 3 (continued) — At fixed price, forced iteration must not add orders; ladder stays 2/2/1 and RUNNING.
            workflow_row_after_signal: typing.Any = None
            elements_after_signal: typing.Any = None
            signal_deadline = time.monotonic() + _T_SIGNAL_SECONDS
            while time.monotonic() < signal_deadline:
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async():
                    if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_signal = grid_sim_util.workflows_util_module.get_automation_state_reader(
                        workflow_row
                    )
                    if reader_after_signal is None:
                        continue
                    candidate_elements = reader_after_signal.state.automation.exchange_account_elements
                    candidate_buys, candidate_sells, candidate_trades = (
                        grid_sim_util.buy_sell_trade_counts_from_exchange_elements(candidate_elements)
                    )
                    if not grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                        candidate_buys,
                        candidate_sells,
                        candidate_trades,
                    ):
                        continue
                    workflow_row_after_signal = workflow_row
                    elements_after_signal = candidate_elements
                    break
                if workflow_row_after_signal is not None:
                    break
                await asyncio.sleep(_POST_STOP_PROTOCOL_POLL_SECONDS)
            assert workflow_row_after_signal is not None
            protocol_state_after_signal = await grid_sim_util.load_protocol_automation_state_for_workflow(
                grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
                workflow_row_after_signal,
            )
            grid_sim_util.assert_protocol_automation_matches_exchange_account_elements(
                protocol_state_after_signal,
                elements_after_signal,
                expected_automation_task_status=octobot_protocol_models.TaskStatus.RUNNING,
            )
            grid_sim_util.assert_protocol_automation_metadata_name(
                protocol_state_after_signal,
                _GRID_AUTOMATION_DISPLAY_NAME,
            )

            # Step 4 — Enqueue AUTOMATION_STOP; stop payload targets the parent workflow id (UUID prefix).
            stop_user_action = grid_sim_util.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id="ua-stop-grid-functional",
            )
            try:
                await asyncio.wait_for(
                    grid_sim_util.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        stop_user_action,
                        wallet_address,
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action stop timed out") from exc

            await _assert_user_action_selector_completed_automation_stop(user_action_id=stop_user_action.id)

            # Step 4 (continued) — Right after stop is sent, ladder counts should still match baseline while
            # protocol status may already be RUNNING or COMPLETED depending on CI timing.
            workflow_row_after_stop_send: typing.Any = None
            elements_after_stop_send: typing.Any = None
            stop_send_deadline = time.monotonic() + _T_STOP_SEND_SECONDS
            while time.monotonic() < stop_send_deadline:
                for workflow_row in sorted(
                    await temp_dbos_scheduler.INSTANCE.list_workflows_async(),
                    key=lambda workflow_status: workflow_status.updated_at or 0,
                    reverse=True,
                ):
                    if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                        continue
                    reader_after_send = grid_sim_util.workflows_util_module.get_automation_state_reader(workflow_row)
                    if reader_after_send is None:
                        continue
                    candidate_elements = reader_after_send.state.automation.exchange_account_elements
                    candidate_buys, candidate_sells, candidate_trades = (
                        grid_sim_util.buy_sell_trade_counts_from_exchange_elements(candidate_elements)
                    )
                    if not grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                        candidate_buys,
                        candidate_sells,
                        candidate_trades,
                    ):
                        continue
                    workflow_row_after_stop_send = workflow_row
                    elements_after_stop_send = candidate_elements
                    break
                if workflow_row_after_stop_send is not None:
                    break
                await asyncio.sleep(_POST_STOP_PROTOCOL_POLL_SECONDS)
            assert workflow_row_after_stop_send is not None
            protocol_state_after_stop_send = await grid_sim_util.load_protocol_automation_state_for_workflow(
                grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
                workflow_row_after_stop_send,
            )
            observed_protocol_status = protocol_state_after_stop_send.status
            acceptable_protocol_statuses = (
                octobot_protocol_models.TaskStatus.RUNNING,
                octobot_protocol_models.TaskStatus.COMPLETED,
            )
            if observed_protocol_status not in acceptable_protocol_statuses:
                pytest.fail(
                    f"Unexpected AutomationState.status after stop send: {observed_protocol_status.value!r}; "
                    f"expected one of {[task_status.value for task_status in acceptable_protocol_statuses]}"
                )
            grid_sim_util.assert_protocol_automation_matches_exchange_account_elements(
                protocol_state_after_stop_send,
                elements_after_stop_send,
                expected_automation_task_status=observed_protocol_status,
                expected_exchange_account_id=_GRID_ACCOUNT_ID,
            )
            grid_sim_util.assert_protocol_automation_metadata_name(
                protocol_state_after_stop_send,
                _GRID_AUTOMATION_DISPLAY_NAME,
            )

            # Step 5 — Wait for the automation workflow to finish with post_actions.stop_automation set.
            final_output_text = await grid_sim_util.wait_for_stop_success_output(
                temp_dbos_scheduler,
                metadata_automation_id,
                _T_STOP_COMPLETE_SECONDS,
            )

            # Step 5 (continued) — Final job output: no error, stop flag, preserved 2/2/1 ladder, wallet in auth.
            assert final_output_text is not None
            parsed_final = grid_sim_util.parse_automation_workflow_output(final_output_text)
            assert parsed_final.error is None
            final_job = grid_sim_util.job_description_dict_from_output(parsed_final)
            # OctoBotActionsJobDescription serialises only non-default fields (empty params omitted).
            # SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS was merged into auth_details from Task.wallet_address.
            assert set(final_job.keys()) == {"auth_details", "state"}
            final_auth_details = octobot_flow_entities.UserAuthentication.from_dict(
                final_job["auth_details"]
            )
            assert final_auth_details.wallet_address == grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS
            final_automation = final_job["state"]["automation"]
            assert final_automation["post_actions"]["stop_automation"] is True
            final_elements = final_automation["exchange_account_elements"]
            final_buys, final_sells, final_trades = grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                final_elements
            )
            assert grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                final_buys,
                final_sells,
                final_trades,
            )

            # Step 6 — Latest SUCCESS workflow row exposes COMPLETED protocol AutomationState matching final output.
            success_rows = [
                workflow_row
                for workflow_row in await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                if workflow_row.status == dbos.WorkflowStatusString.SUCCESS.value
                and grid_sim_util.workflows_util_module.get_automation_id(workflow_row) == metadata_automation_id
            ]
            assert success_rows, "expected at least one SUCCESS workflow for automation after stop"
            final_workflow_row = max(success_rows, key=lambda workflow_status: workflow_status.updated_at or 0)
            protocol_state_final = await grid_sim_util.load_protocol_automation_state_for_workflow(
                grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
                final_workflow_row,
            )
            grid_sim_util.assert_protocol_automation_matches_exchange_account_elements(
                protocol_state_final,
                final_elements,
                expected_automation_task_status=octobot_protocol_models.TaskStatus.COMPLETED,
                expected_exchange_account_id=_GRID_ACCOUNT_ID,
            )
            grid_sim_util.assert_protocol_automation_metadata_name(
                protocol_state_final,
                _GRID_AUTOMATION_DISPLAY_NAME,
            )
