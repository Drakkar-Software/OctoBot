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
import decimal

import octobot_trading.personal_data


class TestHoldingStopCondition:
    """Tests for HoldingStopCondition"""
    
    def test_initialization(self):
        """Test HoldingStopCondition initialization"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.5,
            stop_on_inferior=True
        )
        assert condition.asset_name == "BTC"
        assert condition.amount == decimal.Decimal("10.5")
        assert condition.stop_on_inferior is True
    
    def test_initialization_with_decimal(self):
        """Test HoldingStopCondition initialization with Decimal"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="ETH",
            amount=decimal.Decimal("5.25"),
            stop_on_inferior=False
        )
        assert condition.amount == decimal.Decimal("5.25")
    
    def test_is_met_inferior_true(self):
        """Test is_met when stop_on_inferior is True and condition is met"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        # Mock exchange manager and portfolio
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")  # Less than 10.0
        )
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            assert condition.is_met(exchange_manager) is True
            assert condition._last_match_reason == "Current BTC holdings of 5.0 are lower than the 10.0 threshold."
    
    def test_is_met_inferior_false(self):
        """Test is_met when stop_on_inferior is True and condition is not met"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("15.0")  # More than 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            assert condition.is_met(exchange_manager) is False
            assert condition._last_match_reason == ""
    
    def test_is_met_superior_true(self):
        """Test is_met when stop_on_inferior is False and condition is met"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="ETH",
            amount=10.0,
            stop_on_inferior=False
        )
        
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("15.0")  # More than 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            assert condition.is_met(exchange_manager) is True
            assert condition._last_match_reason == "Current ETH holdings of 15.0 are higher than the 10.0 threshold."
    
    def test_is_met_superior_false(self):
        """Test is_met when stop_on_inferior is False and condition is not met"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="ETH",
            amount=10.0,
            stop_on_inferior=False
        )
        
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")  # Less than 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            assert condition.is_met(exchange_manager) is False
            assert condition._last_match_reason == ""
    
    def test_is_met_exact_amount_inferior(self):
        """Test is_met when holdings equal amount and stop_on_inferior is True"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("10.0")  # Equal to 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            assert condition.is_met(exchange_manager) is True
            assert condition._last_match_reason == "Current BTC holdings of 10.0 are lower than the 10.0 threshold."

    def test_get_match_reason(self):
        """Test get_match_reason returns the last match reason"""
        condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        # Initially empty
        assert condition.get_match_reason() == ""
        
        # After is_met is called and condition is met
        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            condition.is_met(exchange_manager)
            assert condition.get_match_reason() == "Current BTC holdings of 5.0 are lower than the 10.0 threshold."
