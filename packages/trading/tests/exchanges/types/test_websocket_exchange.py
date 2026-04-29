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

import octobot_trading.exchanges.types as exchange_types
import pytest

from tests.exchanges import exchange_manager


@pytest.fixture
def websocket_exchange(exchange_manager):
    return exchange_types.WebSocketExchange(exchange_manager.config, exchange_manager)


def test_clear(websocket_exchange):
    assert websocket_exchange.exchange_manager is not None
    assert websocket_exchange.exchange is not None
    websocket_exchange.websocket_connectors = [mock.Mock(), mock.Mock()]

    websocket_exchange.clear()
    assert websocket_exchange.exchange_manager is None
    assert websocket_exchange.exchange is None
    websocket_exchange.websocket_connectors[0].clear.assert_called_once()
    websocket_exchange.websocket_connectors[1].clear.assert_called_once()
