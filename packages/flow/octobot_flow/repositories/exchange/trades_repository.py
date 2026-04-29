import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import

class TradesRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_trades(self, symbols: list[str]) -> list[dict]:
        if not symbols:
            return []
        return await exchanges_test_tools_import.get_trades(
            self.exchange_manager, None, symbols=symbols
        )
