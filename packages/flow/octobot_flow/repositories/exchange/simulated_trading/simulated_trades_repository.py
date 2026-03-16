import octobot_flow.repositories.exchange.trades_repository as trades_repository_import


class SimulatedTradesRepository(trades_repository_import.TradesRepository):

    async def fetch_trades(self, symbols: list[str]) -> list[dict]:
        # todo add generated trades
        return self.fetched_exchange_data.authenticated_data.trades

