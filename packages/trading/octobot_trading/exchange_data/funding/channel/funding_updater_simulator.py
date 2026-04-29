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
import octobot_backtesting.api as api
import octobot_commons.errors as errors

import octobot_trading.exchange_data.funding.channel.funding_updater as funding_updater
import octobot_trading.util as util


class FundingUpdaterSimulator(funding_updater.FundingUpdater):
    """
    The Funding Update Simulator simulates the exchange funding rate and send it to the Funding Channel
    """
    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer

        self.initial_timestamp = api.get_backtesting_current_time(self.channel.exchange_manager.exchange.backtesting)
        self.last_pushed_timestamp = 0
        self.time_consumer = None

    async def start(self):
        await self.resume()

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            current_time = api.get_backtesting_current_time(self.channel.exchange_manager.exchange.backtesting)
            if current_time - self.last_pushed_timestamp > self.FUNDING_REFRESH_TIME_MAX \
                    or self.last_pushed_timestamp == 0:
                self.last_pushed_timestamp = current_time
                for pair in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
                    funding_rate = await self.channel.exchange_manager.exchange.get_funding_rate(symbol=pair)
                    await self._push_funding(
                        symbol=pair,
                        funding_rate=funding_rate,
                        predicted_funding_rate=funding_rate)
        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data : {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access funding_data : {e}")
        except Exception as e:
            self.logger.exception(e, True, f"Error when updating from timestamp: {e}")

    async def pause(self):
        await util.pause_time_consumer(self)

    async def stop(self):
        await util.stop_and_pause(self)

    async def resume(self):
        await util.resume_time_consumer(self, self.handle_timestamp)
