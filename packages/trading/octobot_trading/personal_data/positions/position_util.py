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


def parse_position_status(raw_position):
    try:
        return enums.PositionStatus(raw_position[enums.ExchangeConstantsPositionColumns.STATUS.value])
    except KeyError:
        return None


def parse_position_side(raw_position):
    try:
        return enums.PositionSide(raw_position[enums.ExchangeConstantsPositionColumns.SIDE.value])
    except KeyError:
        return None


def parse_position_margin_type(raw_position):
    try:
        return enums.MarginType(raw_position[enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value])
    except KeyError:
        return None


def parse_position_mode(raw_position):
    try:
        return enums.PositionMode(raw_position[enums.ExchangeConstantsPositionColumns.POSITION_MODE.value])
    except KeyError:
        return None
