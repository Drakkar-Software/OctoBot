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
import decimal
import asyncio
import mock

import octobot_trading.enums as enums
import octobot_trading.personal_data


@pytest.fixture
def portfolio():
    """Create a real Portfolio instance for testing."""
    portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    # Set up portfolio with various currencies
    portfolio.update_portfolio_from_balance({
        "BTC": {
            "available": decimal.Decimal("100"),
            "total": decimal.Decimal("100")
        },
        "ETH": {
            "available": decimal.Decimal("150"),
            "total": decimal.Decimal("150")
        },
        "USDT": {
            "available": decimal.Decimal("1000"),
            "total": decimal.Decimal("1000")
        }
    }, force_replace=True)
    return portfolio


@pytest.fixture
def mock_trader():
    """Create a mock trader with exchange_manager for order creation."""
    mock_exchange_manager = mock.Mock(
        is_future=False,
        get_exchange_quote_and_base=mock.Mock(return_value=("BTC", "USDT"))
    )
    
    mock_trader = mock.Mock()
    mock_trader.exchange_manager = mock_exchange_manager
    
    return mock_trader


@pytest.fixture
def buy_order(mock_trader):
    """Create a buy order for testing."""
    order = octobot_trading.personal_data.BuyLimitOrder(mock_trader)
    order.update(
        order_type=enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("50000"),
        quantity=decimal.Decimal("1"),
        price=decimal.Decimal("50000")
    )
    return order


@pytest.fixture
def sell_order(mock_trader):
    """Create a sell order for testing."""
    order = octobot_trading.personal_data.SellLimitOrder(mock_trader)
    order.update(
        order_type=enums.TraderOrderType.SELL_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("50000"),
        quantity=decimal.Decimal("0.5"),
        price=decimal.Decimal("50000")
    )
    return order


def test_filled_order_update_event_instantiation(buy_order):
    """Test that FilledOrderUpdateEvent can be instantiated."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(buy_order)
    
    assert event is not None
    assert isinstance(event, octobot_trading.personal_data.FilledOrderUpdateEvent)
    assert isinstance(event, octobot_trading.personal_data.PortfolioUpdateEvent)
    assert isinstance(event, asyncio.Event)


def test_filled_order_update_event_initialization_values(buy_order, sell_order):
    """Test that FilledOrderUpdateEvent stores correct values during initialization."""
    # Test with buy order
    buy_event = octobot_trading.personal_data.FilledOrderUpdateEvent(buy_order)
    
    assert buy_event.origin_quantity == decimal.Decimal("1")
    assert buy_event.origin_price == decimal.Decimal("50000")
    assert buy_event.side == enums.TradeOrderSide.BUY
    assert buy_event.symbol == "BTC/USDT"
    
    # Test with sell order
    sell_event = octobot_trading.personal_data.FilledOrderUpdateEvent(sell_order)
    
    assert sell_event.origin_quantity == decimal.Decimal("0.5")
    assert sell_event.origin_price == decimal.Decimal("50000")
    assert sell_event.side == enums.TradeOrderSide.SELL
    assert sell_event.symbol == "BTC/USDT"


def test_futures_not_supported(mock_trader):
    """Test that FilledOrderUpdateEvent raises NotImplementedError for futures."""
    mock_trader.exchange_manager.is_future = True
    
    order = octobot_trading.personal_data.BuyLimitOrder(mock_trader)
    order.update(
        order_type=enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("50000"),
        quantity=decimal.Decimal("1"),
        price=decimal.Decimal("50000")
    )
    
    with pytest.raises(NotImplementedError, match="Futures are not supported yet"):
        octobot_trading.personal_data.FilledOrderUpdateEvent(order)


def test_get_checked_asset_available_amount_buy(portfolio, buy_order):
    """Test _get_checked_asset_available_amount() for BUY orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(buy_order)
    
    # For BUY orders, should check base currency (BTC)
    available_amount = event._get_checked_asset_available_amount(portfolio)
    assert available_amount == decimal.Decimal("100")


def test_get_checked_asset_available_amount_sell(portfolio, sell_order):
    """Test _get_checked_asset_available_amount() for SELL orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(sell_order)
    
    # For SELL orders, should check quote currency (USDT)
    available_amount = event._get_checked_asset_available_amount(portfolio)
    assert available_amount == decimal.Decimal("1000")


def test_is_resolved_buy_order(portfolio, buy_order):
    """Test is_resolved() for BUY orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(buy_order)
    
    # For BUY orders: checked_amount = origin_quantity = 1
    # Resolved when: available_amount > (checked_amount * 0.95) = available > (1 * 0.95) = available > 0.95
    
    # Portfolio has 100 BTC available, which is > 0.95, so should be resolved
    assert event.is_resolved(portfolio) is True
    
    # Create portfolio with insufficient BTC
    low_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    low_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("0.5"), "total": decimal.Decimal("0.5")},
        "USDT": {"available": decimal.Decimal("1000"), "total": decimal.Decimal("1000")}
    }, force_replace=True)
    # 0.5 is not > 0.95, so should not be resolved
    assert event.is_resolved(low_portfolio) is False
    
    # Create portfolio with exactly at threshold
    threshold_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    threshold_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("0.95"), "total": decimal.Decimal("0.95")},
        "USDT": {"available": decimal.Decimal("1000"), "total": decimal.Decimal("1000")}
    }, force_replace=True)
    # 0.95 is not > 0.95, so should not be resolved
    assert event.is_resolved(threshold_portfolio) is False
    
    # Create portfolio with just above threshold
    above_threshold_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    above_threshold_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("0.951"), "total": decimal.Decimal("0.951")},
        "USDT": {"available": decimal.Decimal("1000"), "total": decimal.Decimal("1000")}
    }, force_replace=True)
    # 0.951 > 0.95, so should be resolved
    assert event.is_resolved(above_threshold_portfolio) is True


def test_is_resolved_sell_order(portfolio, sell_order):
    """Test is_resolved() for SELL orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(sell_order)
    
    # For SELL orders: checked_amount = origin_quantity * origin_price = 0.5 * 50000 = 25000
    # Resolved when: available_amount > (checked_amount * 0.95) = available > (25000 * 0.95) = available > 23750
    
    # Portfolio has 1000 USDT available, which is not > 23750, so should not be resolved
    assert event.is_resolved(portfolio) is False
    
    # Create portfolio with sufficient USDT
    high_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    high_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("100"), "total": decimal.Decimal("100")},
        "USDT": {"available": decimal.Decimal("25000"), "total": decimal.Decimal("25000")}
    }, force_replace=True)
    # 25000 > 23750, so should be resolved
    assert event.is_resolved(high_portfolio) is True
    
    # Create portfolio with exactly at threshold
    threshold_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    threshold_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("100"), "total": decimal.Decimal("100")},
        "USDT": {"available": decimal.Decimal("23750"), "total": decimal.Decimal("23750")}
    }, force_replace=True)
    # 23750 is not > 23750, so should not be resolved
    assert event.is_resolved(threshold_portfolio) is False
    
    # Create portfolio with just above threshold
    above_threshold_portfolio = octobot_trading.personal_data.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    above_threshold_portfolio.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("100"), "total": decimal.Decimal("100")},
        "USDT": {"available": decimal.Decimal("23750.01"), "total": decimal.Decimal("23750.01")}
    }, force_replace=True)
    # 23750.01 > 23750, so should be resolved
    assert event.is_resolved(above_threshold_portfolio) is True


def test_repr_buy_order(buy_order):
    """Test __repr__() for BUY orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(buy_order)
    
    repr_str = repr(event)
    assert "buy" in repr_str.lower() or "BUY" in repr_str
    assert "1" in repr_str
    assert "BTC/USDT" in repr_str
    assert "50000" in repr_str


def test_repr_sell_order(sell_order):
    """Test __repr__() for SELL orders."""
    event = octobot_trading.personal_data.FilledOrderUpdateEvent(sell_order)
    
    repr_str = repr(event)
    assert "sell" in repr_str.lower() or "SELL" in repr_str
    assert "0.5" in repr_str
    assert "BTC/USDT" in repr_str
    assert "50000" in repr_str


def test_different_symbols(mock_trader):
    """Test that FilledOrderUpdateEvent works with different symbols."""
    symbols = ["ETH/USDT", "BTC/ETH", "DOGE/BTC"]
    
    for symbol in symbols:
        order = octobot_trading.personal_data.BuyLimitOrder(mock_trader)
        order.update(
            order_type=enums.TraderOrderType.BUY_LIMIT,
            symbol=symbol,
            current_price=decimal.Decimal("100"),
            quantity=decimal.Decimal("1"),
            price=decimal.Decimal("100")
        )
        
        event = octobot_trading.personal_data.FilledOrderUpdateEvent(order)
        assert event.symbol == symbol
