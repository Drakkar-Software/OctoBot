import octobot_flow.repositories.exchange.positions_repository as positions_repository_import
import octobot_trading.util.test_tools.exchange_data as exchange_data_import


class SimulatedPositionsRepository(positions_repository_import.PositionsRepository):

    async def fetch_positions(self, symbols: list[str]) -> list[exchange_data_import.PositionDetails]:
        # todo update simulated positions with updated orders and trades
        return self.fetched_exchange_data.authenticated_data.positions
