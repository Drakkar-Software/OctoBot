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
import json
import mock
import time
import typing

import pytest

import octobot_node.models
import octobot_node.scheduler.tasks

from . import grid_workflow_simulator_test_util as grid_sim_util
from tests.scheduler import temp_dbos_scheduler


IMPORTED_OCTOBOT_FLOW_GRID_DEPS = grid_sim_util.IMPORTED_OCTOBOT_FLOW_GRID_DEPS

if IMPORTED_OCTOBOT_FLOW_GRID_DEPS:
    import octobot_flow.entities as octobot_flow_entities
    import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
else:
    octobot_flow_entities = None  # type: ignore
    octobot_flow_repositories_exchange_module = None  # type: ignore


_AUTOMATION_ID = "automation_1"

_T_ENQUEUE_SECONDS = 5.0
_T_GRID_SECONDS = 20.0
_T_STOP_SEND_SECONDS = 5.0
_T_STOP_COMPLETE_SECONDS = 10.0


@pytest.mark.skipif(not IMPORTED_OCTOBOT_FLOW_GRID_DEPS, reason="octobot_flow / grid tentacle deps not available")
class TestTriggerTaskGridDbosIntegration:
    @pytest.mark.asyncio
    async def test_trigger_task_grid_simulator_two_iterations_then_stop(self, temp_dbos_scheduler):
        patched_fetch_tickers = grid_sim_util.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE
        )
        patched_fetch_ohlcv = grid_sim_util.fetch_ohlcv_side_effect_for_close_price(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE
        )

        state_payload = grid_sim_util.build_simple_grid_simulator_state_dict(_AUTOMATION_ID, usdc_initial=1000.0)
        task_content = json.dumps({"state": state_payload})
        # Wallet set on Task.wallet_address — OctoBotActionsJob merges it into auth_details (not from task JSON).
        grid_task = octobot_node.models.Task(
            name="test_grid_trigger_automation",
            content=task_content,
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            wallet_address=grid_sim_util.SIMULATOR_GRID_TEST_COMMUNITY_WALLET_ADDRESS,
        )

        # The only mocks are symbol prices to avoid side effects; everything else runs on the target environment.
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
        ):
            try:
                await asyncio.wait_for(
                    octobot_node.scheduler.tasks.trigger_task(grid_task),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("trigger_task timed out enqueueing automation workflow") from exc

            # Step 1 — wait until the simulator grid exposes the ladder (2 buys, 2 sells) and one optimisation trade.
            grid_deadline = time.monotonic() + _T_GRID_SECONDS
            automation_reader_matching: typing.Any = None
            while time.monotonic() < grid_deadline:
                workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
                grid_predicate_met = False
                for workflow_row in workflow_rows:
                    if grid_sim_util.workflows_util_module.get_automation_id(workflow_row) != _AUTOMATION_ID:
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

            elems_after_grid = automation_reader_matching.state.automation.exchange_account_elements
            buys_grid, sells_grid, trades_grid = grid_sim_util.buy_sell_trade_counts_from_exchange_elements(
                elems_after_grid
            )
            assert grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(buys_grid, sells_grid, trades_grid)

            stop_priority_action = {
                "id": "action_stop_priority",
                "dsl_script": "stop_automation()",
            }
            try:
                await asyncio.wait_for(
                    octobot_node.scheduler.tasks.send_actions_to_automation(
                        [stop_priority_action], _AUTOMATION_ID
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("send_actions_to_automation timed out") from exc

            # Step 2 — wait for terminate output with priority stop; expect preserved ladder and trade counts.
            final_output_text = await grid_sim_util.wait_for_stop_success_output(
                temp_dbos_scheduler,
                _AUTOMATION_ID,
                _T_STOP_COMPLETE_SECONDS,
            )

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
