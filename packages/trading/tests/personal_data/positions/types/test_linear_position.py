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
from tests.exchanges.traders import future_trader_simulator_with_default_linear, \
    future_trader_simulator_with_default_inverse, DEFAULT_FUTURE_SYMBOL, DEFAULT_FUTURE_FUNDING_RATE
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


FORTY = decimal.Decimal(40)
TWENTY_FOUR = decimal.Decimal(24)
TWENTY_FIVE = decimal.Decimal(25)
TWELVE_DOT_FIVE = decimal.Decimal('12.5')


async def test_constructor(future_trader_simulator_with_default_inverse):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_inverse
    with pytest.raises(errors.InvalidPosition):
        personal_data.LinearPosition(trader_inst, default_contract)


async def test_update_value(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    await position_inst.update(update_size=constants.ZERO)
    position_inst.update_value()
    assert position_inst.value == constants.ZERO
    await position_inst.update(update_size=constants.ONE_HUNDRED)
    position_inst.update_value()
    assert position_inst.value == constants.ZERO
    await position_inst.update(mark_price=constants.ONE_HUNDRED)
    position_inst.update_value()
    assert position_inst.value == decimal.Decimal("10000")


async def test_update_pnl_with_long_linear_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open long of 24 contracts at 40 usdt
    await position_inst.update(update_size=TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # add long of 1 contract at 80 usdt
    await position_inst.update(update_size=constants.ONE,
                               mark_price=decimal.Decimal(3) * FORTY)
    position_inst.update_pnl()
    # now have 25 contracts each now worth 120 usdt => 2000 in profit
    assert position_inst.unrealized_pnl == decimal.Decimal("2000")


async def test_update_pnl_with_short_linear_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open short of 24 contracts at 40 usdt
    await position_inst.update(update_size=-TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # add short of 1 contract at 4 usdt
    await position_inst.update(update_size=-constants.ONE,
                               mark_price=FORTY / decimal.Decimal(10))
    position_inst.update_pnl()
    # now have 25 contracts each now worth 36 usdt (40 entry - 4 now) => 25 * 36 = 900 in profit
    assert position_inst.unrealized_pnl == decimal.Decimal("900")


async def test_update_pnl_with_loss_with_long_linear_position_inc_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open long of 24 contracts at 40 usdt
    await position_inst.update(update_size=TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # add long of 1 contract at 40 / 2.535485
    await position_inst.update(update_size=constants.ONE,
                               mark_price=FORTY / decimal.Decimal("2.535485"))
    position_inst.update_pnl()
    # now have 25 contracts each now worth 15.7760744 (40/2.535485) usdt => 25 * 40 - 25 * 15.7760744 in loss
    assert position_inst.unrealized_pnl == decimal.Decimal("-605.5981400008282439059982608")


async def test_update_pnl_with_loss_with_long_linear_position_red_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open long of 24 contracts at 40 usdt
    await position_inst.update(update_size=TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # reduce long of 1 contract at 40 / 2.535485
    await position_inst.update(update_size=-constants.ONE,
                               mark_price=FORTY / decimal.Decimal("2.535485"))
    position_inst.update_pnl()
    # now have 23 contracts each now worth 15.7760744 (40/2.535485) usdt => 23 * 40 - 23 * 15.7760744 in loss
    assert position_inst.unrealized_pnl == decimal.Decimal("-557.1502888007619843935183999")


async def test_update_pnl_with_loss_with_short_inc_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open short of 24 contracts at 40 usdt
    await position_inst.update(update_size=-TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # add short of 1 contract at 40 * 1.0954
    await position_inst.update(update_size=-constants.ONE,
                               mark_price=FORTY * decimal.Decimal("1.0954"))
    position_inst.update_pnl()
    # now have 25 contracts each now worth 43.816 (40 * 1.0954) usdt => 25 * 40 - 25 * 43.816 in loss
    assert position_inst.unrealized_pnl == decimal.Decimal("-95.4")


async def test_update_pnl_with_loss_with_short_red_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    # open short of 24 contracts at 40 usdt
    await position_inst.update(update_size=-TWENTY_FOUR, mark_price=FORTY)
    position_inst.update_pnl()
    assert position_inst.unrealized_pnl == constants.ZERO
    # reduce short of 1 contract at 40 * 1.0954
    await position_inst.update(update_size=constants.ONE,
                               mark_price=FORTY * decimal.Decimal("1.0954"))
    position_inst.update_pnl()
    # now have 23 contracts each now worth 43.816 (40 * 1.0954) usdt => 23 * 40 - 23 * 43.816 in loss
    assert position_inst.unrealized_pnl == decimal.Decimal("-87.768")


async def test_update_pnl_with_loss_with_too_big_positions(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    portfolio = exchange_manager_inst.exchange_personal_data.portfolio_manager.portfolio

    # open long of 100 contracts at 40 usdt: not enough funds
    with pytest.raises(errors.PortfolioNegativeValueError):
        await position_inst.update(update_size=constants.ONE_HUNDRED, mark_price=FORTY)
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    assert position_inst.initial_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").position_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # open short of 100 contracts at 40 usdt: not enough funds
    # TODO not working because FutureAsset#update uses self.position_margin = self._ensure_not_negative
    # which cancels the negative margin here and prevents raising on available amount update, is that normal ?
    with pytest.raises(errors.PortfolioNegativeValueError):
        await position_inst.update(update_size=-constants.ONE_HUNDRED, mark_price=FORTY)
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    assert position_inst.initial_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").position_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1000')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')


async def test_update_pnl_with_loss_with_full_long_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    portfolio = exchange_manager_inst.exchange_personal_data.portfolio_manager.portfolio

    # open long of 25 contracts at 40 usdt
    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").position_margin == decimal.Decimal('1000')
    assert portfolio.get_currency_portfolio("USDT").available == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # reduce long of 1 contract at 40 * 1.0954
    await position_inst.update(update_size=-constants.ONE,
                               mark_price=FORTY * decimal.Decimal("1.0954"))

    # now have 24 contracts each now worth 43.816 (40 * 1.0954) usdt => 40 - 43.816 in profit per contract
    assert position_inst.unrealized_pnl == decimal.Decimal("91.584")
    assert position_inst.realised_pnl == decimal.Decimal("3.816")
    assert portfolio.get_currency_portfolio("USDT").position_margin == decimal.Decimal('960')
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('43.816000')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1095.400000')

    # reduce long of 24 contract at 40 - 2
    await position_inst.update(update_size=-TWENTY_FOUR,
                               mark_price=FORTY - decimal.Decimal(2))
    # now have 24 contracts each now worth 38 (40 - 2) usdt => 40 - 38 in loss per contract
    # position got reset
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    # position closed with 40 - 38 in loss per contract
    assert portfolio.get_currency_portfolio("USDT").position_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('955.816')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('955.816000')


async def test_update_pnl_with_loss_with_full_short_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    portfolio = exchange_manager_inst.exchange_personal_data.portfolio_manager.portfolio

    # open short of 25 contracts at 40 usdt
    await position_inst.update(update_size=-TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").position_margin == decimal.Decimal('1000')
    assert portfolio.get_currency_portfolio("USDT").available == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1000')

    # reduce short of 1 contract at 40 * 1.0954
    await position_inst.update(update_size=constants.ONE,
                               mark_price=FORTY * decimal.Decimal("1.0954"))

    # now have 24 contracts each now worth 43.816 (40 * 1.0954) usdt => 40 - 43.816 in loss per contract
    assert position_inst.unrealized_pnl == decimal.Decimal("-91.584")
    assert position_inst.realised_pnl == decimal.Decimal("-3.816")
    assert portfolio.get_currency_portfolio("USDT").position_margin == decimal.Decimal('960')
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('36.184')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('904.6')

    # reduce short of 24 contract at 40 - 2
    await position_inst.update(update_size=TWENTY_FOUR,
                               mark_price=FORTY - decimal.Decimal(2))
    # now have 24 contracts each now worth 38 (40 - 2) usdt => 40 - 38 in profit per contract
    # position got reset
    assert position_inst.unrealized_pnl == constants.ZERO
    assert position_inst.realised_pnl == constants.ZERO
    # position closed with 40 - 38 in profit per contract
    assert portfolio.get_currency_portfolio("USDT").position_margin == constants.ZERO
    assert portfolio.get_currency_portfolio("USDT").available == decimal.Decimal('1044.184')
    assert portfolio.get_currency_portfolio("USDT").total == decimal.Decimal('1044.184')


async def test_update_initial_margin(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    if not os.getenv('CYTHON_IGNORE'):
        await position_inst.update(update_size=constants.ZERO, mark_price=constants.ZERO)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == constants.ZERO
        await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == decimal.Decimal("1000")
        default_contract.set_current_leverage(constants.ONE_HUNDRED)
        position_inst._update_initial_margin()
        assert position_inst.initial_margin == decimal.Decimal("10")


async def test_get_margin_from_size(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.get_margin_from_size(constants.ONE) == decimal.Decimal('40')
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_margin_from_size(constants.ONE) == decimal.Decimal('0.4')
    default_contract.set_current_leverage(constants.ONE)
    assert position_inst.get_margin_from_size(decimal.Decimal('0.01')) == decimal.Decimal('0.4')
    assert position_inst.get_margin_from_size(decimal.Decimal('0.1')) == decimal.Decimal('4')
    assert position_inst.get_margin_from_size(decimal.Decimal('1')) == decimal.Decimal('40')


async def test_get_size_from_margin(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.get_size_from_margin(constants.ONE) == decimal.Decimal('0.025')
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_size_from_margin(constants.ONE) == decimal.Decimal('2.5')
    default_contract.set_current_leverage(constants.ONE)
    assert position_inst.get_size_from_margin(decimal.Decimal('0.01')) == decimal.Decimal('0.00025')
    assert position_inst.get_size_from_margin(decimal.Decimal('0.1')) == decimal.Decimal('0.0025')
    assert position_inst.get_size_from_margin(decimal.Decimal('1')) == decimal.Decimal('0.025')


async def test_calculate_maintenance_margin(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ZERO)
    assert position_inst.calculate_maintenance_margin() == constants.ZERO
    await position_inst.update(update_size=TWELVE_DOT_FIVE, mark_price=FORTY)
    assert position_inst.calculate_maintenance_margin() == decimal.Decimal('5')
    # TODO why changing this ? change position_inst.symbol_contract.maintenance_margin_rate instead ?
    exchange_manager_inst.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_FUTURE_SYMBOL).funding_manager.funding_rate = decimal.Decimal(DEFAULT_FUTURE_FUNDING_RATE)
    await position_inst.update(update_size=TWELVE_DOT_FIVE, mark_price=FORTY)
    assert position_inst.calculate_maintenance_margin() == decimal.Decimal('10')


async def test_update_isolated_liquidation_price_with_long(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    # avoid default maintenance_margin_rate to change liquidation price
    default_contract.maintenance_margin_rate = decimal.Decimal("0.2")

    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal('8')
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("47.60")
    # sell whole position
    await position_inst.update(update_size=-TWENTY_FIVE, mark_price=FORTY * decimal.Decimal(1.2))
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == constants.ZERO


async def test_update_isolated_liquidation_price_with_short(
        future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})
    # avoid default maintenance_margin_rate to change liquidation price
    default_contract.maintenance_margin_rate = decimal.Decimal("0.2")

    await position_inst.update(update_size=-TWELVE_DOT_FIVE, mark_price=FORTY)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("72.0")
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("32.40")
    await position_inst.update(update_size=-TWELVE_DOT_FIVE, mark_price=FORTY / decimal.Decimal(10))
    position_inst.update_isolated_liquidation_price()
    assert position_inst.liquidation_price == decimal.Decimal("32.40")


async def test_get_bankruptcy_price_with_long(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=TWELVE_DOT_FIVE, mark_price=FORTY)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == constants.ZERO
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           FORTY
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal("39.60")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           decimal.Decimal("40")
    await position_inst.update(update_size=TWELVE_DOT_FIVE, mark_price=FORTY * decimal.Decimal(2))
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side) == decimal.Decimal("39.60")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           decimal.Decimal("80")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("1"), position_inst.side, with_mark_price=True) \
           == decimal.Decimal("80")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), position_inst.side) == decimal.Decimal("99")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), enums.PositionSide.SHORT) \
        == decimal.Decimal("101")


async def test_get_bankruptcy_price_with_short(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=-TWELVE_DOT_FIVE, mark_price=FORTY)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, ) == decimal.Decimal("80")
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           decimal.Decimal("40")
    default_contract.set_current_leverage(constants.ONE_HUNDRED)
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, ) == decimal.Decimal('40.4')
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           decimal.Decimal('40')
    await position_inst.update(update_size=TWELVE_DOT_FIVE, mark_price=FORTY * decimal.Decimal(2))
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, ) == constants.ZERO
    assert position_inst.get_bankruptcy_price(position_inst.entry_price, position_inst.side, with_mark_price=True) == \
           constants.ZERO
    default_contract.set_current_leverage(decimal.Decimal("2"))
    await position_inst.update(update_size=-TWELVE_DOT_FIVE, mark_price=FORTY * decimal.Decimal(2))
    assert position_inst.get_bankruptcy_price(decimal.Decimal("1"), position_inst.side, with_mark_price=True) == \
            decimal.Decimal("80")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), position_inst.side) == decimal.Decimal("150")
    assert position_inst.get_bankruptcy_price(decimal.Decimal("100"), enums.PositionSide.LONG) \
        == decimal.Decimal("50")


async def test_get_order_cost(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ZERO)
    assert position_inst.get_order_cost() == constants.ZERO
    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.get_order_cost() == decimal.Decimal("1000.8")


async def test_get_fee_to_open(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ZERO)
    assert position_inst.get_fee_to_open(constants.ZERO, constants.ZERO, position_inst.symbol) == constants.ZERO
    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    assert position_inst.get_fee_to_open(TWENTY_FIVE, FORTY, position_inst.symbol) == decimal.Decimal("0.4")
    assert position_inst.get_fee_to_open(decimal.Decimal(2), FORTY, position_inst.symbol) == decimal.Decimal("0.0320")
    assert position_inst.get_fee_to_open(TWENTY_FIVE, decimal.Decimal(2), position_inst.symbol) == decimal.Decimal("0.02")
    assert position_inst.get_fee_to_open(decimal.Decimal(2), decimal.Decimal(2), position_inst.symbol) == \
           decimal.Decimal("0.0016")


async def test_update_fee_to_close(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=constants.ZERO, mark_price=constants.ZERO)
    position_inst.update_fee_to_close()
    assert position_inst.fee_to_close == constants.ZERO
    await position_inst.update(update_size=TWENTY_FIVE, mark_price=FORTY)
    position_inst.update_fee_to_close()
    assert position_inst.fee_to_close == decimal.Decimal("0.4")


async def test_get_two_way_taker_fee_for_quantity_and_price(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    set_future_exchange_fees(exchange_manager_inst.exchange.connector, default_contract.pair)

    # no need to initialize the position
    leverage = decimal.Decimal("2")
    default_contract.set_current_leverage(leverage)
    assert personal_data.LinearPosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("0.01") * leverage, decimal.Decimal("38497.5"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("0.46197")     # open fees + closing fees in case of liquidation

    assert personal_data.LinearPosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, constants.ONE_HUNDRED, enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal('1.2')     # open fees + closing fees in case of liquidation

    leverage = decimal.Decimal("50")
    default_contract.set_current_leverage(leverage)
    assert personal_data.LinearPosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("39.6")     # open fees + closing fees in case of liquidation

    leverage = constants.ONE_HUNDRED
    default_contract.set_current_leverage(leverage)
    assert personal_data.LinearPosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.LONG, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("79.6")     # open fees + closing fees in case of liquidation

    assert personal_data.LinearPosition(trader_inst, default_contract).get_two_way_taker_fee_for_quantity_and_price(
        decimal.Decimal("10") * leverage, decimal.Decimal("100"), enums.PositionSide.SHORT, DEFAULT_FUTURE_SYMBOL
    ) == decimal.Decimal("80.400000")     # open fees + closing fees in case of liquidation


async def test_update_average_entry_price_increased_long(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=decimal.Decimal(10), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal(15)
    position_inst.update_average_entry_price(decimal.Decimal(100), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("19.54545454545454545454545455")
    position_inst.update_average_entry_price(decimal.Decimal(2), decimal.Decimal(500))
    assert position_inst.entry_price == decimal.Decimal("99.62121212121212121212121217")


async def test_update_average_entry_price_increased_short(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=-decimal.Decimal(10), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(-decimal.Decimal(10), decimal.Decimal(5))
    assert position_inst.entry_price == decimal.Decimal(7.5)
    position_inst.update_average_entry_price(-decimal.Decimal(100), decimal.Decimal(2))
    assert position_inst.entry_price == decimal.Decimal(2.5)
    position_inst.update_average_entry_price(-decimal.Decimal(2), decimal.Decimal(0.1))
    assert position_inst.entry_price == decimal.Decimal("2.100000000000000000925185854")


async def test_update_average_entry_price_decreased_long(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=decimal.Decimal(100), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(-decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("8.888888888888888888888888889")
    position_inst.update_average_entry_price(-decimal.Decimal(50), decimal.Decimal(1.5))
    assert position_inst.entry_price == decimal.Decimal("16.27777777777777777777777778")
    position_inst.update_average_entry_price(-decimal.Decimal(2), decimal.Decimal(7000))
    assert position_inst.entry_price == constants.ZERO


async def test_update_average_entry_price_decreased_short(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
    position_inst.update_from_raw({enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL})

    await position_inst.update(update_size=-decimal.Decimal(100), mark_price=decimal.Decimal(10))
    position_inst.entry_price = decimal.Decimal(10)
    position_inst.update_average_entry_price(decimal.Decimal(10), decimal.Decimal(20))
    assert position_inst.entry_price == decimal.Decimal("8.888888888888888888888888889")
    position_inst.update_average_entry_price(decimal.Decimal(100), decimal.Decimal('35.678'))
    assert position_inst.entry_price == decimal.Decimal("2678.911111111111111111111111")
    position_inst.update_average_entry_price(decimal.Decimal(2), decimal.Decimal("0.0000000025428"))
    assert position_inst.entry_price == decimal.Decimal("2733.582766439857403174603174")


async def test_update_average_exit_price_and_transactions_long(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
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
    # 5 contracts sold at 35 and 8 at 50: average is 44.23076923076923076923076923
    assert position_inst.exit_price == decimal.Decimal("44.23076923076923076923076923")

    # increase position again
    market_buy = personal_data.BuyMarketOrder(trader_inst)
    market_buy.update(order_type=enums.TraderOrderType.BUY_MARKET,
                      symbol=DEFAULT_FUTURE_SYMBOL,
                      quantity_filled=decimal.Decimal(str(5)),
                      filled_price=decimal.Decimal(str(75)))
    await position_inst.update_from_order(market_buy)

    # size did not reduce, exit price is still 44.23076923076923076923076923
    assert position_inst.already_reduced_size == decimal.Decimal("-13")
    assert position_inst.exit_price == decimal.Decimal("44.23076923076923076923076923")
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
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80: average is 55.52631578947368421052631579
    assert position_inst.exit_price == decimal.Decimal("55.52631578947368421052631579")

    # liquidate remaining 1 contract, also updates average exit price
    await position_inst.update(mark_price=decimal.Decimal("0.5"))
    check_created_transaction(exchange_manager_inst, decimal.Decimal("-1"), decimal.Decimal("-20"))

    # position is closed, exit_price and already_reduced_size are reset
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO

    # latest transaction contains the average last exit price
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80 + 1 at 0.5: average is 52.8
    assert get_latest_transaction(exchange_manager_inst).average_exit_price == decimal.Decimal("52.775")


async def test_update_average_exit_price_and_transactions_short(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position_inst = personal_data.LinearPosition(trader_inst, default_contract)
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
    # 5 contracts sold at 20 and 8 at 18: average is 18.76923076923076923076923077
    assert position_inst.exit_price == decimal.Decimal("18.76923076923076923076923077")

    # increase position again
    market_sell = personal_data.SellMarketOrder(trader_inst)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       quantity_filled=decimal.Decimal(str(5)),
                       filled_price=decimal.Decimal(str(19)))
    await position_inst.update_from_order(market_sell)
    # a new fee transaction is created
    assert isinstance(get_latest_transaction(exchange_manager_inst), personal_data.FeeTransaction)

    # size did not reduce, exit price is still 44.23076923076923076923076923
    assert position_inst.already_reduced_size == decimal.Decimal("13")
    assert position_inst.exit_price == decimal.Decimal("18.76923076923076923076923077")

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
    # 5 contracts sold at 20 + 8 at 18 + 6 at 17: average is 18.21052631578947368421052632
    assert position_inst.exit_price == decimal.Decimal("18.21052631578947368421052632")

    # liquidate remaining 1 contract, also updates average exit price
    await position_inst.update(mark_price=decimal.Decimal("50"))
    check_created_transaction(exchange_manager_inst, decimal.Decimal("1"), decimal.Decimal("20"))

    # position is closed, exit_price and already_reduced_size are reset
    assert position_inst.already_reduced_size == constants.ZERO
    assert position_inst.exit_price == constants.ZERO

    # latest transaction contains the average last exit price
    # 5 contracts sold at 35 + 8 at 50 + 6 at 80 + 1 at 50: average is 19.8
    assert get_latest_transaction(exchange_manager_inst).average_exit_price == decimal.Decimal("19.8")
