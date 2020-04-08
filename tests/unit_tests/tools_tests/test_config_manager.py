#  Drakkar-Software OctoBot
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

from config import DEFAULT_REFERENCE_MARKET, CONFIG_TRADING, CONFIG_TRADER_REFERENCE_MARKET
from config.config import load_config
from octobot.tools import ConfigManager
from octobot_commons.symbol_util import split_symbol


def test_get_market_pair():
    config = load_config("tests/static/config.json")

    pair, inverted = ConfigManager.get_market_pair(config, config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET])
    assert pair == ""
    assert inverted is False

    pair, inverted = ConfigManager.get_market_pair(config, "")
    assert pair == ""
    assert inverted is False

    pair, inverted = ConfigManager.get_market_pair(config, "VEN")
    assert pair == "VEN/BTC"
    assert inverted is False

    pair, inverted = ConfigManager.get_market_pair(config, "USDT")
    assert pair == "BTC/USDT"
    assert inverted is True

    pair, inverted = ConfigManager.get_market_pair(config, "XBT")
    assert pair == ""
    assert inverted is False

    # now change config reference market
    config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = "USDT"

    pair, inverted = ConfigManager.get_market_pair(config, "BTC")
    assert pair == "BTC/USDT"
    assert inverted is False

    pair, inverted = ConfigManager.get_market_pair(config, "VEN")
    assert pair == ""
    assert inverted is False

    config[CONFIG_TRADING].pop(CONFIG_TRADER_REFERENCE_MARKET)

    # now use config/constants.py reference market
    pair, inverted = ConfigManager.get_market_pair(config, "ADA")
    assert pair == "ADA/BTC"
    assert split_symbol(pair)[1] == DEFAULT_REFERENCE_MARKET
    assert inverted is False

    config.pop(CONFIG_TRADING)
    pair, inverted = ConfigManager.get_market_pair(config, "ADA")
    assert pair == ""
    assert inverted is False


def test_get_reference_market():
    config = load_config("tests/static/config.json")
    assert ConfigManager.get_reference_market(config) == DEFAULT_REFERENCE_MARKET

    config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = "ETH"
    assert ConfigManager.get_reference_market(config) == "ETH"
