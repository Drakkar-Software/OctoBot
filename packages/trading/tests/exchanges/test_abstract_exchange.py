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

import octobot_trading.exchanges as exchanges
import octobot_trading.enums as enums
import octobot_commons.tests.test_config as test_config

from tests import event_loop


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


EXCHANGE_NAME = "binanceus"


@pytest.fixture
def abstract_exchange():
    config = test_config.load_test_config()
    return exchanges.AbstractExchange(config, exchanges.ExchangeManager(config, EXCHANGE_NAME), None)


@pytest.mark.asyncio
async def test_log_order_creation_error(abstract_exchange):
    logger_mock = mock.Mock()
    abstract_exchange.logger = logger_mock
    error = RuntimeError()
    abstract_exchange.log_order_creation_error(error, enums.TraderOrderType.BUY_MARKET, "BTC/USD",
                                               1.0542454, 100.114, 100.114)
    logger_mock.error.assert_called_once()
    assert all(f"{e}" in logger_mock.mock_calls[0].args[0] for e in (enums.TraderOrderType.BUY_MARKET, "BTC/USD",
                                                                     1.0542454, 100.114, 100.114))
    logger_mock.reset_mock()
    abstract_exchange.log_order_creation_error(error, enums.TraderOrderType.BUY_MARKET, "BTC/USD", 0, None, None)
    logger_mock.error.assert_called_once()
    assert all(f"{e}" in logger_mock.mock_calls[0].args[0] for e in (enums.TraderOrderType.BUY_MARKET, "BTC/USD",
                                                                     0, None, None))
    logger_mock.reset_mock()


async def test_supports_bundled_order_on_order_creation(abstract_exchange):
    order_mock = mock.Mock()
    order_mock.order_type = enums.TraderOrderType.SELL_MARKET
    assert abstract_exchange.supports_bundled_order_on_order_creation(order_mock, enums.TraderOrderType.STOP_LOSS) \
           is False
    abstract_exchange.get_supported_elements(enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS)[
        enums.TraderOrderType.SELL_MARKET
    ] = [enums.TraderOrderType.SELL_MARKET, enums.TraderOrderType.BUY_LIMIT]
    assert abstract_exchange.supports_bundled_order_on_order_creation(order_mock, enums.TraderOrderType.STOP_LOSS) \
           is False
    assert abstract_exchange.supports_bundled_order_on_order_creation(order_mock, enums.TraderOrderType.BUY_LIMIT) \
           is True


async def test_get_order_additional_params(abstract_exchange):
    assert abstract_exchange.get_order_additional_params(None) == {}


async def test_get_bundled_order_parameters(abstract_exchange):
    with pytest.raises(NotImplementedError):
        abstract_exchange.get_bundled_order_parameters(None)
