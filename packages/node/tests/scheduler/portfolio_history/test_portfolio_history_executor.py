import mock
import pytest

import octobot_node.scheduler.portfolio_history.portfolio_history_executor as portfolio_history_executor_module


class TestRunPortfolioHistoryCollectionAccountFilter:
    @pytest.mark.asyncio
    @mock.patch.object(
        portfolio_history_executor_module,
        "_build_context_for_account",
        return_value=None,
    )
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_filters_accounts_when_account_ids_set(
        self, mock_account_provider, mock_build_context,
    ):
        account_one = mock.MagicMock()
        account_one.id = "acc-1"
        account_two = mock.MagicMock()
        account_two.id = "acc-2"
        mock_account_provider.instance.return_value.list_items.return_value = [
            account_one,
            account_two,
        ]

        results = await portfolio_history_executor_module.run_portfolio_history_collection(
            "wallet-user-1",
            account_ids=["acc-2"],
        )

        assert results == []
        mock_account_provider.instance.return_value.list_items.assert_called_once_with(
            "wallet-user-1",
        )
        mock_build_context.assert_called_once_with("wallet-user-1", account_two)
