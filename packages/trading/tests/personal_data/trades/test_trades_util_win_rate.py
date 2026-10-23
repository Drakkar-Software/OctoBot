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

import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests.personal_data.trades import create_executed_trade
from tests import event_loop

pytestmark = pytest.mark.asyncio

SYMBOL = "BTC/USDT"


def _add_filled_trades(exchange_manager, trader, trades):
    trades_manager = exchange_manager.exchange_personal_data.trades_manager
    for index, (side, price, quantity, order_type) in enumerate(trades):
        trade = create_executed_trade(
            trader, side, 1_700_000_000 + index, decimal.Decimal(str(quantity)), decimal.Decimal(str(price)),
            SYMBOL, None
        )
        trade.status = enums.OrderStatus.FILLED
        trade.exchange_trade_type = order_type
        trades_manager.trades[str(index)] = trade


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot"], indirect=True)
async def test_compute_win_rate_spot_losing_market_sell_is_a_loss(backtesting_trader):
    _, exchange_manager, trader = backtesting_trader
    _add_filled_trades(exchange_manager, trader, [
        (enums.TradeOrderSide.BUY, 100, 1, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.SELL, 70, 1, enums.TradeOrderType.MARKET),
    ])
    assert personal_data.compute_win_rate(exchange_manager) == decimal.Decimal(0)


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot"], indirect=True)
async def test_compute_win_rate_spot_uses_average_entry_price(backtesting_trader):
    _, exchange_manager, trader = backtesting_trader
    _add_filled_trades(exchange_manager, trader, [
        # average entry price: 110
        (enums.TradeOrderSide.BUY, 100, 1, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.BUY, 120, 1, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.SELL, 105, 1, enums.TradeOrderType.LIMIT),  # loss
        (enums.TradeOrderSide.SELL, 115, 1, enums.TradeOrderType.LIMIT),  # win
        # new entry at 50, stop loss sold above it (trailing stop in profit)
        (enums.TradeOrderSide.BUY, 50, 2, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.SELL, 55, 2, enums.TradeOrderType.STOP_LOSS),  # win
        # new entry at 50, limit sold below it
        (enums.TradeOrderSide.BUY, 50, 1, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.SELL, 45, 1, enums.TradeOrderType.LIMIT),  # loss
    ])
    assert personal_data.compute_win_rate(exchange_manager) == decimal.Decimal("0.5")


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot"], indirect=True)
async def test_compute_win_rate_spot_sell_without_known_entry(backtesting_trader):
    _, exchange_manager, trader = backtesting_trader
    # selling funds held before the run: no entry price, classified by order type
    _add_filled_trades(exchange_manager, trader, [
        (enums.TradeOrderSide.SELL, 100, 1, enums.TradeOrderType.LIMIT),
        (enums.TradeOrderSide.SELL, 90, 1, enums.TradeOrderType.STOP_LOSS),
    ])
    assert personal_data.compute_win_rate(exchange_manager) == decimal.Decimal("0.5")
