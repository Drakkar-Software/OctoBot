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
import decimal

import octobot_trading.errors as errors
import octobot_trading.personal_data

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestStopWatcher:
    """Tests for StopWatcher"""
    
    def test_initialization_empty_conditions(self):
        """Test StopWatcher initialization with no conditions"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        watcher = octobot_trading.personal_data.StopWatcher([], exchange_manager, callback)
        
        assert watcher.holding_stop_conditions == []
        assert watcher.volatility_stop_conditions == []
        assert watcher._exchange_manager == exchange_manager
        assert watcher._on_stop_callback == callback
        assert watcher.triggered is False
        assert watcher._stopped is False
    
    def test_initialization_with_holding_conditions(self):
        """Test StopWatcher initialization with holding conditions"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        
        assert len(watcher.holding_stop_conditions) == 1
        assert watcher.holding_stop_conditions[0] == holding_condition
        assert len(watcher.volatility_stop_conditions) == 0
    
    def test_initialization_with_volatility_conditions(self):
        """Test StopWatcher initialization with volatility conditions"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        assert len(watcher.volatility_stop_conditions) == 1
        assert watcher.volatility_stop_conditions[0] == volatility_condition
        assert len(watcher.holding_stop_conditions) == 0
    
    def test_initialization_with_mixed_conditions(self):
        """Test StopWatcher initialization with mixed conditions"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher(
            [holding_condition, volatility_condition],
            exchange_manager,
            callback
        )
        
        assert len(watcher.holding_stop_conditions) == 1
        assert len(watcher.volatility_stop_conditions) == 1
    
    async def test_start(self):
        """Test StopWatcher start method"""
        exchange_manager = mock.Mock()
        exchange_manager.id = "test_exchange"
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        watcher.triggered = True
        watcher._stopped = True
        
        # Mock is_met to return False so initialization doesn't raise
        with mock.patch.object(holding_condition, 'is_met', return_value=False):
            with mock.patch.object(watcher, '_subscribe_to_exchange_balance') as mock_subscribe:
                await watcher.start()
                
                assert watcher.triggered is False
                assert watcher._stopped is False
                mock_subscribe.assert_called_once_with("test_exchange")
                callback.assert_not_called()
    
    async def test_start_holding_condition_met_at_start(self):
        """Test start raises StopTriggered when holding condition is met at initialization"""
        exchange_manager = mock.Mock()
        exchange_manager.id = "test_exchange"
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        
        # Mock is_met to return True so initialization raises StopTriggered
        with mock.patch.object(holding_condition, 'is_met', return_value=True):
            with mock.patch.object(watcher, '_subscribe_to_exchange_balance') as mock_subscribe:
                with pytest.raises(errors.StopTriggered) as exc_info:
                    await watcher.start()
                
                assert "is met at initialization" in str(exc_info.value)
                assert watcher.triggered is True
                callback.assert_awaited_once_with(holding_condition)
                # Should not subscribe when condition is met at initialization
                mock_subscribe.assert_not_called()
    
    async def test_start_multiple_holding_conditions_one_met(self):
        """Test start raises StopTriggered when one of multiple holding conditions is met"""
        exchange_manager = mock.Mock()
        exchange_manager.id = "test_exchange"
        callback = mock.AsyncMock()
        
        holding_condition1 = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        holding_condition2 = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="ETH",
            amount=5.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher(
            [holding_condition1, holding_condition2],
            exchange_manager,
            callback
        )
        
        # Mock first condition as not met, second as met
        with mock.patch.object(holding_condition1, 'is_met', return_value=False):
            with mock.patch.object(holding_condition2, 'is_met', return_value=True):
                with mock.patch.object(watcher, '_subscribe_to_exchange_balance') as mock_subscribe:
                    with pytest.raises(errors.StopTriggered) as exc_info:
                        await watcher.start()
                    
                    assert "is met at initialization" in str(exc_info.value)
                    assert watcher.triggered is True
                    callback.assert_awaited_once_with(holding_condition2)
                    mock_subscribe.assert_not_called()
    
    async def test_start_no_holding_conditions(self):
        """Test start without holding conditions doesn't subscribe"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        watcher = octobot_trading.personal_data.StopWatcher([], exchange_manager, callback)
        
        with mock.patch.object(watcher, '_subscribe_to_exchange_balance') as mock_subscribe:
            await watcher.start()
            
            mock_subscribe.assert_not_called()
    
    def test_should_subscribe_to_price_updates_true(self):
        """Test should_subscribe_to_price_updates returns True for matching symbol"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        assert watcher.should_subscribe_to_price_updates("BTC/USDT") is True
    
    def test_should_subscribe_to_price_updates_false(self):
        """Test should_subscribe_to_price_updates returns False for non-matching symbol"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        assert watcher.should_subscribe_to_price_updates("ETH/USDT") is False
    
    def test_should_subscribe_to_price_updates_multiple_conditions(self):
        """Test should_subscribe_to_price_updates with multiple conditions"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        volatility_condition1 = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        volatility_condition2 = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="ETH/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher(
            [volatility_condition1, volatility_condition2],
            exchange_manager,
            callback
        )
        
        assert watcher.should_subscribe_to_price_updates("BTC/USDT") is True
        assert watcher.should_subscribe_to_price_updates("ETH/USDT") is True
        assert watcher.should_subscribe_to_price_updates("XRP/USDT") is False
    
    async def test_on_new_price_updates_condition(self):
        """Test on_new_price updates volatility condition"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        with mock.patch('time.time', return_value=120.0):
            await watcher.on_new_price("BTC/USDT", decimal.Decimal("100.0"))
        
        assert len(volatility_condition._historical_min_and_max_price_by_minute_ts) == 1
    
    async def test_on_new_price_triggers_condition(self):
        """Test on_new_price triggers stop condition when met"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=2,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        # Pre-populate with historical data
        volatility_condition._historical_min_and_max_price_by_minute_ts = [
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(1, decimal.Decimal("100"), decimal.Decimal("100")),
            octobot_trading.personal_data.HistoricalMinAndMaxPrice(2, decimal.Decimal("100"), decimal.Decimal("100")),
        ]
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        # Add a price that exceeds the threshold
        with mock.patch('time.time', return_value=180.0):
            with pytest.raises(errors.StopTriggered):
                await watcher.on_new_price("BTC/USDT", decimal.Decimal("106.0"))
        
        assert watcher.triggered is True
        callback.assert_awaited_once()
    
    async def test_on_new_price_skips_when_triggered(self):
        """Test on_new_price does nothing when already triggered"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        watcher.triggered = True
        
        await watcher.on_new_price("BTC/USDT", decimal.Decimal("100.0"))
        
        assert len(volatility_condition._historical_min_and_max_price_by_minute_ts) == 0
        callback.assert_not_called()
    
    async def test_on_new_price_skips_when_stopped(self):
        """Test on_new_price does nothing when stopped"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        watcher._stopped = True
        
        await watcher.on_new_price("BTC/USDT", decimal.Decimal("100.0"))
        
        assert len(volatility_condition._historical_min_and_max_price_by_minute_ts) == 0
        callback.assert_not_called()
    
    async def test_on_new_price_wrong_symbol(self):
        """Test on_new_price with non-matching symbol"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        volatility_condition = octobot_trading.personal_data.VolatilityStopCondition(
            symbol="BTC/USDT",
            period_in_minutes=10,
            max_allowed_positive_percentage_change=5.0,
            max_allowed_negative_percentage_change=-3.0
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([volatility_condition], exchange_manager, callback)
        
        with mock.patch('time.time', return_value=120.0):
            await watcher.on_new_price("ETH/USDT", decimal.Decimal("100.0"))
        
        # Should not update the BTC/USDT condition
        assert len(volatility_condition._historical_min_and_max_price_by_minute_ts) == 0
    
    async def test_stop(self):
        """Test stop method"""
        exchange_manager = mock.Mock()
        callback = mock.Mock()
        
        watcher = octobot_trading.personal_data.StopWatcher([], exchange_manager, callback)
        
        assert watcher._stopped is False
        await watcher.stop()
        assert watcher._stopped is True
    
    async def test_on_balance_update_triggers_condition(self):
        """Test _on_balance_update triggers holding condition when met"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")  # Less than 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            await watcher._on_balance_update("exchange", "exchange_id", {})
        
        assert watcher.triggered is True
        callback.assert_awaited_once()
    
    async def test_on_balance_update_skips_when_triggered(self):
        """Test _on_balance_update does nothing when already triggered"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        watcher.triggered = True
        
        await watcher._on_balance_update("exchange", "exchange_id", {})
        
        callback.assert_not_called()
    
    async def test_on_balance_update_skips_when_stopped(self):
        """Test _on_balance_update does nothing when stopped"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        watcher._stopped = True
        
        await watcher._on_balance_update("exchange", "exchange_id", {})
        
        callback.assert_not_called()
    
    async def test_on_balance_update_not_met(self):
        """Test _on_balance_update when condition is not met"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        holding_condition = octobot_trading.personal_data.HoldingStopCondition(
            asset_name="BTC",
            amount=10.0,
            stop_on_inferior=True
        )
        
        watcher = octobot_trading.personal_data.StopWatcher([holding_condition], exchange_manager, callback)
        
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("15.0")  # More than 10.0
        )
        
        with mock.patch.object(exchange_manager.exchange_personal_data.portfolio_manager.portfolio, 'get_currency_portfolio', return_value=portfolio_currency):
            await watcher._on_balance_update("exchange", "exchange_id", {})
        
        assert watcher.triggered is False
        callback.assert_not_called()
    
    async def test_on_stop_triggered(self):
        """Test _on_stop_triggered sets triggered flag and calls callback"""
        exchange_manager = mock.Mock()
        callback = mock.AsyncMock()
        
        watcher = octobot_trading.personal_data.StopWatcher([], exchange_manager, callback)
        
        test_condition = mock.Mock()
        
        assert watcher.triggered is False
        await watcher._on_stop_triggered(test_condition)
        
        assert watcher.triggered is True
        callback.assert_awaited_once_with(test_condition)
