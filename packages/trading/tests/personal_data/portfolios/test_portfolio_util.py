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
import copy
import mock
import time
import pytest
import asyncio
import itertools
import random

import octobot_commons.constants
import octobot_commons.logging
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.list_util as list_util
import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data
import octobot_trading.api as trading_api
import octobot_trading.constants as constants
import tests


def test_resolve_sub_portfolios_no_filling_assets():
    master_pf = _sub_pf(0, _content({"BTC": 0.1, "ETH": 9.9999999, "USDT": 100}))
    origin_master_pf = copy.deepcopy(master_pf)

    assert personal_data.resolve_sub_portfolios(master_pf, [], {}) == (
        origin_master_pf, []
    )

    sub_pf_btc = _sub_pf(0, _content({"BTC": 0.01}))
    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pf_btc], {}) == (
        _sub_pf(0, _content({"BTC": 0.09, "ETH": 9.9999999, "USDT": 100})),
        [_sub_pf(0, _content({"BTC": 0.01}))]
    )

    sub_pf_btc_usdt = _sub_pf(1, _content({"BTC": 0.05, "USDT": 100}))
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt], {}
    ) == (
        _sub_pf(0, _content({"BTC": 0.04, "ETH": 9.9999999, "USDT": 0})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100}))
        ]
    )

    # not enough BTC and USDT in master portfolio for this sub portfolio
    sub_pf_btc_usdt_2 = _sub_pf(2, _content({"BTC": 0.06, "USDT": 40, "TRX": 11}))
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2], {}
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 9.9999999, "USDT": 0})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                _content({"BTC": 0.04, "USDT": 0, "TRX": 0}),
                missing_funds=_missing_funds({"BTC": 0.02, "USDT": 40, "TRX": 11})
            )  # adapted to available in master
        ]
    )

    # portfolio with higher priority takes BTC before others
    priority_sub_pf_btc = _sub_pf(0.1, _content({"BTC": 0.02}))
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2, priority_sub_pf_btc], {}
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 9.9999999, "USDT": 0})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(0.1, _content({"BTC": 0.02})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                _content({"BTC": 0.02, "USDT": 0, "TRX": 0}),
                missing_funds=_missing_funds({"BTC": 0.04, "USDT": 40, "TRX": 11})
            )  # adapted to available in master
        ]
    )


def test_resolve_sub_portfolios_no_filling_assets_with_locked_funds():
    master_pf = _sub_pf(
        0,
        _content_with_available({"BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (0.019998, 0.1)})
    )
    sub_pf_btc = _sub_pf(0, _content({"BTC": 0.1}))
    sub_pf_btc.locked_funds_by_asset = trading_api.get_orders_locked_amounts_by_asset([
        _open_order("BTC/USDT", 0.06, 400, "sell", 0.000001, "BTC"),
        _open_order("BTC/USDT", 0.02, 600, "sell", 0.000001, "BTC"),
        _open_order("BTC/USDT", 1, 600, "sell", 0.1, "BTC", is_active=False),  # ignored: inactive order
        _open_order("ETH/USDT", 0.02, 600, "sell", 23, "ETH", is_active=False),   # ignored: inactive order
    ])
    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pf_btc], {}) == (
        _sub_pf(0, _content_with_available({"BTC": (0, 0), "ETH": (0.019998, 0.1), "USDT": (0.019998, 0.1)})),
        [_sub_pf(0, _content_with_available({"BTC": (0.019998, 0.1)}), locked_funds_by_asset=_missing_funds({"BTC": 0.080002}))]
    )

    master_pf = _sub_pf(
        0,
        _content_with_available({"BTC": (0.019997, 0.1), "ETH": (0.1, 0.1), "USDT": (0, 100)})
    )
    sub_pf_1 = _sub_pf(
        0, _content({"BTC": 0.085, "ETH": 0.1}),
        locked_funds_by_asset = trading_api.get_orders_locked_amounts_by_asset([
            _open_order("BTC/USDT", 0.06, 400, "sell", 0.000001, "BTC"),
            _open_order("BTC/USDT", 0.02, 600, "sell", 0.000001, "BTC"),
        ])
    )
    sub_pf_2 = _sub_pf(
        0, _content({"BTC": 0.015, "USDT": 100}),
        locked_funds_by_asset = trading_api.get_orders_locked_amounts_by_asset([
            _open_order("BTC/USDT", 0.1, 30, "buy", 0.000001, "BTC"),
            _open_order("BTC/USDT", 0.1, 60, "buy", 5, "USDT"),
            _open_order("ETH/USDT", 0.1, 4, "buy", 1, "USDT"),
        ])
    )
    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pf_1, sub_pf_2], {}) == (
        _sub_pf(0, _content_with_available({"BTC": (0, 0), "ETH": (0, 0), "USDT": (0, 0)})),
        [
            _sub_pf(0, _content_with_available({"BTC": (0.004998, 0.085), "ETH": (0.1, 0.1)}), locked_funds_by_asset=_missing_funds({"BTC": 0.080002})),
            _sub_pf(0, _content_with_available({"BTC": (0.015, 0.015), "USDT": (0, 100)}), locked_funds_by_asset=_missing_funds({"USDT": 100}))
        ]
    )


def test_resolve_sub_portfolios_with_filling_assets():
    master_pf = _sub_pf(0, _content({"BTC": 0.1, "ETH": 9.9999999, "USDT": 100, "USDC": 100}))
    origin_master_pf = copy.deepcopy(master_pf)
    filling_assets = ["USDC", "SOL"]
    market_prices = {
        "SOL/USDT": 150,
        "BTC/USDC": 83000,
        "ETH/USDC": 2000,
        "USDT/USDC": 1,
        "USDC/TRX": 0.5,    # equivalent to TRX/USDT: 2
    }

    assert personal_data.resolve_sub_portfolios(master_pf, [], market_prices) == (
        origin_master_pf, []
    )

    sub_pf_btc = _sub_pf(0, _content({"BTC": 0.01}))
    sub_pf_btc_usdt = _sub_pf(1, _content({"BTC": 0.05, "USDT": 100}))
    # not enough BTC and USDT in master portfolio for this sub portfolio but can use USDC instead
    sub_pf_btc_usdt_2 = _sub_pf(2, _content({"BTC": 0.04001, "USDT": 40, "TRX": 11}))

    # no allowed filling assets
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2], market_prices
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 9.9999999, "USDT": 0, "USDC": 100})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                _content({"BTC": 0.04, "USDT": 0, "TRX": 0}),
                # BTC not considered as missing since the missing amount % is very low
                missing_funds=_missing_funds({"USDT": 40, "TRX": 11})
            )  # adapted to available in master
        ]
    )

    # no market_prices
    for sub_pf in [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2]:
        sub_pf.allowed_filling_assets = filling_assets
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2], {}
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 9.9999999, "USDT": 0, "USDC": 100})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                _content({"BTC": 0.04, "USDT": 0, "TRX": 0}),
                # BTC not considered as missing since the missing amount % is very low
                missing_funds=_missing_funds({"USDT": 40, "TRX": 11})
            )  # adapted to available in master
        ]
    )

    # now adapt sub portfolio 3
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2], market_prices
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 9.9999999, "USDT": 0, "USDC": 38})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                # 62 = 40 (for USDT) + 22 (for 11 TRX)
                _content({"BTC": 0.04, "USDT": 0, "USDC": 62, "TRX": 0}),
                # BTC not considered as missing since the missing amount % is very low
                funds_deltas=_content({"USDC": 62}),
            )  # adapted to available in master
        ]
    )

    # now adapt sub portfolio 3 and partially 4
    sub_pf_usdt_ada = _sub_pf(5, _content({"ETH": 1, "USDT": 4, "ADA": 1199}), allowed_filling_assets=filling_assets)
    for sub_pf in [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2]:
        sub_pf.allowed_filling_assets = filling_assets
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2, sub_pf_usdt_ada], market_prices
    ) == (
        _sub_pf(0, _content({"BTC": 0, "ETH": 8.9999999, "USDT": 0, "USDC": 34})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(1, _content({"BTC": 0.05, "USDT": 100})),
            _sub_pf(
                2,
                # 62 = 40 (for USDT) + 22 (for 11 TRX)
                _content({"BTC": 0.04, "USDT": 0, "USDC": 62, "TRX": 0}),
                # BTC not considered as missing since the missing amount % is very low
                funds_deltas=_content({"USDC": 62}),
            ),
            _sub_pf(
                5,
                _content({"ETH": 1, "USDT": 0, "USDC": 4, "ADA": 0}),
                funds_deltas=_content({"USDC": 4}),
                missing_funds=_missing_funds({"ADA": 1199}),
            ),
        ]
    )

    # with forbidden assets
    for sub_pf in [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2, sub_pf_usdt_ada]:
        sub_pf.forbidden_filling_assets = ["USDT", "ADA"]
    assert personal_data.resolve_sub_portfolios(
        master_pf, [sub_pf_btc, sub_pf_btc_usdt, sub_pf_btc_usdt_2, sub_pf_usdt_ada], market_prices
    ) == (
        # USDT is kept in master portfolio
        _sub_pf(0, _content({"BTC": 0, "ETH": 8.9999999, "USDT": 100, "USDC": 0})),
        [
            _sub_pf(0, _content({"BTC": 0.01})),
            _sub_pf(
                1,
                _content({"BTC": 0.05,"USDC": 100,"USDT": 0}),
                funds_deltas=_content({"USDC": 100})
            ),
            _sub_pf(
                2,
                # 62 = 40 (for USDT) + 22 (for 11 TRX)
                _content({"BTC": 0.04, "USDC": 0, "USDT": 0, "TRX": 0}),
                # BTC not considered as missing since the missing amount % is very low
                funds_deltas={},
                missing_funds=_missing_funds({"TRX": 11, "USDT": 40}),
            ),
            _sub_pf(
                5,
                _content({"ADA": 0, "ETH": 1, "USDC": 0, "USDT": 0}),
                funds_deltas={},
                missing_funds=_missing_funds({"ADA": 1199, "USDT": 4}),
            ),
        ]
    )


def test_resolve_sub_portfolios_with_unexpected_deltas():
    # more delta in post trade portfolio than actual orders => do not result in negative subportfolio
    master_pf = _sub_pf(0, _content({"BTC": 0.05, "TRX": 0, "USDT": 200}))
    sub_pft = _sub_pf(
        0,
        _content({"BTC": 0.05, "TRX": 13.1, "USDT": 100}),
        funds_deltas=_content({"BTC": -0.05, "TRX": -13.2, "USDT": 100}),
    )

    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pft], {}) == (
        _sub_pf(0,  _content({"BTC": 0.05, "TRX": 0, "USDT": 0})),
        [_sub_pf(0, _content({"BTC": 0, "TRX": 0, "USDT": 200}))]
    )


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas():
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # no filled order
        assert await personal_data.get_portfolio_filled_orders_deltas(pre_trade_content, post_trade_content, [], [], {}, False, None) == _resolved()
        error_log.assert_not_called()

        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.05, 451, "buy"),   # 1 will be ignored, (allowed error margin)
            _order("BTC/USDT", 0.01, 50, "sell"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
        )
        error_log.assert_not_called()

        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.05, 450, "buy"),
            _order("BTC/USDT", 0.01, 50, "buy"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            {},
            _content({"BTC": 0.1, "USDT": -500}),   # all missing: orders can't explain this delta
        )
        error_log.assert_not_called()

        filled_orders = [
            _order("SOL/USDT", 1, 200, "buy"),  # won't be found
            _order("BTC/USDT", 0.06, 100.01, "buy"),    # small change compared to portfolio
            _order("BTC/USDT", 0.01, 50, "buy"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({"BTC": 0.07, "USDT": -350.01}),   # adapted to orders explained orders delta
            _content({"SOL": 1}),   # not found in portfolio delta
        )
        error_log.assert_not_called()

        post_trade_content = _content({"USDT": 500, "SOL": 1})  # now has SOL but no BTC
        filled_orders = [
            _order("SOL/USDT", 1, 200, "buy"),  # won't be found
            _order("BTC/USDT", 0.06, 100.01, "buy"),    # small change compared to portfolio
            _order("BTC/USDT", 0.01, 50, "buy"),    # not found in portfolio delta
        ]
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        )
        assert resolved_delta == _resolved(
            _content({"SOL": 1, "USDT": -350.01}),   # adapted to orders explained orders delta
            _content({"BTC": -0.1}),   # not found in portfolio delta
        )
        assert resolved_delta.get_unexplained_orders_deltas_related_to_filled_orders(filled_orders) == _content(
            {"BTC": -0.1}
        )
        error_log.assert_not_called()

        # only sell orders
        post_trade_content = _content({"USDT": 2000})
        filled_orders = [
            _order("BTC/USDT", 0.06, 400, "sell"),    # small change compared to portfolio
            _order("BTC/USDT", 0.04, 600, "sell"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({"BTC": -0.1, "USDT": 1000}),
            {},
        )
        error_log.assert_not_called()

        # only equivalent sell and buy orders: no BTC delta
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.1, "USDT": 995})
        filled_orders = [
            _order("BTC/USDT", 0.05, 550, "sell"),
            _order("BTC/USDT", 0.05, 555, "buy"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({"USDT": -5}),
            {}, # BTC is not a missing delta as there is no delta (delta = 0)
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_unavailable_funds():
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        pre_trade_content = _content_with_available({"SOL": (0, 0.051), "USDT": (12, 12)})
        post_trade_content = _content_with_available({"SOL": (0, 0), "USDT": (20.93992596600, 20.93992596600)})
        filled_orders = [
            _order("SOL/USDT", 0.051, 8.939925966, "sell"),
        ]
        # with known filled orders
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content_with_available({"SOL": (0, -0.051), "USDT": (8.939925966, 8.939925966)}),
        )
        error_log.assert_not_called()

        # with unknown orders
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], filled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content_with_available({"SOL": (0, -0.051), "USDT": (8.939925966, 8.939925966)}),
            inferred_filled_orders=filled_orders,   # all orders are inferred as filled to explain deltas
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_unknown_filled_or_cancelled_orders():
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    filled_orders = []
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):

        # 1. no unknown_filled_or_cancelled_orders
        unknown_filled_or_cancelled_orders = []
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )  == _resolved()   # deltas are considered from other orders (as no order is provided)
        error_log.assert_not_called()

        # 2. with filled inferred orders
        # 1 order
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1, 502, "buy"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as filled to explain deltas
        )
        # 3 orders
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.05, 451, "buy"),   # 1 will be ignored, (allowed error margin)
            _order("BTC/USDT", 0.01, 50, "sell"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as filled to explain deltas
        )

        # 3. with cancelled inferred orders
        # orders are on the wrong symbol (SOL/USDT)
        # 1 order
        unknown_filled_or_cancelled_orders = [
            _order("SOL/USDT", 0.06, 100, "sell"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            unexplained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # no orders found in deltas
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as cancelled (can't explain delta)
        )
        # 2 orders
        unknown_filled_or_cancelled_orders = [
            _order("SOL/USDT", 0.06, 100, "buy"),  # wrong symbol
            _order("BTC/USDT", 0.05, 451, "sell"),  # wrong side
        ]
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )
        assert resolved_delta == _resolved(
            unexplained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # no orders found in deltas
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as cancelled (can't explain delta)
        )
        assert resolved_delta.get_unexplained_orders_deltas_related_to_filled_orders(filled_orders) == {}
        # 3 orders (those are buy orders that should not be counted as filled because their quote asset is not in portfolio delta => delta come from other orders)
        unknown_filled_or_cancelled_orders = [
            _order("SOL/USDT", 0.06, 100, "buy"),
            _order("DOT/USDT", 0.1, 500, "buy"), 
            _order("PLOP/USDT", 0.01, 50, "buy"),
        ]
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )
        assert resolved_delta == _resolved(
            unexplained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # no orders found in deltas
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as cancelled (can't explain delta)
        )
        assert resolved_delta.get_unexplained_orders_deltas_related_to_filled_orders(filled_orders) == {}

        # 4. multiple filled + cancelled inferred orders
        # multiple filled + cancelled inferred orders
        # filled, filled, cancelled (buy)
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
            _order("BTC/USDT", 0.01, 50, "buy"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the first two orders
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:2],  # first 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[2:],  # last order is inferred as cancelled
        )
        error_log.assert_not_called()

        # filled, filled, cancelled (sell)
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
            _order("BTC/USDT", 0.01, 50, "sell"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the first two orders
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:2],  # first 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[2:],  # last order is inferred as cancelled
        )
        error_log.assert_not_called()

        # filled, filled, cancelled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.04, 400, "buy"),    # same as last order: take 1st working combination
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the last two orders
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:2],  # first 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[2:],  # last order is inferred as cancelled
        )
        error_log.assert_not_called()
        # cancelled, filled, filled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.04, 600, "buy"),    # too large
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the last two orders
            inferred_filled_orders=unknown_filled_or_cancelled_orders[1:],  # last 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[:1],  # first order is inferred as cancelled
        )
        error_log.assert_not_called()

        # with another assert in portfolio delta
        post_trade_content = _content({"BTC": 0.2, "USDT": 500, "ETH": 100})
        # cancelled, filled, filled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.04, 600, "buy"),    # too large
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the last two orders
            unexplained_orders_deltas=_content({"ETH": 100}),   # ETH is not explained by any order
            inferred_filled_orders=unknown_filled_or_cancelled_orders[1:],  # last 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[:1],  # first order is inferred as cancelled
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("is_exchange_fetched_fee", [
    False,
    True,
])
async def test_get_portfolio_filled_orders_deltas_with_unknown_filled_orders_with_fees(is_exchange_fetched_fee):
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # 1 filled order with fees paid in asset in portfolio
        post_trade_content = _content({"BTC": 0.2, "USDT": 499})
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1, 500, "buy", fee={"USDT": 1}, is_exchange_fetched_fee=is_exchange_fetched_fee),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -501}),
            inferred_filled_orders=unknown_filled_or_cancelled_orders,
        )

        # 1 filled order with fees paid in asset NOT in portfolio
        post_trade_content = _content({"BTC": 0.2, "USDT": 500})
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1, 500, "buy", fee={"BNB": 1}, is_exchange_fetched_fee=is_exchange_fetched_fee),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),
            inferred_filled_orders=unknown_filled_or_cancelled_orders,
        )

        # 2 filled orders, 1 cancelled (sell)
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", fee={"BNB": 1}, is_exchange_fetched_fee=is_exchange_fetched_fee),
            _order("BTC/USDT", 0.04, 400, "buy", fee={"BNB": 1}, is_exchange_fetched_fee=is_exchange_fetched_fee),
            _order("BTC/USDT", 0.01, 50, "sell"),    # not found in portfolio delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # explained by the first two orders
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:2],  # first 2 orders are inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[2:],  # last order is inferred as cancelled
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("orders_count, unknown_orders_count", [
    (10, 4),
    (20, 4),    # max unknown_orders_count values before failing max_execution_time=1 on a powerful test computer
    (30, 3),    # max unknown_orders_count values before failing max_execution_time=1 on a powerful test computer
    (60, 2),
    (250, 1)
])
async def test_get_portfolio_filled_orders_deltas_with_lots_of_unknown_filled_or_cancelled_orders(orders_count, unknown_orders_count):
    # goal of the test: making sure the orders identification algo is not too slow with lots of orders
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    filled_orders = []
    max_execution_time = 10 if tests.is_on_github_ci() else 3 # use 10 to let slower computers pass the test. Real target is 3
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # A. all orders are filled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ]
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as filled to explain deltas
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
        )
        # B. all orders are cancelled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ]
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, pre_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as cancelled
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
        )
        unfilled_count = unknown_orders_count
        # C. most orders are filled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ] + [
            _order("ETH/USDT", 0.1, 500, "buy")
            for _ in range(unfilled_count)
        ]
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:-unfilled_count],  # all orders are inferred as filled to explain deltas
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[orders_count:],  # last orders are inferred as cancelled
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
        )
        uncancelled_count = unknown_orders_count
        # D. most orders are cancelled
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / uncancelled_count, 500 / uncancelled_count, "buy")
            for _ in range(uncancelled_count)
        ] + [
            _order("ETH/USDT", 0.1, 500, "buy")
            for _ in range(orders_count)
        ]
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:uncancelled_count],  # all orders are inferred as filled to explain deltas
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[uncancelled_count:],  # last orders are inferred as cancelled
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
        )


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_lots_of_unknown_filled_or_cancelled_orders_on_different_symbols():
    # goal of the test: making sure the orders identification algo is not too slow with lots of orders
    pre_trade_content = _content({"USDT": 500})
    error_log = mock.Mock()

    eth_orders = [
        _order("ETH/USDT", 0.0038, 16.251764 , "buy"),
        _order("ETH/USDT", 0.0038, 16.156764 , "buy"),
        _order("ETH/USDT", 0.0039, 16.484442 , "buy"),
        _order("ETH/USDT", 0.0039, 16.386942 , "buy"),
        _order("ETH/USDT", 0.0039, 16.289442 , "buy"),
        _order("ETH/USDT", 0.0039, 16.191942 , "buy"),
        _order("ETH/USDT", 0.0019, 8.101296 , "buy"),
    ]
    link_orders = [
        _order("LINK/USDT", 0.7, 15.148 , "buy"),
        _order("LINK/USDT", 0.8, 16.832 , "buy"),
        _order("LINK/USDT", 0.3, 6.59934 , "buy"),
        _order("LINK/USDT", 0.3, 6.3327 , "buy"),
    ]
    sol_orders = [
        _order("SOL/USDT", 0.036, 8.309268 , "buy"),
        _order("SOL/USDT", 0.036, 7.973532 , "buy"),
    ]
    ada_orders = [
        _order("ADA/USDT", 9.9, 8.043057 , "buy"),
    ]
    btc_orders = [
        _order("BTC/USDT", 7e-05, 7.9281363 , "buy"),
        _order("BTC/USDT", 0.00018, 20.540133 , "buy"),
        _order("BTC/USDT", 0.00018, 20.396133 , "buy"),
        _order("BTC/USDT", 0.00018, 20.252133 , "buy"),
    ]
    xrp_orders = [
        _order("XRP/USDT", 2.9, 8.337094 , "buy"),
        _order("XRP/USDT", 2.9, 8.00023 , "buy"),
    ]
    unknown_filled_or_cancelled_orders = eth_orders + link_orders + sol_orders + ada_orders + btc_orders + xrp_orders
    max_execution_time = 10 if tests.is_on_github_ci() else 2 # use 10 to let slower computers pass the test. Real target is 2
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # A. simple cases: all orders are filled
        all_filled_deltas = _get_orders_deltas(unknown_filled_or_cancelled_orders)
        post_trade_content = _content({**all_filled_deltas, **{"USDT": all_filled_deltas["USDT"] + decimal.Decimal("500")}})
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content(all_filled_deltas),   # all orders found in deltas
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as filled to explain deltas
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for many symbol orders"
        )
        # B. simple cases: all orders are cancelled
        t0 = time.time()
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, pre_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all orders are inferred as cancelled to explain deltas
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for many symbol orders"
        )
        # C. complex cases: 11 orders are filled, 9 are cancelled: will a long time to find the best combination if not split by symbol
        filled_orders = eth_orders + link_orders
        cancelled_orders = sol_orders + ada_orders + btc_orders + xrp_orders
        assert len(filled_orders) == 11
        total_orders_count = len(filled_orders) + len(cancelled_orders)
        filled_deltas = _get_orders_deltas(filled_orders)
        post_trade_content = _content({**filled_deltas, **{"USDT": filled_deltas["USDT"] + decimal.Decimal("500")}})
        t0 = time.time()
        # no matter the order of unknown orders, the result should be the same: all ETH and LINK orders are filled, the rest are cancelled
        selected_index = random.randint(0, 9)
        selected_indexes = set(str(i) for i in [selected_index, (selected_index + 1) % 10, (selected_index + 2) % 10])
        # randomly select approx 216 "random" permutations
        iterations = 0
        for index, shuffled_unknown_filled_or_cancelled_orders_elements in enumerate(itertools.permutations(
            (eth_orders, link_orders, sol_orders, ada_orders, btc_orders, xrp_orders), 6
        )):
            if str(index)[-1] not in selected_indexes:
                continue
            iterations += 1
            shuffled_unknown_filled_or_cancelled_orders = []
            for elements in shuffled_unknown_filled_or_cancelled_orders_elements:
                shuffled_unknown_filled_or_cancelled_orders.extend(elements)
            assert len(shuffled_unknown_filled_or_cancelled_orders) == total_orders_count
            resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
                pre_trade_content, post_trade_content, [], shuffled_unknown_filled_or_cancelled_orders, {}, False, None
            ) 
            assert len(shuffled_unknown_filled_or_cancelled_orders) == total_orders_count # ensure shuffled_unknown_filled_or_cancelled_orders is not touched
            assert resolved_delta.explained_orders_deltas == _content(filled_deltas)   # all orders found in deltas
            assert resolved_delta.unexplained_orders_deltas == {}   # no unexplained orders
            assert sorted(resolved_delta.inferred_filled_orders, key=lambda o: o.symbol) == sorted(filled_orders, key=lambda o: o.symbol), (
                f"Inferred filled orders={resolved_delta.inferred_filled_orders} for permutation {index}: {list_util.deduplicate([o.symbol for o in shuffled_unknown_filled_or_cancelled_orders])}"
            )
            assert sorted(resolved_delta.inferred_cancelled_orders, key=lambda o: o.symbol) == sorted(cancelled_orders, key=lambda o: o.symbol), (
                f"Inferred cancelled orders={resolved_delta.inferred_cancelled_orders} for permutation {index}: {list_util.deduplicate([o.symbol for o in shuffled_unknown_filled_or_cancelled_orders])}"
            )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for many symbol orders executed {iterations} iterations"
        )

        # D. complex cases: 12 orders are filled, 8 are cancelled, including a LINK/USDT order: will a long time to find the best combination if not split by symbol
        filled_orders = eth_orders + link_orders[:-1] + sol_orders
        cancelled_orders = ada_orders + btc_orders + xrp_orders + link_orders[-1:]
        assert len(filled_orders) == 12
        filled_deltas = _get_orders_deltas(filled_orders)
        post_trade_content = _content({**filled_deltas, **{"USDT": filled_deltas["USDT"] + decimal.Decimal("500")}})
        t0 = time.time()
        unknown_filled_or_cancelled_orders = filled_orders + cancelled_orders
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_filled_or_cancelled_orders, {}, False, None
        )
        # due to very similar order and the order of exec, link order 3 is considered filled instead of link order 4
        resolved_fileld_link_orders = link_orders[:-2]+link_orders[-1:]
        assert resolved_delta == _resolved(
            explained_orders_deltas=_content(filled_deltas),   # all orders found in deltas
            inferred_filled_orders=eth_orders+resolved_fileld_link_orders+sol_orders,  # all orders are inferred as filled to explain deltas
            inferred_cancelled_orders=link_orders[-2:-1] + ada_orders + btc_orders + xrp_orders,  # all orders are inferred as cancelled to explain deltas
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for many symbol orders with mixed cancelled and filled orders"
        )

        # E. complex cases: 12 orders are filled, some of them are known as filled. 8 are cancelled, including a LINK/USDT order: will a long time to find the best combination if not split by symbol
        known_filled_orders = eth_orders + link_orders[1:2]
        unknown_filled_orders = link_orders[2:-1] + sol_orders
        cancelled_orders = ada_orders + btc_orders + xrp_orders + link_orders[-1:]
        assert len(unknown_filled_orders) == 3
        filled_deltas = _get_orders_deltas(known_filled_orders + unknown_filled_orders)
        post_trade_content = _content({
            **filled_deltas, **{
                "USDT": filled_deltas["USDT"] + decimal.Decimal("501"),
                "PLOP": decimal.Decimal("22")
            }
        })
        t0 = time.time()
        unknown_filled_or_cancelled_orders = unknown_filled_orders + cancelled_orders
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, known_filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )
        # due to very similar order and the order of exec, link order 3 is considered filled instead of link order 4
        resolved_fileld_link_orders = [link_orders[-1]]
        filled_deltas["USDT"] += decimal.Decimal("1")  # add 1 for +501 USDT delta
        assert resolved_delta == _resolved(
            explained_orders_deltas=_content(filled_deltas),   # all orders found in deltas
            unexplained_orders_deltas=_content({"PLOP": decimal.Decimal("22")}),   # PLOP delta is not explained
            inferred_filled_orders=resolved_fileld_link_orders+sol_orders,  # all orders are inferred as filled to explain deltas
            inferred_cancelled_orders=link_orders[-2:-1] + ada_orders + btc_orders + xrp_orders,  # all orders are inferred as cancelled to explain deltas
        )
        assert time.time() - t0 < max_execution_time, (
            f"Execution time {time.time() - t0} is greater than {max_execution_time} for many symbol orders with mixed cancelled and filled orders"
        )


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_inferrence_thread():
    # goal of the test: making sure that slow order delta inference is releasing the async loop
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    filled_orders = []
    orders_count = 19
    unfilled_count = 5
    max_execution_time = 25 if tests.is_on_github_ci() else 4 # use 20 to let slower computers pass the test. Real target is 4
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # most orders are filled
        # use single symbol to make sure a thread is used
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ] + [
            _order("BTC/USDT", 1, 500, "buy")
            for _ in range(unfilled_count)
        ]
        t0 = time.time()

        completed_portfolio_filled_orders_deltas = []
        async def _async_looper():
            loops = 0
            while not completed_portfolio_filled_orders_deltas:
                # makes sure the async loop is running and not blocked during get_portfolio_filled_orders_deltas
                loops = loops + 1
                await asyncio_tools.wait_asyncio_next_cycle()
            # portfolio completed
            return loops

        async def _async_get_portfolio_filled_orders_deltas():
            result = await personal_data.get_portfolio_filled_orders_deltas(
                pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
            )
            completed_portfolio_filled_orders_deltas.append(result)
            return result

        with mock.patch.object(asyncio, "to_thread", mock.AsyncMock(wraps=asyncio.to_thread)) as to_thread_mock:
            loops, resolved = await asyncio.gather(
                _async_looper(),
                _async_get_portfolio_filled_orders_deltas()
            )
            end_time = time.time()
            assert loops > 3, f"Loops {loops} is less than 3" # loops = 24 on a fast computer
            assert resolved == _resolved(
                explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all orders found in deltas
                inferred_filled_orders=unknown_filled_or_cancelled_orders[:-unfilled_count],  # all orders are inferred as filled to explain deltas
                inferred_cancelled_orders=unknown_filled_or_cancelled_orders[orders_count:],  # last orders are inferred as cancelled
            )
            # ensure test is not too slow
            assert end_time - t0 < max_execution_time, (
                f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
            )
            to_thread_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_interrupt_get_portfolio_filled_orders_deltas_inferrence_thread():
    # goal of the test: making sure that inference thread is cancelled when task is cancelled
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    warning_log = mock.Mock()
    filled_orders = []
    orders_count = 30
    unfilled_count = 15  # 155.117.520  combinations on worse iterations, requires thread and takes much more than 5 seconds
    max_execution_time = 5
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log, warning=warning_log))):
        # use single symbol to make sure a thread is used
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ] + [
            _order("BTC/USDT", 1, 500, "buy")
            for _ in range(unfilled_count)
        ]
        t0 = time.time()

        completed_portfolio_filled_orders_deltas = []
        loops = []
        async def _async_looper():
            while not completed_portfolio_filled_orders_deltas:
                # makes sure the async loop is running and not blocked during get_portfolio_filled_orders_deltas
                loops.append(1)
                await asyncio_tools.wait_asyncio_next_cycle()
            # portfolio completed
            return loops

        async def _async_get_portfolio_filled_orders_deltas():
            try:
                result = await personal_data.get_portfolio_filled_orders_deltas(
                    pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
                )
                return result
            finally:
                completed_portfolio_filled_orders_deltas.append(1)

        with mock.patch.object(asyncio, "to_thread", mock.AsyncMock(wraps=asyncio.to_thread)) as to_thread_mock:
            task = asyncio.create_task(_async_get_portfolio_filled_orders_deltas())
            async def _async_canceller():
                await asyncio.sleep(0.5)
                task.cancel()
            tasks = [
                asyncio.create_task(_async_looper()),
                asyncio.create_task(_async_canceller()),
                task
            ]
            completed, pending = await asyncio.wait(tasks, timeout=10)
            assert len(completed) == 3
            assert len(pending) == 0
            end_time = time.time()
            assert len(loops) > 3, f"Loops {loops} is less than 3" # loops = 24 on a fast computer
            # coro was cancelled
            with pytest.raises(asyncio.CancelledError):
                task.result()
            # ensure test is not too slow
            assert end_time - t0 < max_execution_time, (
                f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
            )
            to_thread_mock.assert_awaited_once()
            error_log.assert_called_once()
            assert "quick check configurations" in error_log.call_args[0][0]
            warning_log.assert_called_once()
            assert "cancelling background thread" in warning_log.call_args[0][0]


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_inferrence_thread_timeout_and_randomize_secondary_checks():
    # goal of the test: making sure that inference thread is cancelled when task is cancelled
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500})
    error_log = mock.Mock()
    warning_log = mock.Mock()
    filled_orders = []
    orders_count = 30
    unfilled_count = 15  # 155.117.520  combinations on worse iterations, requires thread and takes much more than 5 seconds
    max_execution_time = 8 # CI can be very slow on CI
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log, warning=warning_log))):
        # use single symbol to make sure a thread is used
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.1 / orders_count, 500 / orders_count, "buy")
            for _ in range(orders_count)
        ] + [
            _order("BTC/USDT", 1, 500, "buy")
            for _ in range(unfilled_count)
        ]
        t0 = time.time()

        portfolio_filled_orders_delta_results = []

        async def _async_get_portfolio_filled_orders_deltas(randomize_secondary_checks: bool, timeout: float):
            result = await personal_data.get_portfolio_filled_orders_deltas(
                pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, randomize_secondary_checks, timeout
            )
            portfolio_filled_orders_delta_results.append(result)
            return result

        with (
            mock.patch.object(asyncio, "to_thread", mock.AsyncMock(wraps=asyncio.to_thread)) as to_thread_mock,
            mock.patch.object(random, "shuffle", mock.AsyncMock(wraps=random.shuffle)) as shuffle_mock
        ):
            # 1. NOT randomize secondary checks, timeout is too short: don't start thread
            task = asyncio.create_task(_async_get_portfolio_filled_orders_deltas(False, 0.0001))
            async def _async_canceller():
                await asyncio.sleep(0.5)
                task.cancel()
            tasks = [
                asyncio.create_task(_async_canceller()),
                task
            ]
            await asyncio.wait(tasks, timeout=2)
            # a result was computed and returned
            assert len(portfolio_filled_orders_delta_results) == 1
            assert isinstance(portfolio_filled_orders_delta_results[0], personal_data.ResolvedOrdersPortoflioDelta)
            # ensure values are set
            assert {**portfolio_filled_orders_delta_results[0].explained_orders_deltas, **portfolio_filled_orders_delta_results[0].unexplained_orders_deltas}
            assert portfolio_filled_orders_delta_results[0].inferred_filled_orders + portfolio_filled_orders_delta_results[0].inferred_cancelled_orders
            # thread not started
            to_thread_mock.assert_not_called()
            end_time = time.time()
            # ensure test is not too slow
            assert end_time - t0 < max_execution_time, (
                f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
            )
            assert error_log.call_count == 2
            assert "trying the (slow) 4 other configurations in a separate thread." in error_log.mock_calls[0].args[0]
            assert "was already reached while computing most probable assets" in error_log.mock_calls[1].args[0]
            warning_log.assert_not_called()
            shuffle_mock.assert_not_called()
            to_thread_mock.reset_mock()
            shuffle_mock.reset_mock()
            error_log.reset_mock()
            warning_log.reset_mock()
            portfolio_filled_orders_delta_results.clear()

            # 2. randomize secondary checks, timeout will be reached: start and interrupt thread
            timeout = 1.5 if tests.is_on_github_ci() else 0.5 # CI can be very slow computers
            task = asyncio.create_task(_async_get_portfolio_filled_orders_deltas(True, timeout))
            async def _async_canceller():
                await asyncio.sleep(timeout*2)
                task.cancel()
            tasks = [
                asyncio.create_task(_async_canceller()),
                task
            ]
            await asyncio.wait(tasks, timeout=timeout*2+1)
            # thread was started
            to_thread_mock.assert_awaited_once()
            # a result was computed and returned
            assert len(portfolio_filled_orders_delta_results) == 1
            assert isinstance(portfolio_filled_orders_delta_results[0], personal_data.ResolvedOrdersPortoflioDelta)
            # ensure values are set
            assert {**portfolio_filled_orders_delta_results[0].explained_orders_deltas, **portfolio_filled_orders_delta_results[0].unexplained_orders_deltas}
            assert portfolio_filled_orders_delta_results[0].inferred_filled_orders + portfolio_filled_orders_delta_results[0].inferred_cancelled_orders
            end_time = time.time()
            # ensure test is not too slow
            assert end_time - t0 < max_execution_time, (
                f"Execution time {time.time() - t0} is greater than {max_execution_time} for {orders_count} orders"
            )
            assert error_log.call_count == 1
            assert "trying the (slow) 4 other configurations in a separate thread." in error_log.mock_calls[0].args[0]
            assert warning_log.call_count == 1
            assert f"(remaining of intial {timeout}s) while computing most" in warning_log.mock_calls[0].args[0]
            shuffle_mock.assert_called_once()
            to_thread_mock.reset_mock()
            shuffle_mock.reset_mock()
            error_log.reset_mock()
            warning_log.reset_mock()
            portfolio_filled_orders_delta_results.clear()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_filled_orders_and_unknown_filled_or_cancelled_orders():
    pre_trade_content = _content({"BTC": 0.1, "USDT": 1000, "ETH": 5})
    post_trade_content = _content({"BTC": 0.2, "USDT": 500, "ETH": 8})
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        
        # 1. filled_orders explain part of delta, unknown orders explain the rest
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 150, "buy"),
        ]
        unknown_filled_or_cancelled_orders = [
            _order("ETH/USDT", 3, 250, "buy"),  # explains ETH delta and the remaining USDT delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500, "ETH": 3}),   # all deltas explained
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # unknown order inferred as filled
        )
        error_log.assert_not_called()

        # 2. filled_orders explain part, unknown orders are cancelled (wrong symbol)
        filled_orders = [   
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
        ]
        unknown_filled_or_cancelled_orders = [
            _order("SOL/USDT", 3, 900, "buy"),  # wrong symbol, can't explain ETH delta
        ]
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )
        assert resolved_delta == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # only BTC explained by filled orders
            unexplained_orders_deltas=_content({"ETH": 3}),   # 3 ETH delta is not explained
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # unknown order inferred as cancelled
        )
        assert resolved_delta.get_unexplained_orders_deltas_related_to_filled_orders(filled_orders) == {}
        error_log.assert_not_called()

        # 3. filled_orders explain part, some unknown orders filled, some cancelled
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
        ]
        unknown_filled_or_cancelled_orders = [
            _order("ETH/USDT", 2, 150, "buy"),  # explains part of ETH delta
            _order("SOL/USDT", 1, 300, "buy"),  # wrong symbol, cancelled
            _order("ETH/USDT", 1.01, 253, "buy"),  # explains remaining ETH delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.06, "USDT": -500, "ETH": 3}),   # all deltas explained
            inferred_filled_orders=[unknown_filled_or_cancelled_orders[0], unknown_filled_or_cancelled_orders[2]],  # ETH orders inferred as filled
            inferred_cancelled_orders=[unknown_filled_or_cancelled_orders[1]],  # SOL order inferred as cancelled
        )
        error_log.assert_not_called()

        # 4. filled_orders with fees, unknown orders without fees
        pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
        post_trade_content = _content({"BTC": 0.2, "USDT": 50.2})    # paid 50 USDT in fees
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", fee={"USDT": 25}),
            _order("BTC/USDT", 0.04, 400, "buy", fee={"USDT": 25}),
        ]
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.01, 50, "sell"),  # no fees in unknown orders
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -550}),   # all deltas explained including fees
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # unknown order inferred as cancelled (its deltas can't be found)
        )
        error_log.assert_not_called()

        # 5. filled_orders insufficient, unknown orders complete the explanation
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.2, "USDT": 500})
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),  # only explains part of BTC delta
        ]
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.04, 400, "buy"),  # explains remaining BTC delta
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all deltas explained
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # unknown order inferred as filled
        )
        error_log.assert_not_called()

        # 6. filled_orders explain everything, unknown orders are all cancelled
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.2, "USDT": 500})
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),
            _order("BTC/USDT", 0.04, 400, "buy"),
        ]
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy"),  # would create extra delta => cancelled
            _order("SOL/USDT", 1, 100, "buy"),  # wrong symbol
            _order("DOT/USDT", 2, 200, "sell"),  # wrong symbol
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500}),   # all deltas explained by filled orders
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders,  # all unknown orders inferred as cancelled
        )
        error_log.assert_not_called()

        # 7. complex scenario with multiple assets and mixed order types
        pre_trade_content = _content({"BTC": 0.1, "ETH": 5, "USDT": 1000, "SOL": 10})
        post_trade_content = _content({"BTC": 0.15, "ETH": 8, "USDT": 400, "SOL": 5})
        filled_orders = [
            _order("BTC/USDT", 0.03, 150, "buy"),  # explains part of BTC delta +0.03 BTC -150 USDT
            _order("SOL/USDT", 5, 250, "sell"),    # explains SOL delta -5 SOL +250 USDT
        ] # => +0.03 BTC +100 USDT -5 SOL
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.02, 100, "buy"),  # explains remaining BTC delta +0.02 BTC -100 USDT
            _order("ETH/USDT", 3, 450, "buy"),     # explains ETH delta +3 ETH -450 USDT
            _order("DOT/USDT", 1, 50, "buy"),      # wrong symbol, cancelled +1 DOT -50 USDT    (considered as cancelled)
        ] # => +0.02 BTC -400 USDT +3 ETH +1 DOT
        # total delta: +0.05 BTC -500 USDT -5 SOL +3 ETH +1 DOT
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.05, "ETH": 3, "USDT": -450, "SOL": -5}),   # all deltas explained
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:2],  # first 2 unknown orders inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[2:],  # last unknown order inferred as cancelled
        )
        error_log.assert_not_called()

        # 8. complex scenario with orders compensating each other without fees
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.15, "USDT": 400})
        filled_orders = [
            _order("BTC/USDT", 0.03, 150, "buy"),  # +0.03 BTC -150 USDT
            _order("BTC/USDT", 0.03, 250, "sell"),  # -0.03 BTC +250 USDT
        ] # => +0 BTC +100 USDT
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.03, 250, "buy"),  # compensates last filled sell +0.03 BTC -250 USDT
            _order("BTC/USDT", 0.01, 350, "buy"),  # +0.01 BTC -350 USDT
            _order("BTC/USDT", 0.00999, 98, "buy"),  # +0.00999 BTC -98 USDT
            _order("BTC/USDT", 0.01, 100, "buy"),  # +0.1 BTC -100 USDT (cancelled)
        ] # => +0.04999 BTC -598 USDT
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.05, "USDT": -600}),   # all deltas explained
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:3],  # first 3 unknown orders inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[3:],  # last unknown order inferred as cancelled
        )
        error_log.assert_not_called()

        # 9. complex scenario with orders compensating each other including fees
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.15, "USDT": 397.52222}) # only 2.5 USDT from fees are taken into account
        filled_orders = [
            _order("BTC/USDT", 0.03, 150, "buy", fee={"BNB": 1}),  # +0.03 BTC -150 USDT
            _order("BTC/USDT", 0.03, 250, "sell", fee={"USDT": 3}),  # -0.03 BTC +250 USDT - 3 USDT
        ] # => +0 BTC +100 USDT
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.03, 250, "buy", fee={"USDT": 1}),  # compensates last filled sell +0.03 BTC -250 USDT
            _order("BTC/USDT", 0.01, 350, "buy", fee={"USDT": 1}),  # +0.01 BTC -350 USDT
            _order("BTC/USDT", 0.00999, 100, "buy", fee={"USDT": 1}),  # +0.00999 BTC -100 USDT
            _order("BTC/USDT", 0.01, 100, "buy", fee={"USDT": 1}),  # +0.1 BTC -100 USDT (cancelled)
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        ) == _resolved(
            explained_orders_deltas=_content({"BTC": 0.05, "USDT": -602.47778}),   # all deltas explained, some fees are taken into account, others are ignored because missing from portfolio delta
            inferred_filled_orders=unknown_filled_or_cancelled_orders[:3],  # first 3 unknown orders inferred as filled
            inferred_cancelled_orders=unknown_filled_or_cancelled_orders[3:],  # last unknown order inferred as cancelled
        )
        error_log.assert_not_called()

        # 11. complex scenario of orders with fees with larger portfolio delta than total orders
        pre_trade_content = _content({"BTC": 0, "USDT": 2000, "ETH": 10})
        post_trade_content = _content({"BTC": 0.15, "USDT": 397.52222, "ETH": 11, "SOL": 10})
        filled_orders = [
            _order("BTC/USDT", 0.03, 150, "buy", fee={"BNB": 1}),  # +0.03 BTC -150 USDT
            _order("BTC/USDT", 0.03, 250, "sell", fee={"USDT": 3}),  # -0.03 BTC +250 USDT - 3 USDT
        ] # => +0 BTC +100 USDT
        unknown_filled_or_cancelled_orders = [
            _order("BTC/USDT", 0.03, 250, "buy", fee={"USDT": 1}),  # compensates last filled sell +0.03 BTC -250 USDT
            _order("BTC/USDT", 0.01, 350, "buy", fee={"USDT": 1}),  # +0.01 BTC -350 USDT
            _order("BTC/USDT", 0.00999, 100, "buy", fee={"USDT": 1}),  # +0.00999 BTC -100 USDT
            _order("BTC/USDT", 0.01, 100, "buy", fee={"USDT": 1}),  # +0.1 BTC -100 USDT
        ]
        resolved_delta = await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_filled_or_cancelled_orders, {}, False, None
        )
        assert resolved_delta == _resolved(
            explained_orders_deltas=_content({"BTC": 0.05999, "USDT": -700}),   # all deltas explained, others are ignored because missing from portfolio delta. 
            # Note: fees are not taken into account here as portfolio delta is too large to infer fees and we don't want to rely on estimated fees.
            unexplained_orders_deltas=_content({"ETH": 1, "SOL": 10}),   # ETH & SOL delta are not explained
            inferred_filled_orders=unknown_filled_or_cancelled_orders,  # all filled
            inferred_cancelled_orders=[],  # no inferred cancelled order => they all fit in larger deltas
        )
        assert resolved_delta.get_unexplained_orders_deltas_related_to_filled_orders(filled_orders) == {}
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_considering_fees():
    pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
    post_trade_content = _content({"BTC": 0.2, "USDT": 50.2})    # paid 50 USDT in fees
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # no filled order
        assert await personal_data.get_portfolio_filled_orders_deltas(pre_trade_content, post_trade_content, [], [], {}, False, None) == _resolved(
            {}, {}
        )
        error_log.assert_not_called()

        # with fees: delta is found
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 25}),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 25}),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all orders found in deltas because fees have been taken into account
            _content({"BTC": 0.1, "USDT": -550}),
        )
        error_log.assert_not_called()

        # without fees explanation
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 0.025}),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 0.025}),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # fees can't explain the additional -50 only consider -500
            _content({"BTC": 0.1, "USDT": -500}),
            {}
        )
        error_log.assert_not_called()

        # with small numbers
        pre_trade_content = _content({"BTC": 0.1, "USDT": 0.2})
        post_trade_content = _content({"BTC": 0.089, "USDT": 0.1})    # paid 0.1 USDT and 0.001 BTC in fees
        filled_orders = [
            _order("BTC/USDT", 0.1, 100, "sell", {"USDT": 0.1}),
            _order("BTC/USDT", 0.09, 100, "buy", {"BTC": 0.001}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({"BTC": -0.011, "USDT": -0.1}),
            {}
        )
        error_log.assert_not_called()

        # with USDT holdings increasing

        # A. return ignored assets because no explaining fees
        pre_trade_content = _content({"BTC": 0.1, "USDT": 0.2})
        post_trade_content = _content({"BTC": 0.089, "USDT": 0.8})
        filled_orders = [
            _order("BTC/USDT", 0.1, 100, "sell", {"USDT": 0.000001}),
            _order("BTC/USDT", 0.09, 99.3, "buy", {"BTC": 0.000000001}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # 0.6 is NOT explained by 0.7 from order delta - 0.000001 fees
            _content({"BTC": -0.01}),   # takes a bit too much of post trade portfolio (fees are not considered),
            # will be adapted later on if necessary
            _content({"USDT": 0.6}) # ignored assets
        )
        error_log.assert_not_called()

        # B. success with explaining fees
        pre_trade_content = _content({"BTC": 0.1, "USDT": 0.2})
        post_trade_content = _content({"BTC": 0.089, "USDT": 0.8})
        filled_orders = [
            _order("BTC/USDT", 0.1, 100, "sell", {"USDT": 0.1}),
            _order("BTC/USDT", 0.09, 99.3, "buy", {"BTC": 0.001}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # 0.6 is explained by 0.7 from order delta - 0.1 fees
            _content({"BTC": -0.011, "USDT": 0.6}),
            {}
        )
        error_log.assert_not_called()

        # only equivalent sell and buy orders: no BTC delta
        pre_trade_content = _content({"BTC": 0.1, "USDT": 1000})
        post_trade_content = _content({"BTC": 0.1, "USDT": 995})
        filled_orders = [
            _order("BTC/USDT", 0.05, 550, "sell", {"USDT": 1}),
            _order("BTC/USDT", 0.05, 553, "buy", {"USDT": 1}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({"USDT": -5}),
            {}, # BTC is not a missing delta as there is no delta (delta = 0)
        )
        error_log.assert_not_called()

        # actual fee currency is different from expected fee currency, delta is explained by these fees
        BTC_fees = 0.00000109889 # 10% of computed BTC delta is fees but it's only fetched from portfolio, not expected order fees
        pre_trade_content = _content({"BTC": 0.00226262681, "USDT": 4376.532183487584})
        post_trade_content = _content({"BTC": 0.00227318792 - BTC_fees, "USDT": 4375.22614367084})
        filled_orders = [
            # note: include ignored local exchange fees
            _order("BTC/USDT", 0.00108723, 111.778333746, "sell", {"USDT": 0.111778333746}, local_fees_currencies=["BNB"]),
            _order("BTC/USDT", 0.00109889, 112.972595229, "buy", {"USDT": 0.111778333746}, local_fees_currencies=["BNB"]), # expects USDT as fees but was actually BTC
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # BTC delta from unexpected fees are taken into account and don't create missing deltas
            _content({"BTC": 0.00000946222, "USDT": -1.306039816744}),
            {},
        )
        error_log.assert_not_called()

        # actual fee currency is different from expected fee currency, delta is explained by these fees
        pre_trade_content = _content({"BTC": 0.00226262681, "USDT": 4376.532183487584})
        post_trade_content = _content({"BTC": 0.00227318792, "USDT": 4375.22614367084})
        filled_orders = [
            # note: include ignored local exchange fees
            _order("BTC/USDT", 0.00108723, 111.778333746, "sell", {"USDT": 0.111778333746}, local_fees_currencies=["BNB"]), # expects USDT as fees but was actually something else (like BNB)
            _order("BTC/USDT", 0.00109779111, 112.972595229, "buy", {"USDT": 0.111778333746}, local_fees_currencies=["KCS"]), # expects USDT as fees but was actually something else (like BNB)
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # USDT delta == 4375.22614367084 - 4376.532183487584
            _content({"USDT": -1.306039816744, "BTC": 0.00001056111}),
            {},
        )
        error_log.assert_not_called()

        actual_fees = 0.2775394125  # 0.6% fees
        # actual fees is much smaller than expected, portfolio delta is accepted
        pre_trade_content = _content({"MANA": 103.42087452540375, "USDC": actual_fees})
        post_trade_content = _content({"MANA": 72.65087452540375, "USDC": 0.0827944124999931})
        filled_orders = [
            # note: include unused local exchange fees
            _order("MANA/USDC", 103.05, 37.005255, "sell", {"USDC": actual_fees * 2}, local_fees_currencies=["BNB"]), # expects 1.2% fees
            _order("MANA/USDC", 72.28, 36.644921175, "buy", {"USDC": actual_fees * 2}, local_fees_currencies=["BNB"]),    # expects 1.2% fees
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # USDC delta from portfolio is accepted and not considered as missing
            _content({"MANA": -30.77, "USDC": -0.1947450000000069}),
            {},
        )

        # with real world data and unexplained XRP delta
        pre_trade_content = _content({'ADA': 348.4678994, 'XRP': 50.099980421, 'HBAR': 415.351319913, 'SOL': 0.324842614, 'BNB': 0.067427378, 'TRX': 158.1497955, 'ETH': 0.014648971, 'STETH': 0.014664933, 'BTC': 0.00045070746, 'DOGE': 253.578803158, 'WBTC': 0.00044911, 'USDT': 0.44722602646769})
        post_trade_content = _content({'USDT': 463.91885868343945, 'ADA': 276.9613994, 'XRP': 49.688289426, 'HBAR': 415.351319913, 'SOL': 0.012139614, 'WBTC': 0.00000111, 'ETH': 9.71e-7, 'STETH': 9.33e-7, 'BNB': 0.000001378, 'BTC': 7.46e-9, 'TRX': 0.0000015, 'DOGE': 0.000001158})
        filled_orders = [
            _order("XRP/USDT", 17.19089, 2.9767529739123453 * 17.19089, "sell", {"USDT": 0.0511730329317}),  # doesn't explain the XRP delta
            _order("WBTC/USDT", 0.000448, 113449.7375 * 0.000448, "sell", {"USDT": 0.0508254824}),
            _order("TRX/USDT", 158.149794, 0.32662 * 158.149794, "sell", {"USDT": 0.05165488571628}),
            _order("STETH/USDT", 0.014664 , 3516.7232978723405 * 0.014664, "sell", {"USDT": 0.05156923044}),
            _order("SOL/USDT", 0.312703 , 164.42 * 0.312703, "sell", {"USDT": 0.05141462726}),
            _order("ETH/USDT", 0.014648 , 3522.74 * 0.014648, "sell", {"USDT": 0.05160109552}),
            _order("DOGE/USDT", 253.578802 , 0.2019417164068784 * 253.578802, "sell", {"USDT": 0.05120813852028}),
            _order("BTC/USDT", 0.0004507 , 113640.0 * 0.0004507, "sell", {"USDT": 0.051217548}),
            _order("BNB/USDT", 0.067426 , 767.1 * 0.067426, "sell", {"USDT": 0.0517224846}),
            _order("ADA/USDT", 71.5065 , 0.7216 * 71.5065, "sell", {"USDT": 0.0515990904}),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            _content({'DOGE': -253.578802, 'ADA': -71.5065, 'SOL': -0.312703, 'TRX': -158.149794, 'BNB': -0.067426, 'BTC': -0.0004507, 'WBTC': -0.000448, 'ETH': -0.014648, 'STETH': -0.014664}),
            _content({'XRP': -0.411690995, 'USDT': "463.47163265697176"}),  # todo use those to be accepted in deltas
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_considering_local_exchange_fees():
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # with high fees paid in BNB (real world example)
        # 1. with buy order
        pre_trade_content = _content({"BTC": 0.000164, "BNB": 0.3549429, "USDT": 745.08144})
        post_trade_content = _content({
            "BTC": 0.006404, # 0.000164+0.00016*39
            "BNB": 0.37513215, # should be 0.3549429+0.025 = 0.3799429 BUT all order fees were actually paid in BNB for a total of 0.00481075 BNB (which is large (20%) compared to the 0.025 BNB that we just bought)
            "USDT": 10
        })
        filled_orders = [
            # expected fees are in the wrong currency (actual fees were paid in BNB)
            _order("BNB/USDT", 0.025, 753.92*0.025, "buy", {"BNB": 0.00015}, local_fees_currencies=["BNB"]),
            _order("BTC/USDT", 0.00016*39, 114781.0*0.00016*39, "buy", {"BTC": 9.6E-7*39}, local_fees_currencies=["BNB"]),   # *39 to simulate 39 total other orders
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all deltas are accepted, BNB 20% delta from order is accepted from BNB fees
            explained_orders_deltas=_content({"BTC": 0.00624, "BNB": 0.02018925, "USDT": -735.08144}),
        )
        error_log.assert_not_called()

        pre_trade_content = _content({"BTC": 0.000164, "BNB": 0.3549429, "USDT": 745.08144})
        post_trade_content = _content({
            "BTC": 0.006404, # 0.000164+0.00016*39
            "BNB": 0.32513215, # should be 0.3549429-0.025 = 0.3299429 BUT all order fees were actually paid in BNB for a total of 0.00481075 BNB (which is large (20%) compared to the 0.025 BNB that we just bought)
            "USDT": 47.696  # 745.08144-114781.0*0.00016*39+18.848
        })
        filled_orders = [
            # expected fees are in the wrong currency (actual fees were paid in BNB)
            _order("USDT/BNB", 18.848, 18.848/753.92, "buy", {"BNB": 0.00015}, local_fees_currencies=["BNB"]),
            _order("BTC/USDT", 0.00016*39, 114781.0*0.00016*39, "buy", {"BTC": 9.6E-7*39}, local_fees_currencies=["BNB"]),   # *39 to simulate 39 total other orders
        ]
        assert _rounded_resolved_deltas(await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        )) == _resolved(
            # all deltas are accepted, BNB 20% delta from order is accepted from BNB fees
            explained_orders_deltas=_content({"BTC": 0.00624, "BNB": -0.025, "USDT": -697.38544}),
        )
        error_log.assert_not_called()

        # 2. with sell order
        pre_trade_content = _content({"BTC": 0.000164, "BNB": 0.3549429, "USDT": 745.08144})
        post_trade_content = _content({
            "BTC": 0.006404, # 0.000164+0.00016*39
            "BNB": 0.32513215, # should be 0.3549429-0.025 = 0.3299429 BUT all order fees were actually paid in BNB for a total of 0.00481075 BNB (which is large (20%) compared to the 0.025 BNB that we just bought)
            "USDT": 47.696  # 745.08144-114781.0*0.00016*39+18.848
        })
        filled_orders = [
            # expected fees are in the wrong currency (actual fees were paid in BNB)
            _order("BNB/USDT", 0.025, 753.92*0.025, "sell", {"BNB": 0.00015}, local_fees_currencies=["BNB"]),
            _order("BTC/USDT", 0.00016*39, 114781.0*0.00016*39, "buy", {"BTC": 9.6E-7*39}, local_fees_currencies=["BNB"]),   # *39 to simulate 39 total other orders
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all deltas are accepted, BNB 20% delta from order is accepted from BNB fees
            explained_orders_deltas=_content({"BTC": 0.00624, "BNB": -0.025, "USDT": -697.38544}),
        )
        error_log.assert_not_called()
        pre_trade_content = _content({"BTC": 0.000164, "BNB": 0.3549429, "USDT": 745.08144})
        post_trade_content = _content({
            "BTC": 0.006404, # 0.000164+0.00016*39
            "BNB": 0.37513215, # should be 0.3549429+0.025 = 0.3799429 BUT all order fees were actually paid in BNB for a total of 0.00481075 BNB (which is large (20%) compared to the 0.025 BNB that we just bought)
            "USDT": 10
        })
        filled_orders = [
            # expected fees are in the wrong currency (actual fees were paid in BNB)
            _order("USDT/BNB", 18.848, 18.848/753.92, "sell", {"BNB": 0.00015}, local_fees_currencies=["BNB"]),  # reversed symbol
            _order("BTC/USDT", 0.00016*39, 114781.0*0.00016*39, "buy", {"BTC": 9.6E-7*39}, local_fees_currencies=["BNB"]),   # *39 to simulate 39 total other orders
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all deltas are accepted, BNB 20% delta from order is accepted from BNB fees
            explained_orders_deltas=_content({"BTC": 0.00624, "BNB": 0.02018925, "USDT": -735.08144}),
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_exchange_fetched_fees():
    pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
    post_trade_content = _content({"BTC": 0.2, "USDT": 50.2})    # paid 50 USDT in fees
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # no filled order
        assert await personal_data.get_portfolio_filled_orders_deltas(pre_trade_content, post_trade_content, [], [], {}, False, None) == _resolved(
            {}, {}
        )
        error_log.assert_not_called()

        # with fees: delta is found
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 25}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 25}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all orders found in deltas because fees have been taken into account
            _content({"BTC": 0.1, "USDT": -550}),
        )
        for order in filled_orders:
            assert order.get_computed_fee.call_count > 0
        error_log.assert_not_called()

        # now with unknown orders
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], filled_orders, {}, False, None
        ) == _resolved(
            # all orders found in deltas because fees have been taken into account
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -550}),
            inferred_filled_orders=filled_orders,
        )
        error_log.assert_not_called()

        # same test but fees will be much lower and won't explain all detlas
        filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            _content({"BTC": 0.1, "USDT": -500.2}),
        )
        error_log.assert_not_called()

        # now with unknown orders
        unknown_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_orders, {}, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.2}),
            inferred_filled_orders=unknown_orders,
        )
        error_log.assert_not_called()

        # with an order that is not explained in deltas at all
        unknown_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.05, 450, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.01, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True),
            _order("BTC/USDT", 0.05, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True), # not explained
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, [], unknown_orders, {}, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.2}),
            inferred_filled_orders=unknown_orders[:-1],
            inferred_cancelled_orders=[unknown_orders[-1]],
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_partially_filled_orders():
    # without fees
    pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
    post_trade_content = _content({"BTC": 0.2, "USDT": 100})
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # no filled order
        partially_filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", filled_quantity=0),
            _order("BTC/USDT", 0.05, 450, "buy", filled_quantity=0),
            _order("BTC/USDT", 0.01, 50, "sell", filled_quantity=0),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, partially_filled_orders, [], {}, False, None
        ) == _resolved(
            # all orders are considered as fully filled since filled quantity is 0: they can't be partially filled
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.2}),
        )
        error_log.assert_not_called()

        filled_or_partially_filled_orders = [
            _order("BTC/USDT", 0.12, 600, "buy", filled_quantity=0.11),   # 0.01 unfilled
            _order("BTC/USDT", 0.01, 50, "sell"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_or_partially_filled_orders, [], {}, False, None
        ) == _resolved(
            # all orders found in deltas, even though buy order is not completely filled
            _content({"BTC": 0.1, "USDT": -500.2}),
        )
        error_log.assert_not_called()

        # with exchange fetched fees 
        pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
        post_trade_content = _content({"BTC": 0.2, "USDT": 50.2})    # paid 50 USDT in fees

        filled_orders = [
            _order("BTC/USDT", 0.12, 200, "buy", {"USDT": 25}, is_exchange_fetched_fee=True, filled_quantity=0.06),
            _order("BTC/USDT", 0.1, 900, "buy", {"USDT": 25}, is_exchange_fetched_fee=True, filled_quantity=0.05),
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.01),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(
            # all orders found in deltas because fees have been taken into account
            _content({"BTC": 0.1, "USDT": -550}),
        )
        error_log.assert_not_called()

        # with unknown orders. Note: unknown orders can't be partially filled (or they would have been fetched). 
        # So unknown orders with partially filled amount can't have newly filled amount, or they will be considered as fully filled from their trade (and created with the filled quantity).
        filled_orders = [
            _order("BTC/USDT", 0.2, 1000, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.11),
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.01),
        ]
        unknown_orders = [
            _order("BTC/USDT", 0.2, 1000, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.02, exchange_order_id="order_2"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_orders, {}, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.1}),
            inferred_filled_orders=[],
            inferred_cancelled_orders=unknown_orders,
        )
        error_log.assert_not_called()

        # with an order that is not explained in deltas at all
        filled_orders = [
            _order("BTC/USDT", 0.12, 200, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.06),
            _order("BTC/USDT", 0.1, 900, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.05),
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.01),
        ]
        unknown_orders = [
            _order("BTC/USDT", 0.05, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.03), # not explained
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_orders, {}, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.2}),
            inferred_filled_orders=[],
            inferred_cancelled_orders=unknown_orders,
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_with_partially_filled_orders_and_ignored_filled_quantity_per_order_exchange_id():
    # without fees
    pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
    post_trade_content = _content({"BTC": 0.2, "USDT": 100})
    error_log = mock.Mock()
    ignored_filled_quantity_per_order_exchange_id = {
        "order_1": decimal.Decimal("0.01"),
        "order_2": decimal.Decimal("0.02"),
        "order_3": decimal.Decimal("0.001"),
        "order_999": decimal.Decimal("1"),
    }
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # no NEW filled order delta (deltas are already ignored)
        partially_filled_orders = [
            _order("BTC/USDT", 0.06, 100, "buy", filled_quantity=0.01, exchange_order_id="order_1"),
            _order("BTC/USDT", 0.05, 450, "buy", filled_quantity=0),
            _order("BTC/USDT", 0.01, 50, "sell", filled_quantity=0.001, exchange_order_id="order_3"),
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, partially_filled_orders, [], ignored_filled_quantity_per_order_exchange_id, False, None
        ) == _resolved(
            # only order 2 is found in deltas as it is identified as fully filled (filled quantity is 0, it's not partially filled and is considered as fully filled to partially explain deltas)
            _content({"BTC": 0.05, "USDT": -450}),
        )
        error_log.assert_not_called()

        filled_or_partially_filled_orders = [
            _order("BTC/USDT", 0.12, 600, "buy", filled_quantity=0.12, exchange_order_id="order_1"),   # 0.11 newly filled (0.01 was already)
            _order("BTC/USDT", 0.02, 100, "sell", filled_quantity=0.011, exchange_order_id="order_3"),   # 0.01 newly filled (0.001 was already)
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_or_partially_filled_orders, [], ignored_filled_quantity_per_order_exchange_id, False, None
        ) == _resolved(
            # all orders found in deltas, even though buy order is not completely filled
            _content({"BTC": 0.1, "USDT": -500.2}),
        )
        error_log.assert_not_called()

        # with exchange fetched fees 
        pre_trade_content = _content({"BTC": 0.1, "USDT": 600.2})
        post_trade_content = _content({"BTC": 0.2, "USDT": 50.2})    # paid 50 USDT in fees
        
        filled_orders = [
            _order("BTC/USDT", 0.12, 200, "buy", {"USDT": 25}, is_exchange_fetched_fee=True, filled_quantity=0.07, exchange_order_id="order_1"),   # 0.06 newly filled (0.01 was already)
            _order("BTC/USDT", 0.1, 900, "buy", {"USDT": 25}, is_exchange_fetched_fee=True, filled_quantity=0.07, exchange_order_id="order_2"),   # 0.05 newly filled (0.02 was already)
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.011, exchange_order_id="order_3"),   # 0.01 newly filled (0.001 was already)
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], ignored_filled_quantity_per_order_exchange_id, False, None
        ) == _resolved(
            # all orders found in deltas because fees have been taken into account
            _content({"BTC": 0.1, "USDT": -550}),
        )
        error_log.assert_not_called()

        # with unknown orders. Note: unknown orders can't be partially filled (or they would have been fetched). 
        # So unknown orders with partially filled amount can't have newly filled amount, or they will be considered as fully filled from their trade (and created with the filled quantity).
        filled_orders = [
            _order("BTC/USDT", 0.2, 1000, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.12, exchange_order_id="order_2"),   # 0.1 newly filled (0.02 was already)
        ]
        unknown_orders = [
            _order("BTC/USDT", 0.12, 200, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.01, exchange_order_id="order_1"),   # (0.01 was already)
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.001, exchange_order_id="order_3"),   # (0.001 was already)
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_orders, ignored_filled_quantity_per_order_exchange_id, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.1}),
            inferred_filled_orders=[],
            inferred_cancelled_orders=unknown_orders,
        )
        error_log.assert_not_called()

        # with an order that is not explained in deltas at all
        filled_orders = [
            _order("BTC/USDT", 0.12, 200, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.07, exchange_order_id="order_1"),   # 0.06 newly filled (0.01 was already)
            _order("BTC/USDT", 0.1, 900, "buy", {"USDT": 0.1}, is_exchange_fetched_fee=True, filled_quantity=0.07, exchange_order_id="order_2"),   # 0.05 newly filled (0.02 was already)
            _order("BTC/USDT", 0.1, 500, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.011, exchange_order_id="order_3"),   # 0.01 newly filled (0.001 was already)
        ]
        unknown_orders = [
            _order("BTC/USDT", 0.05, 50, "sell", {"BTC": 0.0000001}, is_exchange_fetched_fee=True, filled_quantity=0.03), # not explained
        ]
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, unknown_orders, ignored_filled_quantity_per_order_exchange_id, False, None
        ) == _resolved(
            # only the part actually explained by fetched fees are taken into account in deltas (instead of -550 USDT)
            explained_orders_deltas=_content({"BTC": 0.1, "USDT": -500.2}),
            inferred_filled_orders=[],
            inferred_cancelled_orders=unknown_orders,
        )
        error_log.assert_not_called()


@pytest.mark.asyncio
async def test_get_accepted_missed_deltas():
    # with no delta
    post_trade_content = _content({"XRP": 40, "USDT": 129.2474232})
    updated_sub_portfolio = _content({"XRP": 50, "USDT": 36.878811542})
    assert personal_data.get_accepted_missed_deltas(
        post_trade_content, updated_sub_portfolio, {}
    ) == ({}, {})

    # base case
    pre_trade_content = _content({"XRP": 40, "USDT": 129.2474232})
    post_trade_content = _content({"XRP": 50, "USDT": 36.878811542})
    sub_portfolio_pre_trade_content = _content({"XRP": 40, "USDT": 129.2474232})
    filled_orders = [
        _order("XRP/USDT", 10, 115.4889262, "buy"),
    ]
    resolved_orders_portfolio_delta = await personal_data.get_portfolio_filled_orders_deltas(
        pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
    )
    deltas, missed_deltas = resolved_orders_portfolio_delta.explained_orders_deltas, resolved_orders_portfolio_delta.unexplained_orders_deltas
    assert deltas == _content({"XRP": 10})
    assert missed_deltas == _content({"USDT": -92.368611658})
    sub_portfolio = personal_data.SubPortfolioData(
        None, None, 0, sub_portfolio_pre_trade_content, None, funds_deltas=deltas
    )
    updated_sub_portfolio = sub_portfolio.get_content_from_total_deltas_and_locked_funds()
    accepted_deltas, remaining_deltas = personal_data.get_accepted_missed_deltas(
        post_trade_content, updated_sub_portfolio, missed_deltas
    )
    assert accepted_deltas == _content({"USDT": -92.368611658})
    assert remaining_deltas == {}

    # with remaining_deltas
    pre_trade_content = _content({"XRP": 40, "USDT": 229.2474232})
    post_trade_content = _content({"XRP": 50, "USDT": 136.878811542})
    sub_portfolio_pre_trade_content = _content({"XRP": 40, "USDT": 129.2474232})
    filled_orders = [
        _order("XRP/USDT", 10, 115.4889262, "buy"),
    ]
    resolved_orders_portfolio_delta = await personal_data.get_portfolio_filled_orders_deltas(
        pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
    )
    deltas, missed_deltas = resolved_orders_portfolio_delta.explained_orders_deltas, resolved_orders_portfolio_delta.unexplained_orders_deltas
    assert deltas == _content({"XRP": 10})
    assert missed_deltas == _content({"USDT": -92.368611658})
    sub_portfolio = personal_data.SubPortfolioData(
        None, None, 0, sub_portfolio_pre_trade_content, None, funds_deltas=deltas
    )
    updated_sub_portfolio = sub_portfolio.get_content_from_total_deltas_and_locked_funds()
    accepted_deltas, remaining_deltas = personal_data.get_accepted_missed_deltas(
        post_trade_content, updated_sub_portfolio, missed_deltas
    )
    # sub portfolio resolved value can still be contained in portfolio: this delta remains as missing
    assert accepted_deltas == {}
    assert remaining_deltas == _content({"USDT": -92.368611658})

    # with missing coin in sub portfolio
    post_trade_content = _content({"XRP": 50})
    sub_portfolio_pre_trade_content = _content({"XRP": 40, "USDT": 229.2474232})
    missed_deltas = _content({"USDT": -229.2474232})
    accepted_deltas, remaining_deltas = personal_data.get_accepted_missed_deltas(
        post_trade_content, sub_portfolio_pre_trade_content, missed_deltas
    )
    # sub portfolio resolved value can still be contained in portfolio: this delta remains as missing
    assert accepted_deltas == _content({"USDT": -229.2474232})
    assert remaining_deltas == {}


@pytest.mark.asyncio
async def test_get_portfolio_filled_orders_deltas_considering_different_fee_tiers():
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(error=error_log))):
        # base 1.2% fees
        pre_trade_usdc = 2.203362439822
        pre_trade_content = _content({"ETH": 0.01145892, "USDC": pre_trade_usdc, 'BTC': 0.01937857})
        filled_orders = [
            _order("BTC/USDC", 0.00091181, 99.2684993932, "sell", {"USDC": 1.1912219927184}),
            _order("XRP/USDC", 3.840399, 9.1942992459, "buy", {"USDC": 0.1103315909508}),
            _order("XLM/USDC", 33.59950349, 9.79704799822749, "buy", {"USDC": 0.11756457597873}),
            _order("SUI/USDC", 2.4, 9.35448, "buy", {"USDC": 0.11225376}),
            _order("SOL/USDC", 0.05705159, 9.78999848, "buy", {"USDC": 0.11747998176}),
            _order("LINK/USDC", 0.61, 9.73987, "buy", {"USDC": 0.11687844}),
            _order("ETH/USDC", 0.00387595, 9.7899907885, "buy", {"USDC": 0.117479889462}),
            _order("DOGE/USDC", 42.3, 9.778068, "buy", {"USDC": 0.117336816}),
            _order("BTC/USDC", 0.00008992, 9.7895661216, "buy", {"USDC": 0.1174747934592}),
            _order("AVAX/USDC", 0.42769768, 9.7899998952, "buy", {"USDC": 0.1174799987424}),
            _order("ADA/USDC", 12.75318927, 9.796999997214, "buy", {"USDC": 0.117563999966568}),
        ]
        max_fees_deltas = {
            "XRP": 3.840399, "SUI": 2.4, "XLM": 33.59950349, "SOL": 0.05705159, "LINK": 0.61, "DOGE": 42.3,
            "AVAX": 0.42769768, "ADA": 12.75318927, "ETH": 0.00387595, "USDC": 0.095113027520412,
            "BTC": -0.00082189
        }
        post_trade_content = _content({
            "XRP": 3.840399, "SUI": 2.4, "XLM": 33.59950349, "SOL": 0.05705159, "LINK": 0.61, "DOGE": 42.3,
            "AVAX": 0.42769768, "ADA": 12.75318927, "ETH": 0.01533487, "USDC": 2.298475467342412, "BTC": 0.01855668
        })
        assert await personal_data.get_portfolio_filled_orders_deltas(
            pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
        ) == _resolved(_content(max_fees_deltas), {})
        error_log.assert_not_called()

        # use coinbase fees tiers for this test
        expected_fees_percent = 1.2
        for real_fee_percent in (1.2, 0.75, 0.4, 0.25, 0.20, 0.16, 0.14, 0.10, 0.08, 0.05):
            total_real_paid_fees = [decimal.Decimal(0)]

            def _get_expected_fees(cost):
                real_paid_fees = decimal.Decimal(str(cost)) * decimal.Decimal(str(real_fee_percent)) / decimal.Decimal(100)
                expected_paid_fees = decimal.Decimal(str(cost)) * decimal.Decimal(str(expected_fees_percent)) / decimal.Decimal(100)
                total_real_paid_fees[0] = total_real_paid_fees[0] + real_paid_fees
                # expected fees are always 1.2%
                return float(expected_paid_fees)

            filled_orders = [
                _order("BTC/USDC", 0.00091181, 99.2684993932, "sell", {"USDC": _get_expected_fees(99.2684993932)}),
                _order("XRP/USDC", 3.840399, 9.1942992459, "buy", {"USDC": _get_expected_fees(9.1942992459)}),
                _order("XLM/USDC", 33.59950349, 9.79704799822749, "buy", {"USDC": _get_expected_fees(9.79704799822749)}),
                _order("SUI/USDC", 2.4, 9.35448, "buy", {"USDC": _get_expected_fees(9.35448)}),
                _order("SOL/USDC", 0.05705159, 9.78999848, "buy", {"USDC": _get_expected_fees(9.78999848)}),
                _order("LINK/USDC", 0.61, 9.73987, "buy", {"USDC": _get_expected_fees(9.73987)}),
                _order("ETH/USDC", 0.00387595, 9.7899907885, "buy", {"USDC": _get_expected_fees(9.7899907885)}),
                _order("DOGE/USDC", 42.3, 9.778068, "buy", {"USDC": _get_expected_fees(9.778068)}),
                _order("BTC/USDC", 0.00008992, 9.7895661216, "buy", {"USDC": _get_expected_fees(9.7895661216)}),
                _order("AVAX/USDC", 0.42769768, 9.7899998952, "buy", {"USDC": _get_expected_fees(9.7899998952)}),
                _order("ADA/USDC", 12.75318927, 9.796999997214, "buy", {"USDC": _get_expected_fees(9.796999997214)}),
            ]

            post_trade_usdc = (
                decimal.Decimal(str(pre_trade_usdc))
                + sum(decimal.Decimal(str(o.total_cost)) for o in filled_orders if o.side == enums.TradeOrderSide.SELL)
                - sum(decimal.Decimal(str(o.total_cost)) for o in filled_orders if o.side == enums.TradeOrderSide.BUY)
                - total_real_paid_fees[0]
            )
            post_trade_content = _content({
                "XRP": 3.840399, "SUI": 2.4, "XLM": 33.59950349, "SOL": 0.05705159, "LINK": 0.61, "DOGE": 42.3,
                "AVAX": 0.42769768, "ADA": 12.75318927, "ETH": 0.01533487, "USDC": float(post_trade_usdc), "BTC": 0.01855668
            })
            local_fees_deltas = {
                "XRP": 3.840399, "SUI": 2.4, "XLM": 33.59950349, "SOL": 0.05705159, "LINK": 0.61, "DOGE": 42.3,
                "AVAX": 0.42769768, "ADA": 12.75318927, "ETH": 0.00387595, "BTC": -0.00082189,
                "USDC": float(post_trade_usdc - decimal.Decimal(str(pre_trade_usdc))),
            }

            if real_fee_percent == 1.2:
                # same result as previous (non looping) test
                assert await personal_data.get_portfolio_filled_orders_deltas(
                    pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
                ) == _resolved(_content(max_fees_deltas), {})
            else:
                resolved_orders_portfolio_delta = await personal_data.get_portfolio_filled_orders_deltas(
                    pre_trade_content, post_trade_content, filled_orders, [], {}, False, None
                )
                # fix rounding issues
                deltas, missing_deltas = resolved_orders_portfolio_delta.explained_orders_deltas, resolved_orders_portfolio_delta.unexplained_orders_deltas
                # fix rounding issues
                local_fees_deltas["USDC"] = float(round(decimal.Decimal(local_fees_deltas["USDC"]), 8))
                assert missing_deltas == {}, f"{real_fee_percent=} {missing_deltas=}"
                for key in (octobot_commons.constants.PORTFOLIO_AVAILABLE, octobot_commons.constants.PORTFOLIO_TOTAL):
                    deltas["USDC"][key] = round(deltas["USDC"][key], 8)
                assert resolved_orders_portfolio_delta.explained_orders_deltas == _content(local_fees_deltas), f"{real_fee_percent=}"

            error_log.assert_not_called()


def test_resolve_sub_portfolios_with_filling_assets_with_locked_funds():
    master_pf = _sub_pf(
        0,
        _content_with_available({
            "BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
        })
    )
    filling_assets = ["USDC", "SOL"]
    market_prices = {
        "SOL/USDT": 150,
        "BTC/USDC": 83000,
        "ETH/USDC": 2000,
        "USDT/USDC": 1,
    }
    sub_pf_btc = _sub_pf(
        0, _content({"BTC": 0.1}),
        allowed_filling_assets=filling_assets,
        locked_funds_by_asset = trading_api.get_orders_locked_amounts_by_asset([
            _open_order("BTC/USDT", 0.06, 400, "sell", 0.000001, "BTC"),
            _open_order("BTC/USDT", 0.02, 600, "sell", 0.000001, "BTC"),
        ])
    )
    # nothing to fill
    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pf_btc], market_prices) == (
        _sub_pf(0, _content_with_available({
            "BTC": (0, 0), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
        })),
        [_sub_pf(0, _content_with_available({"BTC": (0.019998, 0.1)}), locked_funds_by_asset=_missing_funds({"BTC": 0.080002}))]
    )

    master_pf = _sub_pf(
        0,
        _content_with_available({
            "BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
        })
    )
    sub_pf_missing_usdt = _sub_pf(
        1, _content_with_available({"USDT": (140, 150), "SOL": (0, 0.5)}),
        allowed_filling_assets=filling_assets,
        locked_funds_by_asset = trading_api.get_orders_locked_amounts_by_asset([
            _open_order("BTC/USDT", 0.01, 10, "buy", 0.000001, "BTC"),
            _open_order("SOL/USDT", 0.5, 1, "sell", 0.000001, "USDT"),
        ])
    )
    # fill with locked amount
    assert personal_data.resolve_sub_portfolios(master_pf, [sub_pf_btc, sub_pf_missing_usdt], market_prices) == (
        _sub_pf(0, _content_with_available({
            "BTC": (0, 0), "ETH": (0.019998, 0.1), "USDT": (0, 0), "SOL": (0, 0), "USDC": (0, 0)
        })),
        [
            _sub_pf(0, _content_with_available({"BTC": (0.019998, 0.1)}), locked_funds_by_asset=_missing_funds({"BTC": 0.080002})),
            _sub_pf(
                1,
                _content_with_available({"USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)}),
                funds_deltas=_content_with_available({
                    "SOL": (0.5, 0.5), "USDC": (2, 2)
                }),
                missing_funds=_missing_funds({
                    "USDT": float(
                        decimal.Decimal(140)
                        - decimal.Decimal("10.019998")
                        - decimal.Decimal(str(market_prices["SOL/USDT"])) / decimal.Decimal("2")
                        - decimal.Decimal(market_prices["USDT/USDC"] * 2)
                    )
                }),
                locked_funds_by_asset=_missing_funds({"USDT": 10, "SOL": 0.5}),
            )
        ]
    )


def test_get_master_checked_sub_portfolio_update():
    with mock.patch.object(octobot_commons.logging.BotLogger, "warning") as warning_mock:
        # nothing to do: sub portfolio makes sense compared to master
        updated_portfolio_content = _content({"BTC": 0, "ETH": 9.9999999, "USDT": 111, "DOT": 1111})
        updated_sub_portfolio = _content({"BTC": 0, "ETH": 9.9999999, "USDT": 100})
        assert personal_data.get_master_checked_sub_portfolio_update(updated_portfolio_content, updated_sub_portfolio) == {}
        warning_mock.assert_not_called()

        # SOL is not in master portfolio
        updated_sub_portfolio = _content({"BTC": 0, "ETH": 9.9999999, "USDT": 100, "SOL": 10})
        assert personal_data.get_master_checked_sub_portfolio_update(updated_portfolio_content, updated_sub_portfolio) == (
            _content({"SOL": 0})
        )
        warning_mock.assert_called_once()
        assert "SOL removed" in warning_mock.mock_calls[0].args[0]
        warning_mock.reset_mock()

        # SOL is not in master portfolio and is 0 in sub portfolio: this is OK
        updated_sub_portfolio = _content({"BTC": 0, "ETH": 9.9999999, "USDT": 100, "SOL": 0})
        assert personal_data.get_master_checked_sub_portfolio_update(updated_portfolio_content, updated_sub_portfolio) == {}
        warning_mock.assert_not_called()
        warning_mock.reset_mock()

        # can't have 120 USDT with 111 in master portfolio
        updated_sub_portfolio = _content({"BTC": 0, "ETH": 9.9999999, "USDT": 120})
        assert personal_data.get_master_checked_sub_portfolio_update(updated_portfolio_content, updated_sub_portfolio) == (
            _content({"USDT": 111})
        )
        warning_mock.assert_called_once()
        assert "USDT holdings aligned" in warning_mock.mock_calls[0].args[0]
        warning_mock.reset_mock()


def test_get_fees_only_asset_deltas_from_orders():
    assert personal_data.get_fees_only_asset_deltas_from_orders([]) == {}
    # force is_exchange_fetched_fee to set order.fees
    orders = [
        _order("BTC/USDT", 1, 100, "sell", {"USDT": 1}, is_exchange_fetched_fee=True),
        _order("ETH/USDT", 1, 100, "buy", {"USDT": 1}, is_exchange_fetched_fee=True),
    ]
    assert personal_data.get_fees_only_asset_deltas_from_orders(orders) == {}
    orders = [
        _order("BTC/USDT", 1, 100, "sell", {"USDT": 1}, is_exchange_fetched_fee=True),
        _order("ETH/USDT", 1, 100, "buy", {"USDT": 1}, is_exchange_fetched_fee=True),
        _order("SOL/USDT", 1, 100, "buy", {"DOT": 1}, is_exchange_fetched_fee=True),
    ]
    assert personal_data.get_fees_only_asset_deltas_from_orders(orders) == {"DOT": decimal.Decimal(-1)}
    orders = [
        _order("BTC/USDT", 1, 100, "sell", {"BTC": 1}, is_exchange_fetched_fee=True),
        _order("ETH/USDT", 1, 100, "buy", {"BNB": 3.21}, is_exchange_fetched_fee=True),
    ]
    assert personal_data.get_fees_only_asset_deltas_from_orders(orders) == {"BNB": decimal.Decimal("-3.21")}


def _sub_pf(
    priority_key: float,
    content: dict[str, dict[str, decimal.Decimal]],
    allowed_filling_assets: list[str] = None,
    forbidden_filling_assets: list[str] = None,
    funds_deltas: dict[str, dict[str, decimal.Decimal]] = None,
    missing_funds: dict[str, decimal.Decimal] = None,
    locked_funds_by_asset: dict[str, decimal.Decimal] = None,
) -> personal_data.SubPortfolioData:
    return personal_data.SubPortfolioData(
        "", "", priority_key, content, "",
        allowed_filling_assets=allowed_filling_assets or [],
        forbidden_filling_assets=forbidden_filling_assets or [],
        funds_deltas=funds_deltas or {},
        missing_funds=missing_funds or {},
        locked_funds_by_asset=locked_funds_by_asset or {}
    )


def _rounded_resolved_deltas(resolved_deltas: personal_data.ResolvedOrdersPortoflioDelta) -> personal_data.ResolvedOrdersPortoflioDelta:
    # fixes rounding issues if any
    for delta in (resolved_deltas.explained_orders_deltas, resolved_deltas.unexplained_orders_deltas):
        for values in delta.values():
            for holding_type, value in values.items():
                values[holding_type] = round(value, 10)
    return resolved_deltas


def _resolved(
    explained_orders_deltas: dict[str, decimal.Decimal] = None,
    unexplained_orders_deltas: dict[str, decimal.Decimal] = None,
    inferred_filled_orders: list[personal_data.Order] = None,
    inferred_cancelled_orders: list[personal_data.Order] = None,
) -> personal_data.ResolvedOrdersPortoflioDelta:
    return personal_data.ResolvedOrdersPortoflioDelta(
        explained_orders_deltas=explained_orders_deltas or {},
        unexplained_orders_deltas=unexplained_orders_deltas or {},
        inferred_filled_orders=inferred_filled_orders or [],
        inferred_cancelled_orders=inferred_cancelled_orders or [],
    )


def _content(content: dict[str, float]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        key: {
            octobot_commons.constants.PORTFOLIO_TOTAL: decimal.Decimal(str(val)),
            octobot_commons.constants.PORTFOLIO_AVAILABLE: decimal.Decimal(str(val)),
        }
        for key, val in content.items()
    }


def _content_with_available(content: dict[str, tuple[float, float]]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        key: {
            octobot_commons.constants.PORTFOLIO_TOTAL: decimal.Decimal(str(total)),
            octobot_commons.constants.PORTFOLIO_AVAILABLE: decimal.Decimal(str(available)),
        }
        for key, (available, total) in content.items()
    }

def _missing_funds(funds: dict[str, float]) -> dict[str, decimal.Decimal]:
    return {
        key: decimal.Decimal(str(val))
        for key, val in funds.items()
    }

def _get_orders_deltas(orders: list[personal_data.Order]) -> dict[str, decimal.Decimal]:
    return personal_data.get_assets_delta_from_orders(orders, {}, False, True)[0]

def _order(
    symbol: str, quantity: float, cost: float, side: str, fee: dict = None, local_fees_currencies: list[str] = [], is_exchange_fetched_fee: bool = False, filled_quantity: float = None, exchange_order_id: str = None
) -> personal_data.Order:
    trader = mock.Mock(exchange_manager=mock.Mock(exchange=mock.Mock(LOCAL_FEES_CURRENCIES=local_fees_currencies)))
    order = personal_data.Order(trader)
    order.symbol = symbol
    if exchange_order_id is not None:
        order.exchange_order_id = exchange_order_id
    order.origin_quantity = decimal.Decimal(str(quantity))
    order.filled_quantity = decimal.Decimal(str(quantity if filled_quantity is None else filled_quantity))
    order.total_cost = decimal.Decimal(str(cost))
    order.origin_price = order.total_cost / order.origin_quantity
    order.side = enums.TradeOrderSide(side)
    if is_exchange_fetched_fee:
        order.fee = {
            enums.FeePropertyColumns.COST.value: decimal.Decimal(str(next(iter(fee.values())) if fee else 0)),
            enums.FeePropertyColumns.CURRENCY.value: next(iter(fee.keys())) if fee else None,
            enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
        }
    # get_computed_fee returns empty fees when is_exchange_fetched_fee is True to avoid side effects with predicted fees
    order.get_computed_fee = mock.Mock(return_value={
        enums.FeePropertyColumns.COST.value: decimal.Decimal(str(next(iter(fee.values())) if fee and not is_exchange_fetched_fee else 0)),
        enums.FeePropertyColumns.CURRENCY.value: next(iter(fee.keys())) if fee and not is_exchange_fetched_fee else None,
        enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: False,
    })
    return order

def _open_order(symbol: str, quantity: float, cost: float, side: str, fee_cost: float, fee_unit: str, is_active: bool = True) -> personal_data.Order:
    order = _order(symbol, quantity, cost, side)
    order.filled_quantity = constants.ZERO
    order.is_filled = mock.Mock(return_value=False)
    order.get_computed_fee = mock.Mock(
        return_value={
            enums.FeePropertyColumns.CURRENCY.value: fee_unit,
            enums.FeePropertyColumns.COST.value: decimal.Decimal(str(fee_cost)),
        }
    )
    order.is_active = is_active
    return order

def _locked_amounts_by_asset(amount_by_asset: dict[str, float]) -> dict[str, decimal.Decimal]:
    return {
        asset: decimal.Decimal(str(amount))
        for asset, amount in amount_by_asset.items()
    }
