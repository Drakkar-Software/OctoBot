#  Drakkar-Software OctoBot-Trading
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
import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.position_util as position_util

COLUMNS = enums.ExchangeConstantsPositionColumns


def test_parse_position_status_known_value():
    assert (
        position_util.parse_position_status({COLUMNS.STATUS.value: "open"})
        is enums.PositionStatus.OPEN
    )


def test_parse_position_status_missing_key_returns_none():
    assert position_util.parse_position_status({}) is None


def test_parse_position_side_known_value():
    assert (
        position_util.parse_position_side({COLUMNS.SIDE.value: "short"}) is enums.PositionSide.SHORT
    )


def test_parse_position_side_missing_key_returns_none():
    assert position_util.parse_position_side({}) is None


def test_parse_position_margin_type_known_value():
    assert (
        position_util.parse_position_margin_type({COLUMNS.MARGIN_TYPE.value: "isolated"})
        is enums.MarginType.ISOLATED
    )


def test_parse_position_margin_type_missing_key_returns_none():
    assert position_util.parse_position_margin_type({}) is None


def test_parse_position_mode_known_value():
    assert (
        position_util.parse_position_mode({COLUMNS.POSITION_MODE.value: "hedge_mode"})
        is enums.PositionMode.HEDGE
    )


def test_parse_position_mode_missing_key_returns_none():
    assert position_util.parse_position_mode({}) is None
