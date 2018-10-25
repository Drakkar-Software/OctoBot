import ccxt

from trading.exchanges.exchange_manager import ExchangeManager
from config.cst import *
from tests.test_utils.config import load_test_config
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.trade import Trade
from trading.trader.order import SellLimitOrder, OrderConstants
from trading.trader.trades_manager import TradesManager


class TestTradesManager:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 1)
        trades_manager_inst = trader_inst.get_trades_manager()
        return config, exchange_inst, trader_inst, trades_manager_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_get_reference_market(self):
        config, _, trader_inst, _ = self.init_default()
        assert TradesManager.get_reference_market(config) == DEFAULT_REFERENCE_MARKET

        config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = "ETH"
        assert TradesManager.get_reference_market(config) == "ETH"

        self.stop(trader_inst)

    def test_get_profitability(self):
        config, _, trader_inst, trades_manager_inst = self.init_default()
        self.stop(trader_inst)

        profitability, profitability_percent, profitability_diff, market_profitability = \
            trades_manager_inst.get_profitability()
        assert market_profitability is None
        assert profitability == profitability_percent == profitability_diff == 0

        trades_manager_inst.portfolio_origin_value = 20
        trades_manager_inst.profitability_percent = 100

        # set all market values to 1 if unset
        nb_currencies = 0
        for currency in trades_manager_inst.origin_crypto_currencies_values:
            if trades_manager_inst.origin_crypto_currencies_values[currency] != 0:
                nb_currencies += 1

        # decrease initial value of btc to force market_profitability change:
        # => same as +100% for BTC (ratio = nb_currencies + 1 /  nb_currencies in %)
        expected_market_profitability = ((nb_currencies + 1) / nb_currencies * 100) - 100
        trades_manager_inst.origin_crypto_currencies_values["BTC"] = 0.5

        profitability, profitability_percent, profitability_diff, market_profitability = \
            trades_manager_inst.get_profitability(True)
        assert profitability == -10
        assert profitability_percent == -50
        assert profitability_diff == -150
        assert market_profitability == expected_market_profitability

    def test_get_current_holdings_values(self):
        config, _, trader_inst, trades_manager_inst = self.init_default()
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
        holdings = trades_manager_inst.get_current_holdings_values()
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

    def test_add_select_trade_in_history(self):
        _, exchange_inst, trader_inst, trades_manager_inst = self.init_default()
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
