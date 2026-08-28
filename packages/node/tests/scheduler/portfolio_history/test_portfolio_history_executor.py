import mock
import pytest

import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module
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


class TestRunPortfolioHistoryCollectionTradeSymbolLoader:
    @pytest.mark.asyncio
    @mock.patch(
        "octobot_node.scheduler.portfolio_history.portfolio_history_executor.trade_symbols_resolver_module.resolve_trade_symbols",
        new_callable=mock.AsyncMock,
        return_value=[],
    )
    @mock.patch(
        "octobot_node.scheduler.portfolio_history.portfolio_history_executor.automation_states_loader_module.load_wallet_automation_states_for_trade_symbols",
        new_callable=mock.AsyncMock,
    )
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_uses_trade_symbol_loader_not_full_wallet_loader(
        self,
        mock_account_provider,
        load_for_trade_symbols_mock,
        resolve_trade_symbols_mock,
    ):
        account = mock.MagicMock()
        account.id = "acc-1"
        mock_account_provider.instance.return_value.list_items.return_value = [account]
        wallet_automation_states = automation_states_loader_module.WalletAutomationStates(
            protocol_states=[],
            flow_states_by_id={},
        )
        load_for_trade_symbols_mock.return_value = wallet_automation_states

        with mock.patch.object(
            portfolio_history_executor_module,
            "_build_context_for_account",
            return_value=mock.MagicMock(),
        ), mock.patch(
            "octobot_flow.jobs.portfolio_history_job.PortfolioHistoryJob",
        ) as portfolio_history_job_class_mock:
            portfolio_history_job_class_mock.return_value.run = mock.AsyncMock(return_value=[])
            await portfolio_history_executor_module.run_portfolio_history_collection("wallet-user-1")

        load_for_trade_symbols_mock.assert_awaited_once_with("wallet-user-1")
        resolve_trade_symbols_mock.assert_awaited_once()
