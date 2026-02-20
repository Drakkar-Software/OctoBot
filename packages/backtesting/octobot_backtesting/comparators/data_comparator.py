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
import os.path as path

import octobot_commons.logging as logging

import octobot_backtesting.constants as constants
import octobot_backtesting.data as data
import octobot_backtesting.enums as enums


class DataComparator:
    def __init__(self, data_path=constants.BACKTESTING_FILE_PATH):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.data_path = data_path

    def _sorted_str_list(self, values) -> list:
        if not values:
            return []
        return sorted(str(v) for v in values)

    def _timestamps_match(self, existing_start, existing_end, requested_start, requested_end) -> bool:
        req_start_s = int(requested_start / 1000) if requested_start else 0
        req_end_s = int(requested_end / 1000) if requested_end else 0
        # SQLite may return timestamps as strings; normalise to int before comparing
        ex_start_s = int(existing_start) if existing_start else 0
        ex_end_s = int(existing_end) if existing_end else 0
        if req_start_s and ex_start_s != req_start_s:
            return False
        if req_end_s and ex_end_s != req_end_s:
            return False
        return True

    def exchange_description_matches(self, description: dict,
                                     exchange_name: str,
                                     symbols: list,
                                     time_frames: list,
                                     start_timestamp,
                                     end_timestamp) -> bool:
        # 1. data type
        if description.get(enums.DataFormatKeys.DATA_TYPE.value) != enums.DataType.EXCHANGE.value:
            return False
        # 2. version (exchange collector always writes CURRENT_VERSION)
        if description.get(enums.DataFormatKeys.VERSION.value) != constants.CURRENT_VERSION:
            return False
        # 3. exchange name
        if description.get(enums.DataFormatKeys.EXCHANGE.value) != exchange_name:
            return False
        # 4. symbols (order-independent)
        if self._sorted_str_list(description.get(enums.DataFormatKeys.SYMBOLS.value, [])) \
                != self._sorted_str_list(symbols):
            return False
        # 5. time frames (order-independent)
        existing_tfs = self._sorted_str_list(
            tf.value if hasattr(tf, "value") else tf
            for tf in description.get(enums.DataFormatKeys.TIME_FRAMES.value, [])
        )
        requested_tfs = self._sorted_str_list(
            tf.value if hasattr(tf, "value") else tf for tf in (time_frames or [])
        )
        if existing_tfs != requested_tfs:
            return False
        # 6. timestamps
        existing_start = description.get(enums.DataFormatKeys.START_TIMESTAMP.value, 0)
        existing_end = description.get(enums.DataFormatKeys.END_TIMESTAMP.value, 0)
        return self._timestamps_match(existing_start, existing_end, start_timestamp, end_timestamp)

    def social_description_matches(self, description: dict,
                                   services: list,
                                   symbols: list,
                                   start_timestamp,
                                   end_timestamp) -> bool:
        # 1. data type
        if description.get(enums.DataFormatKeys.DATA_TYPE.value) != enums.DataType.SOCIAL.value:
            return False
        # 2. version
        if description.get(enums.DataFormatKeys.VERSION.value) != constants.CURRENT_VERSION:
            return False
        # 3. service names
        # Collector descriptions can contain the selected feed class plus its
        # required underlying services. Accept a superset in existing files.
        existing_services = self._sorted_str_list(description.get(enums.DataFormatKeys.SERVICES.value, []))
        requested_services = self._sorted_str_list(services)
        if not requested_services:
            return False
        if not set(requested_services).issubset(set(existing_services)):
            return False
        # 4. symbols (order-independent)
        # A social file with no symbols means "all symbols": it can satisfy any
        # requested symbol filter. A symbol-scoped file must match exactly.
        existing_symbols = self._sorted_str_list(description.get(enums.DataFormatKeys.SYMBOLS.value, []))
        requested_symbols = self._sorted_str_list(symbols)
        if existing_symbols and existing_symbols != requested_symbols:
            return False
        # 5. timestamps
        existing_start = description.get(enums.DataFormatKeys.START_TIMESTAMP.value, 0)
        existing_end = description.get(enums.DataFormatKeys.END_TIMESTAMP.value, 0)
        return self._timestamps_match(existing_start, existing_end, start_timestamp, end_timestamp)

    def description_matches(self, description: dict, **kwargs) -> bool:
        data_type = description.get(enums.DataFormatKeys.DATA_TYPE.value)
        if data_type == enums.DataType.EXCHANGE.value:
            return self.exchange_description_matches(description, **kwargs)
        if data_type == enums.DataType.SOCIAL.value:
            return self.social_description_matches(description, **kwargs)
        return False

    async def find_matching_data_file(self, **kwargs) -> str | None:
        for file_name in data.get_all_available_data_files(self.data_path):
            description = await data.get_file_description(path.join(self.data_path, file_name))
            if description is None:
                continue
            try:
                if self.description_matches(description, **kwargs):
                    self.logger.debug(f"Found existing matching data file: {file_name}")
                    return file_name
            except Exception as e:
                self.logger.debug(f"Could not compare description of {file_name}: {e}")
        return None
