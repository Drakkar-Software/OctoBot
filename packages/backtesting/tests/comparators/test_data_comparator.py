#  Drakkar-Software OctoBot-Backtesting
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager

import pytest

from octobot_backtesting.comparators.data_comparator import DataComparator
import octobot_backtesting.api as backtesting_api
import octobot_backtesting.constants as constants
import octobot_backtesting.enums as enums

pytestmark = pytest.mark.asyncio

EXCHANGE = "binance"
SYMBOLS = ["ETH/BTC", "BTC/USDT"]
TIME_FRAMES = ["1h", "4h"]
# timestamps in seconds (as stored in the description table)
START_TS_S = 1680000000
END_TS_S = 1690000000
# same timestamps expressed in milliseconds (as passed by callers)
START_TS_MS = START_TS_S * 1000
END_TS_MS = END_TS_S * 1000

SERVICES = ["RedditService", "TwitterService"]

def _make_exchange_db(directory, file_name,
                      exchange=EXCHANGE,
                      symbols=None,
                      time_frames=None,
                      start_ts=START_TS_S,
                      end_ts=END_TS_S,
                      version=constants.CURRENT_VERSION) -> str:
    """Create a minimal v2.0 exchange .data file and return its path."""
    symbols = symbols if symbols is not None else list(SYMBOLS)
    time_frames = time_frames if time_frames is not None else list(TIME_FRAMES)
    file_path = os.path.join(directory, file_name)
    conn = sqlite3.connect(file_path)
    conn.execute(
        "CREATE TABLE description "
        "(timestamp REAL, version TEXT, type TEXT, exchange TEXT, "
        "symbols TEXT, time_frames TEXT, start_timestamp INTEGER, end_timestamp INTEGER)"
    )
    conn.execute(
        "INSERT INTO description VALUES (?,?,?,?,?,?,?,?)",
        (1700000000.0, version, enums.DataType.EXCHANGE.value, exchange,
         json.dumps(symbols), json.dumps(time_frames), start_ts, end_ts),
    )
    # get_database_description v2.0 counts ohlcv rows to compute candles_length
    min_tf = sorted(time_frames)[0]
    conn.execute(
        "CREATE TABLE ohlcv "
        "(timestamp REAL, exchange_name TEXT, cryptocurrency TEXT, symbol TEXT, time_frame TEXT, candle TEXT)"
    )
    for sym in symbols:
        conn.execute(
            "INSERT INTO ohlcv VALUES (?,?,?,?,?,?)",
            (1700000000.0, exchange, "Crypto", sym, min_tf,
             json.dumps([1.0, 2.0, 0.5, 1.5, 100.0, 1700000000.0])),
        )
    conn.commit()
    conn.close()
    return file_path


def _make_social_db(directory, file_name,
                    services=None,
                    symbols=None,
                    start_ts=START_TS_S,
                    end_ts=END_TS_S,
                    version=constants.CURRENT_VERSION) -> str:
    services = services if services is not None else list(SERVICES)
    symbols = symbols if symbols is not None else []
    file_path = os.path.join(directory, file_name)
    conn = sqlite3.connect(file_path)
    # column order matches social_collector._create_description:
    # timestamp, version, type, sources, symbols, start_timestamp, end_timestamp, services
    conn.execute(
        "CREATE TABLE description "
        "(timestamp REAL, version TEXT, type TEXT, sources TEXT, "
        "symbols TEXT, start_timestamp INTEGER, end_timestamp INTEGER, services TEXT)"
    )
    conn.execute(
        "INSERT INTO description VALUES (?,?,?,?,?,?,?,?)",
        (1700000000.0, version, enums.DataType.SOCIAL.value,
         json.dumps([]), json.dumps([str(s) for s in symbols]),
         start_ts, end_ts, json.dumps(services)),
    )
    conn.execute(
        "CREATE TABLE social_events "
        "(timestamp REAL, service_name TEXT, channel TEXT, symbol TEXT, payload TEXT)"
    )
    conn.commit()
    conn.close()
    return file_path


@contextmanager
def _exchange_data_dir(**kwargs):
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_exchange_db(tmpdir, "ExchangeHistoryDataCollector_test.data", **kwargs)
        yield tmpdir


@contextmanager
def _social_data_dir(**kwargs):
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_social_db(tmpdir, "SocialHistoryDataCollector_test.data", **kwargs)
        yield tmpdir


class TestExchangeDescriptionMatches:
    def setup_method(self):
        self.comparator = DataComparator()

    def _make_desc(self, exchange=EXCHANGE, symbols=None, time_frames=None,
                   start_ts=START_TS_S, end_ts=END_TS_S,
                   version=constants.CURRENT_VERSION,
                   data_type=enums.DataType.EXCHANGE.value):
        return {
            enums.DataFormatKeys.DATA_TYPE.value: data_type,
            enums.DataFormatKeys.VERSION.value: version,
            enums.DataFormatKeys.EXCHANGE.value: exchange,
            enums.DataFormatKeys.SYMBOLS.value: symbols if symbols is not None else list(SYMBOLS),
            enums.DataFormatKeys.TIME_FRAMES.value: time_frames if time_frames is not None else list(TIME_FRAMES),
            enums.DataFormatKeys.START_TIMESTAMP.value: start_ts,
            enums.DataFormatKeys.END_TIMESTAMP.value: end_ts,
        }

    def test_exact_match(self):
        desc = self._make_desc()
        assert self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_symbols_order_independent(self):
        desc = self._make_desc(symbols=["BTC/USDT", "ETH/BTC"])
        assert self.comparator.exchange_description_matches(
            desc, EXCHANGE, ["ETH/BTC", "BTC/USDT"], TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_time_frames_order_independent(self):
        desc = self._make_desc(time_frames=["4h", "1h"])
        assert self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, ["1h", "4h"], START_TS_MS, END_TS_MS
        )

    def test_unconstrained_timestamps_match(self):
        desc = self._make_desc(start_ts=0, end_ts=0)
        assert self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, None, None
        )

    def test_wrong_exchange(self):
        desc = self._make_desc(exchange="kraken")
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_symbols(self):
        desc = self._make_desc(symbols=["BTC/USDT"])
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_time_frames(self):
        desc = self._make_desc(time_frames=["1d"])
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_start_timestamp(self):
        desc = self._make_desc(start_ts=START_TS_S + 100)
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_end_timestamp(self):
        desc = self._make_desc(end_ts=END_TS_S + 100)
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_data_type(self):
        desc = self._make_desc(data_type=enums.DataType.SOCIAL.value)
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_wrong_version(self):
        desc = self._make_desc(version="1.0")
        assert not self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

    def test_timestamps_as_strings(self):
        # SQLite databases (via octobot_commons) may return timestamps as strings
        # instead of ints; the comparator must still match correctly.
        desc = self._make_desc(start_ts=str(START_TS_S), end_ts=str(END_TS_S))
        assert self.comparator.exchange_description_matches(
            desc, EXCHANGE, SYMBOLS, TIME_FRAMES, START_TS_MS, END_TS_MS
        )

class TestSocialDescriptionMatches:
    def setup_method(self):
        self.comparator = DataComparator()

    def _make_desc(self, services=None, symbols=None,
                   start_ts=START_TS_S, end_ts=END_TS_S,
                   version=constants.CURRENT_VERSION,
                   data_type=enums.DataType.SOCIAL.value):
        return {
            enums.DataFormatKeys.DATA_TYPE.value: data_type,
            enums.DataFormatKeys.VERSION.value: version,
            enums.DataFormatKeys.SERVICES.value: services if services is not None else list(SERVICES),
            enums.DataFormatKeys.SYMBOLS.value: symbols if symbols is not None else [],
            enums.DataFormatKeys.START_TIMESTAMP.value: start_ts,
            enums.DataFormatKeys.END_TIMESTAMP.value: end_ts,
        }

    def test_exact_match(self):
        desc = self._make_desc()
        assert self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_services_order_independent(self):
        desc = self._make_desc(services=["TwitterService", "RedditService"])
        assert self.comparator.social_description_matches(
            desc, ["RedditService", "TwitterService"], [], START_TS_MS, END_TS_MS
        )

    def test_existing_services_superset_matches_requested_services(self):
        desc = self._make_desc(services=["AlternativeMeServiceFeed", "AlternativeMeService"])
        assert self.comparator.social_description_matches(
            desc, ["AlternativeMeServiceFeed"], [], START_TS_MS, END_TS_MS
        )

    def test_symbols_order_independent(self):
        desc = self._make_desc(symbols=["BTC/USDT", "ETH/BTC"])
        assert self.comparator.social_description_matches(
            desc, SERVICES, ["ETH/BTC", "BTC/USDT"], START_TS_MS, END_TS_MS
        )

    def test_existing_all_symbols_matches_requested_symbols(self):
        desc = self._make_desc(symbols=[])
        assert self.comparator.social_description_matches(
            desc, SERVICES, ["ETH/BTC"], START_TS_MS, END_TS_MS
        )

    def test_existing_symbol_subset_does_not_match_all_symbols_request(self):
        desc = self._make_desc(symbols=["ETH/BTC"])
        assert not self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_unconstrained_timestamps_match(self):
        desc = self._make_desc(start_ts=0, end_ts=0)
        assert self.comparator.social_description_matches(
            desc, SERVICES, [], None, None
        )

    def test_wrong_services(self):
        desc = self._make_desc(services=["TelegramService"])
        assert not self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_wrong_symbols(self):
        desc = self._make_desc(symbols=["ETH/BTC"])
        assert not self.comparator.social_description_matches(
            desc, SERVICES, ["BTC/USDT"], START_TS_MS, END_TS_MS
        )

    def test_wrong_start_timestamp(self):
        desc = self._make_desc(start_ts=START_TS_S + 100)
        assert not self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_wrong_data_type(self):
        desc = self._make_desc(data_type=enums.DataType.EXCHANGE.value)
        assert not self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_wrong_version(self):
        desc = self._make_desc(version="1.0")
        assert not self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )

    def test_timestamps_as_strings(self):
        # SQLite databases (via octobot_commons) may return timestamps as strings
        desc = self._make_desc(start_ts=str(START_TS_S), end_ts=str(END_TS_S))
        assert self.comparator.social_description_matches(
            desc, SERVICES, [], START_TS_MS, END_TS_MS
        )


class TestDescriptionMatches:
    def setup_method(self):
        self.comparator = DataComparator()

    def test_dispatches_to_exchange(self):
        desc = {
            enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.EXCHANGE.value,
            enums.DataFormatKeys.VERSION.value: constants.CURRENT_VERSION,
            enums.DataFormatKeys.EXCHANGE.value: EXCHANGE,
            enums.DataFormatKeys.SYMBOLS.value: list(SYMBOLS),
            enums.DataFormatKeys.TIME_FRAMES.value: list(TIME_FRAMES),
            enums.DataFormatKeys.START_TIMESTAMP.value: START_TS_S,
            enums.DataFormatKeys.END_TIMESTAMP.value: END_TS_S,
        }
        assert self.comparator.description_matches(
            desc,
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )

    def test_dispatches_to_social(self):
        desc = {
            enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.SOCIAL.value,
            enums.DataFormatKeys.VERSION.value: constants.CURRENT_VERSION,
            enums.DataFormatKeys.SERVICES.value: list(SERVICES),
            enums.DataFormatKeys.SYMBOLS.value: [],
            enums.DataFormatKeys.START_TIMESTAMP.value: START_TS_S,
            enums.DataFormatKeys.END_TIMESTAMP.value: END_TS_S,
        }
        assert self.comparator.description_matches(
            desc,
            services=SERVICES, symbols=[], start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )

    def test_unknown_data_type_returns_false(self):
        desc = {enums.DataFormatKeys.DATA_TYPE.value: "unknown"}
        assert not self.comparator.description_matches(desc)


async def test_find_matching_data_file_exchange_match():
    with _exchange_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "ExchangeHistoryDataCollector_test.data"


async def test_find_matching_data_file_exchange_no_match_exchange():
    with _exchange_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name="kraken", symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_exchange_no_match_symbols():
    with _exchange_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name=EXCHANGE, symbols=["XRP/USDT"], time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_exchange_no_match_time_frames():
    with _exchange_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=["1d"],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_exchange_no_match_timestamps():
    with _exchange_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=(START_TS_S + 3600) * 1000, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_exchange_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_social_match():
    with _social_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=SERVICES, symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "SocialHistoryDataCollector_test.data"


async def test_find_matching_data_file_social_no_match_services():
    with _social_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=["TelegramService"], symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_find_matching_data_file_social_match_when_existing_services_is_superset():
    with _social_data_dir(services=["AlternativeMeServiceFeed", "AlternativeMeService"]) as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=["AlternativeMeServiceFeed"], symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "SocialHistoryDataCollector_test.data"


async def test_find_matching_data_file_social_match_when_existing_is_all_symbols():
    with _social_data_dir(symbols=[]) as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=SERVICES, symbols=["ETH/BTC"],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "SocialHistoryDataCollector_test.data"


async def test_find_matching_data_file_social_no_match_timestamps():
    with _social_data_dir() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=SERVICES, symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=(END_TS_S + 3600) * 1000,
        )
        assert result is None


async def test_find_matching_data_file_social_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        comparator = DataComparator(data_path=tmpdir)
        result = await comparator.find_matching_data_file(
            services=SERVICES, symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_api_find_matching_data_file_exchange():
    with _exchange_data_dir() as tmpdir:
        result = await backtesting_api.find_matching_data_file(
            data_path=tmpdir,
            exchange_name=EXCHANGE, symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "ExchangeHistoryDataCollector_test.data"


async def test_api_find_matching_data_file_exchange_no_match():
    with _exchange_data_dir() as tmpdir:
        result = await backtesting_api.find_matching_data_file(
            data_path=tmpdir,
            exchange_name="kraken", symbols=SYMBOLS, time_frames=TIME_FRAMES,
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None


async def test_api_find_matching_data_file_social():
    with _social_data_dir() as tmpdir:
        result = await backtesting_api.find_matching_data_file(
            data_path=tmpdir,
            services=SERVICES, symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result == "SocialHistoryDataCollector_test.data"


async def test_api_find_matching_data_file_social_no_match():
    with _social_data_dir() as tmpdir:
        result = await backtesting_api.find_matching_data_file(
            data_path=tmpdir,
            services=["TelegramService"], symbols=[],
            start_timestamp=START_TS_MS, end_timestamp=END_TS_MS,
        )
        assert result is None
