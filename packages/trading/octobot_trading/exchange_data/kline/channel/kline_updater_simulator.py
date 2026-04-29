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
import octobot_commons.errors as errors

import octobot_trading.exchange_data.kline.channel.kline_updater as kline_updater
import octobot_trading.util as util


class KlineUpdaterSimulator(kline_updater.KlineUpdater):
    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer
        self.exchange_name = self.channel.exchange_manager.exchange_name

        self.last_timestamp_pushed = 0
        self.time_consumer = None

    async def start(self):
        await self.resume()

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            for time_frame in self.channel.exchange_manager.exchange_config.available_time_frames:
                for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
                    kline_data = await self.exchange_data_importer.get_kline_from_timestamps(
                        exchange_name=self.exchange_name,
                        symbol=pair,
                        time_frame=time_frame,
                        inferior_timestamp=timestamp,
                        limit=1)
                    if kline_data and kline_data[0][0] > self.last_timestamp_pushed:
                        self.last_timestamp_pushed = kline_data[0][0]
                        await self.push(time_frame, pair, kline_data[0][-1])
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data : {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access kline_data : {e}")

    async def pause(self):
        if self.time_consumer is not None:
            await util.get_time_channel(self).remove_consumer(self.time_consumer)

    async def stop(self):
        await util.stop_and_pause(self)

    async def resume(self):
        if self.time_consumer is None and not self.channel.is_paused:
            self.time_consumer = await util.get_time_channel(self).new_consumer(self.handle_timestamp)
