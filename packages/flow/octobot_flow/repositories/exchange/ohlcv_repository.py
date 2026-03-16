import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools
import octobot_trading.util.test_tools.exchange_data as exchange_data_import


class OhlcvRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_ohlcv(
        self, symbol: str, time_frame: str, limit: int
    ) -> exchange_data_import.MarketDetails:
        return await exchanges_test_tools.fetch_ohlcv(
            self.exchange_manager, symbol, time_frame, limit
        )
