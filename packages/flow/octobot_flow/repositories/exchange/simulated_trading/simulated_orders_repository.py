import octobot_trading.constants
import octobot_trading.enums

import octobot_flow.repositories.exchange.orders_repository as orders_repository_import


class SimulatedOrdersRepository(orders_repository_import.OrdersRepository):

    async def fetch_open_orders(
        self, symbols: list[str], ignore_unsupported_orders: bool = True
    ) -> list[dict]:
        return []
        # TODO see if returning the orders from the known bot details is necessary in simulated
        return [
            order[octobot_trading.constants.STORAGE_ORIGIN_VALUE] 
            for automation in self.known_automations
            for order in automation.exchange_account_elements.orders.open_orders
            if order[octobot_trading.constants.STORAGE_ORIGIN_VALUE][octobot_trading.enums.ExchangeConstantsOrderColumns.SYMBOL.value] in symbols
        ]
