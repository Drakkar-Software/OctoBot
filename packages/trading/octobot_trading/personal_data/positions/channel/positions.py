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

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as enums
import octobot_trading.constants as constants


class PositionsProducer(exchanges_channel.ExchangeChannelProducer):
    async def push(self, positions):
        await self.perform(positions)

    async def perform(self, positions):
        try:
            for position in positions:
                if not position:
                    continue
                symbol: str = position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]
                changed = await self.channel.exchange_manager.exchange_personal_data. \
                    handle_position_update(symbol=symbol,
                                           side=position[enums.ExchangeConstantsPositionColumns.SIDE.value],
                                           raw_position=position,
                                           should_notify=False)

                if changed:
                    await self.send(cryptocurrency=self.channel.exchange_manager.exchange.
                                    get_pair_cryptocurrency(symbol),
                                    symbol=symbol,
                                    position=position,
                                    is_updated=changed)
        except asyncio.CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.exception(e, True, f"Exception when triggering update: {e}")

    async def send(self, cryptocurrency, symbol, position, is_updated=False):
        for consumer in self.channel.get_filtered_consumers(symbol=symbol):
            await consumer.queue.put({
                "exchange": self.channel.exchange_manager.exchange_name,
                "exchange_id": self.channel.exchange_manager.id,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "position": position,
                "is_updated": is_updated
            })

    async def update_position_from_exchange(self, position,
                                            should_notify=False,
                                            wait_for_refresh=False,
                                            force_job_execution=False,
                                            create_position_producer_if_missing=True):
        """
        Trigger position job refresh from exchange
        :param position: the position to update
        :param wait_for_refresh: if True, wait until the position refresh task to finish
        :param should_notify: if Positions channel consumers should be notified
        :param force_job_execution: When True, position_update_job will bypass its dependencies check
        :param create_position_producer_if_missing: Should be set to False when called by self to prevent spamming
        :return: True if the position was updated
        """
        try:
            await (exchanges_channel.get_chan(
                constants.POSITIONS_CHANNEL, self.channel.exchange_manager.id
            ).producers[-1].update_position_from_exchange(
                position,
                should_notify=should_notify,
                force_job_execution=force_job_execution,
                wait_for_refresh=wait_for_refresh
            ))
        except IndexError:
            if not self.channel.exchange_manager.is_simulated and create_position_producer_if_missing:
                self.logger.debug("Missing positions producer, starting one...")
                await exchanges.create_authenticated_producer_from_parent(self.channel.exchange_manager,
                                                                          self.__class__,
                                                                          force_register_producer=True)
                await self.update_position_from_exchange(
                    position,
                    should_notify=should_notify,
                    wait_for_refresh=wait_for_refresh,
                    force_job_execution=force_job_execution,
                    create_position_producer_if_missing=False
                )



class PositionsChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = PositionsProducer
    CONSUMER_CLASS = exchanges_channel.ExchangeChannelConsumer
