# pylint: disable=E0611
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
import asyncio

import octobot_commons.async_job as async_job
import octobot_commons.html_util as html_util

import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.channel.positions as positions_channel
import octobot_trading.constants as constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchange_data as exchange_data


class PositionsUpdater(positions_channel.PositionsProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    """
    Update positions from exchange
    Can also be used to update a specific positions from exchange
    """

    CHANNEL_NAME = constants.POSITIONS_CHANNEL
    POSITIONS_STARTING_REFRESH_TIME = 12
    POSITION_REFRESH_TIME = 9
    TIME_BETWEEN_POSITIONS_REFRESH = 3

    def __init__(self, channel):
        super().__init__(channel)
        # create async jobs
        self.positions_update_job = async_job.AsyncJob(
            self.fetch_and_push_positions,
            execution_interval_delay=self.POSITION_REFRESH_TIME,
            min_execution_delay=self.TIME_BETWEEN_POSITIONS_REFRESH
        )
        self.position_update_job = async_job.AsyncJob(
            self._position_fetch_and_push,
            is_periodic=False,
            enable_multiple_runs=True
        )
        self.position_update_job.add_job_dependency(self.positions_update_job)
        self.positions_update_job.add_job_dependency(self.position_update_job)

    async def initialize(self) -> None:
        """
        Initialize positions and future contracts
        """
        # fetch future contracts from exchange
        await self.initialize_contracts()

        # subscribe to mark_price channel if necessary
        if not self._has_mark_price_in_position():
            await exchanges_channel.get_chan(constants.MARK_PRICE_CHANNEL, self.channel.exchange_manager.id) \
                .new_consumer(self.handle_mark_price)

        # fetch current positions from exchange
        await self.initialize_positions()

        for pair in self._get_pairs_to_update():
            self.channel.exchange_manager.exchange_personal_data.positions_manager.set_initialized_event(pair)

    async def initialize_contracts(self) -> None:
        """
        Initialize exchange FutureContracts required to manage positions
        """
        for pair in self._get_pairs_to_update():
            try:
                await self.channel.exchange_manager.exchange.load_pair_contract(pair)
                await self._update_contract_settings(pair)
            except NotImplementedError as e:
                self.logger.debug(f"Can't to load {pair} contract info from exchange: {e}. "
                                  f"This contract will be created from fetched positions.")
            except Exception as e:
                self.logger.exception(e, False)
                self.logger.warning(
                    f"Failed to load {pair} contract info : {html_util.get_html_summary_if_relevant(e)}"
                )

    async def initialize_positions(self) -> None:
        """
        Initialize data before starting jobs
        """
        try:
            await self.fetch_and_push()
        except NotImplementedError:
            self.logger.warning("Position updater cannot fetch positions : required methods are not implemented")
            await self.stop()
        except errors.NotSupported:
            self.logger.warning(f"{self.channel.exchange_manager.exchange_name} is not supporting updates")
            await self.stop()
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Fail to initialize positions : {html_util.get_html_summary_if_relevant(e)}"
            )

    async def start(self):
        """
        Start updater jobs
        """
        if not self._should_run():
            return

        await self.initialize()
        await asyncio.sleep(self.POSITIONS_STARTING_REFRESH_TIME)
        await self.positions_update_job.run()

    async def fetch_and_push(self):
        """
        Update positions from exchange
        """
        await self.fetch_and_push_positions()
        await asyncio.sleep(self.TIME_BETWEEN_POSITIONS_REFRESH)

    def _should_run(self):
        return self.channel.exchange_manager.is_future or self.channel.exchange_manager.is_option

    def _is_relevant_position(self, position_dict):
        return position_dict and position_dict.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value, None) \
               in self._get_pairs_to_update()

    async def fetch_and_push_positions(self, retry_attempts=1):
        """
        Update positions from exchange
        """
        symbols = self._get_pairs_to_update() \
            if self.channel.exchange_manager.exchange.REQUIRES_SYMBOL_FOR_EMPTY_POSITION else None
        positions = await self.channel.exchange_manager.exchange.retry_n_time(
            retry_attempts,
            self.channel.exchange_manager.exchange.get_positions, symbols=symbols,
        )
        if positions:
            relevant_positions = [
                position
                for position in positions
                if self._is_relevant_position(position)
            ]
            # initialize relevant contracts first as they might be waited for
            updated = exchange_data.update_contracts_from_positions(self.channel.exchange_manager, relevant_positions)
            if exchange_data.update_contracts_from_positions(self.channel.exchange_manager, positions) or updated:
                await self._update_positions_contract_settings(positions)
            # only consider positions that are relevant to the current setup
            await self._push_positions(relevant_positions)

    async def _push_positions(self, positions):
        await self.push(positions)

        if self._should_push_mark_price():
            for position in positions:
                await self.extract_mark_price(position)

    async def _update_positions_contract_settings(self, positions):
        for position in positions:
            symbol = position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value, None)
            if symbol is not None and symbol in self._get_pairs_to_update():
                await self._update_contract_settings(symbol)

    async def _update_contract_settings(self, symbol):
        try:
            if constants.FORCED_MARGIN_TYPE:
                await self.channel.exchange_manager.trader.set_margin_type(
                    symbol, enums.PositionSide.BOTH, constants.FORCED_MARGIN_TYPE
                )
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Fail to update contracts settings : {html_util.get_html_summary_if_relevant(e)}"
            )
        finally:
            self.channel.exchange_manager.exchange.set_contract_initialized_event(symbol)

    async def extract_mark_price(self, position_dict: dict):
        try:
            await exchanges_channel.get_chan(constants.MARK_PRICE_CHANNEL,
                                             self.channel.exchange_manager.id).get_internal_producer(). \
                push(position_dict[enums.ExchangeConstantsPositionColumns.SYMBOL.value],
                     position_dict[enums.ExchangeConstantsPositionColumns.MARK_PRICE.value])
        except Exception as e:
            self.logger.exception(e, True, f"Fail to update mark price from position : {e}")

    async def update_position_from_exchange(self, position,
                                            should_notify=False,
                                            wait_for_refresh=False,
                                            force_job_execution=False,
                                            create_position_producer_if_missing=True):
        await self.position_update_job.run(force=True, wait_for_task_execution=wait_for_refresh,
                                           ignore_dependencies_check=force_job_execution,
                                           position=position, should_notify=should_notify)

    async def _position_fetch_and_push(self, position, should_notify=False):
        """
        Update Position from exchange
        :param position: the position to update
        :param should_notify: if Positions channel consumers should be notified
        :return: True if the position was updated
        """
        exchange_name = self.channel.exchange_manager.exchange_name
        self.logger.debug(f"Requested update for position: {position} on {exchange_name}")
        raw_position = await self.channel.exchange_manager.exchange.get_position(position.symbol)

        if raw_position:
            self.logger.debug(f"Received update for {position} on {exchange_name}: {raw_position}")

            await self.channel.exchange_manager.exchange_personal_data.handle_position_update(
                symbol=raw_position[enums.ExchangeConstantsPositionColumns.SYMBOL.value],
                side=raw_position[enums.ExchangeConstantsPositionColumns.SIDE.value],
                raw_position=raw_position,
                should_notify=should_notify
            )
        else:
            self.logger.debug(
                f"Can't received update for {position} on {exchange_name}: received position is {raw_position}"
            )


    def _should_push_mark_price(self):
        return self._has_mark_price_in_position()

    def _has_mark_price_in_position(self):
        return self.channel.exchange_manager.exchange.MARK_PRICE_IN_POSITION

    async def handle_mark_price(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price):
        """
        MarkPrice channel consumer callback
        """
        try:
            for symbol_position in self.channel.exchange_manager.exchange_personal_data.positions_manager. \
                    get_symbol_positions(symbol=symbol):
                await symbol_position.update(mark_price=mark_price)
        except Exception as e:
            self.logger.exception(e, True, f"Fail to handle mark price : {e}")

    async def modify(self, added_pairs=None, removed_pairs=None):
        if not self._should_run():
            return
        if added_pairs:
            self.logger.info(f"Fetching positions for new traded symbols: {added_pairs}...")
            await self.fetch_and_push_positions()

    def _get_pairs_to_update(self):
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs + self.channel.exchange_manager.exchange_config.additional_traded_pairs

    async def stop(self) -> None:
        """
        Stop producer by stopping its jobs
        """
        await super().stop()
        if not self._should_run():
            return
        self.positions_update_job.stop()
        self.position_update_job.stop()

    async def resume(self) -> None:
        """
        Resume producer by restarting its jobs
        """
        await super().resume()
        if not self._should_run():
            return
        if not self.is_running:
            await self.run()
