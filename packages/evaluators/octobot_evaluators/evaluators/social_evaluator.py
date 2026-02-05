#  Drakkar-Software OctoBot-Evaluators
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
import abc 
import typing

import async_channel.channels as channels

import octobot_evaluators.evaluators as evaluator

import octobot_services.api as service_api
import octobot_trading.api as exchange_api


class SocialEvaluator(evaluator.AbstractEvaluator):
    __metaclass__ = evaluator.AbstractEvaluator
    SERVICE_FEED_CLASS = None
    ALLOW_SUPER_CLASS_CONFIG = True

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.exchange_id: typing.Optional[str] = None
        self.bot_id: typing.Optional[str] = None
        self.feed_config = {}

    # Override if no service feed is required for a social evaluator
    async def start(self, bot_id: str) -> bool:
        """
        :return: success of the evaluator's start
        """
        self.bot_id = bot_id
        if self.SERVICE_FEED_CLASS is None:
            self.logger.error("SERVICE_FEED_CLASS is required to use a service feed. Consumer can't start.")
        else:
            await super().start(self.bot_id)
            service_feed = service_api.get_service_feed(self.SERVICE_FEED_CLASS, self.bot_id)
            if service_feed is not None:
                service_feed.update_feed_config(self.feed_config)
                await channels.get_chan(service_feed.FEED_CHANNEL.get_name()).new_consumer(self._feed_callback)
                # store exchange_id to use it later for evaluation timestamps
                self.exchange_id = exchange_api.get_exchange_id_from_matrix_id(self.exchange_name, self.matrix_id)
                return True
        return False

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        """
        :param current_time: the current time
        :return: the data cache from the service feed
        """
        try:
            import octobot_services.api as service_api
            return service_api.get_service_feed(self.SERVICE_FEED_CLASS, self.bot_id).get_data_cache(current_time, key)
        except ImportError as e:
            self.logger.exception(e, True, "Can't get data cache: requires OctoBot-Services package installed")
        return None

    def get_current_exchange_time(self):
        try:
            import octobot_trading.api as exchange_api
            if self.exchange_id is not None:
                return exchange_api.get_exchange_current_time(
                    exchange_api.get_exchange_manager_from_exchange_name_and_id(
                        self.exchange_name,
                        self.exchange_id
                    )
                )
        except ImportError:
            self.logger.error(f"Can't get current exchange time: requires OctoBot-Trading package installed")
        return None

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        currencies, _, _ = super()._get_tentacle_registration_topic(all_symbols_by_crypto_currencies,
                                                                    time_frames,
                                                                    real_time_time_frames)
        symbols = [self.symbol]
        to_handle_time_frames = [self.time_frame]
        # by default no symbol registration for social evaluators
        # by default no time frame re+gistration for social evaluators
        return currencies, symbols, to_handle_time_frames

    @abc.abstractmethod
    async def _feed_callback(self, *args):
        raise NotImplementedError("_feed_callback is not implemented")
