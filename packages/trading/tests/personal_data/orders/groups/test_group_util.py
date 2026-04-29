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
import pytest

import octobot_trading.personal_data as personal_data


def test_get_group_class():
    with pytest.raises(KeyError):
        personal_data.get_group_class("")
    with pytest.raises(KeyError):
        personal_data.get_group_class("hello")
    assert personal_data.get_group_class(personal_data.OneCancelsTheOtherOrderGroup.__name__) is \
           personal_data.OneCancelsTheOtherOrderGroup
    assert personal_data.get_group_class(personal_data.BalancedTakeProfitAndStopOrderGroup.__name__) is \
           personal_data.BalancedTakeProfitAndStopOrderGroup
