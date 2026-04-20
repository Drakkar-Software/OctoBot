# Drakkar-Software OctoBot-Tentacles
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
import decimal
import typing

import mock
import pytest
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_order_book_distribution as advanced_order_book_distribution

TARGET_CUMULATED_VOLUME_PERCENT: decimal.Decimal = decimal.Decimal("2")
DAILY_TRADING_VOLUME_PERCENT: decimal.Decimal = decimal.Decimal("1")
BIDS_COUNT: int = 5
ASKS_COUNT: int = 5
MIN_SPREAD: decimal.Decimal = decimal.Decimal("0.005")
MAX_SPREAD: decimal.Decimal = decimal.Decimal("0.05")
PRICE_DISTRIBUTION: advanced_order_book_distribution.OrdersDistribution = advanced_order_book_distribution.OrdersDistribution.LINEAR
FUNDS_DISTRIBUTION: advanced_order_book_distribution.FundsDistribution = advanced_order_book_distribution.FundsDistribution.VALLEY
MAX_BASE_BUDGET: typing.Optional[decimal.Decimal] = decimal.Decimal("0.02")
MAX_QUOTE_BUDGET: typing.Optional[decimal.Decimal] = decimal.Decimal("1000")
MIN_BASE_BUDGET: typing.Optional[decimal.Decimal] = decimal.Decimal("0.0001")
MIN_QUOTE_BUDGET: typing.Optional[decimal.Decimal] = decimal.Decimal("10")
# binance symbol market extract
SYMBOL_MARKET = {
    'id': 'BTCUSDT', 'lowercaseId': 'btcusdt', 'symbol': 'BTC/USDT', 'base': 'BTC', 'quote': 'USDT',
    'settle': None, 'baseId': 'BTC', 'quoteId': 'USDT', 'settleId': None, 'type': 'spot', 'spot': True,
    'margin': True, 'swap': False, 'future': False, 'option': False, 'index': None, 'active': True,
    'contract': False, 'linear': None, 'inverse': None, 'subType': None, 'taker': 0.001, 'maker': 0.001,
    'contractSize': None, 'expiry': None, 'expiryDatetime': None, 'strike': None, 'optionType': None,
    'precision': {'amount': 5, 'price': 2, 'cost': None, 'base': 1e-08, 'quote': 1e-08},
    'limits': {
        'leverage': {'min': None, 'max': None},
        'amount': {'min': 1e-05, 'max': 9000.0},
        'price': {'min': 0.01, 'max': 1000000.0},
        'cost': {'min': 5.0, 'max': 9000000.0},
        'market': {'min': 0.0, 'max': 107.1489592}
    }, 'created': None,
    'percentage': True, 'feeSide': 'get', 'tierBased': False
}


@pytest.fixture
def distribution():
    return advanced_order_book_distribution.AdvancedOrderBookDistribution(
        BIDS_COUNT,
        ASKS_COUNT,
        MIN_SPREAD,
        MAX_SPREAD,
        TARGET_CUMULATED_VOLUME_PERCENT,
        DAILY_TRADING_VOLUME_PERCENT,
        PRICE_DISTRIBUTION,
        FUNDS_DISTRIBUTION,
        MAX_BASE_BUDGET,
        MAX_QUOTE_BUDGET,
        MIN_BASE_BUDGET,
        MIN_QUOTE_BUDGET,
    )


@pytest.fixture
def no_budget_distribution():
    return advanced_order_book_distribution.AdvancedOrderBookDistribution(
        BIDS_COUNT,
        ASKS_COUNT,
        MIN_SPREAD,
        MAX_SPREAD,
        TARGET_CUMULATED_VOLUME_PERCENT,
        DAILY_TRADING_VOLUME_PERCENT,
        PRICE_DISTRIBUTION,
        FUNDS_DISTRIBUTION,
        None,
        None,
    )


def test_compute_distribution_base_config(no_budget_distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
    # without available base / quote values
    assert no_budget_distribution is no_budget_distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert len(no_budget_distribution.asks) == ASKS_COUNT
    assert len(no_budget_distribution.bids) == BIDS_COUNT
    # buy orders: lower than price, ordered from the highest to the lowest
    assert [o.price for o in no_budget_distribution.bids] == [
        decimal.Decimal(str(p)) for p in [49875.11, 49593.86, 49312.61, 49031.36, 48750.11]
    ]
    highest_buy, lowest_buy = no_budget_distribution.bids[0].price, no_budget_distribution.bids[-1].price
    lowest_sell, highest_sell = no_budget_distribution.asks[0].price, no_budget_distribution.asks[-1].price

    # check spread
    assert round(lowest_sell - highest_buy, 1) == round(price * MIN_SPREAD, 1)
    assert round(highest_sell - lowest_buy, 1) == round(price * MAX_SPREAD, 1)

    # check order book depth
    provided_asks_volume_at_target_prices = sum(
        o.amount for o in no_budget_distribution.asks
        if o.price <= price * (1 + TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_base_volume = daily_base_volume * DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_base_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert provided_asks_volume_at_target_prices >= min_target_base_volume * decimal.Decimal("0.999")

    quote_provided_bids_volume_at_target_prices = sum(
        o.amount * o.price for o in no_budget_distribution.bids
        if o.price >= price * (1 - TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_quote_volume = daily_quote_volume * DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_quote_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert quote_provided_bids_volume_at_target_prices >= min_target_quote_volume * decimal.Decimal("0.999")

    # sell orders: higher than price, ordered from the lowest to the highest
    assert [o.price for o in no_budget_distribution.asks] == [
        decimal.Decimal(str(p)) for p in [50125.12, 50406.37, 50687.62, 50968.87, 51250.12]
    ]
    # no budgets: ideal distribution
    # valley mode: orders are larger and larger
    assert [o.amount for o in no_budget_distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.01503, 0.02016, 0.02534, 0.03059, 0.03589]
    ]
    total_bid_size = sum(o.amount for o in no_budget_distribution.bids)
    assert total_bid_size
    # valley mode: orders are larger and larger
    assert [o.amount for o in no_budget_distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.01685, 0.02246, 0.02808, 0.03370, 0.03932]
    ]

    trigger_source = "ref_price"
    available_quote = no_budget_distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.BUY, price, daily_base_volume, daily_quote_volume,
    )
    available_base = no_budget_distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.SELL, price, daily_base_volume, daily_quote_volume,
    )
    # ensure distance computation is correct
    distance_from_ideal_after_swaps = no_budget_distribution.get_shape_distance_from(
        no_budget_distribution.bids + no_budget_distribution.asks,
        available_base, available_quote,
        price, daily_base_volume, daily_quote_volume, trigger_source
    )
    assert 0 < distance_from_ideal_after_swaps < 0.002


def test_compute_distribution_base_config_many_orders(no_budget_distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
    no_budget_distribution.bids_count = 25
    no_budget_distribution.asks_count = 40
    no_budget_distribution.min_spread = decimal.Decimal("0.01")
    no_budget_distribution.max_spread = decimal.Decimal("0.15")
    # without available base / quote values
    assert no_budget_distribution is no_budget_distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert len(no_budget_distribution.asks) == no_budget_distribution.asks_count
    assert len(no_budget_distribution.bids) == no_budget_distribution.bids_count
    # buy orders: lower than price, ordered from the highest to the lowest
    highest_buy, lowest_buy = no_budget_distribution.bids[0].price, no_budget_distribution.bids[-1].price
    lowest_sell, highest_sell = no_budget_distribution.asks[0].price, no_budget_distribution.asks[-1].price

    # check spread
    assert round(lowest_sell - highest_buy, 1) == round(price * no_budget_distribution.min_spread, 1)
    assert round(highest_sell - lowest_buy, 1) == round(price * no_budget_distribution.max_spread, 1)

    # check order book depth
    provided_asks_volume_at_target_prices = sum(
        o.amount for o in no_budget_distribution.asks
        if o.price <= price * (1 + TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_base_volume = daily_base_volume * DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_base_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert provided_asks_volume_at_target_prices >= min_target_base_volume * decimal.Decimal("0.999")

    quote_provided_bids_volume_at_target_prices = sum(
        o.amount * o.price for o in no_budget_distribution.bids
        if o.price >= price * (1 - TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_quote_volume = daily_quote_volume * DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_quote_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert quote_provided_bids_volume_at_target_prices >= min_target_quote_volume * decimal.Decimal("0.999")

    # buy orders: higher than price, ordered from the highest to the lowest
    bid_prices = [o.price for o in no_budget_distribution.bids]
    assert sorted(bid_prices, reverse=True) == bid_prices
    # sell orders: higher than price, ordered from the lowest to the highest
    asks_prices = [o.price for o in no_budget_distribution.asks]
    assert sorted(asks_prices) == asks_prices

    # valley mode: orders are larger and larger
    asks_amounts = [o.amount for o in no_budget_distribution.asks]
    assert sorted(asks_amounts) == asks_amounts
    bids_amounts = [o.amount for o in no_budget_distribution.bids]
    assert sorted(bids_amounts) == bids_amounts

    trigger_source = "ref_price"
    available_quote = no_budget_distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.BUY, price, daily_base_volume, daily_quote_volume,
    )
    available_base = no_budget_distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.SELL, price, daily_base_volume, daily_quote_volume,
    )
    # ensure distance computation is correct
    distance_from_ideal_after_swaps = no_budget_distribution.get_shape_distance_from(
        no_budget_distribution.bids + no_budget_distribution.asks,
        available_base, available_quote,
        price, daily_base_volume, daily_quote_volume, trigger_source
    )
    assert 0 < distance_from_ideal_after_swaps < 0.004


def test_compute_distribution_base_config_with_max_budget(distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
    distribution.max_base_budget = decimal.Decimal("0.001245")
    distribution.max_quote_budget = decimal.Decimal("366.444444")
    # without available base / quote values
    assert distribution is distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert len(distribution.asks) == ASKS_COUNT
    assert len(distribution.bids) == BIDS_COUNT
    # price did not change
    assert [o.price for o in distribution.bids] == [
        decimal.Decimal(str(p)) for p in [49875.11, 49593.86, 49312.61, 49031.36, 48750.11]
    ]
    # price did not change
    assert [o.price for o in distribution.asks] == [
        decimal.Decimal(str(p)) for p in [50125.12, 50406.37, 50687.62, 50968.87, 51250.12]
    ]
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.00088, 0.00118, 0.00148, 0.00179, 0.00210]
    ]
    total_bid_quote_size = sum(o.amount * o.price for o in distribution.bids)
    assert (
        distribution.max_quote_budget * decimal.Decimal("0.99")
        <= total_bid_quote_size
        <= distribution.max_quote_budget
    )
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.00014, 0.00019, 0.00024, 0.00029, 0.00034]
    ]
    total_ask_size = sum(o.amount for o in distribution.asks)
    # rounded to 95% as available_base is very low
    assert (
        distribution.max_base_budget * decimal.Decimal("0.95") <= total_ask_size <= distribution.max_base_budget
    )

    trigger_source = "ref_price"
    available_quote = distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.BUY, price, daily_base_volume, daily_quote_volume,
    )
    available_base = distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.SELL, price, daily_base_volume, daily_quote_volume,
    )
    # ensure distance computation is correct
    distance_from_ideal_after_swaps = distribution.get_shape_distance_from(
        distribution.bids + distribution.asks,
        available_base, available_quote,
        price, daily_base_volume, daily_quote_volume, trigger_source
    )
    assert 0 < distance_from_ideal_after_swaps < 0.006


def test_compute_distribution_base_config_with_min_budget(distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("0.00000000111111111111111111")
    daily_quote_volume = decimal.Decimal("0.22222222222222222222222")
    distribution.max_base_budget = decimal.Decimal("0.001245")
    distribution.max_quote_budget = decimal.Decimal("366.444444")
    # without available base / quote values
    assert distribution is distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert len(distribution.asks) == ASKS_COUNT
    assert len(distribution.bids) == BIDS_COUNT
    # price did not change
    assert [o.price for o in distribution.bids] == [
        decimal.Decimal(str(p)) for p in [49875.11, 49593.86, 49312.61, 49031.36, 48750.11]
    ]
    # price did not change
    assert [o.price for o in distribution.asks] == [
        decimal.Decimal(str(p)) for p in [50125.12, 50406.37, 50687.62, 50968.87, 51250.12]
    ]
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.00002, 0.00003, 0.00004, 0.00004, 0.00005]
    ]
    total_bid_quote_size = sum(o.amount * o.price for o in distribution.bids)
    assert (
        distribution.min_quote_budget * decimal.Decimal("0.8")
        <= total_bid_quote_size
        <= distribution.min_quote_budget * decimal.Decimal("1.1")
    )
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.00001, 0.00001, 0.00002, 0.00002, 0.00002]
    ]
    total_ask_size = sum(o.amount for o in distribution.asks)
    # rounded to 95% as available_base is very low
    assert (
        distribution.min_base_budget * decimal.Decimal("0.8")
        <= total_ask_size <=
        distribution.min_base_budget * decimal.Decimal("0.8")
    )

    trigger_source = "ref_price"
    available_quote = distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.BUY, price, daily_base_volume, daily_quote_volume,
    )
    available_base = distribution.get_ideal_total_volume(
        trading_enums.TradeOrderSide.SELL, price, daily_base_volume, daily_quote_volume,
    )
    # ensure distance computation is correct
    distance_from_ideal_after_swaps = distribution.get_shape_distance_from(
        distribution.bids + distribution.asks,
        available_base, available_quote,
        price, daily_base_volume, daily_quote_volume, trigger_source
    )
    assert 0 < distance_from_ideal_after_swaps < 0.1


def test_compute_distribution_base_config_with_max_available_amounts(distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
    distribution.max_base_budget = decimal.Decimal("0.1245")
    distribution.max_quote_budget = decimal.Decimal("366.444444")
    available_base = decimal.Decimal("0.0945")
    available_quote = decimal.Decimal("199.01")
    # without available base / quote values
    assert distribution is distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET,
        available_base=available_base,
        available_quote=available_quote,
    )
    assert len(distribution.asks) == ASKS_COUNT
    assert len(distribution.bids) == BIDS_COUNT
    # price did not change
    assert [o.price for o in distribution.bids] == [
        decimal.Decimal(str(p)) for p in [49875.11, 49593.86, 49312.61, 49031.36, 48750.11]
    ]
    # price did not change
    assert [o.price for o in distribution.asks] == [
        decimal.Decimal(str(p)) for p in [50125.12, 50406.37, 50687.62, 50968.87, 51250.12]
    ]
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.00047, 0.00064, 0.00080, 0.00097, 0.00114]
    ]
    total_bid_size = sum(o.amount * o.price for o in distribution.bids)
    assert (
        available_quote * decimal.Decimal("0.99") <= total_bid_size <= available_quote
    )
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.01134, 0.01512, 0.01890, 0.02268, 0.02646]
    ]
    total_ask_size = sum(o.amount for o in distribution.asks)
    assert (
        available_base * decimal.Decimal("0.9999") <= total_ask_size <= available_base
    )

    trigger_source = "ref_price"
    # ensure distance computation is correct
    distance_from_ideal_after_swaps = distribution.get_shape_distance_from(
        distribution.bids + distribution.asks,
        available_base, available_quote,
        price, daily_base_volume, daily_quote_volume, trigger_source
    )
    assert 0 < distance_from_ideal_after_swaps < 0.004


def test_infer_full_order_data_after_swaps(no_budget_distribution):
    # init ideal distribution
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10")
    daily_quote_volume = decimal.Decimal("450000")
    no_budget_distribution.bids_count = 10
    no_budget_distribution.asks_count = 10
    no_budget_distribution.min_spread = decimal.Decimal("0.01")
    no_budget_distribution.max_spread = decimal.Decimal("0.15")
    # without available base / quote values
    no_budget_distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert no_budget_distribution.asks
    assert no_budget_distribution.bids
    sorted_ideal_bids = order_book_distribution.get_sorted_sided_orders(no_budget_distribution.bids, True)
    sorted_ideal_asks = order_book_distribution.get_sorted_sided_orders(no_budget_distribution.asks, True)
    ideal_orders = sorted_ideal_bids + sorted_ideal_asks
    available_base = MAX_BASE_BUDGET * 2
    available_quote = MAX_QUOTE_BUDGET * 2

    # 1. ideal orders are open
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        ideal_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert updated_orders == ideal_orders   # no scheduled change

    # 2.a an ideal sell order got filled
    existing_orders = sorted_ideal_bids + sorted_ideal_asks[1:]
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[0:10] == existing_orders[0:10]    # buy orders are identical
    assert updated_orders[11:20] == existing_orders[10:19]    # sell orders are identical
    # (except for 1st sell, which is not in existing orders)
    assert round(updated_orders[10].price, 1) == round(sorted_ideal_asks[0].price, 1)

    # 2.b an ideal sell order got filled and price is too high to recreate it: move buy orders instead
    existing_orders = sorted_ideal_bids + sorted_ideal_asks[1:]
    price = sorted_ideal_asks[0].price + decimal.Decimal("20")
    flat_spread = price * no_budget_distribution.min_spread
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[1:10] == sorted_ideal_bids[0:9]    # buy orders have been moved
    # (except for 1st buy, which is not in existing orders)
    assert updated_orders[0].price > sorted_ideal_bids[0].price
    assert updated_orders[10:19] == existing_orders[10:19]    # sell orders are identical
    # (except for the 1 sell, which is not in existing orders)
    assert updated_orders[10].price > sorted_ideal_asks[0].price

    assert updated_orders[10].price - updated_orders[0].price == flat_spread    # spread is kept

    # 3a filled 1 buy and 1 sell order
    existing_orders = sorted_ideal_bids[1:] + sorted_ideal_asks[1:]
    price = sorted_ideal_asks[0].price + decimal.Decimal("20")
    flat_spread = price * no_budget_distribution.min_spread
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[2:10] == sorted_ideal_bids[1:9]    # buy orders have been moved
    # (except for 1st buy, which is not in existing orders)
    assert updated_orders[0].price > updated_orders[1].price
    assert updated_orders[0].price > sorted_ideal_bids[0].price
    assert updated_orders[11:19] == sorted_ideal_asks[2:10]    # sell orders are identical
    # (except for 1st sell, which is not in existing orders)
    assert updated_orders[10].price > sorted_ideal_asks[0].price

    assert updated_orders[10].price - updated_orders[0].price == flat_spread    # spread is kept

    # 3b filled 2 buy and 3 sell order
    existing_orders = sorted_ideal_bids[2:] + sorted_ideal_asks[3:]
    price = sorted_ideal_asks[3].price + decimal.Decimal("20")
    flat_spread = price * no_budget_distribution.min_spread
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[6:10] == sorted_ideal_bids[2:6]    # buy orders have been moved
    assert updated_orders[0].price > sorted_ideal_bids[0].price
    assert updated_orders[10:15] == sorted_ideal_asks[4:9]    # sell orders have been moved
    assert updated_orders[10].price > sorted_ideal_asks[0].price

    assert updated_orders[10].price - updated_orders[0].price == flat_spread    # spread is kept

    # 4.a outdated buy order
    outdated = sorted_ideal_bids[0]
    outdated_order = mock.Mock(
        side=outdated.side,
        origin_price=outdated.price,
        origin_quantity=outdated.amount,
        trader=mock.Mock(simulate=True),
    )
    price = outdated_order.origin_price - decimal.Decimal("150")    # large difference
    flat_spread = price * no_budget_distribution.min_spread
    existing_orders = sorted_ideal_bids[1:] + sorted_ideal_asks
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, [outdated_order], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[0:8] == sorted_ideal_bids[1:9]    # buy orders have been moved
    assert updated_orders[0].price < sorted_ideal_bids[0].price
    assert updated_orders[11:20] == sorted_ideal_asks[0:9]    # sell orders have been moved
    assert updated_orders[10].price < sorted_ideal_asks[0].price

    assert updated_orders[10].price - updated_orders[0].price == flat_spread    # spread is kept

    # 5. 3 outdated buy order
    outdated_o = sorted_ideal_bids[0:2]
    outdated_orders = [
        mock.Mock(
            side=outdated.side,
            origin_price=outdated.price,
            origin_quantity=outdated.amount,
            trader=mock.Mock(simulate=True),
        )
        for outdated in outdated_o
    ]
    price = outdated_orders[-1].origin_price - decimal.Decimal("1") # small difference
    flat_spread = price * no_budget_distribution.min_spread
    existing_orders = sorted_ideal_bids[2:] + sorted_ideal_asks
    updated_orders = no_budget_distribution.infer_full_order_data_after_swaps(
        existing_orders, outdated_orders, available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 20
    assert updated_orders[0:7] == sorted_ideal_bids[2:9]    # buy orders have been moved
    assert updated_orders[0].price < sorted_ideal_bids[0].price
    assert updated_orders[12:20] == sorted_ideal_asks[0:8]    # sell orders have been moved
    assert updated_orders[10].price < sorted_ideal_asks[0].price

    assert updated_orders[10].price - updated_orders[0].price == flat_spread    # spread is kept


def test_validate_config(distribution):
    distribution.validate_config()  # does not raise

    # bids & asks count
    distribution.asks_count = order_book_distribution.MAX_HANDLED_ASKS_ORDERS
    distribution.validate_config()  # does not raise
    distribution.asks_count = order_book_distribution.MAX_HANDLED_ASKS_ORDERS + 1
    distribution.validate_config()  # does not raise (no limit)
    distribution.bids_count = 999
    distribution.validate_config()  # does not raise (no limit)

    # min spread
    distribution.min_spread = distribution.max_spread
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.min_spread = distribution.max_spread + 1
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.min_spread = distribution.max_spread - 1

    assert 50 > decimal.Decimal("2") * distribution.target_cumulated_volume_percent / trading_constants.ONE_HUNDRED
    distribution.min_spread = decimal.Decimal(50)
    with pytest.raises(ValueError):
        distribution.validate_config()
