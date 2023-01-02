#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import contextlib
import decimal

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
from exchanges_tests import abstract_authenticated_exchange_tester


class AbstractAuthenticatedFutureExchangeTester(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here*
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.FUTURE.value
    PORTFOLIO_TYPE_FOR_SIZE = trading_constants.CONFIG_PORTFOLIO_TOTAL

    async def test_get_empty_linear_and_inverse_positions(self):
        # ensure fetch empty positions
        async with self.local_exchange_manager():
            await self.inner_test_get_empty_linear_and_inverse_positions()

    async def inner_test_get_empty_linear_and_inverse_positions(self):
        positions = await self.get_positions()
        for contract_type in (trading_enums.FutureContractType.LINEAR_PERPETUAL,
                              trading_enums.FutureContractType.INVERSE_PERPETUAL):
            if not self.has_empty_position(self.get_filtered_positions(positions, contract_type)):
                empty_position_symbol = self.get_other_position_symbol(positions, contract_type)
                empty_position = await self.get_position(empty_position_symbol)
                assert self.is_position_empty(empty_position)

    async def inner_test_create_and_fill_market_orders(self):
        portfolio = await self.get_portfolio()
        position = await self.get_position()
        pre_order_positions = await self.get_positions()
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False)
        size = self.get_order_size(portfolio, price)
        # buy: increase position
        buy_market = await self.create_market_order(current_price, size, trading_enums.TradeOrderSide.BUY)
        self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
        await self.wait_for_fill(buy_market)
        post_buy_portfolio = await self.get_portfolio()
        post_buy_position = await self.get_position()
        self.check_portfolio_changed(portfolio, post_buy_portfolio, False)
        self.check_position_changed(position, post_buy_position, True)
        post_order_positions = await self.get_positions()
        self.check_position_in_positions(pre_order_positions + post_order_positions)
        # sell: reset portfolio & position
        sell_market = await self.create_market_order(current_price, size, trading_enums.TradeOrderSide.SELL)
        self.check_created_market_order(sell_market, size, trading_enums.TradeOrderSide.SELL)
        await self.wait_for_fill(sell_market)
        post_sell_portfolio = await self.get_portfolio()
        post_sell_position = await self.get_position()
        self.check_portfolio_changed(post_buy_portfolio, post_sell_portfolio, True)
        self.check_position_changed(post_buy_position, post_sell_position, False)
        # position is back to what it was at the beginning on the test
        self.check_position_size(position, post_sell_position)

    async def test_create_bundled_orders(self):
        async with self.local_exchange_manager(), self.required_empty_position():
            await self.inner_test_create_bundled_orders()

    async def get_position(self, symbol=None):
        return await self.exchange_manager.exchange.get_position(symbol or self.SYMBOL)

    async def get_positions(self):
        return await self.exchange_manager.exchange.get_positions()

    @contextlib.asynccontextmanager
    async def required_empty_position(self):
        position = await self.get_position()
        if not self.is_position_empty(position):
            raise AssertionError(f"Empty {self.SYMBOL} position required for bundle orders tests")
        try:
            yield
        finally:
            position = await self.get_position()
            assert self.is_position_empty(position)

    async def load_contract(self, symbol=None):
        symbol = symbol or self.SYMBOL
        if self.exchange_manager.is_future and symbol not in self.exchange_manager.exchange.pair_contracts:
            await self.exchange_manager.exchange.load_pair_future_contract(symbol)

    async def enable_partial_take_profits_and_stop_loss(self, mode, symbol=None):
        await self.exchange_manager.exchange.set_symbol_partial_take_profit_stop_loss(
            symbol or self.SYMBOL, False, trading_enums.TakeProfitStopLossMode.PARTIAL)

    async def create_market_stop_loss_order(self, current_price, stop_price, size, side, symbol=None,
                                            push_on_exchange=True):
        await self.enable_partial_take_profits_and_stop_loss(trading_enums.TakeProfitStopLossMode.PARTIAL,
                                                             symbol=symbol)
        return await super().create_market_stop_loss_order(
            current_price, stop_price, size, side, symbol=symbol,
            push_on_exchange=push_on_exchange
        )

    async def create_order(self, price, current_price, size, side, order_type,
                           symbol=None, push_on_exchange=True):
        # contracts are required to create orders
        await self.load_contract(symbol)
        return await super().create_order(
            price, current_price, size, side, order_type,
            symbol=symbol, push_on_exchange=push_on_exchange
        )

    def check_position_changed(self, previous_position, updated_position, has_increased, symbol=None):
        # use unified enums as it the ccxt position should have been parsed already
        previous_size = previous_position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value]
        updated_size = updated_position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value]
        if has_increased:
            assert updated_size > previous_size
        else:
            assert updated_size < previous_size

    def check_position_size(self, previous_position, updated_position):
        assert previous_position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value] == \
               updated_position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value]

    def has_empty_position(self, positions):
        for position in positions:
            if self.is_position_empty(position):
                # empty positions included in get_positions
                return True
        return False

    def get_filtered_positions(self, positions, contract_type):
        return [
            position
            for position in positions
            if position[trading_enums.ExchangeConstantsPositionColumns.CONTRACT_TYPE.value] is contract_type
        ]

    def get_other_position_symbol(self, positions_blacklist, contract_type):
        ignored_symbols = set(
            position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value]
            for position in positions_blacklist
        )
        for symbol in self.exchange_manager.exchange.connector.client.markets:
            if symbol in ignored_symbols:
                continue
            if contract_type is trading_enums.FutureContractType.INVERSE_PERPETUAL \
               and self.exchange_manager.exchange.is_inverse_symbol(symbol):
                return symbol
            elif contract_type is trading_enums.FutureContractType.LINEAR_PERPETUAL \
                 and self.exchange_manager.exchange.is_linear_symbol(symbol):
                return symbol
        raise AssertionError(f"No free symbol for {contract_type}")

    def is_position_empty(self, position):
        return position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value] == trading_constants.ZERO

    def check_position_in_positions(self, positions, symbol=None):
        symbol = symbol or self.SYMBOL
        for position in positions:
            if position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value] == symbol:
                return True
        raise AssertionError(f"Can't find position for symbol: {symbol}")

    async def order_in_open_orders(self, previous_open_orders, order):
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders) + 1
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.ID.value] == order.order_id:
                return True
        return False

    def check_theoretical_cost(self, symbol, quantity, price, cost):
        if symbol.is_inverse():
            theoretical_cost = quantity
        else:
            theoretical_cost = quantity * price
        assert theoretical_cost * decimal.Decimal("0.8") <= cost <= theoretical_cost * decimal.Decimal("1.2")
