import octobot_backtesting.util as util
import octobot_commons.enums as commons_enums


class BacktestData:
    def __init__(self, data_files, config, tentacles_config, use_accurate_price_time_frame):
        self.data_files = data_files
        self.config = config
        self.tentacles_config = tentacles_config
        self.importers_by_data_file = None
        self.preloaded_candle_managers = {}
        self.use_cached_markets: bool = False
        self.default_importer = None
        self.use_accurate_price_time_frame: bool = use_accurate_price_time_frame

    async def initialize(self):
        self.importers_by_data_file = {
            data_file: await util.create_importer_from_backtesting_file_name(self.config, data_file,
                                                                             default_importer=self.default_importer)
            for data_file in self.data_files
        }

    async def get_preloaded_candles_manager(self, exchange, symbol, time_frame, start_timestamp, end_timestamp):
        key = self._get_key(exchange, symbol, time_frame, start_timestamp, end_timestamp)
        try:
            return self.preloaded_candle_managers[key]
        except KeyError:
            try:
                import octobot_trading.api as trading_api
                preloaded_candles = await self._get_all_candles(exchange, symbol, time_frame,
                                                                start_timestamp, end_timestamp)
                self.preloaded_candle_managers[key] = await trading_api.create_preloaded_candles_manager(
                    preloaded_candles
                )
                return self.preloaded_candle_managers[key]
            except ImportError:
                self.preloaded_candle_managers[key] = None
        return self.preloaded_candle_managers[key]

    async def _get_all_candles(self, exchange, symbol, time_frame, start_timestamp, end_timestamp):
        # manually filter max candles not to change chronological cache behavior
        all_candles = await self._get_importer(exchange, symbol).get_ohlcv_from_timestamps(
                exchange_name=exchange,
                symbol=symbol,
                time_frame=time_frame,
                inferior_timestamp=start_timestamp,
            )
        return [
            candle[-1]
            for candle in all_candles
            if candle[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value] <= end_timestamp
        ]

    def _get_importer(self, exchange, symbol):
        for importer in self.importers_by_data_file.values():
            if exchange in importer.exchange_name == exchange and symbol in importer.symbols:
                return importer
        raise KeyError("Importer not found")

    def reset_cached_indexes(self):
        for importer in self.importers_by_data_file.values():
            importer.reset_cache()

    async def stop(self):
        for importer in self.importers_by_data_file.values():
            await importer.stop()

    def _get_key(self, *identifiers):
        return "-".join(str(i) for i in identifiers)
