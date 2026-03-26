import decimal
import typing

import octobot_trading.constants as trading_constants

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class PortfolioInterface:
    def __init__(self, exchange_manager: "octobot_trading.exchanges.ExchangeManager"):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager

    @property
    def reference_market(self) -> str:
        return self._exchange_manager.exchange_personal_data.portfolio_manager.reference_market

    def get_holdings_ratio(
        self,
        coin: str,
        traded_symbols_only: bool = False,
        include_assets_in_open_orders: bool = False,
        coins_whitelist: typing.Optional[list] = None,
    ) -> decimal.Decimal:
        ratio = self._exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.get_holdings_ratio(
            coin,
            traded_symbols_only=traded_symbols_only,
            include_assets_in_open_orders=include_assets_in_open_orders,
            coins_whitelist=coins_whitelist,
        )
        return ratio if ratio is not None else trading_constants.ZERO

    def get_traded_assets_holdings_value(
        self,
        unit: str,
        coins_whitelist: typing.Optional[typing.Iterable] = None,
    ) -> decimal.Decimal:
        portfolio_manager = self._exchange_manager.exchange_personal_data.portfolio_manager
        return portfolio_manager.portfolio_value_holder.get_traded_assets_holdings_value(
            unit, coins_whitelist
        )

    def get_free_reference_market_holding(self, reference_market: str) -> decimal.Decimal:
        portfolio_manager = self._exchange_manager.exchange_personal_data.portfolio_manager
        return portfolio_manager.portfolio.get_currency_portfolio(reference_market).available

    def get_currency_portfolio_total(self, currency: str) -> decimal.Decimal:
        portfolio = self._exchange_manager.exchange_personal_data.portfolio_manager.portfolio
        return portfolio.get_currency_portfolio(currency).total

    def get_currency_portfolio_available(self, currency: str) -> decimal.Decimal:
        portfolio = self._exchange_manager.exchange_personal_data.portfolio_manager.portfolio
        return portfolio.get_currency_portfolio(currency).available
