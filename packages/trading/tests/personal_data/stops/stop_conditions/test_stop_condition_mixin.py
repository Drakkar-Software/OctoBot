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
import mock

import octobot_trading.personal_data


class TestStopConditionMixin:
    """Tests for StopConditionMixin"""
    
    def test_is_met_not_implemented(self):
        """Test that is_met raises NotImplementedError"""
        mixin = octobot_trading.personal_data.StopConditionMixin()
        with pytest.raises(NotImplementedError):
            mixin.is_met(mock.Mock())

    def test_get_match_reason_not_implemented(self):
        """Test that get_match_reason raises NotImplementedError"""
        mixin = octobot_trading.personal_data.StopConditionMixin()
        with pytest.raises(NotImplementedError):
            mixin.get_match_reason()
