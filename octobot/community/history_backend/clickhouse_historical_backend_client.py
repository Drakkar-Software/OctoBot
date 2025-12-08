#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing
from datetime import datetime, timezone

import octobot_commons.constants as commons_constants
import octobot_commons.os_util as os_util

try:
    if os_util.is_raspberry_pi_machine():
        raise ImportError("clickhouse_connect is not available on Raspberry Pi")
    else:
        import clickhouse_connect.driver
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock clickhouse_connect.driver imports
        class ClickhouseConnectImportMock:
            async def get_async_client(self, *args):
                raise ImportError("clickhouse_connect not installed")
            class driver:
                class AsyncClient:
                    async def close(self):
                        pass
        clickhouse_connect = ClickhouseConnectImportMock()

import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import octobot.constants as constants
import octobot.community.history_backend.historical_backend_client as historical_backend_client
import octobot.community.history_backend.util as history_backend_util


class ClickhouseHistoricalBackendClient(historical_backend_client.HistoricalBackendClient):

    def __init__(self, **kwargs):
        self._client: typing.Optional[clickhouse_connect.driver.AsyncClient] = None

    async def open(self):
        try:
            self._client = await clickhouse_connect.get_async_client(
                host=constants.CLICKHOUSE_HOST,
                port=int(constants.CLICKHOUSE_PORT),
                username=constants.CLICKHOUSE_USERNAME,
                password=constants.CLICKHOUSE_PASSWORD
            )
        except (TypeError, Exception) as err:
            message = f"Error when connecting to Clickhouse server, {err.__class__.__name__}: {err}"
            commons_logging.get_logger().exception(err, True, message)
            raise err.__class__(message) from err

    async def close(self):
        if self._client is not None:
            await self._client.close()

    async def fetch_candles_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        first_open_time: float,
        last_open_time: float
    ) -> list[list[float]]:
        result = await self._client.query(
            """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_history
            WHERE 
                time_frame = %s
                AND exchange_internal_name = %s
                AND symbol = %s
                AND toDateTime(timestamp) >= toDateTime(%s)
                AND toDateTime(timestamp) <= toDateTime(%s)
            ORDER BY timestamp ASC
            """,
            [time_frame.value, exchange, symbol, first_open_time, last_open_time],
        )
        formatted = self._format_ohlcvs(result.result_rows, False)
        return history_backend_util.deduplicate(formatted, [0])

    async def fetch_extended_candles_history(
        self,
        exchange: str,
        symbols: list[str],
        time_frames: list[commons_enums.TimeFrames],
        first_open_time: typing.Optional[float] = None,
        last_open_time: typing.Optional[float] = None,
    ) -> list[list[typing.Union[float, str]]]:
        time_frame_values = [t.value for t in time_frames]
        timeframe_select = " OR ".join("time_frame = %s" for _ in time_frame_values)
        symbols_select = " OR ".join("symbol = %s" for _ in symbols)
        result = await self._client.query(
            f"""
            SELECT time_frame, symbol, timestamp, open, high, low, close, volume
            FROM ohlcv_history
            WHERE 
                ({timeframe_select})
                AND exchange_internal_name = %s
                AND ({symbols_select})
                AND toDateTime(timestamp) >= toDateTime(%s)
                AND toDateTime(timestamp) <= toDateTime(%s)
            ORDER BY timestamp ASC
            """,
            time_frame_values + [exchange] + symbols + [first_open_time, last_open_time],
        )
        formatted = self._format_ohlcvs(result.result_rows, True)
        return history_backend_util.deduplicate(formatted, [0, 1, 2])


    async def fetch_all_candles_for_exchange(self, exchange: str) -> list[list[float]]:
        result = await self._client.query(
            """
            SELECT time_frame, symbol, timestamp, open, high, low, close, volume 
            FROM ohlcv_history
            WHERE 
                exchange_internal_name = %s
            ORDER BY timestamp ASC
            """,
            [exchange],
        )
        return self._format_ohlcvs(result.result_rows, True)

    async def fetch_candles_history_range(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames
    ) -> tuple[float, float]:
        result = await self._client.query(
            """
            SELECT min(timestamp), max(timestamp)
            FROM ohlcv_history
            WHERE
                time_frame = %s
                AND exchange_internal_name = %s
                AND symbol = %s
            """,
            [time_frame.value, exchange, symbol],
        )
        return (
            history_backend_util.get_utc_timestamp_from_datetime(result.result_rows[0][0]),
            history_backend_util.get_utc_timestamp_from_datetime(result.result_rows[0][1])
        )

    async def insert_candles_history(self, rows: list, column_names: list) -> None:
        await self._client.insert(
            table="ohlcv_history",
            data=rows,
            column_names=column_names,
        )

    @staticmethod
    def _format_ohlcvs(ohlcvs: typing.Iterable, extended: bool) -> list[list[typing.Union[float, str]]]:
        if extended:
            # time frame
            # symbol
            # then uses PriceIndexes order
            # IND_PRICE_TIME = 0
            # IND_PRICE_OPEN = 1
            # IND_PRICE_HIGH = 2
            # IND_PRICE_LOW = 3
            # IND_PRICE_CLOSE = 4
            # IND_PRICE_VOL = 5
            return [
            [
                ohlcv[0],
                ohlcv[1],
                int(history_backend_util.get_utc_timestamp_from_datetime(ohlcv[2])),
                ohlcv[3],
                ohlcv[4],
                ohlcv[5],
                ohlcv[6],
                ohlcv[7],
            ]
            for ohlcv in ohlcvs
        ]
        # uses PriceIndexes order
        # IND_PRICE_TIME = 0
        # IND_PRICE_OPEN = 1
        # IND_PRICE_HIGH = 2
        # IND_PRICE_LOW = 3
        # IND_PRICE_CLOSE = 4
        # IND_PRICE_VOL = 5
        return [
            [
                int(history_backend_util.get_utc_timestamp_from_datetime(ohlcv[0])),
                ohlcv[1],
                ohlcv[2],
                ohlcv[3],
                ohlcv[4],
                ohlcv[5],
            ]
            for ohlcv in ohlcvs
        ]

    @staticmethod
    def get_formatted_time(timestamp: float) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
