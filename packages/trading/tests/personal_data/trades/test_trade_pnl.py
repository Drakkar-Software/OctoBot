#  Drakkar-Software OctoBot
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
import mock
import pytest
import decimal

from tests import event_loop
from tests.exchanges import simulated_exchange_manager, simulated_trader
from tests.personal_data.trades import create_executed_trade

import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.constants as constants


SYMBOL = "BTC/USDT"


def test_empty():
    pnl = personal_data.TradePnl([], [])
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_entry_time()
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_close_time()
    assert pnl.get_total_entry_quantity() == constants.ZERO
    assert pnl.get_total_close_quantity() == constants.ZERO
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_entry_price()
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_close_price()
    assert pnl.get_paid_regular_fees_in_quote() == constants.ZERO
    assert pnl.get_paid_special_fees_by_currency() == {}
    with mock.patch.object(pnl, "get_closed_entry_value", mock.Mock(return_value=constants.ZERO)), \
         mock.patch.object(pnl, "get_close_ratio", mock.Mock(return_value=constants.ZERO)), \
         mock.patch.object(pnl, "get_closed_close_value", mock.Mock(return_value=constants.ONE_HUNDRED)), \
         mock.patch.object(pnl, "get_paid_regular_fees_in_quote", mock.Mock(return_value=constants.ONE)):
        # X/0
        assert pnl.get_profits() == (
            constants.ONE_HUNDRED - constants.ONE,
            constants.ZERO
        )
        with mock.patch.object(pnl, "get_closed_close_value", mock.Mock(return_value=constants.ZERO)), \
             mock.patch.object(pnl, "get_paid_regular_fees_in_quote", mock.Mock(return_value=constants.ZERO)):
            # 0/0
            assert pnl.get_profits() == (
                constants.ZERO,
                constants.ZERO
            )


def test_with_invalid_values(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(0), decimal.Decimal(10), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 1)),
    ])
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_close_ratio()
    with pytest.raises(errors.IncompletePNLError):
        pnl.get_profits()
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(0), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_close_ratio() == constants.ONE
    assert pnl.get_profits() == (
        decimal.Decimal("14"),  # 15 - fees
        constants.ZERO
    )


def test_simple_buy_entry_and_sell_close(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 12
    assert pnl.get_close_time() == 15
    assert pnl.get_total_entry_quantity() == decimal.Decimal(1)
    assert pnl.get_total_close_quantity() == decimal.Decimal(1)
    assert pnl.get_entry_price() == decimal.Decimal(10)
    assert pnl.get_close_price() == decimal.Decimal(15)
    assert pnl.get_closed_entry_value() == decimal.Decimal(10) * decimal.Decimal(1)
    assert pnl.get_closed_close_value() == decimal.Decimal(15) * decimal.Decimal(1)
    assert pnl.get_close_ratio() == decimal.Decimal("1")
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal(1)
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.1") * decimal.Decimal(10)
    assert pnl.get_paid_special_fees_by_currency() == {}
    # started with 10, closed with 15, paid 2 in fees: end value: 13
    assert pnl.get_profits() == (
        decimal.Decimal(15) - decimal.Decimal(10) - decimal.Decimal(2),  # close - entry - fees
        decimal.Decimal(30)  # 10 + 30% = 13
    )


def test_simple_sell_entry_and_buy_close(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 12, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 15, decimal.Decimal("1.5"), decimal.Decimal(10), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 12
    assert pnl.get_close_time() == 15
    assert pnl.get_total_entry_quantity() == decimal.Decimal(1)
    assert pnl.get_total_close_quantity() == decimal.Decimal("1.5")
    assert pnl.get_entry_price() == decimal.Decimal(15)
    assert pnl.get_close_price() == decimal.Decimal(10)
    assert pnl.get_closed_entry_value() == decimal.Decimal(15) * decimal.Decimal(1)
    assert pnl.get_closed_close_value() == decimal.Decimal(10) * decimal.Decimal("1.5")
    assert pnl.get_close_ratio() == decimal.Decimal("1")
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal("1.5")
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.1") * decimal.Decimal(15)
    assert pnl.get_paid_special_fees_by_currency() == {}
    # started with 15, closed with 15, paid 2.5 in fees: end value: 12.5
    assert pnl.get_profits() == (
        decimal.Decimal(15) - decimal.Decimal(15) - decimal.Decimal("2.5"),  # close - entry - fees
        decimal.Decimal("-16.66666666666666666666666667")  # 15 - 16.67% = 12.5
    )


def test_simple_sell_entry_and_buy_close_with_more_funds(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 12, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 15, decimal.Decimal(2), decimal.Decimal(10), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 12
    assert pnl.get_close_time() == 15
    assert pnl.get_total_entry_quantity() == decimal.Decimal(1)
    assert pnl.get_total_close_quantity() == decimal.Decimal(2)
    assert pnl.get_entry_price() == decimal.Decimal(15)
    assert pnl.get_close_price() == decimal.Decimal(10)
    assert pnl.get_closed_entry_value() == decimal.Decimal(15) * decimal.Decimal(1)
    # use "1.5" as closed quantity for value and PNL as only 1.5 come from this entry
    assert pnl.get_closed_close_value() == decimal.Decimal(10) * decimal.Decimal("1.5")
    assert pnl.get_close_ratio() == decimal.Decimal("1")
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal("1.5")
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.1") * decimal.Decimal(15)
    assert pnl.get_paid_special_fees_by_currency() == {}
    # started with 15, closed with 20 (-5 to align with entry), paid 2.5 in fees: end value: 12.5
    assert pnl.get_profits() == (
        decimal.Decimal(15) - decimal.Decimal(15) - decimal.Decimal("2.5"),  # close - entry - fees
        decimal.Decimal("-16.66666666666666666666666667")  # 15 - 16.67% = 12.5
    )


def test_simple_sell_entry_and_buy_close_with_less_funds(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 12, decimal.Decimal(1), decimal.Decimal(15), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 15, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 12
    assert pnl.get_close_time() == 15
    assert pnl.get_total_entry_quantity() == decimal.Decimal(1)
    assert pnl.get_total_close_quantity() == decimal.Decimal(1)
    assert pnl.get_entry_price() == decimal.Decimal(15)
    assert pnl.get_close_price() == decimal.Decimal(10)
    assert pnl.get_closed_entry_value() == decimal.Decimal(15) * decimal.Decimal(1)
    assert pnl.get_closed_close_value() == decimal.Decimal(10) * decimal.Decimal(1)
    assert pnl.get_close_ratio() == decimal.Decimal("0.6666666666666666666666666667")
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal(1)
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.1") * decimal.Decimal(15)
    # started with 15(-5 because of close cost), closed with 10, paid 2.5 in fees: end value: 7.5
    assert pnl.get_profits() == (
        decimal.Decimal(10) - decimal.Decimal(10) - decimal.Decimal("2.5"),  # close - entry - fees
        decimal.Decimal("-25")  # 10 - 25% = 12.5
    )


def test_simple_entry_and_double_close(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal("0.4"), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 0.5)),
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 16, decimal.Decimal(1), decimal.Decimal(16), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 12
    assert pnl.get_close_time() == 16
    assert pnl.get_total_entry_quantity() == decimal.Decimal(1)
    assert pnl.get_total_close_quantity() == decimal.Decimal("1.4")
    assert pnl.get_entry_price() == decimal.Decimal(10)
    assert pnl.get_close_price() == decimal.Decimal("15.5")
    assert pnl.get_closed_entry_value() == decimal.Decimal(10) * decimal.Decimal(1)  # 1 as entry is 1
    assert pnl.get_closed_close_value() == decimal.Decimal("15.5") * decimal.Decimal(1)  # 1 as entry is 1
    assert pnl.get_close_ratio() == decimal.Decimal(1)
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal(1)  # 1 as entry is 1
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.5") + \
           decimal.Decimal("0.1") * decimal.Decimal(10)
    # started with 10, closed with 15.5, paid 2.5 in fees: end value: 13
    assert pnl.get_profits() == (
        decimal.Decimal(15) - decimal.Decimal(10) - decimal.Decimal(2),  # close - entry - fees
        decimal.Decimal(30)  # 10 + 30% = 13
    )


def test_double_simple_entry_and_double_close(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BTC", 0.1)),
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 9, decimal.Decimal("0.5"), decimal.Decimal(9), SYMBOL, _get_fees("BTC", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal("0.4"), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 0.5)),
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 16, decimal.Decimal(1), decimal.Decimal(16), SYMBOL, _get_fees("USDT", 1)),
    ])
    assert pnl.get_entry_time() == 9
    assert pnl.get_close_time() == 16
    assert pnl.get_total_entry_quantity() == decimal.Decimal("1.5")
    assert pnl.get_total_close_quantity() == decimal.Decimal("1.4")
    assert pnl.get_entry_price() == decimal.Decimal("9.5")
    assert pnl.get_close_price() == decimal.Decimal("15.5")
    assert pnl.get_closed_entry_value() == decimal.Decimal("9.5") * decimal.Decimal("1.5")
    assert pnl.get_closed_close_value() == decimal.Decimal("15.5") * decimal.Decimal("1.4")  # 1.4 as close is 1.4
    assert pnl.get_close_ratio() == decimal.Decimal("1.4") / decimal.Decimal("1.5")
    assert pnl.get_closed_pnl_quantity() == decimal.Decimal("1.4")  # 1.4 as close is 1.4
    assert pnl.get_paid_regular_fees_in_quote() == decimal.Decimal(1) + decimal.Decimal("0.5") + \
           decimal.Decimal("0.1") * decimal.Decimal(10) + decimal.Decimal("0.1") * decimal.Decimal(9)
    assert pnl.get_paid_special_fees_by_currency() == {}
    # started with 1.4*9.5=13.3, closed with 1.4*15.5=21.7, paid 3.4 in fees: end value: 5.1
    assert pnl.get_profits() == (
        decimal.Decimal("5"),
        decimal.Decimal("37.5939849624060150375939850")
    )


def test_get_paid_special_fees_by_currency(simulated_trader):
    _, _, trader = simulated_trader
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BNB", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal("0.4"), decimal.Decimal(15), SYMBOL, _get_fees("USDT", 0.5)),
    ])
    assert pnl.get_paid_special_fees_by_currency() == {"BNB": decimal.Decimal(str(0.1))}
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BNB", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal("0.4"), decimal.Decimal(15), SYMBOL, _get_fees("PLOP", 0.5)),
    ])
    assert pnl.get_paid_special_fees_by_currency() == {"BNB": decimal.Decimal(str(0.1)), "PLOP": decimal.Decimal(str(0.5))}
    pnl = personal_data.TradePnl([
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("BNB", 0.1)),
        create_executed_trade(trader, enums.TradeOrderSide.BUY, 12, decimal.Decimal(1), decimal.Decimal(10), SYMBOL, _get_fees("PLOP", 0.1)),
    ], [
        create_executed_trade(trader, enums.TradeOrderSide.SELL, 15, decimal.Decimal("0.4"), decimal.Decimal(15), SYMBOL, _get_fees("PLOP", 0.5)),
    ])
    assert pnl.get_paid_special_fees_by_currency() == {"BNB": decimal.Decimal(str(0.1)), "PLOP": decimal.Decimal(str(0.6))}


def _get_fees(currency, value):
    return {
        enums.FeePropertyColumns.CURRENCY.value: currency,
        enums.FeePropertyColumns.COST.value: decimal.Decimal(str(value))
    }
