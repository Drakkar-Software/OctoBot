import decimal

import octobot_trading.personal_data as personal_data
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import

class PortfolioRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        return personal_data.from_raw_to_formatted_portfolio(
            await exchanges_test_tools_import.get_portfolio(
                self.exchange_manager
            ), as_float=False
        ) # type: ignore
