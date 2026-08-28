#  Drakkar-Software OctoBot-Flow

import contextlib
import decimal

import mock

import octobot_commons.constants as commons_constants


def wire_portfolio_pipeline(
    exchange_manager,
    portfolio_content: dict,
    *,
    portfolio_total: float = 1500.0,
    exchange_name: str = "binanceus",
) -> None:
    stored_portfolio = {
        currency: dict(balances)
        for currency, balances in portfolio_content.items()
    }
    portfolio = mock.Mock()
    portfolio.portfolio = stored_portfolio
    portfolio_manager = mock.Mock()
    portfolio_manager.portfolio = portfolio
    portfolio_manager.reference_market = "USDC"
    portfolio_value_holder = mock.Mock()
    portfolio_value_holder.portfolio_current_value = portfolio_total
    portfolio_value_holder.current_crypto_currencies_values = {
        "BTC": decimal.Decimal("50000"),
        "USDT": decimal.Decimal("1"),
    }
    value_converter = mock.Mock()

    def convert_using_last_prices(amount, currency, _reference_market):
        if currency == "BTC":
            return decimal.Decimal("50000") * amount
        return decimal.Decimal("1") * amount

    value_converter.convert_currency_value_using_last_prices = convert_using_last_prices
    portfolio_value_holder.value_converter = value_converter
    portfolio_manager.portfolio_value_holder = portfolio_value_holder
    portfolio_manager.portfolio_history_update = contextlib.nullcontext

    def handle_balance_update(balance, is_diff_update=False):
        for currency, amounts in balance.items():
            if isinstance(amounts, dict):
                stored_portfolio[currency] = amounts
            else:
                stored_portfolio[currency] = {
                    commons_constants.PORTFOLIO_AVAILABLE: amounts,
                    commons_constants.PORTFOLIO_TOTAL: amounts,
                }
        return True

    portfolio_manager.handle_balance_update = mock.Mock(side_effect=handle_balance_update)
    portfolio_manager.resolve_pending_portfolio_update_events_if_any = mock.AsyncMock()
    exchange_personal_data = exchange_manager.exchange_personal_data
    exchange_personal_data.portfolio_manager = portfolio_manager

    async def handle_portfolio_update(balance, should_notify=False, is_diff_update=False):
        portfolio_manager.handle_balance_update(balance, is_diff_update=is_diff_update)
        await portfolio_manager.resolve_pending_portfolio_update_events_if_any()
        return True

    exchange_personal_data.handle_portfolio_update = mock.AsyncMock(side_effect=handle_portfolio_update)
    exchange_personal_data.handle_portfolio_profitability_update = mock.AsyncMock()
    exchange_manager.get_symbol_data = mock.Mock(return_value=mock.Mock())
    exchange_manager.client_symbols = ["BTC/USDC", "USDC/BTC", "BTC/USDT", "ETH/USDT"]
    exchange_manager.symbol_exists = mock.Mock(return_value=True)
    exchange_manager.exchange_name = exchange_name
