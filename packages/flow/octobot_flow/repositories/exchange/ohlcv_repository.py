import typing

import octobot_commons.enums as common_enums
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_flow.repositories.exchange.channel_producer_ensure as channel_producer_ensure_module
import octobot_trading.exchange_data
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.constants


class OhlcvRepository(base_exchange_repository_import.BaseExchangeRepository):

    @classmethod
    async def ensure_temporary_ohlcv_channel(cls, exchange_manager) -> None:
        await channel_producer_ensure_module.ensure_temporary_channel_producer(
            exchange_manager,
            octobot_trading.constants.OHLCV_CHANNEL,
            octobot_trading.exchange_data.OHLCVUpdater,
        )

    async def fetch_ohlcv(
        self, symbol: str, time_frame: str, limit: int, tickers: dict[str, dict[str, typing.Any]]
    ) -> exchange_data_import.MarketDetails:
        await self.ensure_temporary_ohlcv_channel(self.exchange_manager)
        updater = typing.cast(
            octobot_trading.exchange_data.OHLCVUpdater,
            self.get_channel_updater(octobot_trading.constants.OHLCV_CHANNEL)
        )
        ohlcvs = await updater.fetch_ohlcv(
            symbol, common_enums.TimeFrames(time_frame), limit, allow_cache=True, tickers_backup=tickers
        )
        return exchange_data_import.MarketDetails.from_ohlcvs(symbol, time_frame, ohlcvs)
