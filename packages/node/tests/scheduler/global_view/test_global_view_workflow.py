#  Drakkar-Software OctoBot-Node

import datetime

import mock
import pytest

from tests.scheduler import temp_dbos_scheduler


@pytest.mark.asyncio
class TestGlobalViewRefreshWorkflowRunGlobalViewRefresh:
    @pytest.fixture
    def global_view_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module_loaded

        yield global_view_workflow_module_loaded

    async def test_refreshes_all_wallets_and_accounts_in_parallel_per_wallet(
        self,
        global_view_workflow_module,
    ):
        wallet_ids = ["wallet-a"]
        accounts = [mock.Mock(id="acc-1"), mock.Mock(id="acc-2")]
        account_provider = mock.Mock()
        account_provider.list_registered_wallet_ids.return_value = wallet_ids
        account_provider.list_items.return_value = accounts
        refresh_mock = mock.AsyncMock(return_value=True)
        with mock.patch.object(
            global_view_workflow_module.collection_providers,
            "AccountProvider",
        ) as account_provider_class_mock, mock.patch.object(
            global_view_workflow_module.workflows_retention,
            "should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch.object(
            global_view_workflow_module.GlobalViewRefreshWorkflow,
            "_refresh_single_account",
            refresh_mock,
        ):
            account_provider_class_mock.instance.return_value = account_provider
            result = await global_view_workflow_module.GlobalViewRefreshWorkflow._run_global_view_refresh(
                datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
                None,
            )
        assert result["refreshed_accounts"] == 2
        assert refresh_mock.await_count == 2
