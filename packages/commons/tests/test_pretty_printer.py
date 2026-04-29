#  Drakkar-Software OctoBot-Commons
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
import os
import mock

import octobot_commons.pretty_printer as pretty_printer
import octobot_commons.constants as constants


def test_get_min_string_from_number():
    assert pretty_printer.get_min_string_from_number(1) == "1"
    assert pretty_printer.get_min_string_from_number(-1) == "-1"
    assert pretty_printer.get_min_string_from_number(1.000000000001) == "1"
    assert pretty_printer.get_min_string_from_number(1.000000000001, max_digits=1) == "1"
    assert pretty_printer.get_min_string_from_number(1.00000001, max_digits=8) == "1.00000001"
    assert pretty_printer.get_min_string_from_number(0.00000001, max_digits=8) == "0.00000001"
    assert pretty_printer.get_min_string_from_number(-0.000000009, max_digits=8) == "-0.00000001"
    assert pretty_printer.get_min_string_from_number(100.00000001, max_digits=8) == "100.00000001"
    assert pretty_printer.get_min_string_from_number(-100.00000001, max_digits=8) == "-100.00000001"
    assert pretty_printer.get_min_string_from_number(100.09, max_digits=1) == "100.1"
    assert pretty_printer.get_min_string_from_number(100.06, max_digits=1) == "100.1"
    assert pretty_printer.get_min_string_from_number(100.05, max_digits=1) == "100"
    assert pretty_printer.get_min_string_from_number(100.04, max_digits=1) == "100"
    assert pretty_printer.get_min_string_from_number(101.04, max_digits=1) == "101"
    assert pretty_printer.get_min_string_from_number(100.00000000, max_digits=8) == "100"
    assert pretty_printer.get_min_string_from_number(-100.00000000, max_digits=8) == "-100"
    # with computed max_digits
    assert pretty_printer.get_min_string_from_number(-100.00000001) == "-100"
    assert pretty_printer.get_min_string_from_number(100.00000001) == "100"
    assert pretty_printer.get_min_string_from_number(-1.12345678) == "-1.12"
    assert pretty_printer.get_min_string_from_number(1.12345678) == "1.12"
    assert pretty_printer.get_min_string_from_number(0.12345678) == "0.1235"
    assert pretty_printer.get_min_string_from_number(-0.12345678) == "-0.1235"
    assert pretty_printer.get_min_string_from_number(0.0045678) == "0.004568"
    assert pretty_printer.get_min_string_from_number(-0.0045678) == "-0.004568"
    assert pretty_printer.get_min_string_from_number(0.0000456789) == "0.00004568"
    assert pretty_printer.get_min_string_from_number(-0.0000456789) == "-0.00004568"


def test_round_with_decimal_count():
    assert pretty_printer.round_with_decimal_count(None) == 0
    assert pretty_printer.round_with_decimal_count(1) == 1
    assert pretty_printer.round_with_decimal_count(-1) == -1
    assert pretty_printer.round_with_decimal_count(1.000000000001, max_digits=1) == 1
    if not os.getenv('CYTHON_IGNORE'):
        with mock.patch.object(pretty_printer, "get_min_string_from_number", mock.Mock(return_value="1")) \
                as get_min_string_from_number_mock:
            pretty_printer.round_with_decimal_count(None, max_digits=4)
            get_min_string_from_number_mock.assert_not_called()
            pretty_printer.round_with_decimal_count(1.011, max_digits=4)
            get_min_string_from_number_mock.assert_called_once_with(1.011, 4)


def test_global_portfolio_pretty_print():
    portfolio = {
        "BTC": {constants.PORTFOLIO_TOTAL: decimal.Decimal(1)},
        "ETH": {constants.PORTFOLIO_TOTAL: decimal.Decimal(2)},
        "PLOP": {constants.PORTFOLIO_TOTAL: decimal.Decimal("0.444")},
        "ADA": {constants.PORTFOLIO_TOTAL: decimal.Decimal(0)}
    }
    # without ref market
    for res in (
        pretty_printer.global_portfolio_pretty_print(portfolio),
        pretty_printer.global_portfolio_pretty_print(portfolio, markdown=True)
    ):
        assert "BTC" in res
        assert "1" in res
        assert "ETH" in res
        assert "2" in res
        assert "PLOP" in res
        assert "0.444" in res
        assert "ADA" not in res
    # with ref market
    for res in (
        pretty_printer.global_portfolio_pretty_print(portfolio, ref_market_name="BTC"),
        pretty_printer.global_portfolio_pretty_print(portfolio, ref_market_name="BTC", markdown=True)
    ):
        assert "BTC" in res
        assert "1" in res
        assert "ETH" in res
        assert "2" in res
        assert "PLOP" in res
        assert "0.444" in res
        assert "ADA" not in res
    currency_values = {"ETH": decimal.Decimal("1.5")}
    for res in (
        pretty_printer.global_portfolio_pretty_print(portfolio, currency_values=currency_values,
                                                     ref_market_name="BTC"),
        pretty_printer.global_portfolio_pretty_print(portfolio, currency_values=currency_values,
                                                     ref_market_name="BTC", markdown=True)
    ):
        assert "BTC" in res
        assert "1" in res
        assert "ETH" in res
        assert "2" in res
        assert "3" in res
        assert "PLOP" in res
        assert "0.444" in res
        assert "ADA" not in res
    # with separator
    for res in (
        pretty_printer.global_portfolio_pretty_print(portfolio, currency_values=currency_values,
                                                     ref_market_name="BTC", separator="111"),
        pretty_printer.global_portfolio_pretty_print(portfolio, currency_values=currency_values,
                                                     ref_market_name="BTC", markdown=True, separator="111")
    ):
        assert "BTC" in res
        assert "1" in res
        assert "ETH" in res
        assert "2" in res
        assert "3" in res
        assert "PLOP" in res
        assert "0.444" in res
        assert "ADA" not in res
        assert "111" in res
