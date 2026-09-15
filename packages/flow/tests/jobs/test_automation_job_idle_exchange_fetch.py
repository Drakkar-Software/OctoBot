import mock
import pytest

import octobot_flow.entities
import octobot_flow.jobs.automation_job as automation_job_module
import octobot_flow.jobs.exchange_account_job as exchange_account_job_module


def _automation_job_with_empty_symbol_dag() -> automation_job_module.AutomationJob:
    automation_state = octobot_flow.entities.AutomationState.from_dict(
        {
            "exchange_account_details": {
                "exchange_details": {"internal_name": "binanceus", "exchange_account_id": "acc-1"},
                "auth_details": {},
                "portfolio": {"unit": "USDC"},
            },
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "actions_dag": {"actions": []},
                "exchange_account_elements": {
                    "portfolio": {"content": {"USDC": {"available": 1000.0, "total": 1000.0}}},
                    "orders": {"open_orders": [], "missing_orders": []},
                    "positions": [],
                },
            },
        }
    )
    user_auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
    return automation_job_module.AutomationJob(
        automation_state.to_dict(include_default_values=False),
        [],
        [],
        user_auth_details,
    )


class TestShouldUsePortfolioOnlyExchangeFetch:
    def test_idle_when_no_symbols_open_orders_or_positions(self):
        account_elements = octobot_flow.entities.ExchangeAccountElements(
            orders=octobot_flow.entities.ExchangeAccountElements().orders,
            positions=[],
        )
        assert automation_job_module.AutomationJob._should_use_portfolio_only_exchange_fetch(
            set(),
            account_elements,
        ) is True

    def test_active_when_symbols_present(self):
        assert automation_job_module.AutomationJob._should_use_portfolio_only_exchange_fetch(
            {"BTC/USDC"},
            None,
        ) is False

    def test_active_when_open_orders_present(self):
        account_elements = octobot_flow.entities.ExchangeAccountElements()
        account_elements.orders.open_orders = [{"symbol": "BTC/USDC"}]
        assert automation_job_module.AutomationJob._should_use_portfolio_only_exchange_fetch(
            set(),
            account_elements,
        ) is False


class TestInitAllRequiredExchangeDataIdleFetch:
    @pytest.mark.asyncio
    async def test_idle_automation_uses_portfolio_only_fetch(self):
        automation_job = _automation_job_with_empty_symbol_dag()
        exchange_account_details = automation_job.automation_state.exchange_account_details
        minimal_profile_data = mock.Mock()
        minimal_profile_data.get_traded_symbols.return_value = []

        exchange_account_job_mock = mock.Mock()
        exchange_account_job_mock.get_all_actions_symbols.return_value = []
        exchange_account_job_mock.update_portfolio_only = mock.AsyncMock()
        exchange_account_job_mock.update_public_data = mock.AsyncMock()
        exchange_account_job_mock.update_authenticated_data = mock.AsyncMock()
        exchange_account_job_mock.account_exchange_context.return_value.__aenter__ = mock.AsyncMock(return_value=None)
        exchange_account_job_mock.account_exchange_context.return_value.__aexit__ = mock.AsyncMock(return_value=None)
        exchange_account_job_mock.fetched_dependencies = mock.Mock()
        exchange_account_job_mock.fetched_dependencies.fetched_exchange_data = mock.Mock()

        with (
            mock.patch.object(
                exchange_account_job_module,
                "ExchangeAccountJob",
                return_value=exchange_account_job_mock,
            ),
            mock.patch(
                "octobot_flow.logic.dsl.get_actions_symbol_dependencies",
                return_value=[],
            ),
            mock.patch(
                "octobot_flow.logic.configuration.create_profile_data",
                return_value=mock.Mock(),
            ),
        ):
            await automation_job._init_all_required_exchange_data(
                exchange_account_details,
                None,
                [],
                minimal_profile_data,
            )

        exchange_account_job_mock.update_portfolio_only.assert_awaited_once()
        exchange_account_job_mock.update_public_data.assert_not_called()
        exchange_account_job_mock.update_authenticated_data.assert_not_called()
