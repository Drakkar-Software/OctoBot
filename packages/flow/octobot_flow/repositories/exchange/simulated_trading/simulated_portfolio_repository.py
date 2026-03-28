import decimal

import octobot_flow.repositories.exchange.portfolio_repository as portfolio_repository_import
import octobot_trading.personal_data as trading_personal_data


class SimulatedPortfolioRepository(portfolio_repository_import.PortfolioRepository):

    async def fetch_portfolio(self) -> dict[str, dict[str, decimal.Decimal]]:
        return {}
