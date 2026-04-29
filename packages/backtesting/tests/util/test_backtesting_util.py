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

if not os.getenv('CYTHON_IGNORE'):
    from octobot_backtesting.util.backtesting_util import _parse_class_name_from_backtesting_file


def test_parse_class_name_from_backtesting_file():
    if not os.getenv('CYTHON_IGNORE'):
        assert _parse_class_name_from_backtesting_file("ExchangeHistoryDataCollector_1589740606.4862757") == "ExchangeHistoryDataCollector"
