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
import pytest

from config import CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, CONFIG_WILDCARD, CONFIG_CRYPTO_QUOTE
from core.octobot import OctoBot
from evaluator.cryptocurrency_evaluator import CryptocurrencyEvaluator
from evaluator.symbol_evaluator import SymbolEvaluator
from tests.test_utils.config import load_test_config

# All test coroutines will be treated as marked.
from octobot_commons.symbol_util import split_symbol

pytestmark = pytest.mark.asyncio


def create_bot_with_config(config):
    return OctoBot(config, ignore_config=True)


def check_symbol_evaluator_list(e_factory, symbol, exchange, exchange_count, total_symbol_count):
    assert len(e_factory.symbol_evaluator_list) == total_symbol_count
    symbol_eval = e_factory.symbol_evaluator_list[symbol]
    assert isinstance(symbol_eval, SymbolEvaluator)
    assert symbol_eval.symbol == symbol
    assert len(symbol_eval.trader_simulators) == exchange_count
    assert exchange in symbol_eval.trader_simulators
    assert len(symbol_eval.traders) == exchange_count
    assert exchange in symbol_eval.traders
    assert len(symbol_eval.trading_mode_instances) == 1


def check_crypto_currency_evaluator_list(e_factory, crypto_currency, symbol, crypto_currency_count, symbol_count):
    assert len(e_factory.crypto_currency_evaluator_list) == crypto_currency_count
    assert crypto_currency in e_factory.crypto_currency_evaluator_list
    crypto_evaluator = e_factory.crypto_currency_evaluator_list[crypto_currency]
    assert isinstance(crypto_evaluator, CryptocurrencyEvaluator)
    assert crypto_evaluator.crypto_currency == crypto_currency
    assert len(crypto_evaluator.symbol_evaluator_list) == symbol_count
    assert symbol in crypto_evaluator.symbol_evaluator_list
    assert crypto_evaluator.symbol_evaluator_list[symbol] is e_factory.symbol_evaluator_list[symbol]


def perform_evaluator_factory_tests(e_factory, crypto_currency, symbol, exchange,
                                    exchange_count, crypto_currency_count, total_symbol_count, symbol_count):
    # symbol_evaluator_list
    check_symbol_evaluator_list(e_factory, symbol, exchange, exchange_count, total_symbol_count)

    # trading mode instance
    btc_trading_mode = e_factory.symbol_evaluator_list[symbol].trading_mode_instances
    assert exchange in btc_trading_mode

    # crypto_currency_evaluator_list
    check_crypto_currency_evaluator_list(e_factory, crypto_currency, symbol, crypto_currency_count, symbol_count)


async def test_evaluator_factory_with_one_symbol():
    crypto_currency = "Bitcoin"
    symbol = "BTC/USDT"
    exchange = "binance"
    config = load_test_config()
    config[CONFIG_CRYPTO_CURRENCIES] = {
        crypto_currency:
            {
                CONFIG_CRYPTO_PAIRS: [symbol]
            }
    }
    bot = create_bot_with_config(config)
    await bot.initialize()

    perform_evaluator_factory_tests(bot.evaluator_factory, crypto_currency, symbol, exchange, 1, 1, 1, 1)


async def test_evaluator_factory_with_three_symbols():
    crypto_currency = "Ethereum"
    symbols = ["ETH/USDT", "ETH/BTC", "ETH/BNB", "ETH/EOS"]
    exchange = "binance"
    config = load_test_config()
    config[CONFIG_CRYPTO_CURRENCIES] = {
        crypto_currency:
            {
                CONFIG_CRYPTO_PAIRS: symbols
            }
    }
    bot = create_bot_with_config(config)
    await bot.initialize()

    # ETH/BNB and ETH/EOS not in symbol list --> 2 of 4
    perform_evaluator_factory_tests(bot.evaluator_factory, crypto_currency, "ETH/USDT", exchange, 1, 1, 2, 2)
    perform_evaluator_factory_tests(bot.evaluator_factory, crypto_currency, "ETH/BTC", exchange, 1, 1, 2, 2)


async def test_evaluator_factory_with_multiple_currencies():
    eth_crypto_currency = "Ethereum"
    eth_symbols = ["ETH/USDT", "ETH/BTC", "ETH/BNB", "ETH/EOS"]
    btc_crypto_currency = "Bitcoin"
    btc_symbols = ["BTC/USDT", "BTC/BNB"]
    exchange = "binance"
    config = load_test_config()
    config[CONFIG_CRYPTO_CURRENCIES] = {
        eth_crypto_currency:
            {
                CONFIG_CRYPTO_PAIRS: eth_symbols
            },
        btc_crypto_currency:
            {
                CONFIG_CRYPTO_PAIRS: btc_symbols
            }
    }
    bot = create_bot_with_config(config)
    await bot.initialize()

    # ETH/BNB and ETH/EOS not in symbol list --> 2 of 4
    perform_evaluator_factory_tests(bot.evaluator_factory, eth_crypto_currency, "ETH/USDT", exchange, 1, 2, 3, 2)
    perform_evaluator_factory_tests(bot.evaluator_factory, eth_crypto_currency, "ETH/BTC", exchange, 1, 2, 3, 2)

    # BTC/BNB not in symbol list --> 1 of 2
    perform_evaluator_factory_tests(bot.evaluator_factory, btc_crypto_currency, "BTC/USDT", exchange, 1, 2, 3, 1)


async def test_evaluator_factory_with_wildcard():
    btc_crypto_currency = "Bitcoin"
    btc_quote = "BTC"
    exchange = "binance"
    config = load_test_config()
    config[CONFIG_CRYPTO_CURRENCIES] = {
        btc_crypto_currency:
            {
                CONFIG_CRYPTO_PAIRS: CONFIG_WILDCARD,
                CONFIG_CRYPTO_QUOTE: btc_quote
            }
    }
    bot = create_bot_with_config(config)
    await bot.initialize()

    symbol_count = len(set([
        symbol if split_symbol(symbol)[1] == btc_quote else None
        for symbol in bot.evaluator_factory.octobot.exchange_factory.exchanges_list['binance'].exchange.client.symbols
    ])) - 1  # -1 for 1 None (set consequence)

    perform_evaluator_factory_tests(bot.evaluator_factory, btc_crypto_currency, "ETH/BTC", exchange,
                                    1, 1, symbol_count, symbol_count)
