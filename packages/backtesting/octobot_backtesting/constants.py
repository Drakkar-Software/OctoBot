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
import os

import octobot_commons.enums as enums

CONFIG_BACKTESTING = "backtesting"
CONFIG_BACKTESTING_DATA_FILES = "files"
CONFIG_ANALYSIS_ENABLED_OPTION = "post_analysis_enabled"
CONFIG_BACKTESTING_OTHER_MARKETS_STARTING_PORTFOLIO = 10000
BACKTESTING_DATA_OHLCV = "ohlcv"
BACKTESTING_DATA_TRADES = "trades"
BACKTESTING_FILE_PATH = os.path.join(CONFIG_BACKTESTING, "data")
BACKTESTING_DATA_FILE_EXT = ".data"
BACKTESTING_DATA_FILE_TEMP_EXT = ".part"
BACKTESTING_DATA_FILE_SEPARATOR = "_"
CURRENT_VERSION = "2.0"
BACKTESTING_DATA_FILE_TIME_WRITE_FORMAT = '%Y%m%d_%H%M%S'
BACKTESTING_DATA_FILE_TIME_READ_FORMAT = BACKTESTING_DATA_FILE_TIME_WRITE_FORMAT.replace("_", "")
BACKTESTING_DATA_FILE_TIME_DISPLAY_FORMAT = '%d %B %Y at %H:%M:%S'
BACKTESTING_DEFAULT_JOIN_TIMEOUT = 1800  # 30min

BACKTESTING_TIME_FRAMES_TO_DISPLAY = [enums.TimeFrames.THIRTY_MINUTES.value,
                                      enums.TimeFrames.ONE_HOUR.value,
                                      enums.TimeFrames.FOUR_HOURS.value,
                                      enums.TimeFrames.ONE_DAY.value]
