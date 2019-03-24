#  Drakkar-Software OctoBot
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


from config import CONFIG_BACKTESTING, CONFIG_ENABLED_OPTION


def backtesting_enabled(config):
    return CONFIG_BACKTESTING in config and CONFIG_ENABLED_OPTION in config[CONFIG_BACKTESTING] \
           and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]


class BacktestingEndedException(Exception):
    def __init__(self, symbol=""):
        self.msg = f"Backtesting finished for {symbol}."
        super().__init__(self.msg)


class BacktestingDataFileException(Exception):
    def __init__(self, file_name):
        self.msg = f"Unhandled backtesting data for: {file_name}."
        super().__init__(self.msg)
