#  Drakkar-Software OctoBot-Commons
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
import octobot_commons.str_util as str_util


def test_camel_to_snake_empty():
    assert str_util.camel_to_snake("") == ""


def test_camel_to_snake_single_letter():
    assert str_util.camel_to_snake("A") == "a"


def test_camel_to_snake_trading_mode_style():
    assert str_util.camel_to_snake("GridTradingMode") == "grid_trading_mode"
    assert str_util.camel_to_snake("IndexTradingMode") == "index_trading_mode"
    assert str_util.camel_to_snake("AbstractTradingMode") == "abstract_trading_mode"


def test_camel_to_snake_already_lowercase():
    assert str_util.camel_to_snake("already_snake") == "already_snake"


def test_camel_to_snake_single_word_upper():
    assert str_util.camel_to_snake("Trading") == "trading"
