import decimal
import typing

import octobot_trading.api as trading_api
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as personal_data
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data


class PortfolioRepository(base_exchange_repository_import.BaseExchangeRepository):

    @classmethod
    async def ensure_temporary_balance_channel(cls, exchange_manager) -> None:
        await trading_exchanges.create_producers(
            exchange_manager,
            [trading_personal_data.BalanceUpdater],
            start_producers=False,
        )

    async def fetch_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        
        updater = typing.cast(
            trading_personal_data.BalanceUpdater,
            self.get_channel_updater(trading_constants.BALANCE_CHANNEL)
        )
        portfolio = await updater.fetch_portfolio()
        return personal_data.from_raw_to_formatted_portfolio(
            personal_data.filter_empty_values(portfolio), as_float=False
        ) # type: ignore

    async def fetch_and_apply_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        updater = typing.cast(
            trading_personal_data.BalanceUpdater,
            self.get_channel_updater(trading_constants.BALANCE_CHANNEL)
        )
        raw_portfolio = await updater.fetch_portfolio()
        filtered_portfolio = personal_data.filter_empty_values(raw_portfolio)
        decimal_balance = personal_data.parse_decimal_portfolio(filtered_portfolio)
        await self.exchange_manager.exchange_personal_data.handle_portfolio_update(
            decimal_balance,
            should_notify=False,
        )
        return trading_api.get_portfolio(self.exchange_manager, as_decimal=False)  # type: ignore
