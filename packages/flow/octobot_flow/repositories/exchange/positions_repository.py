import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

class PositionsRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_positions(self, symbols: list[str]) -> list[exchange_data_import.PositionDetails]:
        raw_positions = await exchanges_test_tools_import.get_positions(
            self.exchange_manager, None, symbols=symbols
        )
        return [self._parse_position(position) for position in raw_positions]


    def _parse_position(self, raw_position: dict) -> exchange_data_import.PositionDetails:
        return exchange_data_import.PositionDetails(
            position=raw_position, contract=self._parse_contract(raw_position)
        )

    def _parse_contract(self, raw_position: dict) -> dict:
        raise NotImplementedError("Not _parse_contract not implemented")
