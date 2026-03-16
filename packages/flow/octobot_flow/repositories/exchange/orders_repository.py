import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import

class OrdersRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_open_orders(
        self, symbols: list[str], ignore_unsupported_orders: bool = True
    ) -> list[dict]:
        if not symbols:
            return []
        return await exchanges_test_tools_import.get_open_orders(
            self.exchange_manager, None, symbols=symbols, ignore_unsupported_orders=ignore_unsupported_orders
        )
