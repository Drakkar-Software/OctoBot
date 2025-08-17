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

import clickhouse_connect.driver

import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import octobot.constants as constants
import octobot.community.history_backend.historical_backend_client as historical_backend_client


class ClickhouseHistoricalBackendClient(historical_backend_client.HistoricalBackendClient):

    def __init__(self):
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
        formatted = self._format_ohlcvs(result.result_rows)
        return _deduplicate(formatted, 0)

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
            _get_utc_timestamp_from_datetime(result.result_rows[0][0]),
            _get_utc_timestamp_from_datetime(result.result_rows[0][1])
        )

    async def insert_candles_history(self, rows: list, column_names: list) -> None:
        await self._client.insert(
            table="ohlcv_history",
            data=rows,
            column_names=column_names,
        )

    @staticmethod
    def _format_ohlcvs(ohlcvs: typing.Iterable) -> list[list[float]]:
        # uses PriceIndexes order
        # IND_PRICE_TIME = 0
        # IND_PRICE_OPEN = 1
        # IND_PRICE_HIGH = 2
        # IND_PRICE_LOW = 3
        # IND_PRICE_CLOSE = 4
        # IND_PRICE_VOL = 5
        return [
            [
                int(_get_utc_timestamp_from_datetime(ohlcv[0])),
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

def _get_utc_timestamp_from_datetime(dt: datetime) -> float:
    """
    Convert a datetime to a timestamp in UTC
    WARNING: usable here as we know this DB stores time in UTC only
    """
    return dt.replace(tzinfo=timezone.utc).timestamp()


def _deduplicate(elements, key) -> list:
    # from https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in elements if not (x[key] in seen or seen_add(x[key]))]
