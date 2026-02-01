#  Drakkar-Software OctoBot-Backtesting
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

import async_channel.channels as channels
import async_channel.util as channel_util

import octobot_commons.logging as logging
import octobot_commons.tentacles_management as tentacles_management

import octobot_backtesting.util as backtesting_util
import octobot_backtesting.time as backtesting_time


class Backtesting:
    def __init__(self, config, exchange_ids, matrix_id, backtesting_files,
                 importers_by_data_file=None, backtest_data=None, bot_id=None):
        self.config = config
        self.backtesting_files = backtesting_files
        self.importers_by_data_file = importers_by_data_file or {}
        self.logger = logging.get_logger(self.__class__.__name__)

        self.exchange_ids = exchange_ids
        self.matrix_id = matrix_id
        self.bot_id = bot_id or ""

        self.importers = []
        self.backtest_data = backtest_data
        self.time_manager = None
        self.time_updater = None
        self.time_channel = None

    async def initialize(self):
        time_chan_name = self.get_time_chan_name()  # not in try to be able to raise on error
        try:
            self.time_manager = backtesting_time.TimeManager(config=self.config)
            self.time_manager.initialize()

            self.time_channel = await channel_util.create_channel_instance(
                backtesting_time.TimeChannel,
                channels.set_chan,
                is_synchronized=True,
                channel_name=time_chan_name
            )

            self.time_updater = backtesting_time.TimeUpdater(
                channels.get_chan(self.get_time_chan_name()),
                self
            )
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing backtesting : {e}.")

    def use_accurate_price_time_frame(self) -> bool:
        for importer in self.importers:
            if not importer.provides_accurate_price_time_frame():
                return False
        if self.backtest_data:
            return self.backtest_data.use_accurate_price_time_frame
        return True

    def get_time_chan_name(self):
        return backtesting_time.TimeChannel.get_name(self.bot_id)

    async def stop(self):
        await self.delete_time_channel()

    async def delete_time_channel(self):
        await self.time_channel.stop()
        for consumer in self.time_channel.consumers:
            await self.time_channel.remove_consumer(consumer)
        self.time_channel.flush()
        channels.del_chan(self.get_time_chan_name())

    async def start_time_updater(self):
        await self.time_updater.run()

    async def _create_importer(self, backtesting_file):
        return await backtesting_util.create_importer_from_backtesting_file_name(
            self.config,
            backtesting_file,
            backtesting_util.get_default_importer()
        )

    async def create_importers(self):
        try:
            self.importers = []
            for backtesting_file in self.backtesting_files:
                if self.importers_by_data_file is not None and backtesting_file in self.importers_by_data_file:
                    self.importers.append(self.importers_by_data_file[backtesting_file])
                else:
                    self.importers.append(await self._create_importer(backtesting_file))
        except TypeError:
            pass

    async def handle_time_update(self, timestamp):
        if self.time_manager:
            self.time_manager.set_current_timestamp(timestamp)

    def get_importers(self, importer_parent_class=None) -> list:
        return [importer
                for importer in self.importers
                if tentacles_management.default_parents_inspection(importer.__class__, importer_parent_class)] \
            if importer_parent_class is not None else self.importers

    def get_progress(self):
        if self._has_nothing_to_do():
            return 0
        return 1 - (self.time_manager.get_remaining_iteration() / self.time_manager.get_total_iteration())

    def is_in_progress(self):
        if self._has_nothing_to_do():
            return False
        else:
            return self.time_manager.get_remaining_iteration() > 0

    def _has_nothing_to_do(self):
        return not self.time_manager or self.time_manager.get_total_iteration() == 0

    def has_finished(self):
        return self.time_updater and self.time_updater.finished_event.is_set()
