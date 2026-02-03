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
import collections
import contextlib
import typing

import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.tree as commons_tree

import octobot_trading.personal_data.positions.position_factory as position_factory
import octobot_trading.personal_data.positions.position as position_import
import octobot_trading.util as util
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.exchange_channel as exchange_channel


class PositionsManager(util.Initializable):
    POSITION_ID_SEPARATOR = "_"

    def __init__(self, trader):
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.trader = trader
        self.positions: collections.OrderedDict[str, position_import.Position] = collections.OrderedDict()
        self.logged_unsupported_positions: set[str] = set()

        # When True, liquidation prices, PNL and other metrics are only read from exchange.
        # They are never computed by OctoBot
        self.is_exclusively_using_exchange_position_details: bool = False

        self._enable_position_update_from_order: bool = True

    async def initialize_impl(self):
        self._reset_positions()

    def get_symbol_position(self, symbol, side):
        """
        Returns or create the symbol position instance
        :param symbol: the position symbol
        :param side: the position side
        :return: the existing position or the newly created position
        """
        return self._get_or_create_position(symbol=symbol, side=side)

    def get_order_position(self, order, contract=None):
        """
        Returns the position that matches the order
        :param order: the order
        :param contract: the symbol contract (optional)
        :return: the existing position or the newly created position that matches the order
        """
        future_contract = contract if contract is not None \
            else self.trader.exchange_manager.exchange.get_pair_future_contract(order.symbol)
        return self.get_symbol_position(symbol=order.symbol,
                                        side=None if future_contract.is_one_way_position_mode()
                                        else order.get_position_side(future_contract))

    def get_symbol_positions(self, symbol=None):
        """
        Returns symbol positions if exist
        :param symbol: the position symbol
        :return: the symbol positions
        """
        if symbol is None:
            return list(self.positions.values())
        return self._get_symbol_positions(symbol)

    def get_symbol_position_margin_type(self, symbol: str) -> enums.MarginType:
        positions = self.get_symbol_positions(symbol=symbol)
        if len(positions) != 1:
            raise ValueError(f"{len(positions)} positions found for symbol {symbol}")
        return positions[0].symbol_contract.margin_type

    async def upsert_position(self, symbol: str, side, raw_position: dict) -> bool:
        """
        Create or update a position from a raw dictionary
        :param symbol: the position symbol
        :param side: the position side
        :param raw_position: the position raw dictionary
        :return: True when the creation or the update succeeded
        """
        self._ensure_support(raw_position)
        position_id = self._position_id_factory(symbol=symbol, side=side)
        if position_id not in self.positions:
            new_position = position_factory.create_position_instance_from_raw(self.trader, raw_position=raw_position)
            new_position.position_id = position_id
            return await self._finalize_position_creation(new_position, is_from_exchange_data=True)

        return self.positions[position_id].update_from_raw(raw_position)

    def _ensure_support(self, raw_position):
        if (
            raw_position.get(enums.ExchangeConstantsPositionColumns.POSITION_MODE.value, enums.PositionMode.ONE_WAY)
            is not enums.PositionMode.ONE_WAY
            and raw_position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]
            not in self.logged_unsupported_positions
        ):
            # TODO important error to display
            self.logger.error(
                f"{raw_position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]} position is in "
                f"{raw_position[enums.ExchangeConstantsPositionColumns.POSITION_MODE.value].name} mode. "
                f"This mode is not supported and will create unexpected behaviors in OctoBot. Please switch "
                f"to {enums.PositionMode.ONE_WAY.name} mode on {self.trader.exchange_manager.exchange_name}."
            )
            self.logged_unsupported_positions.add(raw_position[enums.ExchangeConstantsPositionColumns.SYMBOL.value])

    def set_initialized_event(self, symbol):
        commons_tree.EventProvider.instance().trigger_event(
            self.trader.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.trader.exchange_manager.exchange_name,
                commons_enums.InitializationEventExchangeTopics.POSITIONS.value,
                symbol=symbol
            )
        )

    async def recreate_position(self, position) -> bool:
        """
        Recreate position from an existing position instance
        :param position: the position instance to recreate
        :return: True when the recreation succeeded
        """
        new_position = position_factory.create_position_instance_from_raw(self.trader, raw_position=position.to_dict())
        position.clear()
        position.position_id = self._position_id_factory(symbol=position.symbol, side=position.side)
        return await self._finalize_position_creation(new_position)

    async def handle_position_update_from_order(self, order, require_exchange_update: bool) -> bool:
        """
        Handle a position update from an order update
        :param order: the order
        :param require_exchange_update: when True, will sync with exchange position, otherwise will predict the
        position changes using order data (as in trading simulator)
        :return: True if the position was updated
        """
        if self.trader.can_trade_if_not_paused() and self._enable_position_update_from_order:
            # portfolio might be updated when refreshing the position
            async with self.trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_history_update():
                if self.trader.simulate or not require_exchange_update:
                    # update simulated positions
                    return await self._refresh_simulated_position_from_order(order)
                if require_exchange_update and order.is_filled():
                    # on real trading when orders is filled: reload positions to ensure positions sync
                    try:
                        await self.refresh_real_trader_position(self.get_order_position(order))
                        return True
                    except Exception as err:
                        self.logger.exception(
                            err, True, f"Error while refreshing real trader {order.symbol} position: {err}"
                        )
        return False

    def add_position(self, position: position_import.Position):
        self.positions[position.position_id] = position

    async def _refresh_simulated_position_from_order(self, order):
        if order.is_filled():
            # Don't update if order filled quantity is null
            if order.filled_quantity == 0:
                return False

            position_instance = order.exchange_manager.exchange_personal_data.positions_manager.get_order_position(
                order, contract=order.exchange_manager.exchange.get_pair_future_contract(order.symbol))
            try:
                await position_instance.update_from_order(order)
                return True
            except errors.PortfolioNegativeValueError as portfolio_negative_value_error:
                self.logger.exception(portfolio_negative_value_error, True,
                                      f"Failed to update portfolio via position : {portfolio_negative_value_error} "
                                      f"for order {order.to_dict()}")
        return False

    async def refresh_real_trader_position(self, position, force_job_execution=False):
        """
        :param position: the position instance to refresh
        :param force_job_execution: force_job_execution
        Call POSITIONS_CHANNEL producer to refresh real trader position
        """
        await exchange_channel.get_chan(
            constants.POSITIONS_CHANNEL, self.trader.exchange_manager.id
        ).get_internal_producer().update_position_from_exchange(
            position, wait_for_refresh=True, force_job_execution=force_job_execution
        )

    def upsert_position_instance(self, position: position_import.Position) -> bool:
        """
        Save an existing position instance to positions list
        :param position: the position instance
        :return: True when the operation succeeded
        """
        if position.position_id not in self.positions:
            self.add_position(position)
            return True
        return False

    def clear(self):
        """
        Clear all positions and the position OrderedDict
        """
        for position in self.positions.values():
            position.clear()
        self._reset_positions()

    def create_position_id(self, position: position_import.Position) -> str:
        return self._position_id_factory(
            position.symbol, side=None if position.symbol_contract.is_one_way_position_mode() else position.side
        )

    @contextlib.contextmanager
    def disabled_positions_update_from_order(self):
        """
        Can be used to locally disable position refresh when an order is updated
        """
        self._enable_position_update_from_order = False
        try:
            yield
        finally:
            self._enable_position_update_from_order = True

    # private

    def _position_id_factory(
        self, symbol: str, side: typing.Union[None, enums.PositionSide], expiration_time=None
    ) -> str:
        """
        Generate a position ID for one way and hedge position modes
        :param symbol: the position symbol
        :param side: the position side. Should be None (or enums.PositionSide.BOTH) for one-way positions
        :param expiration_time: the symbol expiration timestamp
        :return: the computed position id
        """
        return f"{symbol}" \
               f"{'' if expiration_time is None else self.POSITION_ID_SEPARATOR + str(expiration_time)}" \
               f"{'' if side is enums.PositionSide.BOTH or side is None else self.POSITION_ID_SEPARATOR + side.value}"

    async def _finalize_position_creation(self, new_position, is_from_exchange_data=False) -> bool:
        """
        Ends a position creation process
        :param new_position: the new position instance
        :param is_from_exchange_data: True when the exchange creation comes from exchange data
        :return: True when the process succeeded
        """
        self.add_position(new_position)
        await new_position.initialize(is_from_exchange_data=is_from_exchange_data)
        return True

    def _create_symbol_position(self, symbol, position_id):
        """
        Creates a position when it doesn't exist for the specified symbol
        :param symbol: the new position symbol
        :param side: the new position id
        :return: the new symbol position instance
        """
        new_position = position_factory.create_symbol_position(self.trader, symbol)
        new_position.position_id = position_id
        self.add_position(new_position)
        return new_position

    def _get_or_create_position(self, symbol, side):
        """
        Get or create position by symbol and side
        :param symbol: the expected position symbol
        :param side: the expected position side
        :return: the matching position
        """
        expected_position_id = self._position_id_factory(symbol=symbol, side=side)
        try:
            return self.positions[expected_position_id]
        except KeyError:
            self._create_symbol_position(symbol, expected_position_id)
        return self.positions[expected_position_id]

    def _get_symbol_positions(self, symbol):
        """
        Get symbol positions in each side
        :param symbol: the position symbol
        :return: existing symbol positions list
        """
        positions = []
        for side in [enums.PositionSide.BOTH, enums.PositionSide.SHORT, enums.PositionSide.LONG]:
            position_id = self._position_id_factory(symbol=symbol, side=side)
            try:
                positions.append(self.positions[position_id])
            except KeyError:
                pass
        return positions

    def _reset_positions(self):
        """
        Clear all position references
        """
        self.positions = collections.OrderedDict()
