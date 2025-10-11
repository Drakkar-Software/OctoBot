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
import octobot_commons.enums as commons_enums


class HistoricalBackendClient:
    """Abstract base class for historical data backend clients"""

    async def open(self):
        raise NotImplementedError("open is not implemented")

    async def close(self):
        raise NotImplementedError("close is not implemented")

    async def fetch_candles_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        first_open_time: float,
        last_open_time: float
    ) -> list[list[float]]:
        raise NotImplementedError("fetch_candles_history is not implemented")

    async def fetch_extended_candles_history(
        self,
        exchange: str,
        symbols: list[str],
        time_frames: list[commons_enums.TimeFrames],
        first_open_time: typing.Optional[float] = None,
        last_open_time: typing.Optional[float] = None,
    ) -> list[list[typing.Union[float, str]]]:
        raise NotImplementedError("fetch_extended_candles_history is not implemented")

    async def fetch_candles_history_range(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames
    ) -> tuple[float, float]:
        raise NotImplementedError("fetch_candles_history_range is not implemented")

    async def insert_candles_history(self, rows: list, column_names: list) -> None:
        raise NotImplementedError("insert_candles_history is not implemented")

    async def fetch_all_candles_for_exchange(self, exchange: str) -> list[list[float]]:
        raise NotImplementedError("fetch_all_candles_for_exchange is not implemented")

    @staticmethod
    def get_formatted_time(timestamp: float):
        raise NotImplementedError("get_formatted_time is not implemented")
