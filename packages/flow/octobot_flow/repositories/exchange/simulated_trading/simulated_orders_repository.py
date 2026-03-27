import octobot_flow.repositories.exchange.orders_repository as orders_repository_import


class SimulatedOrdersRepository(orders_repository_import.OrdersRepository):

    async def fetch_open_orders(
        self, symbols: list[str], ignore_unsupported_orders: bool = True
    ) -> list[dict]:
        return []
