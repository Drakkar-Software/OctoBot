import decimal
import typing

import octobot_trading.personal_data as personal_data
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data

class PortfolioRepository(base_exchange_repository_import.BaseExchangeRepository):

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
        return personal_data.from_raw_to_formatted_portfolio(filtered_portfolio, as_float=False)  # type: ignore
