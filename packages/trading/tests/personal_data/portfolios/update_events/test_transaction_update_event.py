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

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.update_events.transaction_update_event as transaction_update_event
import octobot_trading.personal_data.portfolios.update_events.portfolio_update_event as portfolio_update_event
import octobot_trading.personal_data.portfolios.types.spot_portfolio as spot_portfolio


@pytest.fixture
def portfolio():
    """Create a real Portfolio instance for testing."""
    portfolio = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
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
        },
        "DOGE": {
            "available": decimal.Decimal("50"),
            "total": decimal.Decimal("50")
        }
    }, force_replace=True)
    return portfolio


def test_transaction_update_event_instantiation(portfolio):
    """Test that TransactionUpdateEvent can be instantiated."""
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("10")
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    assert event is not None
    assert isinstance(event, transaction_update_event.TransactionUpdateEvent)
    assert isinstance(event, portfolio_update_event.PortfolioUpdateEvent)
    assert isinstance(event, asyncio.Event)


def test_transaction_update_event_initialization_values(portfolio):
    """Test that TransactionUpdateEvent stores correct values during initialization."""
    currency = "BTC"
    amount = decimal.Decimal("10")
    initial_holdings = decimal.Decimal("100")
    
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency,
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount
    }
    
    # Test with added funds
    event_added = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    assert event_added.currency == currency
    assert event_added.amount == amount
    assert event_added.initial_currency_holdings == initial_holdings
    assert event_added.are_added_funds is True
    
    # Test with withdrawn funds
    event_withdrawn = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=False
    )
    
    assert event_withdrawn.currency == currency
    assert event_withdrawn.amount == amount
    assert event_withdrawn.initial_currency_holdings == initial_holdings
    assert event_withdrawn.are_added_funds is False


def test_get_holdings(portfolio):
    """Test that _get_holdings() correctly retrieves holdings from portfolio."""
    # Test with ETH which exists in the portfolio
    expected_holdings = decimal.Decimal("150")
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "ETH",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("5")
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    # Test _get_holdings with the same portfolio
    holdings = event._get_holdings(portfolio)
    assert holdings == expected_holdings
    
    # Test with BTC which exists in the portfolio
    transaction_btc = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("1")
    }
    event_btc = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction_btc,
        are_added_funds=True
    )
    btc_holdings = event_btc._get_holdings(portfolio)
    assert btc_holdings == decimal.Decimal("100")
    
    # Test with a currency that doesn't exist (should return 0)
    transaction_xyz = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "XYZ",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("1")
    }
    event_xyz = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction_xyz,
        are_added_funds=True
    )
    xyz_holdings = event_xyz._get_holdings(portfolio)
    assert xyz_holdings == constants.ZERO


def test_is_resolved_added_funds(portfolio):
    """Test is_resolved() for added funds (deposits)."""
    amount = decimal.Decimal("10")
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    # For added funds: delta = amount, so resolved when:
    # updated >= initial + (amount * 0.95) = 100 + (10 * 0.95) = 100 + 9.5 = 109.5
    # Threshold: 109.5
    
    # Create updated portfolios with different holdings
    updated_portfolio_90 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_90.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("90"), "total": decimal.Decimal("90")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_90) is False
    
    updated_portfolio_100 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_100.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("100"), "total": decimal.Decimal("100")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_100) is False
    
    updated_portfolio_109_5 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_109_5.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("109.5"), "total": decimal.Decimal("109.5")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_109_5) is True
    
    # Case: updated holdings = 110 (above threshold, should not be resolved)
    updated_portfolio_110 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_110.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("110"), "total": decimal.Decimal("110")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_110) is True


def test_is_resolved_withdrawn_funds(portfolio):
    """Test is_resolved() for withdrawn funds (withdrawals)."""
    amount = decimal.Decimal("10")
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=False
    )
    
    # For withdrawn funds: delta = -amount, so resolved when:
    # updated <= initial + (delta * 0.95) = 100 + (-10 * 0.95) = 100 - 9.5 = 90.5
    # Threshold: 90.5
    
    # Create updated portfolios with different holdings
    updated_portfolio_90 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_90.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("90"), "total": decimal.Decimal("90")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_90) is True
    
    updated_portfolio_90_5 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_90_5.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("90.5"), "total": decimal.Decimal("90.5")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_90_5) is True
    
    # Case: updated holdings = 100 (above threshold, should not be resolved)
    assert event.is_resolved(portfolio) is False
    
    updated_portfolio_91 = spot_portfolio.SpotPortfolio(exchange_name="test_exchange", is_simulated=True)
    updated_portfolio_91.update_portfolio_from_balance({
        "BTC": {"available": decimal.Decimal("91"), "total": decimal.Decimal("91")}
    }, force_replace=True)
    assert event.is_resolved(updated_portfolio_91) is False


def test_is_resolved_zero_amount(portfolio):
    """Test is_resolved() with zero amount transaction."""
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: constants.ZERO
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    # With zero amount: updated <= initial + (0 * 0.95) = updated <= initial
    # So if updated == initial, it should be resolved
    assert event.is_resolved(portfolio) is True


def test_repr_added_funds(portfolio):
    """Test __repr__() for added funds."""
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("10")
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=True
    )
    
    repr_str = repr(event)
    assert "+BTC" in repr_str
    assert "10" in repr_str
    assert "100" in repr_str


def test_repr_withdrawn_funds(portfolio):
    """Test __repr__() for withdrawn funds."""
    transaction = {
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "ETH",
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("5")
    }
    
    event = transaction_update_event.TransactionUpdateEvent(
        initial_portfolio=portfolio,
        transaction=transaction,
        are_added_funds=False
    )
    
    repr_str = repr(event)
    assert "-ETH" in repr_str
    assert "5" in repr_str
    assert "150" in repr_str  # ETH initial holdings from fixture


def test_different_currencies(portfolio):
    """Test that TransactionUpdateEvent works with different currencies."""
    currencies = ["BTC", "ETH", "USDT", "DOGE"]
    expected_holdings = {
        "BTC": decimal.Decimal("100"),
        "ETH": decimal.Decimal("150"),
        "USDT": decimal.Decimal("1000"),
        "DOGE": decimal.Decimal("50")
    }
    
    for currency in currencies:
        transaction = {
            enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency,
            enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal("1")
        }
        
        event = transaction_update_event.TransactionUpdateEvent(
            initial_portfolio=portfolio,
            transaction=transaction,
            are_added_funds=True
        )
        
        assert event.currency == currency
        assert event.initial_currency_holdings == expected_holdings[currency]
