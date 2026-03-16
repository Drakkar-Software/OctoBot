import decimal

import octobot_flow.repositories.exchange.portfolio_repository as portfolio_repository_import
import octobot_trading.personal_data as trading_personal_data


class SimulatedPortfolioRepository(portfolio_repository_import.PortfolioRepository):

    async def fetch_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        # todo update simulated portfolio with updated orders and trades
        return trading_personal_data.format_dict_portfolio_values(
            self.fetched_exchange_data.authenticated_data.portfolio.full_content, True
        ) # type: ignore
