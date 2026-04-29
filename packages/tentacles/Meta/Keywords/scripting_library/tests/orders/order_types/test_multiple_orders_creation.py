#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import pytest
import mock
import decimal
import contextlib
import os

import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.api as api
import octobot_trading.errors as errors
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import tentacles.Meta.Keywords.scripting_library as scripting_library


from tentacles.Meta.Keywords.scripting_library.tests import event_loop, mock_context, \
    skip_if_octobot_trading_mocking_disabled
from tentacles.Meta.Keywords.scripting_library.tests.exchanges import backtesting_trader, backtesting_config, \
    backtesting_exchange_manager, fake_backtesting
import tentacles.Meta.Keywords.scripting_library.tests.test_utils.order_util as test_order_util


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_orders_with_invalid_values(mock_context, skip_if_octobot_trading_mocking_disabled):
    # skip_if_octobot_trading_mocking_disabled mock_context.trader, "create_order"
    initial_usdt_holdings, btc_price = await _usdt_trading_context(mock_context)

    if os.getenv('CYTHON_IGNORE'):
        return
    with mock.patch.object(trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)), \
         mock.patch.object(order_util, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)), \
         mock.patch.object(mock_context.trader, "create_order", mock.AsyncMock()) as create_order_mock:

        with pytest.raises(errors.InvalidArgumentError):
            # no amount
            await scripting_library.market(
                mock_context,
                side="buy"
            )
            create_order_mock.assert_not_called()
            create_order_mock.reset_mock()

        with pytest.raises(errors.InvalidArgumentError):
            # negative amount
            await scripting_library.market(
                mock_context,
                amount="-1",
                side="buy"
            )
            create_order_mock.assert_not_called()
            create_order_mock.reset_mock()

        with pytest.raises(errors.InvalidArgumentError):
            # missing offset parameter
            await scripting_library.limit(
                mock_context,
                target_position="20%",
                side="buy"
            )

        with pytest.raises(errors.InvalidArgumentError):
            # missing side parameter
            await scripting_library.market(
                mock_context,
                amount="1"
            )

        # orders without having enough funds
        for amount, side in ((1, "sell"), (0.000000001, "buy")):
            await scripting_library.market(
                mock_context,
                amount=amount,
                side=side
            )
            create_order_mock.assert_not_called()
            create_order_mock.reset_mock()
            mock_context.orders_writer.log_many.assert_not_called()
            mock_context.orders_writer.log_many.reset_mock()
            mock_context.logger.warning.assert_called_once()
            mock_context.logger.warning.reset_mock()


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_orders_amount_then_position_sequence(mock_context):
    initial_usdt_holdings, btc_price = await _usdt_trading_context(mock_context)
    mock_context.exchange_manager.is_future = True
    symbol_contract = api.create_default_future_contract(
            "BTC/USDT", decimal.Decimal(1), trading_enums.FutureContractType.LINEAR_PERPETUAL,
            trading_constants.DEFAULT_SYMBOL_POSITION_MODE
        )
        # We have to hardcode the symbol contract as it's not a futures symbol so we can't use load_pair_contract
    mock_context.exchange_manager.exchange.pair_contracts[mock_context.symbol] = symbol_contract

    if os.getenv('CYTHON_IGNORE'):
        return
    with mock.patch.object(trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)), \
         mock.patch.object(order_util, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)):

        # buy for 10% of the total portfolio value
        orders = await scripting_library.market(
            mock_context,
            amount="10%",
            side="buy"
        )
        btc_val = decimal.Decimal(10)   # 10.00
        usdt_val = decimal.Decimal(45000)   # 45000.00
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

        # buy for 10% of the portfolio available value
        orders = await scripting_library.limit(
            mock_context,
            amount="10%a",
            offset="0",
            side="buy"
        )
        btc_val = btc_val + decimal.Decimal(str((45000 * decimal.Decimal("0.1")) / 500))    # 19.0
        usdt_val = usdt_val * decimal.Decimal(str(0.9))     # 40500.00
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

        # buy for for 10% of the current position value
        orders = await scripting_library.market(
            mock_context,
            amount="10%p",
            side="buy"
        )
        usdt_val = usdt_val - (btc_val * decimal.Decimal("0.1") * btc_price)   # 39550.00
        btc_val = btc_val * decimal.Decimal("1.1")   # 20.90
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

    # price changes to 1000
    btc_price = 1000
    mock_context.exchange_manager.exchange_personal_data.portfolio_manager.handle_mark_price_update(
        "BTC/USDT", btc_price)
    with mock.patch.object(trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)), \
         mock.patch.object(order_util, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)):

        # buy to reach a target position of 25 btc
        orders = await scripting_library.market(
            mock_context,
            target_position=25
        )
        usdt_val = usdt_val - ((25 - btc_val) * btc_price)   # 35450.00
        btc_val = decimal.Decimal(25)   # 25
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

        # buy to reach a target position of 60% of the total portfolio (in BTC)
        orders = await scripting_library.limit(
            mock_context,
            target_position="60%",
            offset=0
        )
        previous_btc_val = btc_val
        btc_val = (btc_val + (usdt_val / btc_price)) * decimal.Decimal("0.6")   # 36.27
        usdt_val = usdt_val - (btc_val - previous_btc_val) * btc_price   # 24180.00
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

        # buy to reach a target position including an additional 50% of the available USDT in BTC
        orders = await scripting_library.market(
            mock_context,
            target_position="50%a"
        )
        btc_val = btc_val + usdt_val / 2 / btc_price   # 48.36
        usdt_val = usdt_val / 2   # 12090.00
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)

        # sell to keep only 10% of the position, sell at 2000 (1000 + 100%)
        orders = await scripting_library.limit(
            mock_context,
            target_position="10%p",
            offset="100%"
        )
        usdt_val = usdt_val + btc_val * decimal.Decimal("0.9") * (btc_price * 2)  # 99138.00
        btc_val = btc_val / 10   # 4.836
        await _fill_and_check(mock_context, btc_val, usdt_val, orders)


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_concurrent_orders(mock_context):
    async with _20_percent_position_trading_context(mock_context) as context_data:
        btc_val, usdt_val, btc_price = context_data

        # create 3 sell orders (at price = 500 + 10 = 510)
        # that would end up selling more than what we have if not executed sequentially
        # 1st order is 80% of available btc, second is 80% of the remaining 20% and so on

        orders = []
        async def create_order(amount):
            orders.append(
                (await scripting_library.limit(
                    mock_context,
                    amount=amount,
                    offset=10,
                    side="sell"
                ))[0]
            )
        await asyncio.gather(
            *(
                create_order("80%a")
                for _ in range(3)
            )
        )

        initial_btc_holdings = btc_val
        btc_val = initial_btc_holdings * (decimal.Decimal("0.2") ** 3)
        usdt_val = usdt_val + (initial_btc_holdings - btc_val) * (btc_price + 10)   # 50118.40
        await _fill_and_check(mock_context, btc_val, usdt_val, orders, orders_count=3)

        # create 3 buy orders (at price = 500 + 10 = 510) all of them for a target position of 10%
        # first order gets created to have this 10% position, others are also created like this, ending up in a 30%
        # position

        # update portfolio current value
        mock_context.exchange_manager.exchange_personal_data.portfolio_manager.handle_balance_updated()

        orders = []

        async def create_order(target_position):
            orders.append(
                (await scripting_library.limit(
                    mock_context,
                    target_position=target_position,
                    offset=10
                ))[0]
            )
        await asyncio.gather(
            *(
                create_order("10%")
                for _ in range(3)
            )
        )

        initial_btc_holdings = btc_val  # 0.16
        initial_total_val = initial_btc_holdings * btc_price + usdt_val
        initial_position_percent = decimal.Decimal(initial_btc_holdings * btc_price / initial_total_val)
        btc_val = initial_btc_holdings + \
                  initial_total_val * (decimal.Decimal("0.1") - initial_position_percent) * 3 / btc_price    # 29.79904
        usdt_val = usdt_val - (btc_val - initial_btc_holdings) * (btc_price + 10)   # 35002.4896
        await _fill_and_check(mock_context, btc_val, usdt_val, orders, orders_count=3)


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_sell_limit_with_stop_loss_orders_single_sell_and_stop_with_oco_group(mock_context):
    async with _20_percent_position_trading_context(mock_context) as context_data:
        btc_val, usdt_val, btc_price = context_data

        mock_context.allow_artificial_orders = True  # make stop loss not lock funds
        oco_group = scripting_library.create_one_cancels_the_other_group(mock_context)
        sell_limit_orders = await scripting_library.limit(
            mock_context,
            target_position="0%",
            offset=50,
            group=oco_group
        )
        # add_to_order_group(oco_group, sell_limit_orders)
        stop_loss_orders = await scripting_library.stop_loss(
            mock_context,
            target_position="0%",
            offset=-75,
            group=oco_group
        )
        assert len(sell_limit_orders) == len(stop_loss_orders) == 1

        # stop order is filled
        usdt_val = usdt_val + btc_val * (btc_price - 75)   # 48500.00
        btc_val = trading_constants.ZERO    # 0.00
        await _fill_and_check(mock_context, btc_val, usdt_val, stop_loss_orders, logged_orders_count=2)
        # linked order is cancelled
        assert sell_limit_orders[0].is_cancelled()


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_sell_limit_with_stop_loss_orders_two_sells_and_stop_with_oco(mock_context):
    async with _20_percent_position_trading_context(mock_context) as context_data:
        btc_val, usdt_val, btc_price = context_data

        mock_context.allow_artificial_orders = True  # make stop loss not lock funds
        oco_group = scripting_library.create_one_cancels_the_other_group(mock_context)
        stop_loss_orders = await scripting_library.stop_loss(
            mock_context,
            target_position="0%",
            offset=-50,
            side="sell",
            group=oco_group,
            tag="exitPosition"
        )
        take_profit_limit_orders_1 = await scripting_library.limit(
            mock_context,
            target_position="50%p",
            offset=50
        )
        take_profit_limit_orders_2 = await scripting_library.limit(
            mock_context,
            target_position="0%p",
            offset=100,
            group=oco_group,
            tag="exitPosition"
        )

        # take_profit_limit_orders_1 filled
        available_btc_val = trading_constants.ZERO  # 10.00
        total_btc_val = btc_val / 2  # 10.00
        usdt_val = usdt_val + btc_val / 2 * (btc_price + 50)   # 40000.00
        await _fill_and_check(mock_context, available_btc_val, usdt_val, take_profit_limit_orders_1,
                              btc_total=total_btc_val)
        # linked order is not cancelled
        assert stop_loss_orders[0].is_open()

        # take_profit_limit_orders_2 filled
        usdt_val = usdt_val + btc_val / 2 * (btc_price + 100)   # 40000.00
        btc_val = trading_constants.ZERO  # 0.00
        await _fill_and_check(mock_context, btc_val, usdt_val, take_profit_limit_orders_2)
        # linked order is cancelled
        assert stop_loss_orders[0].is_cancelled()


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_sell_limit_with_multiple_stop_loss_and_sell_orders_in_balanced_take_profit_and_stop_group(mock_context):
    async with _20_percent_position_trading_context(mock_context) as context_data:
        btc_val, usdt_val, btc_price = context_data

        mock_context.allow_artificial_orders = True  # make stop loss not lock funds
        btsl_group_1 = scripting_library.create_balanced_take_profit_and_stop_group(mock_context)
        g1_stop_1 = await scripting_library.stop_loss(
            mock_context, amount="2", offset=-50, side="sell", group=btsl_group_1, tag="exitPosition1"
        )
        g1_stop_2 = await scripting_library.stop_loss(
            mock_context, amount="3", offset=-100, side="sell", group=btsl_group_1, tag="exitPosition1"
        )
        g1_stop_3 = await scripting_library.stop_loss(
            mock_context, amount="4", offset=-150, side="sell", group=btsl_group_1, tag="exitPosition1"
        )
        g1_tp_1 = await scripting_library.limit(
            mock_context, amount="4", offset=50, side="sell", group=btsl_group_1, tag="exitPosition1"
        )
        g1_tp_2 = await scripting_library.limit(
            mock_context, amount="5", offset=100, side="sell", group=btsl_group_1, tag="exitPosition1"
        )

        btsl_group_2 = scripting_library.create_balanced_take_profit_and_stop_group(mock_context)
        g2_stop_1 = await scripting_library.stop_loss(
            mock_context, amount="5", offset=-50, side="sell", group=btsl_group_2, tag="exitPosition1"
        )
        g2_tp_1 = await scripting_library.limit(
            mock_context, amount="3", offset=50, side="sell", group=btsl_group_2, tag="exitPosition1"
        )
        g2_tp_2 = await scripting_library.limit(
            mock_context, amount="2", offset=100, side="sell", group=btsl_group_2, tag="exitPosition1"
        )

        # g1_tp_1 filled
        available_btc_val = decimal.Decimal(6)
        sold_btc = decimal.Decimal(4)
        total_btc_val = btc_val - sold_btc
        usdt_val = usdt_val + sold_btc * (btc_price + 50)
        await _fill_and_check(mock_context, available_btc_val, usdt_val, g1_tp_1, btc_total=total_btc_val)
        # g1_stop_3 is cancelled (same size), other are untouched
        assert g1_stop_3[0].is_cancelled()
        assert all(o[0].is_open() for o in [g1_stop_1, g1_stop_2, g1_tp_2, g2_stop_1, g2_tp_1, g2_tp_2])

        # g1_stop_1 filled
        sold_btc = decimal.Decimal(2)
        total_btc_val = total_btc_val - sold_btc
        usdt_val = usdt_val + sold_btc * (btc_price - 50)
        await _fill_and_check(mock_context, available_btc_val, usdt_val, g1_stop_1, btc_total=total_btc_val)
        # g1_tp_1 is edited (reduced size), other are untouched
        assert g1_tp_2[0].origin_quantity == decimal.Decimal(3)  # 5 - 2
        assert all(o[0].is_open() for o in [g1_stop_2, g1_tp_2, g2_stop_1, g2_tp_1, g2_tp_2])

        # g2_stop_1 filled
        sold_btc = decimal.Decimal(5)
        total_btc_val = total_btc_val - sold_btc
        usdt_val = usdt_val + sold_btc * (btc_price - 50)
        await _fill_and_check(mock_context, available_btc_val, usdt_val, g2_stop_1, btc_total=total_btc_val)
        # g1_tp_1 is edited (reduced size), other are untouched
        assert all(o[0].is_cancelled() for o in [g2_tp_1, g2_tp_2])
        assert all(o[0].is_open() for o in [g1_stop_2, g1_tp_2])

        # g1_stop_2 cancelled
        await mock_context.trader.cancel_order(g1_stop_2[0])
        # g1_tp_2 is cancelled as well
        assert all(o[0].is_cancelled() for o in [g1_stop_2, g1_tp_2])
        assert scripting_library.get_open_orders(mock_context) == []


@pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=["backtesting_config"])
async def test_multiple_sell_limit_with_stop_loss_rounding_issues_in_balanced_take_profit_and_stop_group(mock_context):
    async with _20_percent_position_trading_context(mock_context) as context_data:
        btc_val, usdt_val, btc_price = context_data

        mock_context.allow_artificial_orders = True  # make stop loss not lock funds
        btsl_group_1 = scripting_library.create_balanced_take_profit_and_stop_group(mock_context)
        # disable to create orders
        await btsl_group_1.enable(False)
        position_size = decimal.Decimal(20)
        added_amount = decimal.Decimal("0.00100001111")

        market_1 = await scripting_library.market(mock_context, amount=added_amount, side="buy")
        assert market_1[0].is_filled()
        amount = position_size + decimal.Decimal("0.00100001")  # ending "111" got truncated
        assert api.get_portfolio_currency(mock_context.exchange_manager, "BTC").total == amount
        assert api.get_portfolio_currency(mock_context.exchange_manager, "BTC").available == amount

        g1_stop_1 = await scripting_library.stop_loss(
            mock_context, amount=amount, offset=-50, side="sell", group=btsl_group_1, tag="exitPosition1"
        )
        g1_tp_1 = await scripting_library.limit(
            mock_context, amount=amount * decimal.Decimal("0.5"), offset=50, side="sell", group=btsl_group_1,
            reduce_only=True
        )
        g1_tp_2 = await scripting_library.limit(
            mock_context, amount=amount * decimal.Decimal("0.5"), offset=100, side="sell", group=btsl_group_1,
            reduce_only=True
        )

        assert g1_stop_1[0].origin_quantity == amount
        assert g1_tp_1[0].origin_quantity == decimal.Decimal('10.00050001')
        assert g1_tp_2[0].origin_quantity == decimal.Decimal('10.00050000')

        # enable order group: no order edit is triggered as scripting_library took care of the rounding issue of
        # 20.00100001 / 2
        await btsl_group_1.enable(False)

        assert g1_stop_1[0].origin_quantity == amount
        assert g1_tp_1[0].origin_quantity == decimal.Decimal('10.00050001')
        assert g1_tp_2[0].origin_quantity == decimal.Decimal('10.00050000')


async def _usdt_trading_context(mock_context):
    initial_usdt_holdings = 50000
    mock_context.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal(0), 'total': decimal.Decimal(0)},
        'ETH': {'available': decimal.Decimal(0), 'total': decimal.Decimal(0)},
        'USDT': {'available': decimal.Decimal(str(initial_usdt_holdings)),
                 'total': decimal.Decimal(str(initial_usdt_holdings))}
    }, mock_context.exchange_manager)
    mock_context.exchange_manager.exchange_personal_data.portfolio_manager.handle_balance_updated()
    btc_price = 500
    mock_context.exchange_manager.exchange_personal_data.portfolio_manager.handle_mark_price_update(
        "BTC/USDT", btc_price)
    return initial_usdt_holdings, btc_price


@contextlib.asynccontextmanager
async def _20_percent_position_trading_context(mock_context):
    initial_usdt_holdings, btc_price = await _usdt_trading_context(mock_context)
    usdt_val = decimal.Decimal(str(initial_usdt_holdings))
    with mock.patch.object(trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)), \
            mock.patch.object(order_util, "get_up_to_date_price", mock.AsyncMock(return_value=btc_price)):
        # initial limit buy order: buy with 20% of portfolio
        buy_limit_orders = await scripting_library.limit(
            mock_context,
            target_position="20%",
            offset=0,
            side="buy"
        )
        btc_val = (usdt_val * decimal.Decimal("0.2")) / btc_price  # 20.00
        usdt_val = usdt_val * decimal.Decimal("0.8")  # 40000.00
        # position size = 20 BTC
        await _fill_and_check(mock_context, btc_val, usdt_val, buy_limit_orders)
        yield btc_val, usdt_val, btc_price


async def _fill_and_check(mock_context, btc_available, usdt_available, orders,
                          btc_total=None, usdt_total=None, orders_count=1, logged_orders_count=None):
    for order in orders:
        if isinstance(order, trading_personal_data.LimitOrder):
            await test_order_util.fill_limit_or_stop_order(order)
        elif isinstance(order, trading_personal_data.MarketOrder):
            await test_order_util.fill_market_order(order)

    _ensure_orders_validity(mock_context, btc_available, usdt_available, orders,
                            btc_total=btc_total, usdt_total=usdt_total, orders_count=orders_count,
                            logged_orders_count=logged_orders_count)


def _ensure_orders_validity(mock_context, btc_available, usdt_available, orders,
                            btc_total=None, usdt_total=None, orders_count=1, logged_orders_count=None):
    exchange_manager = mock_context.exchange_manager
    btc_total = btc_total or btc_available
    usdt_total = usdt_total or usdt_available
    assert len(orders) == orders_count
    assert all(isinstance(order, trading_personal_data.Order) for order in orders)
    assert mock_context.orders_writer.log_many.call_count == logged_orders_count or orders_count
    mock_context.orders_writer.log_many.reset_mock()
    mock_context.logger.warning.assert_not_called()
    mock_context.logger.warning.reset_mock()
    mock_context.logger.exception.assert_not_called()
    mock_context.logger.exception.reset_mock()
    assert api.get_portfolio_currency(exchange_manager, "BTC").available == btc_available
    assert api.get_portfolio_currency(exchange_manager, "BTC").total == btc_total
    assert api.get_portfolio_currency(exchange_manager, "USDT").available == usdt_available
    assert api.get_portfolio_currency(exchange_manager, "USDT").total == usdt_total
