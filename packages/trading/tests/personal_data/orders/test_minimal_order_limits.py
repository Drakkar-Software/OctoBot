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
import decimal

import pytest

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data.orders.decimal_order_adapter as decimal_order_adapter

_MARKET = trading_enums.ExchangeConstantsMarketStatusColumns
_UNSET = object()


def _symbol_market(
    amount_min=_UNSET,
    amount_precision=_UNSET,
    cost_min=_UNSET,
    price_min=_UNSET,
):
    limits = _MARKET.LIMITS.value
    amount_limits = _MARKET.LIMITS_AMOUNT.value
    cost_limits = _MARKET.LIMITS_COST.value
    price_limits = _MARKET.LIMITS_PRICE.value
    market = {
        limits: {
            amount_limits: {},
            cost_limits: {},
            price_limits: {},
        },
        _MARKET.PRECISION.value: {},
    }
    if amount_min is not _UNSET:
        market[limits][amount_limits][_MARKET.LIMITS_AMOUNT_MIN.value] = amount_min
    if cost_min is not _UNSET:
        market[limits][cost_limits][_MARKET.LIMITS_COST_MIN.value] = cost_min
    if price_min is not _UNSET:
        market[limits][price_limits][_MARKET.LIMITS_PRICE_MIN.value] = price_min
    if amount_precision is not _UNSET:
        market[_MARKET.PRECISION.value][_MARKET.PRECISION_AMOUNT.value] = amount_precision
    return market


class TestGetMinimalOrderAmount:
    """Checks the minimum amount used when an order is below exchange size limits."""

    def test_returns_decimal_exchange_min_amount(self):
        market = _symbol_market(amount_min="0.001")
        assert decimal_order_adapter.get_minimal_order_amount(market) == decimal.Decimal("0.001")

    def test_keeps_explicit_zero_min_amount(self):
        market = _symbol_market(amount_min=0, amount_precision=8)
        assert decimal_order_adapter.get_minimal_order_amount(market) == trading_constants.ZERO

    def test_derives_amount_from_precision_when_min_is_missing(self):
        market = _symbol_market(amount_min=None, amount_precision=8)
        assert decimal_order_adapter.get_minimal_order_amount(market) == decimal.Decimal("1e-8")

    def test_returns_zero_when_precision_is_missing(self):
        market = _symbol_market(amount_min=None, amount_precision=None)
        assert decimal_order_adapter.get_minimal_order_amount(market) == trading_constants.ZERO

    def test_raises_when_market_has_no_amount_limit(self):
        with pytest.raises(trading_errors.NotSupported):
            decimal_order_adapter.get_minimal_order_amount({})


class TestGetMinimalOrderCost:
    """Checks the minimum cost used when an order is below exchange cost limits."""

    def test_returns_exchange_min_cost_unchanged(self):
        market = _symbol_market(cost_min=10.0, amount_min=1, price_min=1)
        assert decimal_order_adapter.get_minimal_order_cost(market) == 10.0

    def test_ignores_zero_min_cost_and_uses_amount_times_price(self):
        market = _symbol_market(cost_min=0, amount_min=2, price_min=2)
        assert decimal_order_adapter.get_minimal_order_cost(market) == 4

    def test_prefers_caller_price_over_market_price_min(self):
        market = _symbol_market(cost_min=None, amount_min=2, price_min=99)
        assert decimal_order_adapter.get_minimal_order_cost(market, default_price=10) == 20

    def test_uses_market_price_min_when_caller_omits_price(self):
        market = _symbol_market(cost_min=None, amount_min=3, price_min=5)
        assert decimal_order_adapter.get_minimal_order_cost(market) == 15

    def test_raises_when_cost_cannot_be_derived(self):
        market = _symbol_market(cost_min=None, amount_min=None, price_min=None)
        with pytest.raises(trading_errors.NotSupported):
            decimal_order_adapter.get_minimal_order_cost(market)

    def test_raises_when_market_has_no_limits(self):
        with pytest.raises(trading_errors.NotSupported):
            decimal_order_adapter.get_minimal_order_cost({})
