#  Drakkar-Software OctoBot-Tentacles
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
import os

import pytest

import octobot_commons.tests as commons_tests
import octobot_commons.constants as commons_constants
import octobot_trading.util.test_tools.spot_rest_exchange_test_tools as spot_rest_exchange_test_tools
import octobot_commons.configuration as configuration
from ...binance import Binance

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def _test_spot_rest():
    config = commons_tests.load_test_config()
    config[commons_constants.CONFIG_EXCHANGES][Binance.get_name()] = {
        commons_constants.CONFIG_EXCHANGE_KEY: configuration.encrypt(
            os.getenv(f"{Binance.get_name()}_API_KEY".upper())).decode(),
        commons_constants.CONFIG_EXCHANGE_SECRET: configuration.encrypt(
            os.getenv(f"{Binance.get_name()}_API_SECRET".upper())).decode()
    }
    config[commons_constants.CONFIG_TRADER][commons_constants.CONFIG_ENABLED_OPTION] = True
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_ENABLED_OPTION] = False

    test_tools = spot_rest_exchange_test_tools.SpotRestExchangeTests(config=config, exchange_name=Binance.get_name())
    test_tools.expected_crypto_in_balance = ["BNB", "BTC", "BUSD", "ETH", "LTC", "TRX", "USDT", "XRP"]
    await test_tools.initialize()
    await test_tools.run(symbol="BTC/USDT")
    await test_tools.stop()
    await test_tools.test_all_callback_triggered()
