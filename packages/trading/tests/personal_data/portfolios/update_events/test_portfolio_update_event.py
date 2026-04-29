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
import asyncio

import octobot_trading.personal_data.portfolios.update_events.portfolio_update_event as portfolio_update_event
import octobot_trading.personal_data


class ConcretePortfolioUpdateEvent(portfolio_update_event.PortfolioUpdateEvent):
    """Concrete implementation for testing purposes."""
    def __init__(self, resolved_value: bool = False):
        super().__init__()
        self.resolved_value = resolved_value

    def is_resolved(
        self, updated_portfolio: octobot_trading.personal_data.Portfolio
    ) -> bool:
        return self.resolved_value


def test_is_resolved_not_implemented():
    """Test that calling is_resolved() on base class raises NotImplementedError."""
    event = portfolio_update_event.PortfolioUpdateEvent()
    assert isinstance(event, asyncio.Event)
    mock_portfolio = mock.Mock()
    
    with pytest.raises(NotImplementedError, match="is_resolved must be implemented"):
        event.is_resolved(mock_portfolio)


def test_concrete_subclass_implementation():
    """Test that a concrete subclass can properly implement is_resolved()."""
    mock_portfolio = mock.Mock()
    
    # Test with resolved_value=True
    event_resolved = ConcretePortfolioUpdateEvent(resolved_value=True)
    assert event_resolved.is_resolved(mock_portfolio) is True
    
    # Test with resolved_value=False
    event_not_resolved = ConcretePortfolioUpdateEvent(resolved_value=False)
    assert event_not_resolved.is_resolved(mock_portfolio) is False
