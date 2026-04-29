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

import octobot_trading.personal_data.orders.cancel_policies.cancel_policy_factory as cancel_policy_factory_import
import octobot_trading.personal_data.orders.cancel_policies.expiration_time_order_cancel_policy as expiration_time_order_cancel_policy_import
import octobot_trading.personal_data.orders.cancel_policies.chained_order_filling_price_order_cancel_policy as chained_order_filling_price_order_cancel_policy_import
import octobot_trading.errors as errors


class TestCancelPolicyFactory:
    """Test the cancel_policy_factory module"""

    def test_create_expiration_time_order_cancel_policy(self):
        """Test creating ExpirationTimeOrderCancelPolicy from factory"""
        policy = cancel_policy_factory_import.create_cancel_policy(
            "ExpirationTimeOrderCancelPolicy",
            {"expiration_time": 1000.0}
        )
        
        assert isinstance(policy, expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy)
        assert policy.expiration_time == 1000.0

    def test_create_chained_order_filling_price_order_cancel_policy(self):
        """Test creating ChainedOrderFillingPriceOrderCancelPolicy from factory"""
        policy = cancel_policy_factory_import.create_cancel_policy(
            "ChainedOrderFillingPriceOrderCancelPolicy",
            {}
        )
        
        assert isinstance(policy, chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy)

    def test_create_chained_order_filling_price_order_cancel_policy_with_none_kwargs(self):
        """Test creating ChainedOrderFillingPriceOrderCancelPolicy with None kwargs"""
        policy = cancel_policy_factory_import.create_cancel_policy(
            "ChainedOrderFillingPriceOrderCancelPolicy",
            None
        )
        
        assert isinstance(policy, chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy)

    def test_create_chained_order_filling_price_order_cancel_policy_with_empty_kwargs(self):
        """Test creating ChainedOrderFillingPriceOrderCancelPolicy with empty kwargs"""
        policy = cancel_policy_factory_import.create_cancel_policy(
            "ChainedOrderFillingPriceOrderCancelPolicy",
            {}
        )
        
        assert isinstance(policy, chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy)

    def test_create_unknown_policy_raises_not_implemented_error(self):
        """Test that creating unknown policy raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            cancel_policy_factory_import.create_cancel_policy(
                "UnknownPolicy",
                {}
            )
        
        assert "Unsupported cancel policy class name: UnknownPolicy" in str(exc_info.value)

    def test_create_expiration_time_order_cancel_policy_with_none_kwargs(self):
        """Test creating ExpirationTimeOrderCancelPolicy with None kwargs"""
        # This should fail because expiration_time is required
        with pytest.raises(errors.InvalidCancelPolicyError) as exc_info:
            cancel_policy_factory_import.create_cancel_policy(
                "ExpirationTimeOrderCancelPolicy",
                None
            )
        
        assert "Invalid kwargs for ExpirationTimeOrderCancelPolicy" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, TypeError)

    def test_create_expiration_time_order_cancel_policy_with_invalid_kwargs(self):
        """Test creating ExpirationTimeOrderCancelPolicy with invalid kwargs"""
        with pytest.raises(errors.InvalidCancelPolicyError) as exc_info:
            cancel_policy_factory_import.create_cancel_policy(
                "ExpirationTimeOrderCancelPolicy",
                {"invalid_param": "value"}
            )
        
        assert "Invalid kwargs for ExpirationTimeOrderCancelPolicy" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, TypeError)

    def test_create_chained_order_filling_price_order_cancel_policy_with_invalid_kwargs(self):
        """Test creating ChainedOrderFillingPriceOrderCancelPolicy with invalid kwargs"""
        with pytest.raises(errors.InvalidCancelPolicyError) as exc_info:
            cancel_policy_factory_import.create_cancel_policy(
                "ChainedOrderFillingPriceOrderCancelPolicy",
                {"invalid_param": "value"}
            )
        
        assert "Invalid kwargs for ChainedOrderFillingPriceOrderCancelPolicy" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, TypeError)
