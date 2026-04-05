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
