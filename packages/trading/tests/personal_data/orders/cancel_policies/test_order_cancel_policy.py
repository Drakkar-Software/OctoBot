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
import mock
import pytest

import octobot_trading.personal_data.orders.cancel_policies.order_cancel_policy as order_cancel_policy_import


class TestOrderCancelPolicy:
    """Test the base OrderCancelPolicy class"""

    def test_should_cancel_not_implemented(self):
        """Test that should_cancel raises NotImplementedError in base class"""
        policy = order_cancel_policy_import.OrderCancelPolicy()
        order_mock = mock.Mock()
        
        with pytest.raises(NotImplementedError):
            policy.should_cancel(order_mock)
