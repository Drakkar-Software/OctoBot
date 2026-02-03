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
import mock.mock
import pytest
import octobot_trading.api as api
import octobot_trading.exchanges as exchanges
import octobot_commons.authentication as commons_authentication

from tests.exchanges import exchange_manager
from tests import event_loop


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_build_trading_modes_if_required(exchange_manager):
    builder = exchanges.ExchangeBuilder({}, "binanceus")
    builder.exchange_manager = exchange_manager
    tentacles_setup_config = exchange_manager.tentacles_setup_config

    # no set trader: no trading mode creation attempt
    assert builder.exchange_manager.trader is None
    await builder._build_trading_modes_if_required(None, tentacles_setup_config)
    assert builder.exchange_manager.trader is None

    # with trader simulator: will attempt to create a trading mode and fail (because of the None arg)
    builder.is_simulated()
    with mock.patch.object(
        commons_authentication.Authenticator, "has_open_source_package", mock.Mock(return_value=False)
    ) as has_open_source_package_mock:
        # get_is_using_trading_mode_on_exchange returns True
        trading_mode_class = mock.Mock(
            get_is_using_trading_mode_on_exchange=mock.Mock(return_value=True),
            get_supported_exchange_types=mock.Mock(return_value=[]),
            return_value=mock.Mock(
                initialize=mock.AsyncMock(),
            ),
        )
        with pytest.raises(AttributeError):
            await builder._build_trading_modes_if_required(None, tentacles_setup_config)
        has_open_source_package_mock.assert_not_called()
        await builder._build_trading_modes_if_required(trading_mode_class, tentacles_setup_config)
        trading_mode_class.get_is_using_trading_mode_on_exchange.assert_called_once_with(builder.exchange_name, tentacles_setup_config)
        trading_mode_class.get_supported_exchange_types.assert_called_once()
        trading_mode_class.return_value.initialize.assert_awaited_once()
        has_open_source_package_mock.assert_called_once()
        trading_mode_class.reset_mock()
        trading_mode_class.get_is_using_trading_mode_on_exchange.reset_mock()
        trading_mode_class.get_supported_exchange_types.reset_mock()
        trading_mode_class.return_value.initialize.reset_mock()

        # get_is_using_trading_mode_on_exchange returns False
        trading_mode_class.get_is_using_trading_mode_on_exchange.return_value = False
        await builder._build_trading_modes_if_required(trading_mode_class, tentacles_setup_config)
        trading_mode_class.get_is_using_trading_mode_on_exchange.assert_called_once_with(builder.exchange_name, tentacles_setup_config)
        trading_mode_class.get_supported_exchange_types.assert_not_called()
        trading_mode_class.return_value.initialize.assert_not_called()
        has_open_source_package_mock.assert_called_once()

    # raised by default has_open_source_package (which should be overriden)
    trading_mode_class.get_is_using_trading_mode_on_exchange.return_value = True
    with pytest.raises(NotImplementedError):
        await builder._build_trading_modes_if_required(trading_mode_class, tentacles_setup_config)


async def test_build_collector_exchange(exchange_manager):
    new_exchange_manager = await api.create_exchange_builder(exchange_manager.config, exchange_manager.exchange_name) \
        .is_simulated() \
        .is_rest_only() \
        .is_exchange_only() \
        .is_without_auth() \
        .is_ignoring_config() \
        .disable_trading_mode() \
        .use_tentacles_setup_config(exchange_manager.tentacles_setup_config) \
        .build()
    assert new_exchange_manager is not exchange_manager
    assert new_exchange_manager.config is exchange_manager.config
    assert new_exchange_manager.exchange_name == exchange_manager.exchange_name
    assert new_exchange_manager.tentacles_setup_config is exchange_manager.tentacles_setup_config
    await new_exchange_manager.stop()
