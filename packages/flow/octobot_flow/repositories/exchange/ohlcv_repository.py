import typing

import octobot_commons.enums as common_enums
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.exchange_data
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.constants


class OhlcvRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_ohlcv(
        self, symbol: str, time_frame: str, limit: int, tickers: dict[str, dict[str, typing.Any]]
    ) -> exchange_data_import.MarketDetails:
        updater = typing.cast(
            octobot_trading.exchange_data.OHLCVUpdater,
            self.get_channel_updater(octobot_trading.constants.OHLCV_CHANNEL)
        )
        ohlcvs = await updater.fetch_ohlcv(
            symbol, common_enums.TimeFrames(time_frame), limit, allow_cache=True, tickers_backup=tickers
        )
        return exchange_data_import.MarketDetails(
            symbol=symbol,
            time_frame=time_frame,
            close=[ohlcv[common_enums.PriceIndexes.IND_PRICE_CLOSE.value] for ohlcv in ohlcvs],
            open=[ohlcv[common_enums.PriceIndexes.IND_PRICE_OPEN.value] for ohlcv in ohlcvs],
            high=[ohlcv[common_enums.PriceIndexes.IND_PRICE_HIGH.value] for ohlcv in ohlcvs],
            low=[ohlcv[common_enums.PriceIndexes.IND_PRICE_LOW.value] for ohlcv in ohlcvs],
            volume=[ohlcv[common_enums.PriceIndexes.IND_PRICE_VOL.value] for ohlcv in ohlcvs],
            time=[ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value] for ohlcv in ohlcvs],
        )

