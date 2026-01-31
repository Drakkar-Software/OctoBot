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
import mock
import pytest

import octobot_trading.personal_data as personal_data


@pytest.fixture
def trader():
    return mock.Mock(exchange_manager=mock.Mock())


def test_create_trailing_profile():
    with pytest.raises(NotImplementedError):
        personal_data.create_trailing_profile("Plop", {})
    with pytest.raises(TypeError):
        personal_data.create_trailing_profile(
            personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT, {}
        )
    assert isinstance(personal_data.create_trailing_profile(
        personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT, {"steps": []}
    ), personal_data.FilledTakeProfitTrailingProfile)

    trailing_profile = personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(price, price, True)
        for price in (10000, 12000, 13000)
    ])
    assert personal_data.create_trailing_profile(
        personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT, trailing_profile.to_dict()
    ) == trailing_profile


def test_create_filled_take_profit_trailing_profile(trader):
    with pytest.raises(ValueError):
        personal_data.create_filled_take_profit_trailing_profile(decimal.Decimal("0.5"), [])
    order_1 = personal_data.Order(trader)
    order_1.trigger_above = True
    order_1.origin_price = decimal.Decimal(1)
    order_2 = personal_data.Order(trader)
    order_2.trigger_above = True
    order_2.origin_price = decimal.Decimal(2)
    trailing_profile = personal_data.create_filled_take_profit_trailing_profile(
        decimal.Decimal("0.5"), [order_1, order_2]
    )
    assert trailing_profile == personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(0.5, 1, True),
        personal_data.TrailingPriceStep(1, 2, True),
    ])

    order_1.trigger_above = False
    order_1.origin_price = decimal.Decimal(1)
    order_2 = personal_data.Order(trader)
    order_2.trigger_above = False
    order_2.origin_price = decimal.Decimal(2)
    trailing_profile = personal_data.create_filled_take_profit_trailing_profile(
        decimal.Decimal("0.5"), [order_1, order_2]
    )
    assert trailing_profile == personal_data.FilledTakeProfitTrailingProfile([
        personal_data.TrailingPriceStep(0.5, 1, False),
        personal_data.TrailingPriceStep(1, 2, False),
    ])

    # incompatible trigger_above values (can't be both True and False)
    order_2.trigger_above = True
    with pytest.raises(ValueError):
        personal_data.create_filled_take_profit_trailing_profile(decimal.Decimal("0.5"), [order_1, order_2])
