#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import mock
import decimal
import pytest

import octobot.errors as errors
import octobot_trading.constants as trading_constants

import tentacles.Automation.trigger_events.volatility_threshold_event.volatility_threshold as volatility_threshold


class TestHistoricalMinAndMaxPrice:
    """Tests for HistoricalMinAndMaxPrice"""

    def test_initialization(self):
        """Test HistoricalMinAndMaxPrice initialization"""
        hist_price = volatility_threshold.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        assert hist_price.minute_ts == 12345
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("110.0")

    def test_update_with_new_min(self):
        """Test update method with new minimum price"""
        hist_price = volatility_threshold.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("95.0"))
        assert hist_price.min_price == decimal.Decimal("95.0")
        assert hist_price.max_price == decimal.Decimal("110.0")

    def test_update_with_new_max(self):
        """Test update method with new maximum price"""
        hist_price = volatility_threshold.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("115.0"))
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("115.0")

    def test_update_with_middle_price(self):
        """Test update method with price between min and max"""
        hist_price = volatility_threshold.HistoricalMinAndMaxPrice(
            minute_ts=12345,
            min_price=decimal.Decimal("100.0"),
            max_price=decimal.Decimal("110.0")
        )
        hist_price.update(decimal.Decimal("105.0"))
        assert hist_price.min_price == decimal.Decimal("100.0")
        assert hist_price.max_price == decimal.Decimal("110.0")

    def test_update_multiple_times(self):
        """Test multiple updates"""
        hist_price = volatility_threshold.HistoricalMinAndMaxPrice(
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


class TestVolatilityThresholdChecker:
    """Tests for VolatilityThresholdChecker"""

    def _create_checker(
        self,
        symbol="BTC/USDT",
        period_in_minutes=10,
        max_allowed_positive_percentage_change=5.0,
        max_allowed_negative_percentage_change=3.0,
    ):
        """Create a VolatilityThresholdChecker instance with computed ratios.

        Ratios are computed manually to allow testing with zero percentage
        values (validate_config rejects zero values).
        """
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol=symbol,
            period_in_minutes=period_in_minutes,
            max_allowed_positive_percentage_change=decimal.Decimal(str(max_allowed_positive_percentage_change)),
            max_allowed_negative_percentage_change=decimal.Decimal(str(max_allowed_negative_percentage_change)),
        )
        checker._max_positive_ratio = (
            trading_constants.ONE + checker.max_allowed_positive_percentage_change / decimal.Decimal(100)
        )
        checker._max_negative_ratio = (
            trading_constants.ONE - checker.max_allowed_negative_percentage_change / decimal.Decimal(100)
        )
        return checker

    def test_initialization(self):
        """Test VolatilityThresholdChecker initialization"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        assert checker.symbol == "BTC/USDT"
        assert checker.period_in_minutes == 10
        assert checker.max_allowed_positive_percentage_change == decimal.Decimal("5.0")
        assert checker.max_allowed_negative_percentage_change == decimal.Decimal("3.0")
        assert checker._max_positive_ratio == decimal.Decimal("1.05")
        assert checker._max_negative_ratio == decimal.Decimal("0.97")

    def test_initialization_with_decimals(self):
        """Test VolatilityThresholdChecker initialization with Decimal values"""
        checker = self._create_checker(
            symbol="ETH/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=10.5,
            max_allowed_negative_percentage_change=5.5
        )
        assert checker._max_positive_ratio == decimal.Decimal("1.105")
        assert checker._max_negative_ratio == decimal.Decimal("0.945")

    def test_validate_config_valid(self):
        """Test validate_config succeeds and sets ratios for valid config"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=decimal.Decimal("5.0"),
            max_allowed_negative_percentage_change=decimal.Decimal("3.0"),
        )
        checker.validate_config()
        assert checker._max_positive_ratio == decimal.Decimal("1.05")
        assert checker._max_negative_ratio == decimal.Decimal("0.97")

    def test_validate_config_missing_symbol(self):
        """Test validate_config raises when symbol is not set"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol=None,
            period_in_minutes=10,
            max_allowed_positive_percentage_change=decimal.Decimal("5.0"),
            max_allowed_negative_percentage_change=decimal.Decimal("3.0"),
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="symbol and period in minutes must be set"):
            checker.validate_config()

    def test_validate_config_missing_period(self):
        """Test validate_config raises when period_in_minutes is not set"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=0,
            max_allowed_positive_percentage_change=decimal.Decimal("5.0"),
            max_allowed_negative_percentage_change=decimal.Decimal("3.0"),
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="symbol and period in minutes must be set"):
            checker.validate_config()

    def test_validate_config_zero_positive_percentage(self):
        """Test validate_config raises when max_allowed_positive_percentage_change is zero"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=trading_constants.ZERO,
            max_allowed_negative_percentage_change=decimal.Decimal("3.0"),
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="max allowed positive percentage change must be > 0"):
            checker.validate_config()

    def test_validate_config_negative_positive_percentage(self):
        """Test validate_config raises when max_allowed_positive_percentage_change is negative"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=decimal.Decimal("-1.0"),
            max_allowed_negative_percentage_change=decimal.Decimal("3.0"),
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="max allowed positive percentage change must be > 0"):
            checker.validate_config()

    def test_validate_config_zero_negative_percentage(self):
        """Test validate_config raises when max_allowed_negative_percentage_change is zero"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=decimal.Decimal("5.0"),
            max_allowed_negative_percentage_change=trading_constants.ZERO,
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="max allowed negative percentage change must be > 0"):
            checker.validate_config()

    def test_validate_config_negative_negative_percentage(self):
        """Test validate_config raises when max_allowed_negative_percentage_change is negative"""
        checker = volatility_threshold.VolatilityThresholdChecker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=decimal.Decimal("5.0"),
            max_allowed_negative_percentage_change=decimal.Decimal("-2.0"),
        )
        with pytest.raises(errors.InvalidAutomationConfigError, match="max allowed negative percentage change must be > 0"):
            checker.validate_config()

    def test_check_threshold_not_enough_data(self):
        """Test _check_threshold returns False when not enough historical data"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # No data
        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

        # Only one data point
        checker._historical_min_and_max_price_by_minute_ts.append(
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100"))
        )
        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

    def test_check_threshold_positive_volatility_exceeded(self):
        """Test _check_threshold when positive volatility threshold is exceeded"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # Add historical data
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with high max price (106 > 100 * 1.05)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is True
        assert reason is not None
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in reason

    def test_check_threshold_negative_volatility_exceeded(self):
        """Test _check_threshold when negative volatility threshold is exceeded"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # Add historical data
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with low min price (96 < 100 * 0.97)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("96"), decimal.Decimal("100")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is True
        assert reason is not None
        assert "BTC/USDT reference price of 96.0 is bellow the 2 minutes average low value of 100.0 -3.0%." in reason

    def test_check_threshold_within_threshold(self):
        """Test _check_threshold when volatility is within threshold"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # Add historical data within threshold
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute within threshold
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("98"), decimal.Decimal("104")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

    def test_check_threshold_ignores_positive_when_zero(self):
        """Test _check_threshold ignores positive volatility check when max_allowed_positive_percentage_change is ZERO"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=trading_constants.ZERO,
            max_allowed_negative_percentage_change=3.0
        )

        # Add historical data with extreme positive volatility
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with very high max price (200% increase)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("200")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

    def test_check_threshold_ignores_negative_when_zero(self):
        """Test _check_threshold ignores negative volatility check when max_allowed_negative_percentage_change is ZERO"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=0
        )

        # Add historical data with extreme negative volatility
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with very low min price (50% decrease)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("50"), decimal.Decimal("100")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

    def test_check_threshold_both_zero_never_triggers(self):
        """Test _check_threshold never triggers when both percentage changes are ZERO"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=0,
            max_allowed_negative_percentage_change=0
        )

        # Add historical data with extreme volatility in both directions
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute with extreme volatility
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("10"), decimal.Decimal("1000")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is False
        assert reason is None

    def test_check_threshold_negative_zero_positive_triggers(self):
        """Test _check_threshold can still trigger on positive when negative is ZERO"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=trading_constants.ZERO
        )

        # Add historical data that exceeds positive threshold
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute exceeds positive threshold (106 > 100 * 1.05)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is True
        assert reason is not None
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in reason

    def test_check_threshold_positive_zero_negative_triggers(self):
        """Test _check_threshold can still trigger on negative when positive is ZERO"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=trading_constants.ZERO,
            max_allowed_negative_percentage_change=3.0
        )

        # Add historical data that exceeds negative threshold
        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            # Current minute exceeds negative threshold (96 < 100 * 0.97)
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("96"), decimal.Decimal("100")),
        ]

        is_met, reason = checker._check_threshold()
        # Should trigger on negative volatility
        assert is_met is True
        assert reason is not None
        assert "BTC/USDT reference price of 96.0 is bellow the 2 minutes average low value of 100.0 -3.0%." in reason

    def test_on_new_price_creates_new_minute(self):
        """Test on_new_price creates a new minute entry"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        with mock.patch('time.time', return_value=120.0):  # 2 minutes
            checker.on_new_price(decimal.Decimal("100.0"))

        assert len(checker._historical_min_and_max_price_by_minute_ts) == 1
        assert checker._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("100.0")
        assert checker._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("100.0")

    def test_on_new_price_updates_existing_minute(self):
        """Test on_new_price updates existing minute when called multiple times"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # Add multiple prices in the same minute
        with mock.patch('time.time', return_value=120.0):
            checker.on_new_price(decimal.Decimal("100.0"))
            checker.on_new_price(decimal.Decimal("95.0"))
            checker.on_new_price(decimal.Decimal("105.0"))

        assert len(checker._historical_min_and_max_price_by_minute_ts) == 1
        assert checker._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("95.0")
        assert checker._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("105.0")

    def test_on_new_price_limits_history_size(self):
        """Test on_new_price limits history to period_in_minutes + 1"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=3,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        # Add prices for 6 different minutes (should keep only last 4)
        for minute in range(6):
            with mock.patch('time.time', return_value=float(minute * 60)):
                checker.on_new_price(decimal.Decimal("100.0"))

        # Should have at most period_in_minutes + 1 entries
        assert len(checker._historical_min_and_max_price_by_minute_ts) == 4

    def test_update_last_historical_min_and_max_price_new_minute(self):
        """Test _update_last_historical_min_and_max_price with new minute"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        checker._update_last_historical_min_and_max_price(1, decimal.Decimal("100.0"))
        assert len(checker._historical_min_and_max_price_by_minute_ts) == 1

        checker._update_last_historical_min_and_max_price(2, decimal.Decimal("105.0"))
        assert len(checker._historical_min_and_max_price_by_minute_ts) == 2

    def test_update_last_historical_min_and_max_price_same_minute(self):
        """Test _update_last_historical_min_and_max_price with same minute"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        checker._update_last_historical_min_and_max_price(1, decimal.Decimal("100.0"))
        checker._update_last_historical_min_and_max_price(1, decimal.Decimal("95.0"))
        checker._update_last_historical_min_and_max_price(1, decimal.Decimal("110.0"))

        assert len(checker._historical_min_and_max_price_by_minute_ts) == 1
        assert checker._historical_min_and_max_price_by_minute_ts[0].min_price == decimal.Decimal("95.0")
        assert checker._historical_min_and_max_price_by_minute_ts[0].max_price == decimal.Decimal("110.0")

    def test_check_threshold_returns_reason_in_tuple(self):
        """Test _check_threshold returns the reason as second element of tuple when met"""
        checker = self._create_checker(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )

        checker._historical_min_and_max_price_by_minute_ts = [
            volatility_threshold.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
            volatility_threshold.HistoricalMinAndMaxPrice(3, decimal.Decimal("100"), decimal.Decimal("106")),
        ]

        is_met, reason = checker._check_threshold()
        assert is_met is True
        assert reason is not None
        assert "BTC/USDT reference price of 106.0 is above the 2 minutes average high value of 100.0 +5.0%." in reason


class TestVolatilityThreshold:
    """Tests for VolatilityThreshold"""

    def _create_trigger(
        self,
        symbol="BTC/USDT",
        period_in_minutes=10,
        max_allowed_positive_percentage_change=5.0,
        max_allowed_negative_percentage_change=3.0,
        exchange="binance"
    ):
        """Create and configure a VolatilityThreshold instance."""
        trigger = volatility_threshold.VolatilityThreshold()
        trigger.apply_config({
            volatility_threshold.VolatilityThreshold.EXCHANGE: exchange,
            volatility_threshold.VolatilityThreshold.SYMBOL: symbol,
            volatility_threshold.VolatilityThreshold.PERIOD_IN_MINUTES: period_in_minutes,
            volatility_threshold.VolatilityThreshold.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE: max_allowed_positive_percentage_change,
            volatility_threshold.VolatilityThreshold.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE: max_allowed_negative_percentage_change,
        })
        return trigger

    def test_apply_config_sets_exchange(self):
        """Test apply_config sets exchange on the trigger"""
        trigger = self._create_trigger(exchange="binance")
        assert trigger.exchange == "binance"

    def test_apply_config_sets_exchange_none_when_empty(self):
        """Test apply_config sets exchange to None when empty string"""
        trigger = self._create_trigger(exchange="")
        assert trigger.exchange is None

    def test_apply_config_populates_checker(self):
        """Test apply_config correctly configures the internal VolatilityThresholdChecker"""
        trigger = self._create_trigger(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=3.0
        )
        checker = trigger.volatility_threshold_checker
        assert checker.symbol == "BTC/USDT"
        assert checker.period_in_minutes == 10
        assert checker.max_allowed_positive_percentage_change == decimal.Decimal("5.0")
        assert checker.max_allowed_negative_percentage_change == decimal.Decimal("3.0")
        assert checker._max_positive_ratio == decimal.Decimal("1.05")
        assert checker._max_negative_ratio == decimal.Decimal("0.97")

    def test_apply_config_populates_checker_with_decimals(self):
        """Test apply_config correctly computes ratios with decimal values"""
        trigger = self._create_trigger(
            symbol="ETH/USDT",
            period_in_minutes=5,
            max_allowed_positive_percentage_change=10.5,
            max_allowed_negative_percentage_change=5.5
        )
        checker = trigger.volatility_threshold_checker
        assert checker._max_positive_ratio == decimal.Decimal("1.105")
        assert checker._max_negative_ratio == decimal.Decimal("0.945")
