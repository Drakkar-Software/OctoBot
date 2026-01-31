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
import decimal

import pytest

import octobot_trading.errors
import octobot_trading.personal_data as personal_data


@pytest.fixture
def trigger_above_filled_tp_trailing_profile():
    return personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price + 1, price, True)
        for price in (12000, 10000, 13000, 15000)  # on purpose not ordered
    ])


@pytest.fixture
def trigger_bellow_filled_tp_trailing_profile():
    return personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price + 1, price, False)
        for price in (12000, 10000, 13000, 15000)  # on purpose not ordered
    ])


def test_get_type(trigger_above_filled_tp_trailing_profile):
    assert trigger_above_filled_tp_trailing_profile.get_type() is personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT


def test_update_and_get_trailing_price_trigger_above(trigger_above_filled_tp_trailing_profile):
    # no trigger_price_reached
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("19")) is None

    # first trigger price reached
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("10000")) \
           == decimal.Decimal("10001")

    # first trigger price reached again: no new trailing price
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("10000")) \
           is None

    # third price reached (second price is skipped)
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("13300")) \
           == decimal.Decimal("13001")

    # last price reached
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("16300")) \
           == decimal.Decimal("15001")

    # now exhausted
    assert trigger_above_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("13300")) is None

def test_update_and_get_trailing_price_trigger_bellow(trigger_bellow_filled_tp_trailing_profile):
    # no trigger_price_reached
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("190000")) is None

    # first trigger price reached
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("15000")) \
           == decimal.Decimal("15001")

    # first trigger price reached again: no new trailing price
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("15000")) \
           is None

    # third price reached (second price is skipped)
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("11300")) \
           == decimal.Decimal("12001")

    # last price reached
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("6300")) \
           == decimal.Decimal("10001")

    # now exhausted
    assert trigger_bellow_filled_tp_trailing_profile.update_and_get_trailing_price(decimal.Decimal("6300")) is None
