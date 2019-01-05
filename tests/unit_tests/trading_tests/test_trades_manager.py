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

from trading.exchanges.exchange_manager import ExchangeManager
from config import *
from tests.test_utils.config import load_test_config
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.trade import Trade
from trading.trader.order import SellLimitOrder, OrderConstants
from trading.trader.trades_manager import TradesManager


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestTradesManager:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 1)
        await trader_inst.portfolio.initialize()
        trades_manager_inst = trader_inst.get_trades_manager()
        await trades_manager_inst.initialize()
        return config, exchange_inst, trader_inst, trades_manager_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_get_reference_market(self):
        config, _, trader_inst, _ = await self.init_default()
        assert TradesManager.get_reference_market(config) == DEFAULT_REFERENCE_MARKET

        config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = "ETH"
        assert TradesManager.get_reference_market(config) == "ETH"

        self.stop(trader_inst)

    async def test_get_profitability(self):
        config, _, trader_inst, trades_manager_inst = await self.init_default()
        self.stop(trader_inst)

        profitability, profitability_percent, profitability_diff, market_profitability = \
            await trades_manager_inst.get_profitability()
        assert market_profitability is None
        assert profitability == profitability_percent == profitability_diff == 0

        trades_manager_inst.portfolio_origin_value = 20
        trades_manager_inst.profitability_percent = 100

        # set all market values to 1 if unset
        nb_currencies = 0
        for currency in \
                trades_manager_inst.only_symbol_currency_filter(trades_manager_inst.origin_crypto_currencies_values):
            if trades_manager_inst.origin_crypto_currencies_values[currency] != 0:
                nb_currencies += 1

        # decrease initial value of btc to force market_profitability change:
        # => same as +100% for BTC (ratio = nb_currencies + 1 /  nb_currencies in %)
        expected_market_profitability = ((nb_currencies + 1) / nb_currencies * 100) - 100
        trades_manager_inst.origin_crypto_currencies_values["BTC"] = 0.5

        profitability, profitability_percent, profitability_diff, market_profitability = \
            await trades_manager_inst.get_profitability(True)
        assert profitability == -10
        assert profitability_percent == -50
        assert profitability_diff == -150
        assert market_profitability == expected_market_profitability

    async def test_get_current_holdings_values(self):
        _, _, trader_inst, trades_manager_inst = await self.init_default()
        self.stop(trader_inst)
        btc_currency = "BTC"
        usd_currency = "USD"
        ada_currency = "ADA"

        usd_price_in_btc = 50
        trades_manager_inst.current_crypto_currencies_values = {
            btc_currency: 1,
            usd_currency: usd_price_in_btc,
            ada_currency: 10
        }
        holdings = await trades_manager_inst.get_current_holdings_values()
        btc_holding = trader_inst.portfolio.portfolio[btc_currency][CONFIG_PORTFOLIO_TOTAL]
        usd_holding = trader_inst.portfolio.portfolio[usd_currency][CONFIG_PORTFOLIO_TOTAL]
        ada_holding = 0
        portfolio = trader_inst.portfolio.portfolio
        if ada_currency not in portfolio:
            portfolio[ada_currency] = {}
        portfolio[ada_currency][CONFIG_PORTFOLIO_TOTAL] = ada_holding
        assert len(holdings) == len(trades_manager_inst.current_crypto_currencies_values)
        assert holdings[btc_currency] == btc_holding * 1    # ref market is btc => btc_holding*1
        assert holdings[usd_currency] == usd_price_in_btc * usd_holding
        assert holdings[ada_currency] == 0

    async def test_add_select_trade_in_history(self):
        _, exchange_inst, trader_inst, trades_manager_inst = await self.init_default()
        self.stop(trader_inst)
        assert len(trades_manager_inst.get_trade_history()) == 0
        symbol = "BTC/USD"
        new_order = SellLimitOrder(trader_inst)
        new_order.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT], symbol, 90, 4, 90)
        new_trade = Trade(exchange_inst, new_order)

        # add new trade
        trades_manager_inst.add_new_trade_in_history(new_trade)
        assert len(trades_manager_inst.get_trade_history()) == 1
        assert trades_manager_inst.get_trade_history()[0] == new_trade

        # doesn't add an existing trade
        trades_manager_inst.add_new_trade_in_history(new_trade)
        assert len(trades_manager_inst.get_trade_history()) == 1
        assert trades_manager_inst.get_trade_history()[0] == new_trade

        # select trade
        assert trades_manager_inst.select_trade_history() == trades_manager_inst.get_trade_history()

        new_order2 = SellLimitOrder(trader_inst)
        new_order2.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT], "BTC/EUR", 90, 4, 90)
        new_trade2 = Trade(exchange_inst, new_order2)

        trades_manager_inst.add_new_trade_in_history(new_trade2)
        assert len(trades_manager_inst.get_trade_history()) == 2
        assert trades_manager_inst.select_trade_history(symbol) == [new_trade]
