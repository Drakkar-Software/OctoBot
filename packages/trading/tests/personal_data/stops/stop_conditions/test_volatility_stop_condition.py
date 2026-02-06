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

import octobot_trading.constants as trading_constants
import octobot_trading.personal_data


class TestHistoricalMinAndMaxPrice:
    """Tests for HistoricalMinAndMaxPrice"""
    
    def test_initialization(self):
        """Test HistoricalMinAndMaxPrice initialization"""
        hist_price = octobot_trading.personal_data.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        assert hist_price.minute_ts == 12345
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("110.0")
    
    def test_update_with_new_min(self):
        """Test update method with new minimum price"""
        hist_price = octobot_trading.personal_data.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("95.0"))
        assert hist_price.min_price == decimal.Decimal("95.0")
        assert hist_price.max_price == decimal.Decimal("110.0")
    
    def test_update_with_new_max(self):
        """Test update method with new maximum price"""
        hist_price = octobot_trading.personal_data.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("115.0"))
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("115.0")
    
    def test_update_with_middle_price(self):
        """Test update method with price between min and max"""
        hist_price = octobot_trading.personal_data.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("105.0"))
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("110.0")
    
    def test_update_multiple_times(self):
        """Test multiple updates"""
        hist_price = octobot_trading.personal_data.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("100.0")
        )
        hist_price.update(decimal.Decimal("95.0"))
        hist_price.update(decimal.Decimal("120.0"))
        hist_price.update(decimal.Decimal("90.0"))
        hist_price.update(decimal.Decimal("125.0"))
        assert hist_price.min_price == decimal.Decimal("90.0")
        assert hist_price.max_price == decimal.Decimal("125.0")


class TestVolatilityStopCondition:
    """Tests for VolatilityStopCondition"""
    
    def test_initialization(self):
        """Test VolatilityStopCondition initialization"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        assert condition.symbol == "BTC/USDT"
        assert condition.period_in_minutes == 10
        assert condition.max_allowed_positive_percentage_change == decimal.Decimal("5.0")
        assert condition.max_allowed_negative_percentage_change == decimal.Decimal("3.0")
        assert condition._max_positive_ratio == decimal.Decimal("1.05")
        assert condition._max_negative_ratio == decimal.Decimal("0.97")
    
    def test_initialization_with_decimals(self):
        """Test VolatilityStopCondition initialization with Decimal values"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="ETH/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=decimal.Decimal("10.5"),
            max_allowed_negative_percentage_change=decimal.Decimal("5.5")
        )
        assert condition._max_positive_ratio == decimal.Decimal("1.105")
        assert condition._max_negative_ratio == decimal.Decimal("0.945")
    
    def test_is_met_not_enough_data(self):
        """Test is_met returns False when not enough historical data"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        exchange_manager = mock.Mock()
        
        # No data
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
        
        # Only one data point
        condition._historical_min_and_max_price_by_minute_ts.append(
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100"))
        )
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
    
    def test_is_met_positive_volatility_exceeded(self):
        """Test is_met when positive volatility threshold is exceeded"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add historical data
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with high max price (106 > 100 * 1.05)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]
        
        exchange_manager = mock.Mock()
        assert condition.is_met(exchange_manager) is True
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in condition._last_match_reason
    
    def test_is_met_negative_volatility_exceeded(self):
        """Test is_met when negative volatility threshold is exceeded"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add historical data
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with low min price (96 < 100 * 0.97)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("96"), decimal.Decimal("100")),
        ]
        
        exchange_manager = mock.Mock()
        assert condition.is_met(exchange_manager) is True
        assert "BTC/USDT reference price of 96.0 is bellow the 2 minutes average low value of 100.0 -3.0%." in condition._last_match_reason
    
    def test_is_met_within_threshold(self):
        """Test is_met when volatility is within threshold"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add historical data within threshold
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute within threshold
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("98"), decimal.Decimal("104")),
        ]
        
        exchange_manager = mock.Mock()
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
    
    def test_is_met_ignores_positive_when_zero(self):
        """Test is_met ignores positive volatility check when max_allowed_positive_percentage_change is ZERO"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=trading_constants.ZERO,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add historical data with extreme positive volatility
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with very high max price (200% increase)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("200")),
        ]
        
        exchange_manager = mock.Mock()
        # Should not trigger despite extreme positive volatility
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
    
    def test_is_met_ignores_negative_when_zero(self):
        """Test is_met ignores negative volatility check when max_allowed_negative_percentage_change is ZERO"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=0
        )
        
        # Add historical data with extreme negative volatility
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with very low min price (50% decrease)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("50"), decimal.Decimal("100")),
        ]
        
        exchange_manager = mock.Mock()
        # Should not trigger despite extreme negative volatility
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
    
    def test_is_met_both_zero_never_triggers(self):
        """Test is_met never triggers when both percentage changes are ZERO"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=0,
            max_allowed_negative_percentage_change=0
        )
        
        # Add historical data with extreme volatility in both directions
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with extreme volatility
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("10"), decimal.Decimal("1000")),
        ]
        
        exchange_manager = mock.Mock()
        # Should never trigger when both are ZERO
        assert condition.is_met(exchange_manager) is False
        assert condition._last_match_reason == ""
    
    def test_is_met_negative_zero_positive_triggers(self):
        """Test is_met can still trigger on positive when negative is ZERO"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=trading_constants.ZERO
        )
        
        # Add historical data that exceeds positive threshold
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute exceeds positive threshold (106 > 100 * 1.05)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]
        
        exchange_manager = mock.Mock()
        # Should trigger on positive volatility
        assert condition.is_met(exchange_manager) is True
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in condition._last_match_reason
    
    def test_is_met_positive_zero_negative_triggers(self):
        """Test is_met can still trigger on negative when positive is ZERO"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=trading_constants.ZERO,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add historical data that exceeds negative threshold
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute exceeds negative threshold (96 < 100 * 0.97)
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("96"), decimal.Decimal("100")),
        ]
        
        exchange_manager = mock.Mock()
        # Should trigger on negative volatility
        assert condition.is_met(exchange_manager) is True
        assert "BTC/USDT reference price of 96.0 is bellow the 2 minutes average low value of 100.0 -3.0%." in condition._last_match_reason
    
    def test_on_new_price_creates_new_minute(self):
        """Test on_new_price creates a new minute entry"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        with mock.patch('time.time', return_value=120.0):  # 2 minutes
            condition.on_new_price(decimal.Decimal("100.0"))
        
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 1
        assert condition._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("100.0")
        assert condition._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("100.0")
    
    def test_on_new_price_updates_existing_minute(self):
        """Test on_new_price updates existing minute when called multiple times"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        # Add multiple prices in the same minute
        with mock.patch('time.time', return_value=120.0):
            condition.on_new_price(decimal.Decimal("100.0"))
            condition.on_new_price(decimal.Decimal("95.0"))
            condition.on_new_price(decimal.Decimal("105.0"))
        
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 1
        assert condition._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("95.0")
        assert condition._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("105.0")
    
    def test_on_new_price_limits_history_size(self):
        """Test on_new_price limits history to period_in_minutes + 1"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=3,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Add prices for 6 different minutes (should keep only last 4)
        for minute in range(6):
            with mock.patch('time.time', return_value=float(minute * 60)):
                condition.on_new_price(decimal.Decimal("100.0"))
        
        # Should have at most period_in_minutes + 1 entries
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 4
    
    def test_update_last_historical_min_and_max_price_new_minute(self):
        """Test _update_last_historical_min_and_max_price with new minute"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        condition._update_last_historical_min_and_max_price(1, decimal.Decimal("100.0"))
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 1
        
        condition._update_last_historical_min_and_max_price(2, decimal.Decimal("105.0"))
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 2
    
    def test_update_last_historical_min_and_max_price_same_minute(self):
        """Test _update_last_historical_min_and_max_price with same minute"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        condition._update_last_historical_min_and_max_price(1, decimal.Decimal("100.0"))
        condition._update_last_historical_min_and_max_price(1, decimal.Decimal("95.0"))
        condition._update_last_historical_min_and_max_price(1, decimal.Decimal("110.0"))
        
        assert len(condition._historical_min_and_max_price_by_minute_ts) == 1
        assert condition._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("95.0")
        assert condition._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("110.0")

    def test_get_match_reason(self):
        """Test get_match_reason returns the last match reason"""
        condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        
        # Initially empty
        assert condition.get_match_reason() == ""
        
        # Add historical data that will trigger
        condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]
        
        exchange_manager = mock.Mock()
        condition.is_met(exchange_manager)
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in condition.get_match_reason()
