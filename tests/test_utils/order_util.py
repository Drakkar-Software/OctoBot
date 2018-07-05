import random
import time

from config.cst import SIMULATOR_LAST_PRICES_TO_CHECK


def fill_limit_or_stop_order(limit_or_stop_order, min_price, max_price):
    last_prices = []
    for i in range(0, SIMULATOR_LAST_PRICES_TO_CHECK):
        last_prices.insert(i, {})
        last_prices[i]["price"] = random.uniform(min_price, max_price)
        last_prices[i]["timestamp"] = time.time()

    limit_or_stop_order.last_prices = last_prices
    limit_or_stop_order.created_time = time.time()
    limit_or_stop_order.update_order_status()


def fill_market_order(market_order, price):
    last_prices = [{
        "price": price
    }]

    market_order.last_prices = last_prices
    market_order.update_order_status()
