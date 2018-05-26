import ccxt

from evaluator.evaluator_order_creator import EvaluatorOrderCreator
from trading.exchanges.exchange_manager import ExchangeManager
from config.cst import EvaluatorStates
from tests.test_utils.config import load_test_config
from trading.trader.portfolio import Portfolio
from trading.trader.order import *
from trading.trader.trader_simulator import TraderSimulator
from config.cst import ExchangeConstantsMarketStatusColumns as Ecmsc


def _get_tools():
    config = load_test_config()
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    exchange_inst = exchange_manager.get_exchange()
    trader_inst = TraderSimulator(config, exchange_inst, 0.3)
    trader_inst.stop_order_manager()
    trader_inst.portfolio.portfolio["SUB"] = {
        Portfolio.TOTAL: 0.000000000000000000005,
        Portfolio.AVAILABLE: 0.000000000000000000005
    }
    trader_inst.portfolio.portfolio["BNB"] = {
        Portfolio.TOTAL: 0.000000000000000000005,
        Portfolio.AVAILABLE: 0.000000000000000000005
    }
    trader_inst.portfolio.portfolio["USDT"] = {
        Portfolio.TOTAL: 2000,
        Portfolio.AVAILABLE: 2000
    }
    symbol = "BTC/USDT"
    return config, exchange_inst, trader_inst, symbol


def test_can_create_order():
    config, exchange, trader, symbol = _get_tools()
    # portfolio: "BTC": 10 "USD": 1000
    not_owned_symbol = "ETH/BTC"
    not_owned_market = "BTC/ETH"
    min_trigger_symbol = "SUB/BTC"
    min_trigger_market = "ADA/BNB"

    # order from neutral state => false
    assert not EvaluatorOrderCreator.can_create_order(symbol, exchange, trader, EvaluatorStates.NEUTRAL)

    # sell order using a currency with 0 available
    assert not EvaluatorOrderCreator.can_create_order(not_owned_symbol, exchange, trader, EvaluatorStates.SHORT)
    assert not EvaluatorOrderCreator.can_create_order(not_owned_symbol, exchange, trader, EvaluatorStates.VERY_SHORT)

    # sell order using a currency with < min available
    assert not EvaluatorOrderCreator.can_create_order(min_trigger_symbol, exchange, trader, EvaluatorStates.SHORT)
    assert not EvaluatorOrderCreator.can_create_order(min_trigger_symbol, exchange, trader, EvaluatorStates.VERY_SHORT)

    # sell order using a currency with > min available
    assert EvaluatorOrderCreator.can_create_order(not_owned_market, exchange, trader, EvaluatorStates.SHORT)
    assert EvaluatorOrderCreator.can_create_order(not_owned_market, exchange, trader, EvaluatorStates.VERY_SHORT)

    # buy order using a market with 0 available
    assert not EvaluatorOrderCreator.can_create_order(not_owned_market, exchange, trader, EvaluatorStates.LONG)
    assert not EvaluatorOrderCreator.can_create_order(not_owned_market, exchange, trader, EvaluatorStates.VERY_LONG)

    # buy order using a market with < min available
    assert not EvaluatorOrderCreator.can_create_order(min_trigger_market, exchange, trader, EvaluatorStates.LONG)
    assert not EvaluatorOrderCreator.can_create_order(min_trigger_market, exchange, trader, EvaluatorStates.VERY_LONG)

    # buy order using a market with > min available
    assert EvaluatorOrderCreator.can_create_order(not_owned_symbol, exchange, trader, EvaluatorStates.LONG)
    assert EvaluatorOrderCreator.can_create_order(not_owned_symbol, exchange, trader, EvaluatorStates.VERY_LONG)


def test_can_create_order_unknown_symbols():
    config, exchange, trader, symbol = _get_tools()
    unknown_symbol = "VI?/BTC"
    unknown_market = "BTC/*s?"
    unknown_everything = "VI?/*s?"

    # buy order with unknown market
    assert not EvaluatorOrderCreator.can_create_order(unknown_market, exchange, trader, EvaluatorStates.LONG)
    assert not EvaluatorOrderCreator.can_create_order(unknown_market, exchange, trader, EvaluatorStates.VERY_LONG)
    assert EvaluatorOrderCreator.can_create_order(unknown_market, exchange, trader, EvaluatorStates.SHORT)
    assert EvaluatorOrderCreator.can_create_order(unknown_market, exchange, trader, EvaluatorStates.VERY_SHORT)

    # sell order with unknown symbol
    assert not EvaluatorOrderCreator.can_create_order(unknown_symbol, exchange, trader, EvaluatorStates.SHORT)
    assert not EvaluatorOrderCreator.can_create_order(unknown_symbol, exchange, trader, EvaluatorStates.VERY_SHORT)
    assert EvaluatorOrderCreator.can_create_order(unknown_symbol, exchange, trader, EvaluatorStates.LONG)
    assert EvaluatorOrderCreator.can_create_order(unknown_symbol, exchange, trader, EvaluatorStates.VERY_LONG)

    # neutral state with unknown symbol, market and everything
    assert not EvaluatorOrderCreator.can_create_order(unknown_symbol, exchange, trader, EvaluatorStates.NEUTRAL)
    assert not EvaluatorOrderCreator.can_create_order(unknown_market, exchange, trader, EvaluatorStates.NEUTRAL)
    assert not EvaluatorOrderCreator.can_create_order(unknown_everything, exchange, trader, EvaluatorStates.NEUTRAL)


def _check_order_limits(order, market_status):
    symbol_market_limits = market_status[Ecmsc.LIMITS.value]
    limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
    limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
    limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]

    min_quantity = limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]
    max_quantity = limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]
    min_cost = limit_cost[Ecmsc.LIMITS_COST_MIN.value]
    max_cost = limit_cost[Ecmsc.LIMITS_COST_MAX.value]
    min_price = limit_price[Ecmsc.LIMITS_PRICE_MIN.value]
    max_price = limit_price[Ecmsc.LIMITS_PRICE_MAX.value]
    maximal_price_digits = market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_PRICE.value]
    maximal_volume_digits = market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_AMOUNT.value]
    order_cost = order.origin_price*order.origin_quantity

    assert order_cost <= max_cost
    assert order_cost >= min_cost
    assert order.origin_price <= max_price
    assert order.origin_price >= min_price
    assert (order.origin_price*10**maximal_price_digits).is_integer()  # rounded value using trading rules
    assert order.origin_quantity <= max_quantity
    assert order.origin_quantity >= min_quantity
    assert (order.origin_quantity*10**maximal_volume_digits/10*10).is_integer()  # rounded value using trading rules
    # (/10*10 to remove python wtf rounding system)


def _check_linked_order(order, linked_order, order_type, order_price, market_status):
    assert linked_order.exchange == order.exchange
    assert linked_order.trader == order.trader
    assert linked_order.order_notifier == order.order_notifier
    assert linked_order.order_type == order_type
    assert linked_order.created_last_price == order.created_last_price
    assert linked_order.origin_price == order_price
    assert linked_order.linked_orders[0] == order
    assert linked_order.created_last_price == order.created_last_price
    assert linked_order.currency == order.currency
    assert linked_order.currency_total_fees == order.currency_total_fees
    assert linked_order.market_total_fees == order.market_total_fees
    assert linked_order.filled_price == order.filled_price
    assert linked_order.filled_quantity == order.filled_quantity
    assert linked_order.linked_to == order
    assert linked_order.status == order.status
    assert linked_order.symbol == order.symbol
    _check_order_limits(order, market_status)


def test_valid_create_new_order():
    config, exchange, trader, symbol = _get_tools()
    portfolio = trader.get_portfolio()
    order_creator = EvaluatorOrderCreator()

    market_status = exchange.get_market_status(symbol)

    # portfolio: "BTC": 10 "USD": 1000
    last_btc_price = 6943.01

    # order from neutral state
    assert order_creator.create_new_order(-1, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL) is None
    assert order_creator.create_new_order(0.5, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL) is None
    assert order_creator.create_new_order(0, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL) is None
    assert order_creator.create_new_order(-0.5, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL) is None
    assert order_creator.create_new_order(-1, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL) is None

    # valid sell limit order (price adapted)
    orders = order_creator.create_new_order(0.65, symbol, exchange, trader, portfolio, EvaluatorStates.SHORT)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, SellLimitOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == 6995.95045125
    assert order.created_last_price == last_btc_price
    assert order.order_type == TraderOrderType.SELL_LIMIT
    assert order.side == TradeOrderSide.SELL
    assert order.status == OrderStatus.OPEN
    assert order.exchange == exchange
    assert order.trader == trader
    assert order.currency_total_fees == 0
    assert order.market_total_fees == 0
    assert order.filled_price == 0
    assert order.origin_quantity == 7.6
    assert order.filled_quantity == order.origin_quantity
    assert order.is_simulated is True
    assert order.linked_to is None

    _check_order_limits(order, market_status)

    assert len(order.linked_orders) == 1
    _check_linked_order(order, order.linked_orders[0], TraderOrderType.STOP_LOSS, 6595.8595, market_status)

    # valid buy limit order with (price and quantity adapted)
    orders = order_creator.create_new_order(-0.65, symbol, exchange, trader, portfolio, EvaluatorStates.LONG)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, BuyLimitOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == 6890.06954875
    assert order.created_last_price == last_btc_price
    assert order.order_type == TraderOrderType.BUY_LIMIT
    assert order.side == TradeOrderSide.BUY
    assert order.status == OrderStatus.OPEN
    assert order.exchange == exchange
    assert order.trader == trader
    assert order.currency_total_fees == 0
    assert order.market_total_fees == 0
    assert order.filled_price == 0
    assert order.origin_quantity == 0.21892522
    assert order.filled_quantity == order.origin_quantity
    assert order.is_simulated is True
    assert order.linked_to is None

    _check_order_limits(order, market_status)

    # assert len(order.linked_orders) == 1  # check linked orders when it will be developed

    # valid buy market order with (price and quantity adapted)
    orders = order_creator.create_new_order(-1, symbol, exchange, trader, portfolio, EvaluatorStates.VERY_LONG)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, BuyMarketOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == last_btc_price
    assert order.created_last_price == last_btc_price
    assert order.order_type == TraderOrderType.BUY_MARKET
    assert order.side == TradeOrderSide.BUY
    assert order.status == OrderStatus.OPEN
    assert order.exchange == exchange
    assert order.trader == trader
    assert order.currency_total_fees == 0
    assert order.market_total_fees == 0
    assert order.filled_price == 0
    assert order.origin_quantity == 0.03540179
    assert order.filled_quantity == order.origin_quantity
    assert order.is_simulated is True
    assert order.linked_to is None

    _check_order_limits(order, market_status)

    # valid buy market order with (price and quantity adapted)
    orders = order_creator.create_new_order(1, symbol, exchange, trader, portfolio, EvaluatorStates.VERY_SHORT)
    assert len(orders) == 1
    order = orders[0]
    assert isinstance(order, SellMarketOrder)
    assert order.currency == "BTC"
    assert order.symbol == "BTC/USDT"
    assert order.origin_price == last_btc_price
    assert order.created_last_price == last_btc_price
    assert order.order_type == TraderOrderType.SELL_MARKET
    assert order.side == TradeOrderSide.SELL
    assert order.status == OrderStatus.OPEN
    assert order.exchange == exchange
    assert order.trader == trader
    assert order.currency_total_fees == 0
    assert order.market_total_fees == 0
    assert order.filled_price == 0
    assert order.origin_quantity == 2.4
    assert order.filled_quantity == order.origin_quantity
    assert order.is_simulated is True
    assert order.linked_to is None

    _check_order_limits(order, market_status)


def test_invalid_create_new_order():
    config, exchange, trader, symbol = _get_tools()
    portfolio = trader.get_portfolio()
    order_creator = EvaluatorOrderCreator()

    # portfolio: "BTC": 10 "USD": 1000
    min_trigger_market = "ADA/BNB"

    # invalid buy order with not trade data
    orders = order_creator.create_new_order(0.6, min_trigger_market, exchange, trader, portfolio, EvaluatorStates.SHORT)
    assert orders is None

    trader.portfolio.portfolio["BTC"] = {
        Portfolio.TOTAL: 2000,
        Portfolio.AVAILABLE: 0.000000000000000000005
    }

    # invalid buy order with not enough currency to sell
    orders = order_creator.create_new_order(0.6, symbol, exchange, trader, portfolio, EvaluatorStates.SHORT)
    assert len(orders) == 0

    trader.portfolio.portfolio["USDT"] = {
        Portfolio.TOTAL: 2000,
        Portfolio.AVAILABLE: 0.000000000000000000005
    }

    # invalid buy order with not enough currency to buy
    orders = order_creator.create_new_order(-0.6, symbol, exchange, trader, portfolio, EvaluatorStates.LONG)
    assert len(orders) == 0


def test_split_create_new_order():
    config, exchange, trader, symbol = _get_tools()
    portfolio = trader.get_portfolio()
    order_creator = EvaluatorOrderCreator()
    last_btc_price = 6943.01

    market_status = exchange.get_market_status(symbol)
    trader.portfolio.portfolio["BTC"] = {
        Portfolio.TOTAL: 2000000001,
        Portfolio.AVAILABLE: 2000000001
    }
    # split orders because order too big and coin price too high
    orders = order_creator.create_new_order(0.6, symbol, exchange, trader, portfolio, EvaluatorStates.SHORT)
    assert len(orders) == 11
    adapted_order = orders[0]
    identical_orders = orders[1:]

    assert isinstance(adapted_order, SellLimitOrder)
    assert adapted_order.currency == "BTC"
    assert adapted_order.symbol == "BTC/USDT"
    assert adapted_order.origin_price == 6998.55407999
    assert adapted_order.created_last_price == last_btc_price
    assert adapted_order.order_type == TraderOrderType.SELL_LIMIT
    assert adapted_order.side == TradeOrderSide.SELL
    assert adapted_order.status == OrderStatus.OPEN
    assert adapted_order.exchange == exchange
    assert adapted_order.trader == trader
    assert adapted_order.currency_total_fees == 0
    assert adapted_order.market_total_fees == 0
    assert adapted_order.filled_price == 0
    assert adapted_order.origin_quantity == 51133425.486746
    assert adapted_order.filled_quantity == adapted_order.origin_quantity
    assert adapted_order.is_simulated is True
    assert adapted_order.linked_to is None

    _check_order_limits(adapted_order, market_status)

    assert len(adapted_order.linked_orders) == 1
    _check_linked_order(adapted_order, adapted_order.linked_orders[0], TraderOrderType.STOP_LOSS, 6595.8595, market_status)

    for order in identical_orders:
        assert isinstance(order, SellLimitOrder)
        assert order.currency == adapted_order.currency
        assert order.symbol == adapted_order.symbol
        assert order.origin_price == adapted_order.origin_price
        assert order.created_last_price == adapted_order.created_last_price
        assert order.order_type == adapted_order.order_type
        assert order.side == adapted_order.side
        assert order.status == adapted_order.status
        assert order.exchange == adapted_order.exchange
        assert order.trader == adapted_order.trader
        assert order.currency_total_fees == adapted_order.currency_total_fees
        assert order.market_total_fees == adapted_order.market_total_fees
        assert order.filled_price == adapted_order.filled_price
        assert order.origin_quantity == 142886657.52532542
        assert order.origin_quantity > adapted_order.origin_quantity
        assert order.filled_quantity > adapted_order.filled_quantity
        assert order.is_simulated == adapted_order.is_simulated
        assert order.linked_to == adapted_order.linked_to
        assert len(order.linked_orders) == 1

        _check_order_limits(order, market_status)
        _check_linked_order(order, order.linked_orders[0], TraderOrderType.STOP_LOSS, 6595.8595, market_status)

    trader.portfolio.portfolio["USDT"] = {
        Portfolio.TOTAL: 20000000000,
        Portfolio.AVAILABLE: 20000000000
    }

    # set btc last price to 6998.55407999 * 0.000001 = 0.00699855408
    exchange.get_exchange().set_recent_trades_multiplier_factor(0.000001)
    # split orders because order too big and too many coins
    orders = order_creator.create_new_order(-0.6, symbol, exchange, trader, portfolio, EvaluatorStates.LONG)
    assert len(orders) == 3
    adapted_order = orders[0]
    identical_orders = orders[1:]

    assert isinstance(adapted_order, BuyLimitOrder)
    assert adapted_order.currency == "BTC"
    assert adapted_order.symbol == "BTC/USDT"
    assert adapted_order.origin_price == 0.00688746
    assert adapted_order.created_last_price == 0.0069430099999999995
    assert adapted_order.order_type == TraderOrderType.BUY_LIMIT
    assert adapted_order.side == TradeOrderSide.BUY
    assert adapted_order.status == OrderStatus.OPEN
    assert adapted_order.exchange == exchange
    assert adapted_order.trader == trader
    assert adapted_order.currency_total_fees == 0
    assert adapted_order.market_total_fees == 0
    assert adapted_order.filled_price == 0
    assert adapted_order.origin_quantity == 131640311622.76904
    assert adapted_order.filled_quantity == adapted_order.origin_quantity
    assert adapted_order.is_simulated is True
    assert adapted_order.linked_to is None

    _check_order_limits(adapted_order, market_status)

    # assert len(order.linked_orders) == 1  # check linked orders when it will be developed

    for order in identical_orders:
        assert isinstance(order, BuyLimitOrder)
        assert order.currency == adapted_order.currency
        assert order.symbol == adapted_order.symbol
        assert order.origin_price == adapted_order.origin_price
        assert order.created_last_price == adapted_order.created_last_price
        assert order.order_type == adapted_order.order_type
        assert order.side == adapted_order.side
        assert order.status == adapted_order.status
        assert order.exchange == adapted_order.exchange
        assert order.trader == adapted_order.trader
        assert order.currency_total_fees == adapted_order.currency_total_fees
        assert order.market_total_fees == adapted_order.market_total_fees
        assert order.filled_price == adapted_order.filled_price
        assert order.origin_quantity == 1000000000000.0
        assert order.origin_quantity > adapted_order.origin_quantity
        assert order.filled_quantity > adapted_order.filled_quantity
        assert order.is_simulated == adapted_order.is_simulated
        assert order.linked_to == adapted_order.linked_to

        _check_order_limits(order, market_status)

        # assert len(order.linked_orders) == 1 # check linked orders when it will be developed
