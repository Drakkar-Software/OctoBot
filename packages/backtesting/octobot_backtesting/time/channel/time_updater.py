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
import asyncio
import time

import octobot_backtesting.channels_manager as channels_manager
import octobot_backtesting.time.channel.time as time_channel


class TimeUpdater(time_channel.TimeProducer):
    def __init__(self, channel, backtesting):
        super().__init__(channel, backtesting)
        self.backtesting = backtesting
        self.time_manager = backtesting.time_manager
        self.starting_time = time.time()
        self.simulation_duration = 0
        self.finished_event = asyncio.Event()

        self.channels_manager = None

    async def start(self):
        self.channels_manager = channels_manager.ChannelsManager(
            self.backtesting.exchange_ids,
            self.backtesting.matrix_id,
            self.backtesting.get_time_chan_name(),

        )
        await self.channels_manager.initialize()
        cleared_producers = False
        while not self.should_stop:
            try:
                current_timestamp = self.time_manager.current_timestamp
                await self.push(self.time_manager.current_timestamp)

                self.logger.info(f"Progress : {round(min(self.backtesting.get_progress(), 1) * 100, 2)}% "
                                 f"[{current_timestamp}]")

                # Call synchronous channels callbacks
                await self.channels_manager.handle_new_iteration(current_timestamp)

                if self.time_manager.has_finished():
                    self.logger.debug("Maximum timestamp hit, stopping...")
                    self.simulation_duration = time.time() - self.starting_time
                    self.logger.info(f"Lasted {round(self.simulation_duration, 3)}s")
                    await self.stop()
                else:
                    # jump to the next time point
                    self.time_manager.next_timestamp()
                    if not cleared_producers:
                        self.channels_manager.clear_empty_channels_producers()
                        self.channels_manager.update_producers_by_priority_levels()
                        cleared_producers = True
            except Exception as e:
                self.logger.exception(e, True, f"Fail to update time : {e}")
        await self.backtesting.delete_time_channel()
        self.channels_manager.flush()
        self.finished_event.set()
        self.backtesting = None

    async def stop(self) -> None:
        self.channels_manager.stop()
        await super().stop()

    async def modify(self, set_timestamp=None, minimum_timestamp=None, maximum_timestamp=None) -> None:
        if set_timestamp is not None:
            self.time_manager.set_current_timestamp(set_timestamp)

        if minimum_timestamp is not None:
            self.time_manager.set_minimum_timestamp(minimum_timestamp)
            self.time_manager.set_current_timestamp(minimum_timestamp)

        if maximum_timestamp is not None:
            self.time_manager.set_maximum_timestamp(maximum_timestamp)

    async def run(self) -> None:
        """
        Overrides default producer run() because producer task wont be created in synchronized context
        """
        await self.channel.register_producer(self)
        self.create_task()
