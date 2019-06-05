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

import ccxt
import pytest
from octobot_trading.exchanges import ExchangeSimulator

from tests.test_utils.config import load_test_config
from octobot_trading.exchanges import ExchangeManager

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestExchangeManager:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        return config, exchange_manager

    async def test_create_exchanges(self):
        _, exchange_manager = await self.init_default()

        assert exchange_manager.exchange_dispatcher is not None
        assert exchange_manager.exchange is not None
        assert exchange_manager.is_ready
        assert exchange_manager.client_symbols is not None

        # simulated
        exchange_manager.is_simulated = True
        await exchange_manager.create_exchanges()

        assert isinstance(exchange_manager.exchange, ExchangeSimulator)

    async def test_enabled(self):
        _, exchange_manager = await self.init_default()

        assert exchange_manager.enabled()

    async def test__set_config_traded_pairs(self):
        _, exchange_manager = await self.init_default()

        exchange_manager.config[CONFIG_CRYPTO_CURRENCIES] = {
            "Neo": {
                "pairs": ["NEO/BTC"]
            },
            "Ethereum": {
                "pairs": ["ETH/USDT"]
            },
            "Icon": {
                "pairs": ["ICX/BTC"]
            }
        }

        exchange_manager._set_config_traded_pairs()

        assert exchange_manager.cryptocurrencies_traded_pairs == {
            "Ethereum": ["ETH/USDT"],
            "Icon": ["ICX/BTC"],
            "Neo": ["NEO/BTC"]
        }

    async def test__set_config_traded_pairs_wildcard(self):
        _, exchange_manager = await self.init_default()
        exchange_manager.config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": "*",
                "quote": "BTC"
            }
        }

        exchange_manager._set_config_traded_pairs()

        assert "ICX/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "NEO/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "VEN/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "XLM/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "ONT/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "BTC/USDT" not in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "ETH/USDT" not in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "NEO/BNB" not in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]

    async def test__set_config_traded_pairs_wildcard_with_add(self):
        _, exchange_manager = await self.init_default()
        exchange_manager.config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": "*",
                "quote": "BTC",
                "add": ["BTC/USDT"]
            }
        }

        exchange_manager._set_config_traded_pairs()

        assert "ICX/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "NEO/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "VEN/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "XLM/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "ONT/BTC" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "BTC/USDT" in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "ETH/USDT" not in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
        assert "NEO/BNB" not in exchange_manager.cryptocurrencies_traded_pairs["Bitcoin"]
