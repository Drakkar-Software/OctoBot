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
import pytest

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution

BIDS_COUNT: int = 5
ASKS_COUNT: int = 5
MIN_SPREAD: decimal.Decimal = decimal.Decimal("0.005")
MAX_SPREAD: decimal.Decimal = decimal.Decimal("0.05")
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
    return order_book_distribution.OrderBookDistribution(
        BIDS_COUNT,
        ASKS_COUNT,
        MIN_SPREAD,
        MAX_SPREAD,
    )


def test_compute_distribution_base_config(distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
    # without available base / quote values
    assert distribution is distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert len(distribution.asks) == ASKS_COUNT
    assert len(distribution.bids) == BIDS_COUNT
    # buy orders: lower than price, ordered from the highest to the lowest
    assert [o.price for o in distribution.bids] == [
        decimal.Decimal(str(p)) for p in [49875.11, 49593.86, 49312.61, 49031.36, 48750.11]
    ]
    highest_buy, lowest_buy = distribution.bids[0].price, distribution.bids[-1].price
    lowest_sell, highest_sell = distribution.asks[0].price, distribution.asks[-1].price

    # check spread
    assert round(lowest_sell - highest_buy, 1) == round(price * MIN_SPREAD, 1)
    assert round(highest_sell - lowest_buy, 1) == round(price * MAX_SPREAD, 1)

    # check order book depth
    provided_asks_volume_at_target_prices = sum(
        o.amount for o in distribution.asks
        if o.price <= price * (1 + order_book_distribution.TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_base_volume = daily_base_volume * order_book_distribution.DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_base_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert provided_asks_volume_at_target_prices >= min_target_base_volume * decimal.Decimal("0.999")

    quote_provided_bids_volume_at_target_prices = sum(
        o.amount * o.price for o in distribution.bids
        if o.price >= price * (1 - order_book_distribution.TARGET_CUMULATED_VOLUME_PERCENT / decimal.Decimal(100))
    )
    min_target_quote_volume = daily_quote_volume * order_book_distribution.DAILY_TRADING_VOLUME_PERCENT / decimal.Decimal(100)
    assert min_target_quote_volume > decimal.Decimal("0")
    # use 99.9 of target value to account for decimal trunc
    assert quote_provided_bids_volume_at_target_prices >= min_target_quote_volume * decimal.Decimal("0.999")

    # sell orders: higher than price, ordered from the lowest to the highest
    assert [o.price for o in distribution.asks] == [
        decimal.Decimal(str(p)) for p in [50125.12, 50406.37, 50687.62, 50968.87, 51250.12]
    ]
    assert [o.amount for o in distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.03609, 0.03629, 0.0365, 0.03671, 0.03692]
    ]
    total_bid_size = sum(o.amount for o in distribution.bids)
    assert total_bid_size
    assert [o.amount for o in distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.04044, 0.04044, 0.04044, 0.04044, 0.04044]
    ]

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


def test_compute_distribution_base_config_with_max_available_amounts(distribution):
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10.1111111111111111111111111")
    daily_quote_volume = decimal.Decimal("450000.22222222222222222222222")
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
    # volumes are reduced according available funds
    assert [o.amount for o in distribution.bids] == [
        decimal.Decimal(str(a)) for a in [0.00079, 0.0008, 0.0008, 0.00081, 0.00081]
    ]
    total_bid_size = sum(o.amount * o.price for o in distribution.bids)
    assert (
        available_quote * decimal.Decimal("0.99") <= total_bid_size <= available_quote
    )
    # volumes are reduced according to budget
    assert [o.amount for o in distribution.asks] == [
        decimal.Decimal(str(a)) for a in [0.0189, 0.0189, 0.0189, 0.0189, 0.0189]
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
    assert 0 < distance_from_ideal_after_swaps < 0.008


def test_infer_full_order_data_after_swaps(distribution):
    # init ideal distribution
    price = decimal.Decimal("50000.12")
    daily_base_volume = decimal.Decimal("10")
    daily_quote_volume = decimal.Decimal("450000")
    distribution.bids_count = 5
    distribution.asks_count = 5
    distribution.min_spread = decimal.Decimal("0.01")
    distribution.max_spread = decimal.Decimal("0.15")
    # without available base / quote values
    distribution.compute_distribution(
        price, daily_base_volume, daily_quote_volume, SYMBOL_MARKET
    )
    assert distribution.asks
    assert distribution.bids
    sorted_ideal_bids = order_book_distribution.get_sorted_sided_orders(distribution.bids, True)
    sorted_ideal_asks = order_book_distribution.get_sorted_sided_orders(distribution.asks, True)
    ideal_orders = sorted_ideal_bids + sorted_ideal_asks
    available_base = decimal.Decimal("0.04")
    available_quote = decimal.Decimal("2000")

    # 1. ideal orders are open
    updated_orders = distribution.infer_full_order_data_after_swaps(
        ideal_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert updated_orders == ideal_orders   # no scheduled change

    # 2.a an ideal sell order got filled
    existing_orders = sorted_ideal_bids + sorted_ideal_asks[1:]
    updated_orders = distribution.infer_full_order_data_after_swaps(
        existing_orders, [], available_base, available_quote, price, daily_base_volume, daily_quote_volume
    )
    assert len(updated_orders) == 10
    assert updated_orders[0:5] == existing_orders[0:5]    # buy orders are identical
    assert updated_orders[6:10] == existing_orders[5:9]    # sell orders are identical
    # (except for 1st sell, which is not in existing orders)
    assert round(updated_orders[5].price, 1) == round(sorted_ideal_asks[0].price, 1)


def test_validate_config(distribution):
    distribution.validate_config()  # does not raise

    # bids & asks count
    distribution.asks_count = order_book_distribution.MAX_HANDLED_ASKS_ORDERS
    distribution.validate_config()  # does not raise
    distribution.asks_count = order_book_distribution.MAX_HANDLED_ASKS_ORDERS + 1
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.asks_count = order_book_distribution.MAX_HANDLED_ASKS_ORDERS
    distribution.bids_count = order_book_distribution.MAX_HANDLED_BIDS_ORDERS + 1
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.bids_count = order_book_distribution.MAX_HANDLED_BIDS_ORDERS

    # min spread
    distribution.min_spread = distribution.max_spread
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.min_spread = distribution.max_spread + 1
    with pytest.raises(ValueError):
        distribution.validate_config()
    distribution.min_spread = distribution.max_spread - 1

    assert 50 > decimal.Decimal("2") * order_book_distribution.TARGET_CUMULATED_VOLUME_PERCENT / trading_constants.ONE_HUNDRED
    distribution.min_spread = decimal.Decimal(50)
    with pytest.raises(ValueError):
        distribution.validate_config()


def test_get_order_volumes_decreasing(distribution):
    """Test _get_order_volumes with DECREASING direction."""
    side = trading_enums.TradeOrderSide.BUY
    total_volume = decimal.Decimal("100")
    order_prices = [
        decimal.Decimal("50000"),
        decimal.Decimal("49900"),
        decimal.Decimal("49800"),
        decimal.Decimal("49700"),
        decimal.Decimal("49600"),
    ]
    multiplier = decimal.Decimal("1.5")
    
    volumes = distribution._get_order_volumes(
        side, total_volume, order_prices, 
        multiplier=multiplier, direction=order_book_distribution.DECREASING
    )
    
    # DECREASING: orders are smaller when closer to reference price
    # First order (closest to reference) should be smallest
    # Last order (farthest from reference) should be largest
    assert len(volumes) == len(order_prices)
    assert all(vol > decimal.Decimal("0") for vol in volumes)
    
    # Verify volumes are in decreasing order (first is smallest, last is largest)
    for i in range(len(volumes) - 1):
        assert volumes[i] < volumes[i + 1], \
            f"DECREASING direction: volume at index {i} ({volumes[i]}) should be less than at index {i+1} ({volumes[i+1]})"
    
    # Verify total volume matches (allowing for small rounding errors, but never exceeds)
    total = sum(volumes)
    assert total <= total_volume, \
        f"Total volume should not exceed {total_volume}, got {total}"
    assert total >= total_volume - decimal.Decimal("0.01"), \
        f"Total volume should be close to {total_volume}, got {total}"


def test_get_order_volumes_increasing(distribution):
    """Test _get_order_volumes with INCREASING direction."""
    side = trading_enums.TradeOrderSide.SELL
    total_volume = decimal.Decimal("200")
    order_prices = [
        decimal.Decimal("50100"),
        decimal.Decimal("50200"),
        decimal.Decimal("50300"),
        decimal.Decimal("50400"),
        decimal.Decimal("50500"),
    ]
    multiplier = decimal.Decimal("2.0")
    
    volumes = distribution._get_order_volumes(
        side, total_volume, order_prices, 
        multiplier=multiplier, direction=order_book_distribution.INCREASING
    )
    
    # INCREASING: orders are larger when closer to reference price
    # First order (closest to reference) should be largest
    # Last order (farthest from reference) should be smallest
    assert len(volumes) == len(order_prices)
    assert all(vol > decimal.Decimal("0") for vol in volumes)
    
    # Check that the first orders are smaller than the later ones
    for i in range(len(volumes) - 1):
        assert volumes[i] < volumes[i + 1], \
            f"INCREASING direction: volume at index {i} ({volumes[i]}) should be less than at index {i+1} ({volumes[i+1]})"
    
    # Verify total volume matches (allowing for small rounding errors, but never exceeds)
    total = sum(volumes)
    assert total <= total_volume, \
        f"Total volume should not exceed {total_volume}, got {total}"
    assert total >= total_volume - decimal.Decimal("0.01"), \
        f"Total volume should be close to {total_volume}, got {total}"


def test_get_order_volumes_random(distribution):
    """Test _get_order_volumes with RANDOM direction."""
    import random
    
    # Set seed for reproducible test
    random.seed(42)
    
    side = trading_enums.TradeOrderSide.BUY
    total_volume = decimal.Decimal("150")
    order_prices = [
        decimal.Decimal("50000"),
        decimal.Decimal("49900"),
        decimal.Decimal("49800"),
        decimal.Decimal("49700"),
        decimal.Decimal("49600"),
    ]
    multiplier = decimal.Decimal("0.3")
    
    volumes = distribution._get_order_volumes(
        side, total_volume, order_prices, 
        multiplier=multiplier, direction=order_book_distribution.RANDOM
    )
    
    # RANDOM: volumes should be randomly distributed
    assert len(volumes) == len(order_prices)
    assert all(vol > decimal.Decimal("0") for vol in volumes)
    
    # Verify total volume matches (allowing for small rounding errors, but never exceeds)
    total = sum(volumes)
    assert total <= total_volume, \
        f"Total volume should not exceed {total_volume}, got {total}"
    assert total >= total_volume - decimal.Decimal("0.01"), \
        f"Total volume should be close to {total_volume}, got {total}"
    
    # Verify volumes are within expected range based on multiplier
    # With multiplier 0.3, volumes should be between 0.7 * average and 1.3 * average
    average_order_size = total_volume / decimal.Decimal(str(len(order_prices)))
    min_expected = average_order_size * decimal.Decimal("0.7")
    max_expected = average_order_size * decimal.Decimal("1.3")
    
    for vol in volumes:
        assert min_expected <= vol <= max_expected, \
            f"Volume {vol} should be between {min_expected} and {max_expected}"
