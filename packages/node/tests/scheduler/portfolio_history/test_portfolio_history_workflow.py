import datetime
import mock
import pytest

import octobot_node.scheduler.workflows.params as workflow_params_module

from tests.scheduler import temp_dbos_scheduler


@pytest.fixture
def portfolio_history_workflow_module(temp_dbos_scheduler):
    import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow
    return portfolio_history_workflow


class TestPortfolioHistoryScheduleInput:
    def test_get_schedule_input_enables_catch_up_once_on_startup(self, portfolio_history_workflow_module):
        schedule_input = portfolio_history_workflow_module.get_schedule_input()
        assert schedule_input["automatic_backfill"] is False
        assert schedule_input["catch_up_once_on_startup"] is True
        assert schedule_input["queue_name"] == "portfolio_history_queue"


class TestPortfolioHistoryWorkflow:
    @pytest.mark.asyncio
    @mock.patch("octobot_node.scheduler.workflows.portfolio_history_workflow.portfolio_history_executor_module")
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_iterates_wallets_and_delegates(
        self, mock_account_provider, mock_executor, portfolio_history_workflow_module,
    ):
        mock_account_provider.instance.return_value.list_collectable_wallet_ids.return_value = [
            "wallet1", "wallet2",
        ]

        mock_result = mock.MagicMock()
        mock_result.skipped = False
        mock_result.error = None
        mock_executor.run_portfolio_history_collection = mock.AsyncMock(return_value=[mock_result])

        result = await portfolio_history_workflow_module.PortfolioHistoryWorkflow._run_collection(
            datetime.datetime.now(datetime.timezone.utc)
        )
        assert mock_executor.run_portfolio_history_collection.call_count == 2
        assert result["succeeded"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    @mock.patch("octobot_node.scheduler.workflows.portfolio_history_workflow.portfolio_history_executor_module")
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_error_isolation_per_wallet(
        self, mock_account_provider, mock_executor, portfolio_history_workflow_module,
    ):
        mock_account_provider.instance.return_value.list_collectable_wallet_ids.return_value = [
            "wallet1", "wallet2",
        ]
        mock_executor.run_portfolio_history_collection = mock.AsyncMock(
            side_effect=[Exception("fail"), [mock.MagicMock(skipped=False, error=None)]]
        )

        result = await portfolio_history_workflow_module.PortfolioHistoryWorkflow._run_collection(
            datetime.datetime.now(datetime.timezone.utc)
        )
        # wallet1 failed, wallet2 succeeded.
        assert result["succeeded"] == 1

    @pytest.mark.asyncio
    @mock.patch("octobot_node.scheduler.workflows.portfolio_history_workflow.logger")
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_top_level_exception_is_logged_and_does_not_propagate(
        self, mock_account_provider, mock_logger, portfolio_history_workflow_module,
    ):
        mock_account_provider.instance.return_value.list_collectable_wallet_ids.side_effect = (
            AttributeError("missing method")
        )

        result = await portfolio_history_workflow_module.PortfolioHistoryWorkflow._run_collection(
            datetime.datetime.now(datetime.timezone.utc)
        )

        mock_logger.exception.assert_called_once()
        assert result == {"succeeded": 0, "failed": 0, "skipped": 0}

    @pytest.mark.asyncio
    @mock.patch("octobot_node.scheduler.workflows.portfolio_history_workflow.portfolio_history_executor_module")
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_uses_wallet_whitelist_from_params_without_listing_all_wallets(
        self, mock_account_provider, mock_executor, portfolio_history_workflow_module,
    ):
        mock_result = mock.MagicMock()
        mock_result.skipped = False
        mock_result.error = None
        mock_executor.run_portfolio_history_collection = mock.AsyncMock(return_value=[mock_result])
        collection_params = workflow_params_module.PortfolioHistoryCollectionParams(
            wallet_ids=["wallet-user-1"],
            account_ids=["acc-1"],
        )

        result = await portfolio_history_workflow_module.PortfolioHistoryWorkflow._run_collection(
            datetime.datetime.now(datetime.timezone.utc),
            collection_params,
        )

        mock_account_provider.instance.return_value.list_collectable_wallet_ids.assert_not_called()
        mock_executor.run_portfolio_history_collection.assert_awaited_once_with(
            "wallet-user-1",
            account_ids=["acc-1"],
        )
        assert result["succeeded"] == 1
