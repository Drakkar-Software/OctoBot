#  Drakkar-Software OctoBot-Flow

import mock
import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums

import octobot_flow.logic.exchange.portfolio.valuation_unit as valuation_unit_module


class TestResolvePortfolioValuationUnit:
    def test_returns_exchange_default_quote_currency_when_set(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_option_value.return_value = "USDC"
        assert valuation_unit_module.resolve_portfolio_valuation_unit(exchange_manager) == "USDC"
        exchange_manager.exchange.get_option_value.assert_called_once_with(
            trading_enums.ExchangeClientOptions.DEFAULT_QUOTE_CURRENCY
        )

    def test_falls_back_to_default_reference_market_when_option_missing(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange.get_option_value.return_value = None
        assert (
            valuation_unit_module.resolve_portfolio_valuation_unit(exchange_manager)
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )
