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
import contextlib
import decimal
import copy

import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.positions.position_util as position_util
import octobot_trading.personal_data.positions.states as positions_states
import octobot_trading.personal_data.transactions.transaction_factory as transaction_factory
import octobot_trading.util as util
import octobot_trading.constants as constants


class Position(util.Initializable):
    def __init__(self, trader, symbol_contract):
        """
        When adding a new "dynamic" attribute, please add it to self.restore()
        """
        super().__init__()
        if self.is_inverse() is not symbol_contract.is_inverse_contract():
            raise errors.InvalidPosition(f"This position requires a "
                                         f"{'inverse' if symbol_contract.is_inverse_contract else 'linear'} contract")
        self.trader = trader
        self.exchange_manager = trader.exchange_manager
        self.simulated = trader.simulate

        self.logger_name = None
        self.position_id = None             # position id within OctoBot
        self.exchange_position_id = None    # position id as fetched from exchange, local to the user account
        self.timestamp = 0
        self.symbol = None
        self.currency, self.market = None, None
        self.status = enums.PositionStatus.OPEN
        self.side = enums.PositionSide.UNKNOWN

        # Contract
        self.symbol_contract = symbol_contract

        # Prices
        self.entry_price = constants.ZERO
        self.exit_price = constants.ZERO
        self.mark_price = constants.ZERO
        self.liquidation_price = constants.ZERO
        self.fee_to_close = constants.ZERO

        # Size
        self.quantity = constants.ZERO  # unleverage size
        self.size = constants.ZERO  # size of the position (in asset)
        self.already_reduced_size = constants.ZERO
        self.value = constants.ZERO # value of the position
        self.initial_margin = constants.ZERO    # locked funds from the wallet to maintain position
        self.margin = constants.ZERO    # initial_margin + fee to close
        self.auto_deposit_margin = False

        # PNL
        self.unrealized_pnl = constants.ZERO
        self.realised_pnl = constants.ZERO

        # original position attributes
        self.creation_time = self.exchange_manager.exchange.get_exchange_current_time()

        # position state is initialized in initialize_impl()
        self.state = None

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_logger_name(self):
        """
        :return: The position logger name
        """
        if self.logger_name is None:
            self.logger_name = f"{self.get_name()} | {self.position_id}"
        return self.logger_name

    async def initialize_impl(self, **kwargs):
        """
        Initialize position status update tasks
        """
        positions_states.create_position_state(self, **kwargs)
        if self.state.has_to_be_async_synchronized():
            await self.state.initialize()

    def on_idle(self, force_open=False, is_from_exchange_data=False):
        """
        Triggers a new position idle state
        :param force_open: if the new state should be forced
        :param is_from_exchange_data: if it's call from exchange data
        """
        self.state = positions_states.IdlePositionState(self, is_from_exchange_data=is_from_exchange_data)
        self.state.sync_initialize(forced=force_open)

    def on_active(self, force_open=False, is_from_exchange_data=False):
        """
        Triggers a new position active state
        :param force_open: if the new state should be forced
        :param is_from_exchange_data: if it's call from exchange data
        """
        self.state = positions_states.ActivePositionState(self, is_from_exchange_data=is_from_exchange_data)
        self.state.sync_initialize(forced=force_open)

    def on_liquidate(self, force_liquidate=False, is_from_exchange_data=False):
        """
        Triggers a new position liquidation state
        :param force_liquidate: if the new state should be forced
        :param is_from_exchange_data: if it's call from exchange data
        """
        self.state = positions_states.LiquidatePositionState(self, is_from_exchange_data=is_from_exchange_data)

    def _should_change(self, original_value, new_value):
        if new_value is not None and original_value != new_value:
            return True

    def _update(self, position_id, exchange_position_id, symbol, currency, market, timestamp,
                entry_price, mark_price, liquidation_price,
                quantity, size, value, initial_margin, auto_deposit_margin,
                unrealized_pnl, realised_pnl, fee_to_close,
                status=None):
        changed: bool = False

        if self._should_change(self.position_id, position_id):
            self.position_id = position_id

        if self._should_change(self.exchange_position_id, exchange_position_id):
            self.exchange_position_id = exchange_position_id

        if self._should_change(self.symbol, symbol):
            self.symbol, self.currency, self.market = symbol, currency, market

        if self._should_change(self.timestamp, timestamp):
            self.timestamp = timestamp
            # if we have a timestamp, it's a real trader => need to format timestamp if necessary
            self.creation_time = self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)
        if not self.timestamp:
            if not timestamp:
                self.creation_time = self.exchange_manager.exchange.get_exchange_current_time()
            else:
                # if we have a timestamp, it's a real trader => need to format timestamp if necessary
                self.creation_time = self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)
            self.timestamp = self.creation_time

        if self._should_change(self.quantity, quantity):
            self.quantity = quantity
            changed = True

        if self._should_change(self.size, size):
            self.size = size
            changed = True

        if self._should_change(self.value, value):
            self.value = value
            changed = True

        if self._should_change(self.initial_margin, initial_margin):
            self.initial_margin = initial_margin
            self._update_margin()
            changed = True

        if self._should_change(self.auto_deposit_margin, auto_deposit_margin):
            self.auto_deposit_margin = auto_deposit_margin
            changed = True

        if self._should_change(self.unrealized_pnl, unrealized_pnl):
            self.unrealized_pnl = unrealized_pnl
            changed = True

        if self._should_change(self.realised_pnl, realised_pnl):
            self.realised_pnl = realised_pnl
            changed = True

        if self._should_change(self.entry_price, entry_price):
            self.entry_price = entry_price
            changed = True

        if self._should_change(self.mark_price, mark_price):
            self.mark_price = mark_price
            changed = True

        if self._should_change(self.fee_to_close, fee_to_close):
            self.fee_to_close = fee_to_close
            self._update_margin()
            changed = True

        if self._should_change(self.liquidation_price, liquidation_price):
            self.liquidation_price = liquidation_price
            changed = True

        if self._should_change(self.status.value, status):
            self.status = enums.PositionStatus(status)

        self._update_quantity_or_size_if_necessary()
        # update side after quantity as it relies on self.quantity
        self._update_side(
            not entry_price,
            creation_timestamp=self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)
        )
        self._update_prices_if_necessary(mark_price)
        if changed:
            # ensure fee to close and margin are up to date now that all other attributes are set
            self.update_fee_to_close()
            self._update_margin()
        return changed

    async def ensure_position_initialized(self, **kwargs):
        """
        Checks if the position has already been initialized
        When it's not initialize it
        """
        if self.state is None:
            await self.initialize(**kwargs)

    async def update(self, update_size=None, mark_price=None, update_margin=None):
        """
        Updates position size and / or mark price
        :param update_size: the size update value
        :param mark_price: the mark price update value
        :param update_margin: the margin update value
        """
        await self.ensure_position_initialized()

        try:
            with self.update_or_restore():
                if mark_price is not None:
                    self._update_mark_price(mark_price, force_entry_check=bool(update_size or update_margin))
                if update_margin is not None:
                    self._update_size_from_margin(update_margin)
                if update_size is not None:
                    self._update_size(update_size)
            if not self.is_idle():
                self._check_for_liquidation()
            else:
                await self.close()
        except errors.LiquidationPriceReached:
            self._update_exit_data(self.get_quantity_to_close(), self.mark_price)
            await self._create_liquidation_state()

    async def update_on_liquidation(self):
        """
        Update portfolio and position from a liquidation
        """
        size_update = self.get_quantity_to_close()
        self.unrealized_pnl = -self.initial_margin
        realised_pnl_update = self._update_realized_pnl_from_size_update(
            size_update, is_closing=True, update_price=self.mark_price,
            trigger_source=enums.PNLTransactionSource.LIQUIDATION)
        self._on_size_update(size_update, realised_pnl_update, self.unrealized_pnl, False)
        await self.close()

    def _update_mark_price(self, mark_price, check_liquidation=True, force_entry_check=False):
        """
        Updates position mark_price and triggers size related attributes update
        :param mark_price: the update mark_price
        """
        self.mark_price = mark_price
        self._update_prices_if_necessary(mark_price, force_entry_check=force_entry_check)
        if check_liquidation:
            self._check_for_liquidation()
        if not self.is_idle() and self.exchange_manager.is_simulated:
            self.update_value()
            self.update_pnl()

    def _update_prices_if_necessary(self, mark_price, force_entry_check=False):
        """
        Update the position entry price and mark price when their value is 0 or when the position is new
        :param mark_price: the current mark_price
        """
        if self.mark_price == constants.ZERO:
            self.mark_price = mark_price
        if self.entry_price == constants.ZERO and (force_entry_check or not self.is_idle()):
            self.entry_price = mark_price

    def _update_size_from_margin(self, margin_update):
        """
        Updates position size and margin by converting margin to size and calling self._update_size
        :param margin_update: the position margin update
        """
        try:
            self._update_size(self.get_size_from_margin(margin_update))
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            pass

    def is_order_increasing_size(self, order):
        """
        Check if an order increase the position size
        :param order: the order instance
        :return: True if the order increase the position size when filled
        """
        if order.reduce_only or order.close_position:
            return False  # Only reducing
        return (
                (self.is_idle() and self.symbol_contract.is_one_way_position_mode())
                or (self.is_long() and order.is_long())
                or (self.is_short() and order.is_short())
        )

    async def update_from_order(self, order):
        """
        Update position size and entry price from filled order portfolio
        :param order: the filled order instance
        :return: the updated quantity, True if the order increased position size
        """
        # consider the order filled price as the current reference price for pnl computation
        # do not check liquidation as our position might be closed by this order
        self._update_mark_price(order.filled_price, check_liquidation=False, force_entry_check=True)

        # get size to close to check if closing
        size_to_close = self.get_quantity_to_close()

        # Remove / add order fees from realized pnl
        realised_pnl_fees_update = self._update_realized_pnl_from_order(order)

        trigger_source = order_util.get_pnl_transaction_source_from_order(order)

        # Close position if order is closing position
        if order.close_position:
            # set position size to 0 to schedule position close at the next update
            self._update_size(size_to_close,
                              realised_pnl_update=realised_pnl_fees_update,
                              trigger_source=trigger_source)
            return

        # Calculates position quantity update from order
        size_update = self._calculates_size_update_from_filled_order(order, size_to_close)

        # set position entry price if necessary
        self._update_prices_if_necessary(order.filled_price)

        # Updates position average entry price from order only when increasing position side
        if self._is_update_increasing_size(size_update):
            if self.size == constants.ZERO:
                self.creation_time = self.exchange_manager.exchange.get_exchange_current_time()
            self.update_average_entry_price(size_update, order.filled_price)
        elif self._is_update_reversing_side(size_update):
            # don't use size_update here as it is larger than size
            self._update_exit_data(size_to_close, self.mark_price)
        elif self._is_update_decreasing_size(size_update):
            self._update_exit_data(size_update, self.mark_price)

        # update size and realised pnl
        self._update_size(size_update, realised_pnl_update=realised_pnl_fees_update, trigger_source=trigger_source)
        if size_to_close and self.is_idle():
            # don't keep previous position pnl etc when position is now idle
            await self.close()

    def _update_realized_pnl_from_order(self, order):
        """
        Updates the position realized pnl from order
        Removes order's fees from realized pnl
        :param order: the realized pnl update
        """
        fees_currency = order.currency if self.symbol_contract.is_inverse_contract() else order.market
        realised_pnl_update = -order.get_total_fees(fees_currency)
        transaction_factory.create_fee_transaction(self.exchange_manager, fees_currency, self.symbol,
                                                   quantity=realised_pnl_update,
                                                   order_id=order.order_id)
        self.realised_pnl += realised_pnl_update
        return realised_pnl_update

    def _calculates_size_update_from_filled_order(self, order, size_to_close):
        """
        Calculates position size update from an order filled quantity
        :param order: the filled order
        :param size_to_close: the size to close the position
        :return: the position size update
        """
        order_quantity = order.filled_quantity if order.is_long() else -order.filled_quantity
        if order.reduce_only or not self.symbol_contract.is_one_way_position_mode():
            if self.is_long() and order.is_short():
                return max(order_quantity, size_to_close)
            if self.is_short() and order.is_long():
                return min(order_quantity, size_to_close)
            if not order.reduce_only:
                return order_quantity
            # Can't reduce position
            return constants.ZERO
        return order_quantity

    def _is_update_increasing_size(self, size_update):
        """
        :param size_update: the size update
        :return: True if this update will increase position size
        """
        if self.is_idle():
            return True
        if self.is_long():
            return size_update > constants.ZERO
        return size_update < constants.ZERO

    def _is_update_decreasing_size(self, size_update):
        """
        :param size_update: the size update
        :return: True if this update will increase position size
        """
        if self.is_idle():
            return False
        if self.is_long():
            return size_update < constants.ZERO
        return size_update > constants.ZERO

    def _is_update_reversing_side(self, size_update):
        """
        :param size_update: the size update
        :return: True if this update will reverse position side
        """
        if self.is_long():
            return self.size + size_update < constants.ZERO
        return self.size + size_update > constants.ZERO

    def _is_update_closing(self, size_update):
        """
        :param size_update: the size update
        :return: True if this update will close the position
        """
        if self.is_idle():
            return True
        if self.is_long():
            return self.size + size_update <= constants.ZERO
        return self.size + size_update >= constants.ZERO

    def is_exclusively_using_exchange_position_details(self) -> bool:
        return (
            self.exchange_manager.exchange_personal_data.positions_manager
            .is_exclusively_using_exchange_position_details
        )

    def _update_size(self, size_update, realised_pnl_update=constants.ZERO,
                     trigger_source=enums.PNLTransactionSource.UNKNOWN):
        """
        Updates position size and triggers size related attributes update
        :param size_update: the size quantity
        :param realised_pnl_update: the current realised pnl update
        :return: True if the update increased position size
        """
        margin_update = constants.ZERO
        is_update_increasing_position_size = self._is_update_increasing_size(size_update)
        if self._is_update_reversing_side(size_update):
            realised_pnl_update += self._update_realized_pnl_from_size_update(
                self.get_quantity_to_close(), is_closing=True,
                update_price=self.mark_price, trigger_source=trigger_source
            )
        elif self._is_update_decreasing_size(size_update):
            realised_pnl_update += self._update_realized_pnl_from_size_update(
                size_update, is_closing=self._is_update_closing(size_update),
                update_price=self.mark_price, trigger_source=trigger_source
            )
        self._check_and_update_size(size_update)
        self._update_quantity()
        self._update_side(True)
        if self.exchange_manager.is_simulated and not self.is_exclusively_using_exchange_position_details():
            margin_update = self._update_initial_margin()
            self.update_fee_to_close()
            self.update_liquidation_price()
            self.update_value()
            self.update_pnl()
        self._on_size_update(size_update,
                             realised_pnl_update,
                             margin_update,
                             is_update_increasing_position_size)

    def _update_realized_pnl_from_size_update(self, size_update, is_closing=False, update_price=constants.ZERO,
                                              trigger_source=enums.PNLTransactionSource.UNKNOWN):
        """
        Updates the position realized pnl from update size
        :param size_update: the position update size
        :param is_closing: True when the position will be closed after size update
        """
        try:
            realised_pnl_update = -size_update / self.size * self.unrealized_pnl
            transaction_factory.create_realised_pnl_transaction(self.exchange_manager,
                                                                self.get_currency(),
                                                                self.symbol,
                                                                self.side,
                                                                realised_pnl=realised_pnl_update,
                                                                is_closed_pnl=is_closing,
                                                                cumulated_closed_quantity=self.already_reduced_size,
                                                                closed_quantity=size_update,
                                                                first_entry_time=self.creation_time,
                                                                average_entry_price=self.entry_price,
                                                                average_exit_price=self.exit_price,
                                                                order_exit_price=update_price,
                                                                leverage=self.symbol_contract.current_leverage,
                                                                trigger_source=trigger_source)
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            realised_pnl_update = constants.ZERO
        self.realised_pnl += realised_pnl_update
        return realised_pnl_update

    def _check_and_update_size(self, size_update):
        """
        Updates the position size with a valid size according to the contract position mode if not close the position
        This check is not mandatory when using one way position mode because it can't produce invalid size with
        :param size_update: the size update
        """
        if not self.symbol_contract.is_one_way_position_mode() and \
                ((self.is_long() and self.size + size_update < constants.ZERO) or
                 (self.is_short() and self.size + size_update > constants.ZERO)):
            self.size = constants.ZERO
        else:
            self.size += size_update

    def _update_quantity_or_size_if_necessary(self):
        """
        Set quantity from size if quantity is not set and size is set or update size
        """
        if self.quantity == constants.ZERO and self.size != constants.ZERO:
            self._update_quantity()
        elif self.size == constants.ZERO and self.quantity != constants.ZERO:
            self.size = self.quantity * self.symbol_contract.current_leverage

    def _update_quantity(self):
        """
        Update position quantity from position size
        """
        self.quantity = self.size / self.symbol_contract.current_leverage

    def update_value(self):
        raise NotImplementedError("update_value not implemented")

    def update_pnl(self):
        """
        Update position unrealised pnl
        """
        try:
            self.unrealized_pnl = self.get_unrealized_pnl(self.mark_price)
            self.on_pnl_update()
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            self.unrealized_pnl = constants.ZERO

    def _update_exit_data(self, size_update, price):
        """
        Update position average exit price and already_reduced_size
        """
        try:
            self.update_average_exit_price(size_update, price)
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            self.exit_price = constants.ZERO
        self.already_reduced_size += size_update

    def get_unrealized_pnl(self, price):
        raise NotImplementedError("get_unrealized_pnl not implemented")

    def get_margin_from_size(self, size):
        raise NotImplementedError("get_margin_from_size not implemented")

    def get_size_from_margin(self, margin):
        raise NotImplementedError("get_size_from_margin not implemented")

    def _update_initial_margin(self):
        """
        Updates position initial margin
        """
        margin_update = constants.ZERO
        try:
            previous_initial_margin = self.initial_margin
            self.initial_margin = self.get_margin_from_size(self.size).copy_abs()
            self._update_margin()
            margin_update = self.initial_margin - previous_initial_margin
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            self.initial_margin = constants.ZERO
        return margin_update

    def update_average_entry_price(self, update_size, update_price):
        raise NotImplementedError("get_average_entry_price not implemented")

    def update_average_exit_price(self, update_size, update_price):
        raise NotImplementedError("update_average_exit_price not implemented")

    def get_initial_margin_rate(self):
        """
        :return: Initial Margin Rate = 1 / Leverage
        """
        try:
            return constants.ONE / self.symbol_contract.current_leverage
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            return constants.ZERO

    def get_currency(self):
        """
        :return: position currency
        """
        return self.currency if self.symbol_contract.is_inverse_contract() else self.market

    def calculate_maintenance_margin(self):
        raise NotImplementedError("calculate_maintenance_margin not implemented")

    def update_liquidation_price(self):
        """
        Updates position liquidation price
        Should call _update_fee_to_close() at the end of the implementation
        """
        if self.symbol_contract.is_isolated():
            self.update_isolated_liquidation_price()
        else:
            self.update_cross_liquidation_price()

    def update_cross_liquidation_price(self):
        raise NotImplementedError("update_cross_liquidation_price not implemented")

    def update_isolated_liquidation_price(self):
        raise NotImplementedError("update_isolated_liquidation_price not implemented")

    def get_bankruptcy_price(self, price, side, with_mark_price=False):
        """
        The bankruptcy price refers to the price at which the initial margin of all positions is lost.
        :param price: the price to compute bankruptcy from
        :param side: the side of the position
        :param with_mark_price: if price should be mark price instead of entry price
        :return: the bankruptcy price
        """
        raise NotImplementedError("get_bankruptcy_price not implemented")

    def get_maker_fee(self, symbol):
        """
        :return: Position maker fee
        """
        try:
            symbol_fees = self.exchange_manager.exchange.get_fees(symbol)
            return decimal.Decimal(
                f"{symbol_fees[enums.ExchangeConstantsMarketPropertyColumns.MAKER.value]}")
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            return constants.ZERO

    def get_taker_fee(self, symbol):
        """
        :return: Position taker fee
        """
        try:
            symbol_fees = self.exchange_manager.exchange.get_fees(symbol)
            return decimal.Decimal(
                f"{symbol_fees[enums.ExchangeConstantsMarketPropertyColumns.TAKER.value]}")
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            return constants.ZERO

    def get_two_way_taker_fee_for_quantity_and_price(self, quantity, price, side, symbol):
        """
        # Fee to open = (Quantity of contracts * Order Price) x Taker fee
        # Fee to close = (Quantity of contracts * Bankruptcy Price derived from Order Price) x Taker fee
        :return: 2-way taker fee = fee to open + fee to close
        """
        return self.get_fee_to_open(quantity, price, symbol) + self.get_fee_to_close(quantity, price, side, symbol)

    def get_two_way_taker_fee(self):
        """
        :return: 2-way taker fee = fee to open + fee to close
        """
        return self.get_fee_to_open(self.size, self.mark_price, self.symbol) + self.fee_to_close

    def get_order_cost(self):
        raise NotImplementedError("get_order_cost not implemented")

    def get_fee_to_open(self, quantity, price, symbol):
        raise NotImplementedError("get_fee_to_open not implemented")

    def get_fee_to_close(self, quantity, price, side, symbol, with_mark_price=False):
        raise NotImplementedError("get_fee_to_close not implemented")

    def update_fee_to_close(self):
        raise NotImplementedError("update_fee_to_close not implemented")

    @staticmethod
    def is_inverse():
        raise NotImplementedError("is_inverse not implemented")

    def _update_margin(self):
        """
        Updates position margin = Initial margin + Fee to close
        """
        self.margin = self.initial_margin + self.fee_to_close

    def is_open(self):
        return self.state is None or self.state.is_open()

    def is_liquidated(self):
        return self.state is not None and self.state.is_liquidated()

    def is_refreshing(self):
        return self.state is not None and self.state.is_refreshing()

    def is_long(self):
        return self.side is enums.PositionSide.LONG

    def is_short(self):
        return self.side is enums.PositionSide.SHORT

    def is_idle(self):
        return self.quantity == constants.ZERO

    def get_quantity_to_close(self):
        """
        :return: the order quantity to close the position
        """
        return -self.size

    def get_unrealized_pnl_percent(self):
        """
        :return: Unrealized P&L% = [ Position's unrealized P&L / Position Margin ] x 100%
        """
        try:
            return (self.unrealized_pnl / self.margin) * constants.ONE_HUNDRED
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            return constants.ZERO

    def on_pnl_update(self):
        """
        Triggers external calls when position pnl has been updated
        """
        self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.update_portfolio_from_pnl(self)

    def _on_side_update(self, reset_entry_price, creation_timestamp=0):
        """
        Resets the side related data when a position side changes
        """
        if reset_entry_price:
            self._reset_entry_price()
        self.exit_price = constants.ZERO
        self.already_reduced_size = constants.ZERO
        # use update_timestamp when available, use exchange time otherwise
        self.creation_time = creation_timestamp or self.exchange_manager.exchange.get_exchange_current_time()
        logging.get_logger(self.get_logger_name()).debug(f"Changed position side: now {self.side.name}")
        # update position state if necessary
        positions_states.create_position_state(self)

    def _on_size_update(self,
                        size_update,
                        realised_pnl_update,
                        margin_update,
                        is_update_increasing_position_size):
        """
        Triggers external calls when position size has been updated
        """
        self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio. \
            update_portfolio_data_from_position_size_update(self,
                                                            realised_pnl_update,
                                                            size_update,
                                                            margin_update,
                                                            is_update_increasing_position_size)
        # update position state if necessary
        positions_states.create_position_state(self)

    async def recreate(self):
        """
        Recreate itself using its PositionManager instance
        """
        self.exchange_manager.exchange_personal_data.positions_manager.recreate_position(self)

    def update_from_raw(self, raw_position):
        symbol = str(raw_position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value, None))
        currency, market = self.exchange_manager.get_exchange_quote_and_base(symbol)
        position_id = (
            self.position_id or raw_position.get(enums.ExchangeConstantsPositionColumns.LOCAL_ID.value) or symbol
        )
        # side is managed locally, do not parse it
        return self._update(
            symbol=symbol,
            currency=currency,
            market=market,
            entry_price=raw_position.get(enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value, constants.ZERO),
            mark_price=raw_position.get(enums.ExchangeConstantsPositionColumns.MARK_PRICE.value, constants.ZERO),
            liquidation_price=raw_position.get(enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value,
                                               constants.ZERO),
            quantity=raw_position.get(enums.ExchangeConstantsPositionColumns.QUANTITY.value, constants.ZERO),
            size=raw_position.get(enums.ExchangeConstantsPositionColumns.SIZE.value, constants.ZERO),
            value=raw_position.get(enums.ExchangeConstantsPositionColumns.NOTIONAL.value, constants.ZERO),
            initial_margin=raw_position.get(enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value,
                                            constants.ZERO),
            auto_deposit_margin=raw_position.get(
                enums.ExchangeConstantsPositionColumns.AUTO_DEPOSIT_MARGIN.value, False
            ),
            position_id=position_id,
            exchange_position_id=str(raw_position.get(enums.ExchangeConstantsPositionColumns.ID.value, None) or symbol),
            timestamp=raw_position.get(enums.ExchangeConstantsPositionColumns.TIMESTAMP.value, 0),
            unrealized_pnl=raw_position.get(enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value,
                                            constants.ZERO),
            realised_pnl=raw_position.get(enums.ExchangeConstantsPositionColumns.REALISED_PNL.value, constants.ZERO),
            fee_to_close=raw_position.get(enums.ExchangeConstantsPositionColumns.CLOSING_FEE.value, constants.ZERO),
            status=position_util.parse_position_status(raw_position)
        )

    def to_dict(self):
        return {
            enums.ExchangeConstantsPositionColumns.ID.value: self.exchange_position_id,
            enums.ExchangeConstantsPositionColumns.LOCAL_ID.value: self.position_id,
            enums.ExchangeConstantsPositionColumns.SYMBOL.value: self.symbol,
            enums.ExchangeConstantsPositionColumns.STATUS.value: self.status.value,
            enums.ExchangeConstantsPositionColumns.TIMESTAMP.value: self.timestamp,
            enums.ExchangeConstantsPositionColumns.SIDE.value: self.side.value,
            enums.ExchangeConstantsPositionColumns.QUANTITY.value: self.quantity,
            enums.ExchangeConstantsPositionColumns.SIZE.value: self.size,
            enums.ExchangeConstantsPositionColumns.NOTIONAL.value: self.value,
            enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: self.initial_margin,
            enums.ExchangeConstantsPositionColumns.AUTO_DEPOSIT_MARGIN.value: self.auto_deposit_margin,
            enums.ExchangeConstantsPositionColumns.COLLATERAL.value: self.margin,
            enums.ExchangeConstantsPositionColumns.LEVERAGE.value: self.symbol_contract.current_leverage,
            enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value: self.symbol_contract.margin_type.value
                if self.symbol_contract and self.symbol_contract.margin_type else None,
            enums.ExchangeConstantsPositionColumns.POSITION_MODE.value: self.symbol_contract.position_mode.value
                if self.symbol_contract and self.symbol_contract.position_mode else None,
            enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: self.entry_price,
            enums.ExchangeConstantsPositionColumns.MARK_PRICE.value: self.mark_price,
            enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value: self.liquidation_price,
            enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value: self.unrealized_pnl,
            enums.ExchangeConstantsPositionColumns.REALISED_PNL.value: self.realised_pnl,
            enums.ExchangeConstantsPositionColumns.MAINTENANCE_MARGIN_RATE.value: self.symbol_contract.maintenance_margin_rate,
        }

    def _check_for_liquidation(self):
        """
        _check_for_liquidation defines rules for a position to be liquidated
        """
        if self.liquidation_price.is_nan() or self.is_exclusively_using_exchange_position_details():
            # should skip liquidation check
            return
        if (self.is_short()
            and self.mark_price >= self.liquidation_price > constants.ZERO) or (
            self.is_long()
            and self.mark_price <= self.liquidation_price > constants.ZERO
        ):
            raise errors.LiquidationPriceReached

    async def _create_liquidation_state(self):
        """
        create liquidation state
        """
        self.status = enums.PositionStatus.LIQUIDATING
        positions_states.create_position_state(self)
        await self.state.initialize()

    def _reset_entry_price(self):
        """
        Reset the entry price to ZERO and force entry price update
        """
        self.entry_price = constants.ZERO
        self._update_prices_if_necessary(self.mark_price)

    def _update_side(self, reset_entry_price, creation_timestamp=0):
        """
        Checks if self.side still represents the position side
        Only relevant when account is using one way position mode
        """
        if self.symbol_contract.is_one_way_position_mode() or self.side is enums.PositionSide.UNKNOWN:
            changed_side = False
            if self.quantity > constants.ZERO:
                if self.side is not enums.PositionSide.LONG:
                    self.side = enums.PositionSide.LONG
                    changed_side = True
            elif self.quantity < constants.ZERO:
                if self.side is not enums.PositionSide.SHORT:
                    self.side = enums.PositionSide.SHORT
                    changed_side = True
            else:
                self.side = enums.PositionSide.UNKNOWN
            if changed_side:
                self._on_side_update(reset_entry_price, creation_timestamp)

    def __str__(self):
        return self.to_string()

    def to_string(self):
        currency = self.get_currency()
        position_mode = self.symbol_contract.position_mode.value \
            if self.symbol_contract.position_mode else 'no position mode'
        return (f"{self.symbol} | "
                f"Size : {round(self.size, 10).normalize()} "
                f"({round(self.value, 10).normalize()} {currency}) "
                f"--> {self.side.value} {self.symbol_contract} | "
                f"Mark price : {round(self.mark_price, 10).normalize()} | "
                f"Entry price : {round(self.entry_price, 10).normalize()} | "
                f"Margin : {round(self.margin, 10).normalize()} {currency} | "
                f"Unrealized PNL : {round(self.unrealized_pnl, 14).normalize()} {currency} "
                f"({round(self.get_unrealized_pnl_percent(), 3)}%) | "
                f"Liquidation price : {round(self.liquidation_price, 10).normalize()} | "
                f"Realised PNL : {round(self.realised_pnl, 14).normalize()} {currency} "
                f"State : {self.state.state.value if self.state is not None else 'Unknown'} "
                f"({position_mode})")

    async def close(self):
        await self.reset()

    async def reset(self):
        """
        Reset position attributes
        """
        self.entry_price = constants.ZERO
        self.exit_price = constants.ZERO
        self.mark_price = constants.ZERO
        self.quantity = constants.ZERO
        self.size = constants.ZERO
        self.already_reduced_size = constants.ZERO
        self.value = constants.ZERO
        self.initial_margin = constants.ZERO
        self.margin = constants.ZERO
        self.liquidation_price = constants.ZERO
        self.fee_to_close = constants.ZERO
        self.status = enums.PositionStatus.OPEN
        self.side = enums.PositionSide.UNKNOWN
        self.unrealized_pnl = constants.ZERO
        self.realised_pnl = constants.ZERO
        self.creation_time = 0
        self.timestamp = 0
        self.on_pnl_update()  # notify portfolio to reset unrealized PNL
        positions_states.create_position_state(self)

    def clear(self):
        """
        Clear position references
        """
        if self.state:
            self.state.clear()
        self.trader = None
        self.exchange_manager = None

    def restore(self, other_position):
        """
        Restore a position from another one
        :param other_position: the other position instance
        """
        self.entry_price = other_position.entry_price
        self.exit_price = other_position.exit_price
        self.mark_price = other_position.mark_price
        self.liquidation_price = other_position.liquidation_price
        self.fee_to_close = other_position.fee_to_close
        self.quantity = other_position.quantity
        self.size = other_position.size
        self.already_reduced_size = other_position.already_reduced_size
        self.value = other_position.value
        self.initial_margin = other_position.initial_margin
        self.margin = other_position.margin
        self.unrealized_pnl = other_position.unrealized_pnl
        self.realised_pnl = other_position.realised_pnl

    @contextlib.contextmanager
    def update_or_restore(self):
        """
        Ensure update complete without raising PortfolioNegativeValueError else restore Position instance's attributes
        """
        previous_position = copy.copy(self)
        try:
            yield
        except errors.PortfolioNegativeValueError:
            logging.get_logger(self.get_logger_name()).info("Restoring after PortfolioNegativeValueError...")
            self.restore(previous_position)
            raise
