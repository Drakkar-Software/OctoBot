import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import *
from tests.test_utils.config import load_test_config
from trading.trader.order import *
from trading.trader.order_notifier import OrderNotifier
from trading.trader.trader import Trader


class TestTrader:
    DEFAULT_SYMBOL = "BTC/USDT"

    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = Trader(config, exchange_inst)
        return config, exchange_inst, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_enabled(self):
        config, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = True
        assert Trader.enabled(config)

        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        assert not Trader.enabled(config)

    def test_get_risk(self):
        config, exchange_inst, trader_inst = self.init_default()
        self.stop(trader_inst)

        config[CONFIG_TRADER][CONFIG_TRADER_RISK] = 0
        trader_1 = Trader(config, exchange_inst)
        assert trader_1.get_risk() == CONFIG_TRADER_RISK_MIN
        self.stop(trader_1)

        config[CONFIG_TRADER][CONFIG_TRADER_RISK] = 2
        trader_2 = Trader(config, exchange_inst)
        assert trader_2.get_risk() == CONFIG_TRADER_RISK_MAX
        self.stop(trader_2)

        config[CONFIG_TRADER][CONFIG_TRADER_RISK] = 0.5
        trader_2 = Trader(config, exchange_inst)
        assert trader_2.get_risk() == 0.5
        self.stop(trader_2)

    def test_cancel_order(self):
        _, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       self.DEFAULT_SYMBOL,
                       70,
                       10,
                       70)

        assert market_buy not in trader_inst.get_open_orders()

        trader_inst.get_order_manager().add_order_to_list(market_buy)

        assert market_buy in trader_inst.get_open_orders()

        trader_inst.cancel_order(market_buy)

        assert market_buy not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    def test_cancel_open_orders_default_symbol(self):
        config, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       self.DEFAULT_SYMBOL,
                       70,
                       10,
                       70)

        # Test sell order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
                        self.DEFAULT_SYMBOL,
                        70,
                        10,
                        70)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      self.DEFAULT_SYMBOL,
                      70,
                      10,
                      70)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        market_sell.order_notifier = OrderNotifier(config, market_sell)
        limit_buy.order_notifier = OrderNotifier(config, limit_buy)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(market_sell)
        trader_inst.get_order_manager().add_order_to_list(limit_buy)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()

        trader_inst.cancel_open_orders(self.DEFAULT_SYMBOL)

        assert market_buy not in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    def test_cancel_open_orders_multi_symbol(self):
        config, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test sell order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
                        self.DEFAULT_SYMBOL,
                        70,
                        10,
                        70)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      self.DEFAULT_SYMBOL,
                      70,
                      10,
                      70)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        market_sell.order_notifier = OrderNotifier(config, market_sell)
        limit_buy.order_notifier = OrderNotifier(config, limit_buy)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(market_sell)
        trader_inst.get_order_manager().add_order_to_list(limit_buy)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        trader_inst.cancel_open_orders(self.DEFAULT_SYMBOL)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        self.stop(trader_inst)

    def test_notify_order_close(self):
        config, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                      "BTC/USD",
                      60,
                      10,
                      60)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)
        stop_loss.order_notifier = OrderNotifier(config, stop_loss)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(stop_loss)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        trader_inst.notify_order_close(limit_sell, True)
        trader_inst.notify_order_close(market_buy, True)

        assert market_buy not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()
        assert stop_loss in trader_inst.get_open_orders()

        self.stop(trader_inst)

    def test_notify_order_close_with_linked_orders(self):
        config, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                      "BTC/USD",
                      60,
                      10,
                      60)

        stop_loss.add_linked_order(limit_sell)
        limit_sell.add_linked_order(stop_loss)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        stop_loss.order_notifier = OrderNotifier(config, stop_loss)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(stop_loss)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        trader_inst.notify_order_close(limit_sell)

        assert market_buy in trader_inst.get_open_orders()
        assert stop_loss not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()

        self.stop(trader_inst)
