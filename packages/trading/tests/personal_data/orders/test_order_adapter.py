#  Drakkar-Software OctoBot-Trading
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
import math
import pytest

from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc
import octobot_trading.personal_data as personal_data
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_adapt_price():
    # will use symbol market
    symbol_market = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_PRICE.value: 4}}
    assert personal_data.adapt_price(symbol_market, 0.0001) == 0.0001
    assert personal_data.adapt_price(symbol_market, 0.00015) == 0.0001
    assert personal_data.adapt_price(symbol_market, 0.005) == 0.005
    assert personal_data.adapt_price(symbol_market, 1) == 1

    assert personal_data.adapt_price(symbol_market, 56.5128597145) == 56.5128
    assert personal_data.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.0000

    # will use default (CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
    symbol_market = {Ecmsc.PRECISION.value: {}}
    assert personal_data.adapt_price(symbol_market, 0.0001) == 0.0001
    assert personal_data.adapt_price(symbol_market, 0.00015) == 0.00014999
    assert personal_data.adapt_price(symbol_market, 0.005) == 0.005
    assert personal_data.adapt_price(symbol_market, 1) == 1.0000000000000000000000001
    assert personal_data.adapt_price(symbol_market, 1) == 1

    assert personal_data.adapt_price(symbol_market, 56.5128597145) == 56.51285971
    assert personal_data.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.00000145


async def test_get_additional_dusts_to_quantity_if_necessary():
    symbol_market = {Ecmsc.LIMITS.value: {
        Ecmsc.LIMITS_AMOUNT.value: {
            Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5
        },
        Ecmsc.LIMITS_COST.value: {
            Ecmsc.LIMITS_COST_MIN.value: 1
        }
    }}

    current_symbol_holding = 5
    quantity = 3
    price = 1
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity + 0

    current_symbol_holding = 5
    quantity = 4
    price = 1
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity + 1

    current_symbol_holding = 5
    quantity = 4.5
    price = 1
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity + 0.5

    symbol_market = {Ecmsc.LIMITS.value: {
        Ecmsc.LIMITS_AMOUNT.value: {
            Ecmsc.LIMITS_AMOUNT_MIN.value: 0.005
        },
        Ecmsc.LIMITS_COST.value: {
            Ecmsc.LIMITS_COST_MIN.value: 0.00005
        }
    }}

    current_symbol_holding = 0.99000000001
    quantity = 0.9
    price = 0.5
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity + 0

    current_symbol_holding = 0.99000000001
    quantity = 0.0215245845
    price = 0.5
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity + 0

    current_symbol_holding = 0.99999999
    quantity = 0.99999
    price = 0.5
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == 0.99999999

    current_symbol_holding = 0.88
    quantity = 0.7055680057024826
    price = 0.0002
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            price,
                                                            symbol_market,
                                                            current_symbol_holding) == 0.88

    # price = 0 => no dust
    assert personal_data.add_dusts_to_quantity_if_necessary(quantity,
                                                            0,
                                                            symbol_market,
                                                            current_symbol_holding) == quantity


async def test_check_and_adapt_order_details_if_necessary():
    symbol_market = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5,
                Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 1,
                Ecmsc.LIMITS_COST_MAX.value: 200
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.5,
                Ecmsc.LIMITS_PRICE_MAX.value: 50
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 8,
            Ecmsc.PRECISION_AMOUNT.value: 8
        }
    }

    invalid_cost_symbol_market = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5,
                Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: None,
                Ecmsc.LIMITS_COST_MAX.value: None
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.5,
                Ecmsc.LIMITS_PRICE_MAX.value: 50
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 8,
            Ecmsc.PRECISION_AMOUNT.value: 8
        }
    }

    # correct min
    quantity = 0.5
    price = 2
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # correct max
    quantity = 100
    price = 2
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # correct
    quantity = 10
    price = 0.6
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # correct
    quantity = 3
    price = 49.9
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # invalid price > but valid cost
    quantity = 1
    price = 100
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # invalid price < but valid cost
    quantity = 10
    price = 0.1
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (quantity, price)]

    # invalid price > and invalid cost from exchange => use price => invalid
    quantity = 1
    price = 100
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, invalid_cost_symbol_market) == []

    # invalid price < and invalid cost from exchange => use price => invalid
    quantity = 1
    price = 0.1
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, invalid_cost_symbol_market) == []

    # invalid cost <
    quantity = 0.5
    price = 1
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

    # invalid cost >
    quantity = 10
    price = 49
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (1.83673469, 49),
        (4.08163265, 49),
        (4.08163265, 49)]

    # high cost but no max cost => valid
    quantity = 10
    price = 49
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [
        (1.83673469, 49),
        (4.08163265, 49),
        (4.08163265, 49)]

    # invalid cost with invalid price >=
    quantity = 10
    price = 50
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(2, 50),
                                                                                                        (4, 50),
                                                                                                        (4, 50)]

    # invalid cost with invalid price > and invalid cost from exchange => use price => invalid
    quantity = 10
    price = 51
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, invalid_cost_symbol_market) == []

    # invalid amount >
    quantity = 200
    price = 5
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(40.0, 5),
                                                                                                        (40.0, 5),
                                                                                                        (40.0, 5),
                                                                                                        (40.0, 5),
                                                                                                        (40.0, 5)]

    # invalid amount <
    quantity = 0.4
    price = 5
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

    symbol_market = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.0000005,
                Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 0.00000001,
                Ecmsc.LIMITS_COST_MAX.value: 10
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.000005,
                Ecmsc.LIMITS_PRICE_MAX.value: 50
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 8,
            Ecmsc.PRECISION_AMOUNT.value: 8
        }
    }

    # correct quantity
    # to test _adapt_order_quantity_because_quantity
    quantity = 5000
    price = 0.001
    expected = [(100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                (100.0, 0.001), (100.0, 0.001)]
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == expected

    # price = 0 => no order
    quantity = 10
    price = 0
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

    symbol_market_without_max = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.0000005,
                Ecmsc.LIMITS_AMOUNT_MAX.value: None,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 0.00000001,
                Ecmsc.LIMITS_COST_MAX.value: None
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.000005,
                Ecmsc.LIMITS_PRICE_MAX.value: None
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 8,
            Ecmsc.PRECISION_AMOUNT.value: 8
        }
    }

    # high cost but no max cost => no split
    quantity = 10
    price = 49
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market_without_max) == [
        (10, 49)]

    # high quantity but no max quantity => no split
    quantity = 10000000
    price = 49
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market_without_max) == \
           [(10000000, 49)]

    # high price but no max price => no split
    quantity = 10
    price = 4900000
    assert personal_data.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market_without_max) == [
        (10, 4900000)]


async def test_split_orders():
    symbol_market = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 1,
                Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 1,
                Ecmsc.LIMITS_COST_MAX.value: 30
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.001,
                Ecmsc.LIMITS_PRICE_MAX.value: 1000
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 1,
            Ecmsc.PRECISION_AMOUNT.value: 1
        }
    }

    symbol_market_without_max = {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 1,
                Ecmsc.LIMITS_AMOUNT_MAX.value: None,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 1,
                Ecmsc.LIMITS_COST_MAX.value: None
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 1,
                Ecmsc.LIMITS_PRICE_MAX.value: None
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 1,
            Ecmsc.PRECISION_AMOUNT.value: 1
        }
    }
    max_cost = symbol_market[Ecmsc.LIMITS.value][Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MAX.value]
    max_quantity = symbol_market[Ecmsc.LIMITS.value][Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value]

    # normal situation, split because of cost
    total_price = 100
    valid_quantity = 5
    price = 20
    assert personal_data.split_orders(total_price, max_cost, valid_quantity,
                                      max_quantity, price, valid_quantity, symbol_market) \
           == [(0.5, 20), (1.5, 20), (1.5, 20), (1.5, 20)]

    # normal situation, split because of quantity
    total_price = 5.0255
    valid_quantity = 502.55
    price = 0.01
    assert personal_data.split_orders(total_price, max_cost, valid_quantity,
                                      max_quantity, price, valid_quantity, symbol_market) \
           == [(2.5, 0.01), (100, 0.01), (100, 0.01), (100, 0.01), (100, 0.01), (100, 0.01)]

    # missing info situation, split because of cost
    max_quantity = None
    total_price = 100
    valid_quantity = 5
    price = 20
    assert personal_data.split_orders(total_price, max_cost, valid_quantity,
                                      max_quantity, price, valid_quantity, symbol_market_without_max) \
           == [(0.5, 20), (1.5, 20), (1.5, 20), (1.5, 20)]

    # missing info situation, split because of quantity
    max_quantity = symbol_market[Ecmsc.LIMITS.value][Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value]
    max_cost = None
    total_price = 5.0255
    valid_quantity = 502.55
    price = 0.01
    assert personal_data.split_orders(total_price, max_cost, valid_quantity,
                                      max_quantity, price, valid_quantity, symbol_market_without_max) \
           == [(2.5, 0.01), (100, 0.01), (100, 0.01), (100, 0.01), (100, 0.01), (100, 0.01)]

    # missing info situation, can't split
    max_quantity = None
    max_cost = None
    total_price = 5.0255
    valid_quantity = 502.55
    price = 0.01
    with pytest.raises(RuntimeError):
        assert personal_data.split_orders(total_price, max_cost, valid_quantity,
                                          max_quantity, price, valid_quantity, symbol_market_without_max)


async def test_adapt_quantity():
    # will use symbol market
    symbol_market = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_AMOUNT.value: 4}}
    assert personal_data.adapt_quantity(symbol_market, 0.0001) == 0.0001
    assert personal_data.adapt_quantity(symbol_market, 0.00015) == 0.0001
    assert personal_data.adapt_quantity(symbol_market, 0.005) == 0.005
    assert personal_data.adapt_quantity(symbol_market, 1) == 1.0000000000000000000000001
    assert personal_data.adapt_quantity(symbol_market, 1) == 1

    assert personal_data.adapt_quantity(symbol_market, 56.5128597145) == 56.5128
    assert personal_data.adapt_quantity(symbol_market, 1251.0000014576121234854513) == 1251.0000

    # will use default (0)
    symbol_market = {Ecmsc.PRECISION.value: {}}
    assert personal_data.adapt_quantity(symbol_market, 0.0001) == 0
    assert personal_data.adapt_quantity(symbol_market, 0.00015) == 0
    assert personal_data.adapt_quantity(symbol_market, 0.005) == 0
    assert personal_data.adapt_quantity(symbol_market, 1) == 1.0000000000000000000000001
    assert personal_data.adapt_quantity(symbol_market, 1) == 1

    assert personal_data.adapt_quantity(symbol_market, 56.5128597145) == 56
    assert personal_data.adapt_quantity(symbol_market, 1251.0000014576121234854513) == 1251


async def test_trunc_with_n_decimal_digits():
    assert personal_data.trunc_with_n_decimal_digits(1.00000000001, 10) == 1
    assert personal_data.trunc_with_n_decimal_digits(1.00000000001, 11) == 1.00000000001
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 3) == 578
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 4) == 578.0001
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 7) == 578.000145
    assert personal_data.trunc_with_n_decimal_digits(11111111111111578.000145000156, 7) == 11111111111111578.000145
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 9) == 578.000145
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 10) == 578.0001450001
    assert personal_data.trunc_with_n_decimal_digits(578.000145000156, 12) == 578.000145000156
    assert personal_data.trunc_with_n_decimal_digits(11111111111111578.000145000156,
                                                     12) == 11111111111111578.000145000156
    assert math.isnan(personal_data.trunc_with_n_decimal_digits(math.nan, 12))
