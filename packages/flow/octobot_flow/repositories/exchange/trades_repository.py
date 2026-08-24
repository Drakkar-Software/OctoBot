import typing

import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as trading_personal_data

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import


class TradesRepository(base_exchange_repository_import.BaseExchangeRepository):

    @classmethod
    async def ensure_temporary_trades_channel(cls, exchange_manager) -> None:
        await trading_exchanges.create_exchange_channels(exchange_manager)
        await trading_exchanges.create_producers(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )

    async def fetch_trades(self, symbols: list[str]) -> list[dict]:
        if not symbols:
            return []
        updater = typing.cast(
            trading_personal_data.TradesUpdater,
            self.get_channel_updater(trading_constants.TRADES_CHANNEL),
        )
        raw_trades = await updater.fetch_trades(symbols)
        return [
            parsed_trade
            for raw_trade in raw_trades
            if (parsed_trade := trading_personal_data.TradesUpdater.ensure_parsing(
                self.exchange_manager, raw_trade
            ))
        ]
