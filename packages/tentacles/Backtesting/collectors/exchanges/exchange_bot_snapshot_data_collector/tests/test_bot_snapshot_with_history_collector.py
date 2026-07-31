#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_commons.enums as commons_enums
import octobot_commons.symbols as commons_symbols
import tentacles.Backtesting.collectors.exchanges.exchange_bot_snapshot_data_collector.\
    bot_snapshot_with_history_collector as collector_module


JAN_2025_TIMESTAMP_MS = 1738070700001
JUL_2026_TIMESTAMP_MS = 1785004800000
JAN_2025_TIMESTAMP_SEC = JAN_2025_TIMESTAMP_MS // 1000
JUL_2026_TIMESTAMP_SEC = JUL_2026_TIMESTAMP_MS // 1000


def _minimal_collector(start_timestamp=None, end_timestamp=None):
    symbol = commons_symbols.parse_symbol("BTC/USDT")
    collector = collector_module.ExchangeBotSnapshotWithHistoryCollector(
        config={},
        exchange_name="binance",
        exchange_type="spot",
        tentacles_setup_config=mock.Mock(),
        symbols=[symbol],
        time_frames=[commons_enums.TimeFrames.ONE_MINUTE],
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    collector.exchange_manager = mock.Mock()
    collector.fetch_exchange_manager = mock.Mock()
    return collector


class TestExchangeBotSnapshotWithHistoryCollectorAdaptTimestamps:
    @pytest.mark.asyncio
    async def test_keeps_user_start_timestamp_when_live_data_starts_earlier(self):
        collector = _minimal_collector(
            start_timestamp=JUL_2026_TIMESTAMP_MS,
            end_timestamp=JUL_2026_TIMESTAMP_MS + 1000,
        )
        with mock.patch.object(
            collector,
            "get_first_candle_timestamp",
            mock.AsyncMock(return_value=JAN_2025_TIMESTAMP_MS),
        ):
            await collector.adapt_timestamps()
        assert collector.start_timestamp == JUL_2026_TIMESTAMP_MS

    @pytest.mark.asyncio
    async def test_uses_live_start_when_user_start_not_configured(self):
        collector = _minimal_collector(end_timestamp=JUL_2026_TIMESTAMP_MS)
        with mock.patch.object(
            collector,
            "get_first_candle_timestamp",
            mock.AsyncMock(return_value=JAN_2025_TIMESTAMP_MS),
        ):
            await collector.adapt_timestamps()
        assert collector.start_timestamp == JAN_2025_TIMESTAMP_MS


class TestExchangeBotSnapshotWithHistoryCollectorGetFirstCandleTimestamp:
    @pytest.mark.asyncio
    async def test_filters_live_snapshot_to_respect_ideal_start_timestamp(self):
        collector = _minimal_collector()
        symbol = collector.symbols[0]
        time_frame = collector.time_frames[0]
        fetch_data_id = collector.get_fetch_data_id(symbol, time_frame)
        snapshot_candles = [
            [JAN_2025_TIMESTAMP_SEC, 1, 1, 1, 1, 1],
            [JUL_2026_TIMESTAMP_SEC, 2, 2, 2, 2, 2],
        ]
        with mock.patch.object(
            collector_module.trading_api,
            "get_symbol_data",
            mock.Mock(return_value=mock.Mock()),
        ), mock.patch.object(
            collector,
            "get_ohlcv_snapshot",
            mock.Mock(return_value=snapshot_candles),
        ):
            first_timestamp = await collector.get_first_candle_timestamp(
                JUL_2026_TIMESTAMP_MS, symbol, time_frame
            )
        assert first_timestamp == JUL_2026_TIMESTAMP_MS
        assert collector.fetched_data[collector_module.ExchangeBotSnapshotWithHistoryCollector.OHLCV][fetch_data_id] == [
            snapshot_candles[1]
        ]

    @pytest.mark.asyncio
    async def test_fetches_from_exchange_when_live_snapshot_is_before_ideal_start(self):
        collector = _minimal_collector()
        symbol = collector.symbols[0]
        time_frame = collector.time_frames[0]
        fetch_data_id = collector.get_fetch_data_id(symbol, time_frame)
        exchange_candles = [[JUL_2026_TIMESTAMP_SEC, 3, 3, 3, 3, 3]]
        collector.fetch_exchange_manager.exchange.get_symbol_prices = mock.AsyncMock(
            return_value=exchange_candles
        )
        with mock.patch.object(
            collector_module.trading_api,
            "get_symbol_data",
            mock.Mock(return_value=mock.Mock()),
        ), mock.patch.object(
            collector,
            "get_ohlcv_snapshot",
            mock.Mock(return_value=[[JAN_2025_TIMESTAMP_SEC, 1, 1, 1, 1, 1]]),
        ):
            first_timestamp = await collector.get_first_candle_timestamp(
                JUL_2026_TIMESTAMP_MS, symbol, time_frame
            )
        assert first_timestamp == JUL_2026_TIMESTAMP_MS
        assert collector.fetched_data[collector_module.ExchangeBotSnapshotWithHistoryCollector.OHLCV][fetch_data_id] == \
            exchange_candles
        collector.fetch_exchange_manager.exchange.get_symbol_prices.assert_awaited_once_with(
            "BTC/USDT", time_frame, limit=1, since=JUL_2026_TIMESTAMP_MS
        )


class TestExchangeBotSnapshotWithHistoryCollectorGetOhlcvHistory:
    @pytest.mark.asyncio
    async def test_fill_after_starts_at_configured_start_when_database_is_older(self):
        collector = _minimal_collector(
            start_timestamp=JUL_2026_TIMESTAMP_MS,
            end_timestamp=JUL_2026_TIMESTAMP_MS + 86400000,
        )
        collector.is_creating_database = False
        collector.exchange_manager.exchange.get_pair_cryptocurrency = mock.Mock(return_value="BTC")
        symbol = collector.symbols[0]
        time_frame = collector.time_frames[0]
        fetch_data_id = collector.get_fetch_data_id(symbol, time_frame)
        collector.fetched_data[collector_module.ExchangeBotSnapshotWithHistoryCollector.OHLCV][fetch_data_id] = [
            [JUL_2026_TIMESTAMP_SEC, 2, 2, 2, 2, 2],
        ]
        database_candles = [
            ([], [JAN_2025_TIMESTAMP_SEC, 1, 1, 1, 1, 1]),
        ]
        collect_historical_ohlcv_mock = mock.AsyncMock(return_value=0)
        with mock.patch.object(
            collector,
            "_import_candles_from_datafile",
            mock.AsyncMock(return_value=database_candles),
        ), mock.patch.object(
            collector,
            "_check_ohlcv_integrity",
            mock.AsyncMock(return_value={}),
        ), mock.patch.object(
            collector,
            "save_ohlcv",
            mock.AsyncMock(),
        ), mock.patch.object(
            collector,
            "collect_historical_ohlcv",
            collect_historical_ohlcv_mock,
        ):
            await collector.get_ohlcv_history("binance", symbol, time_frame)
        collect_historical_ohlcv_mock.assert_awaited_once()
        assert collect_historical_ohlcv_mock.await_args.args[4] == JUL_2026_TIMESTAMP_MS
        assert collect_historical_ohlcv_mock.await_args.args[5] == collector.end_timestamp
