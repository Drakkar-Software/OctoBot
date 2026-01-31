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
import os

import pytest
import octobot_trading.constants as constants
import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.errors as errors

from tests import event_loop
from tests.exchanges import future_simulated_exchange_manager, set_future_exchange_fees
from tests.personal_data import check_created_transaction, get_latest_transaction
from tests.exchanges.traders import future_trader_simulator_with_default_inverse, \
    future_trader_simulator_with_default_linear, DEFAULT_FUTURE_SYMBOL, DEFAULT_FUTURE_FUNDING_RATE
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_constructor(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    with pytest.raises(errors.InvalidPosition):
        personal_data.InversePosition(trader_inst, default_contract)


async def test_update_value(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
    position_inst.update_value()
    assert position_inst.value == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED)
    position_inst.update_value()
    assert position_inst.value == constants.ZERO
    await position_inst.update(mark_price=constants.ONE_HUNDRED)
    position_inst.update_value()
    assert position_inst.value == constants.ONE


async def test_update_pnl_with_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED,
                               mark_price=decimal.Decimal(2) * constants.ONE_HUNDRED)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ONE


async def test_update_pnl_with_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse

    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    await position_inst.update(update_size=-constants.ONE_HUNDRED,
                               mark_price=constants.ONE_HUNDRED / decimal.Decimal(10))
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == decimal.Decimal("18.00")


async def test_update_pnl_with_loss_with_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse

    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED,
                               mark_price=constants.ONE_HUNDRED * decimal.Decimal(0.8666))
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == decimal.Decimal("-0.3078698361412415355738660840")


async def test_update_pnl_with_loss_with_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse

    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    await position_inst.update(update_size=-constants.ONE_HUNDRED,
                               mark_price=constants.ONE_HUNDRED * decimal.Decimal(10.0566477))
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == decimal.Decimal("-1.801126572227443130874085649")


async def test_update_initial_margin(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    if not os.getenv('CYTHON_IGNORE'):
        await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == constants.ZERO
        await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == constants.ONE
        default_contract.set_current_leverage(constants.ONE_HUNDRED)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == decimal.Decimal("0.01")


async def test_get_margin_from_size(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_margin_from_size(constants.ONE) == decimal.Decimal('0.01')
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_margin_from_size(constants.ONE) == decimal.Decimal('0.0001')
    default_contract.set_current_leverage(constants.ONE)
    assert position_inst.get_margin_from_size(decimal.Decimal('0.01')) == decimal.Decimal('0.0001')
    assert position_inst.get_margin_from_size(decimal.Decimal('0.1')) == decimal.Decimal('0.001')
    assert position_inst.get_margin_from_size(decimal.Decimal('1')) == decimal.Decimal('0.01')


async def test_get_size_from_margin(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_size_from_margin(constants.ONE) == decimal.Decimal('100')
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_size_from_margin(constants.ONE) == decimal.Decimal('10000')
    default_contract.set_current_leverage(constants.ONE)
    assert position_inst.get_size_from_margin(decimal.Decimal('0.01')) == constants.ONE
    assert position_inst.get_size_from_margin(decimal.Decimal('0.1')) == decimal.Decimal('10')
    assert position_inst.get_size_from_margin(decimal.Decimal('1')) == decimal.Decimal('100')


async def test_calculate_maintenance_margin(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
    assert position_inst.calculate_maintenance_margin() == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.calculate_maintenance_margin() == decimal.Decimal('0.01')
    exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_FUTURE_SYMBOL).funding_manager.funding_rate = decimal.Decimal(DEFAULT_FUTURE_FUNDING_RATE)
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.calculate_maintenance_margin() == decimal.Decimal("0.02")


async def test_update_isolated_liquidation_price_with_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_FUTURE_SYMBOL).funding_manager.funding_rate = decimal.Decimal(DEFAULT_FUTURE_FUNDING_RATE)
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("50.25125628140703517587939698")
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    await position_inst.update(update_size=constants.ONE_HUNDRED,
                               mark_price=decimal.Decimal(2) * constants.ONE_HUNDRED)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("1E+2")


async def test_update_isolated_liquidation_price_with_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_FUTURE_SYMBOL).funding_manager.funding_rate = decimal.Decimal(DEFAULT_FUTURE_FUNDING_RATE)
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("1.00E+4")
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    await position_inst.update(update_size=-constants.ONE_HUNDRED,
                               mark_price=constants.ONE_HUNDRED / decimal.Decimal(10))
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("1E+2")


async def test_get_bankruptcy_price_with_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal(50)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == decimal.Decimal(50)
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal("99.00990099009900990099009901")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == decimal.Decimal('99.00990099009900990099009901')
    await position_inst.update(update_size=constants.ONE_HUNDRED,
                               mark_price=decimal.Decimal(2) * constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal("99.00990099009900990099009901")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == decimal.Decimal("198.0198019801980198019801980")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("200"), position_inst.side) == decimal.Decimal("198.0198019801980198019801980")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("200"), enums.PositionSide.SHORT) \
        == decimal.Decimal("202.0202020202020202020202020")


async def test_get_bankruptcy_price_with_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == constants.ZERO
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == constants.ZERO
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal("101.0101010101010101010101010")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == decimal.Decimal("101.0101010101010101010101010")
    await position_inst.update(update_size=constants.ONE_HUNDRED,
                               mark_price=decimal.Decimal(2) * constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == constants.ZERO
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == constants.ZERO
    default_contract.set_current_leverage(decimal.Decimal("7"))
    position_inst.entry_price = constants.ONE_HUNDRED
    await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(decimal.Decimal("20"), position_inst.side, with_mark_price=True) == \
           decimal.Decimal("116.6666666666666666666666667")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), position_inst.side) == \
           decimal.Decimal("116.6666666666666666666666667")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), enums.PositionSide.LONG) \
        == decimal.Decimal("87.5")


async def test_get_order_cost(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_order_cost() == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_order_cost() == decimal.Decimal("1.0012")


async def test_get_fee_to_open(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_fee_to_open(position_inst.size, position_inst.entry_price, position_inst.symbol) == \
           constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    assert position_inst.get_fee_to_open(position_inst.size, position_inst.entry_price, position_inst.symbol) == \
           decimal.Decimal("0.0004")
    assert position_inst.get_fee_to_open(decimal.Decimal(50), position_inst.entry_price, position_inst.symbol) == \
           decimal.Decimal("0.0002")
    assert position_inst.get_fee_to_open(position_inst.size, decimal.Decimal(150), position_inst.symbol) == \
           decimal.Decimal("0.0002666666666666666666666666667")
    assert position_inst.get_fee_to_open(decimal.Decimal(50), decimal.Decimal(150), position_inst.symbol) == \
           decimal.Decimal("0.0001333333333333333333333333333")


async def test_update_fee_to_close(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ONE_HUNDRED)
    position_inst.update_fee_to_close()
    assert position_inst.fee_to_close == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=constants.ONE_HUNDRED)
    position_inst.update_fee_to_close()
    assert position_inst.fee_to_close == decimal.Decimal("0.0008")


async def test_get_two_way_taker_fee_for_quantity_and_price(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    leverage = decimal.Decimal("2")
    default_contract.set_current_leverage(leverage)
    assert personal_data.InversePosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("400") * leverage, decimal.Decimal("37025.5"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.00002160673049654967522383222374")  # open fees + closing fees in case of liquidation

    assert personal_data.InversePosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, constants.ONE_HUNDRED, enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.0002")     # open fees + closing fees in case of liquidation

    leverage = decimal.Decimal("50")
    default_contract.set_current_leverage(leverage)
    assert personal_data.InversePosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.00404")     # open fees + closing fees in case of liquidation

    leverage = decimal.Decimal(constants.ONE_HUNDRED)
    default_contract.set_current_leverage(leverage)
    assert personal_data.InversePosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.00804")     # open fees + closing fees in case of liquidation

    assert personal_data.InversePosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.007960")     # open fees + closing fees in case of liquidation


async def test_update_average_entry_price_increased_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=decimal.Decimal(10), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("13.33333333333333333333333333")
    position_inst.update_average_entry_price(decimal.Decimal(100), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("19.13043478260869565217391304")
    position_inst.update_average_entry_price(decimal.Decimal(2), decimal.Decimal(500))
    assert position_inst.entry_price == decimal.Decimal("22.78218847083189506385916465")


async def test_update_average_entry_price_increased_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=-decimal.Decimal(10), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(-decimal.Decimal(10), decimal.Decimal(5))
    assert position_inst.entry_price == decimal.Decimal("6.666666666666666666666666667")
    position_inst.update_average_entry_price(-decimal.Decimal(100), decimal.Decimal(2))
    assert position_inst.entry_price == decimal.Decimal("2.135922330097087378640776699")
    position_inst.update_average_entry_price(-decimal.Decimal(2), decimal.Decimal(0.1))
    assert position_inst.entry_price == decimal.Decimal("0.4861878453038674251843327502")


async def test_update_average_entry_price_decreased_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=decimal.Decimal(100), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(-decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("9.473684210526315789473684211")
    position_inst.update_average_entry_price(-decimal.Decimal(25), decimal.Decimal(1.5))
    assert position_inst.entry_price == constants.ZERO
    position_inst.update_average_entry_price(-decimal.Decimal(2), decimal.Decimal(7000))
    assert position_inst.entry_price == constants.ZERO


async def test_update_average_entry_price_decreased_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    await position_inst.update(update_size=-decimal.Decimal(100), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("9.473684210526315789473684211")
    position_inst.update_average_entry_price(decimal.Decimal(30), decimal.Decimal('35.678'))
    assert position_inst.entry_price == decimal.Decimal("7.205574131005542714808248993")
    position_inst.update_average_entry_price(decimal.Decimal(2), decimal.Decimal("0.0000000025428"))
    assert position_inst.entry_price == constants.ZERO


async def test_update_average_exit_price_and_transactions_long(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=decimal.Decimal(10), mark_price=decimal.Decimal(10))
    # size did not reduce, exit price is not set
    assert position_inst.exit_price == constants.ZERO

    # increase position
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(5)),
                      filled_price=decimal.Decimal(str(25)))
    await position_inst.update_from_order(market_buy)

    # size did not reduce, exit price is still not set
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO
    # a new fee transaction is created
    assert isinstance(get_latest_transaction(exchange_manager_inst), personal_data.FeeTransaction)

    # decrease position
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(5)),
                       filled_price=decimal.Decimal(str(35)))
    await position_inst.update_from_order(market_sell)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("-5"), decimal.Decimal("-5"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("-5")
    # contracts sold at 35
    assert position_inst.exit_price == decimal.Decimal(str(35))

    # decrease position again
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(8)),
                       filled_price=decimal.Decimal(str(50)))
    await position_inst.update_from_order(market_sell)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("-8"), decimal.Decimal("-13"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("-13")
    # inverse position: average is average using contract value in BTC
    # 5 contracts sold at 35 and 8 at 50: average is 42.92452830188679245283018867
    assert position_inst.exit_price == decimal.Decimal("42.92452830188679245283018867")

    # increase position again
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(5)),
                      filled_price=decimal.Decimal(str(75)))
    await position_inst.update_from_order(market_buy)

    # size did not reduce, exit price is still 42.92452830188679245283018867
    assert position_inst.already_reduced_size == decimal.Decimal("-13")
    assert position_inst.exit_price == decimal.Decimal("42.92452830188679245283018867")
    # a new fee transaction is created
    assert isinstance(get_latest_transaction(exchange_manager_inst), personal_data.FeeTransaction)

    # decrease position again
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(6)),
                       filled_price=decimal.Decimal(str(80)))
    await position_inst.update_from_order(market_sell)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("-6"), decimal.Decimal("-19"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("-19")
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80: average is 50.28355387523629489603024574
    assert position_inst.exit_price == decimal.Decimal("50.28355387523629489603024574")

    # liquidate remaining 1 contract, also updates average exit price
    await position_inst.update(mark_price=decimal.Decimal("0.5"))
    check_created_transaction(exchange_manager_inst, decimal.Decimal("-1"), decimal.Decimal("-20"))

    # position is closed, exit_price and already_reduced_size are reset
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO

    # latest transaction contains the average last exit price
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80 + 1 at 0.5: average is 8.410934214478822469209972964
    # TODO => seems weird but is logical when looking at the formula => this means the lower the price, the larger
    #  its weight on the computation ?
    assert get_latest_transaction(exchange_manager_inst).average_exit_price == decimal.Decimal("8.410934214478822469209972964")


async def test_update_average_exit_price_and_transactions_short(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    position_inst = personal_data.InversePosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=-decimal.Decimal(10), mark_price=decimal.Decimal(25))
    # size did not reduce, exit price is not set
    assert position_inst.exit_price == constants.ZERO

    # increase position
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(5)),
                       filled_price=decimal.Decimal(str(25)))
    await position_inst.update_from_order(market_sell)
    # a new fee transaction is created
    assert isinstance(get_latest_transaction(exchange_manager_inst), personal_data.FeeTransaction)

    # size did not reduce, exit price is still not set
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO

    # decrease position
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(5)),
                      filled_price=decimal.Decimal(str(20)))
    await position_inst.update_from_order(market_buy)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("5"), decimal.Decimal("5"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("5")
    # contracts sold at 20
    assert position_inst.exit_price == decimal.Decimal(str(20))

    # decrease position again
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(8)),
                      filled_price=decimal.Decimal(str(18)))
    await position_inst.update_from_order(market_buy)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("8"), decimal.Decimal("13"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("13")
    # inverse position: average is average using contract value in BTC
    # 5 contracts sold at 20 and 8 at 18: average is 18.72000000000000000000000000
    assert position_inst.exit_price == decimal.Decimal("18.72000000000000000000000000")

    # increase position again
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(5)),
                       filled_price=decimal.Decimal(str(19)))
    await position_inst.update_from_order(market_sell)
    # a new fee transaction is created
    assert isinstance(get_latest_transaction(exchange_manager_inst), personal_data.FeeTransaction)

    # size did not reduce, exit price is still 18.72000000000000000000000000
    assert position_inst.already_reduced_size == decimal.Decimal("13")
    assert position_inst.exit_price == decimal.Decimal("18.72000000000000000000000000")

    # decrease position again
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(6)),
                      filled_price=decimal.Decimal(str(17)))
    await position_inst.update_from_order(market_buy)
    check_created_transaction(exchange_manager_inst, decimal.Decimal("6"), decimal.Decimal("19"))

    # size reduced, exit price is updated
    assert position_inst.already_reduced_size == decimal.Decimal("19")
    # 5 contracts sold at 20 + 8 at 18 + 6 at 17: average is 18.14040561622464898595943837
    assert position_inst.exit_price == decimal.Decimal("18.14040561622464898595943837")

    # liquidate remaining 1 contract, also updates average exit price
    await position_inst.update(mark_price=decimal.Decimal("2050"))
    check_created_transaction(exchange_manager_inst, decimal.Decimal("1"), decimal.Decimal("20"))

    # position is closed, exit_price and already_reduced_size are reset
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO

    # latest transaction contains the average last exit price
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80 + 1 at 2050: average is 19.08627464701953810180867781
    assert get_latest_transaction(exchange_manager_inst).average_exit_price == decimal.Decimal("19.08627464701953810180867781")
