#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities
import octobot_flow.enums as octobot_flow_enums
import octobot_flow.jobs.automation_runner_job as automation_runner_job_module
import octobot_flow.jobs.exchange_account_job as exchange_account_job_module


def _runner_job() -> automation_runner_job_module.AutomationRunnerJob:
    automation_state = mock.Mock()
    automation_state.has_exchange.return_value = True
    automation_state.exchange_account_details.is_simulated.return_value = False
    automation_state.automation.exchange_account_elements = octobot_flow.entities.ExchangeAccountElements(
        orders=exchange_data_import.OrdersDetails(
            open_orders=[{"symbol": "BTC/USDC"}],
        ),
    )
    return automation_runner_job_module.AutomationRunnerJob(
        automation_state,
        octobot_flow.entities.FetchedDependencies(),
        None,
        0.0,
    )


class TestAutomationRunnerJobFetchTradesAfterExecutionIfNeeded:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "changed_elements, missing_orders, should_fetch",
        [
            pytest.param(
                [octobot_flow_enums.ChangedElements.ORDERS],
                None,
                True,
                id="orders_changed",
            ),
            pytest.param(
                [octobot_flow_enums.ChangedElements.PORTFOLIO],
                None,
                True,
                id="portfolio_changed",
            ),
            pytest.param(
                [],
                [{"symbol": "BTC/USDC"}],
                True,
                id="missing_orders_present",
            ),
            pytest.param(
                [octobot_flow_enums.ChangedElements.POSITIONS],
                None,
                False,
                id="no_fetch_trigger",
            ),
        ],
    )
    @mock.patch.object(
        exchange_account_job_module.ExchangeAccountJob,
        "fetch_trades_from_orders",
        new_callable=mock.AsyncMock,
        return_value=[{"id": "trade-1"}],
    )
    async def test_fetch_trades_after_execution(
        self,
        fetch_trades_from_orders,
        changed_elements,
        missing_orders,
        should_fetch,
    ):
        runner_job = _runner_job()
        if missing_orders is not None:
            runner_job.automation_state.automation.exchange_account_elements.orders.missing_orders = (
                missing_orders
            )

        await runner_job._fetch_trades_after_execution_if_needed(changed_elements)

        if should_fetch:
            fetch_trades_from_orders.assert_awaited_once()
        else:
            fetch_trades_from_orders.assert_not_called()
