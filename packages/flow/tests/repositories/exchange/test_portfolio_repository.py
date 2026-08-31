#  Drakkar-Software OctoBot-Flow

import decimal

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_trading.constants as trading_constants

import octobot_flow.entities
import octobot_flow.repositories.exchange.portfolio_repository as portfolio_repository_module

pytestmark = pytest.mark.asyncio


class TestFetchAndApplyPortfolio:
    async def test_applies_decimal_balance_to_portfolio_manager(self):
        balance_content = {
            "USDT": {
                "total": 1000.0,
                "free": 1000.0,
            },
            "BTC": {
                "total": 0.1,
                "free": 0.1,
            },
        }
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data = mock.Mock()
        exchange_manager.exchange_personal_data.handle_portfolio_update = mock.AsyncMock(return_value=True)
        balance_updater = mock.Mock()
        balance_updater.fetch_portfolio = mock.AsyncMock(return_value=balance_content)
        get_channel_updater_mock = mock.Mock(return_value=balance_updater)
        repository = portfolio_repository_module.PortfolioRepository(
            exchange_manager,
            known_automations=[],
            fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
        )
        with mock.patch.object(
            repository,
            "get_channel_updater",
            get_channel_updater_mock,
        ):
            formatted_portfolio = await repository.fetch_and_apply_portfolio()

        exchange_manager.exchange_personal_data.handle_portfolio_update.assert_awaited_once()
        applied_balance = exchange_manager.exchange_personal_data.handle_portfolio_update.await_args.args[0]
        assert applied_balance["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("0.1")
        assert applied_balance["USDT"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("1000.0")
        assert formatted_portfolio["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("0.1")
        get_channel_updater_mock.assert_called_once_with(trading_constants.BALANCE_CHANNEL)
