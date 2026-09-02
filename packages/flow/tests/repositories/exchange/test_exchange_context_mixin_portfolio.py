#  Drakkar-Software OctoBot-Flow

import contextlib

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.profiles as commons_profiles

import octobot_flow.entities
import octobot_flow.repositories.exchange.exchange_context_mixin as exchange_context_mixin_module


class _PredictiveExchangeContext(exchange_context_mixin_module.ExchangeContextMixin):
    USE_PREDICTIVE_ORDERS_SYNC: bool = True

    def init_predictive_orders_exchange_data(self, exchange_data):
        exchange_account_elements = self.automation_state.automation.exchange_account_elements
        if exchange_account_elements is None:
            return
        exchange_data.portfolio_details.content = exchange_account_elements.portfolio.content
        exchange_data.orders_details.open_orders = list(exchange_account_elements.orders.open_orders)


def _automation_state_with_locked_portfolio_and_open_orders() -> octobot_flow.entities.AutomationState:
    return octobot_flow.entities.AutomationState.from_dict(
        {
            "exchange_account_details": {
                "exchange_details": {"internal_name": "binanceus"},
                "auth_details": {},
                "portfolio": {},
            },
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "actions_dag": {"actions": []},
                "exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "USDC": {
                                commons_constants.PORTFOLIO_AVAILABLE: 2.0,
                                commons_constants.PORTFOLIO_TOTAL: 500.0,
                            },
                            "BTC": {
                                commons_constants.PORTFOLIO_AVAILABLE: 0.000015,
                                commons_constants.PORTFOLIO_TOTAL: 0.004995,
                            },
                        },
                    },
                    "orders": {
                        "open_orders": [{"symbol": "BTC/USDC", "id": "order_1"}],
                        "missing_orders": [],
                    },
                    "positions": [],
                },
            },
        }
    )


def _simulator_profile_data() -> commons_profiles.ProfileData:
    profile_data = mock.Mock(spec=commons_profiles.ProfileData)
    profile_data.trader_simulator = mock.Mock(enabled=True)
    return profile_data


@pytest.mark.asyncio
class TestExchangeContextMixinPortfolioHydration:
    async def test_predictive_sync_relocks_available_from_open_orders(self):
        exchange_context = _PredictiveExchangeContext(
            _automation_state_with_locked_portfolio_and_open_orders(),
            octobot_flow.entities.FetchedDependencies(),
        )
        portfolio_manager = mock.Mock()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager

        @contextlib.asynccontextmanager
        async def exchange_manager_from_exchange_data(*_args, **_kwargs):
            yield exchange_manager

        @contextlib.asynccontextmanager
        async def predictive_order_sync_context(*_args, **_kwargs):
            yield

        with (
            mock.patch(
                "octobot_flow.repositories.exchange.exchange_context_mixin.evaluators_api.create_matrix",
                return_value="matrix_1",
            ),
            mock.patch(
                "octobot_flow.repositories.exchange.exchange_context_mixin.evaluators_api.del_matrix",
            ),
            mock.patch(
                "octobot_flow.repositories.exchange.exchange_context_mixin.octobot_tentacles_manager.api.get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch(
                "octobot_flow.repositories.exchange.exchange_context_mixin.octobot_trading.exchanges.exchange_manager_from_exchange_data",
                exchange_manager_from_exchange_data,
            ),
            mock.patch.object(
                exchange_context,
                "_predictive_order_sync_context",
                predictive_order_sync_context,
            ),
            exchange_context.profile_data_provider.profile_data_context(_simulator_profile_data()),
        ):
            async with exchange_context.exchange_manager_context():
                pass

        portfolio_manager.apply_forced_portfolio.assert_called_once_with(
            {
                "USDC": 500.0,
                "BTC": 0.004995,
            },
            update_available_funds_from_open_orders=True,
        )
