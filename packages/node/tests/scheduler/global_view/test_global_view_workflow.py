#  Drakkar-Software OctoBot-Node

import datetime

import mock
import pytest

import octobot_flow.entities
import octobot_protocol.models as protocol_models

from tests.scheduler import temp_dbos_scheduler


class TestGlobalViewScheduleInput:
    def test_get_schedule_input_disables_automatic_backfill(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module

        schedule_input = global_view_workflow_module.get_schedule_input()
        assert schedule_input["automatic_backfill"] is False


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
        account_provider.list_collectable_wallet_ids.return_value = wallet_ids
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
            )
        assert result["refreshed_accounts"] == 2
        assert refresh_mock.await_count == 2


@pytest.mark.asyncio
class TestRefreshWalletAccounts:
    @pytest.fixture
    def global_view_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module_loaded

        yield global_view_workflow_module_loaded

    async def test_skips_wallet_when_not_registered(self, global_view_workflow_module):
        import octobot.community.wallet_backend.errors as wallet_backend_errors_module

        account_provider = mock.Mock()
        account_provider.list_items.side_effect = wallet_backend_errors_module.WalletNotFoundError(
            "Wallet not found"
        )
        mock_logger = mock.Mock()
        with mock.patch.object(
            global_view_workflow_module.collection_providers,
            "AccountProvider",
        ) as account_provider_class_mock, mock.patch.object(
            global_view_workflow_module.octobot_commons_logging,
            "get_logger",
            return_value=mock_logger,
        ):
            account_provider_class_mock.instance.return_value = account_provider
            refreshed_count = await global_view_workflow_module.GlobalViewRefreshWorkflow._refresh_wallet_accounts(
                "wallet-missing",
            )
        assert refreshed_count == 0
        mock_logger.warning.assert_called_once()

    async def test_propagates_unexpected_list_items_errors(self, global_view_workflow_module):
        account_provider = mock.Mock()
        account_provider.list_items.side_effect = RuntimeError("storage failure")
        with mock.patch.object(
            global_view_workflow_module.collection_providers,
            "AccountProvider",
        ) as account_provider_class_mock:
            account_provider_class_mock.instance.return_value = account_provider
            try:
                await global_view_workflow_module.GlobalViewRefreshWorkflow._refresh_wallet_accounts(
                    "wallet-1",
                )
                raise AssertionError("Expected RuntimeError")
            except RuntimeError as error:
                assert str(error) == "storage failure"


def _exchange_account() -> protocol_models.Account:
    account_timestamp = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    return protocol_models.Account(
        id="account-1",
        name="Kraken Live",
        is_simulated=False,
        created_at=account_timestamp,
        updated_at=account_timestamp,
        specifics=protocol_models.AccountSpecifics(
            actual_instance=protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                remote_account_id="remote-1",
                exchange_config_ids=["exchange-config-1"],
            )
        ),
    )


@pytest.mark.asyncio
class TestRefreshSingleAccount:
    @pytest.fixture
    def global_view_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module_loaded

        yield global_view_workflow_module_loaded

    async def test_logs_success_summary_after_refresh(self, global_view_workflow_module):
        account = _exchange_account()
        refresh_result = octobot_flow.entities.GlobalViewAccountRefreshResult(
            updated_account=account,
            changed_order_ids={"gone-order-1"},
            open_orders=[{"exchange_id": "stays-order-2"}, {"exchange_id": "stays-order-3"}],
        )
        mock_logger = mock.Mock()
        with (
            mock.patch.object(
                global_view_workflow_module.global_view_executor_module,
                "refresh_account_global_view",
                mock.AsyncMock(return_value=refresh_result),
            ),
            mock.patch.object(
                global_view_workflow_module.automation_trigger_module,
                "trigger_account_automations",
                mock.AsyncMock(),
            ) as trigger_mock,
            mock.patch.object(
                global_view_workflow_module.exchange_account_resolver,
                "get_exchange_config",
                return_value=protocol_models.ExchangeConfig(
                    id="exchange-config-1",
                    name="kraken-main",
                    exchange="kraken",
                    sandboxed=False,
                ),
            ),
            mock.patch.object(
                global_view_workflow_module.octobot_commons_logging,
                "get_logger",
                return_value=mock_logger,
            ),
        ):
            succeeded = await global_view_workflow_module.GlobalViewRefreshWorkflow._refresh_single_account(
                "wallet-1",
                account,
            )
        assert succeeded is True
        trigger_mock.assert_awaited_once_with("wallet-1", "account-1", {"gone-order-1"})
        mock_logger.info.assert_called_once()
        info_args = mock_logger.info.call_args.args
        assert info_args[0].startswith("Account global view refresh succeeded:")
        assert info_args[1:] == (
            "account-1",
            "wallet-1",
            "Kraken Live",
            "kraken",
            False,
            2,
            1,
            True,
            "n/a",
            "n/a",
        )
