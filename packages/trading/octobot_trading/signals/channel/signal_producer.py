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
import async_channel.enums as channel_enums
import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_commons.signals as signals
import octobot_trading.signals.channel.remote_trading_signal as signals_channel


class RemoteTradingSignalProducer(signals_channel.RemoteTradingSignalChannelProducer):
    def __init__(self, channel, bot_id):
        super().__init__(channel)
        # the trading mode instance logger
        self.logger = logging.get_logger(self.__class__.__name__)

        # Define trading modes default consumer priority level
        self.priority_level: int = channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value

        self.bot_id = bot_id

    async def stop(self) -> None:
        """
        Stops non-triggered tasks management
        """
        self.logger.debug("Stopping producer: this should normally not be happening unless OctoBot is stopping")
        await super().stop()

    async def subscribe_to_product_feed(self, feed_id):
        await authentication.Authenticator.instance().register_feed_callback(commons_enums.CommunityChannelTypes.SIGNAL,
                                                                             self.on_new_signal,
                                                                             identifier=feed_id)

    async def on_new_signal(self, parsed_message) -> None:
        try:
            signal_bundle = signals.create_signal_bundle(parsed_message)
            if not signal_bundle.signals:
                self.logger.info(f"No signal in received signal bundle, message: {parsed_message}")
            for signal in signal_bundle.signals:
                await self.send(signal, self.bot_id, signal_bundle.identifier, signal_bundle.version)
        except Exception as e:
            self.logger.exception(e, True, f"Error when processing signal: {e}")

    def flush(self) -> None:
        """
        Flush all instance objects reference
        """
        self.exchange_manager = None
