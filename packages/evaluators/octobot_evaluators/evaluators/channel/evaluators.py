# cython: language_level=3
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

import async_channel.constants as channel_constants

import octobot_commons.logging as logging

import octobot_evaluators.evaluators.channel as evaluator_channels


class EvaluatorsChannelConsumer(evaluator_channels.EvaluatorChannelConsumer):
    """
    EvaluatorChannelConsumer adapted for EvaluatorsChannel
    """


class EvaluatorsChannelProducer(evaluator_channels.EvaluatorChannelProducer):
    """
    EvaluatorChannelProducer adapted for EvaluatorsChannel
    """

    # noinspection PyMethodOverriding
    async def send(self,
                   matrix_id,
                   data,
                   evaluator_name=channel_constants.CHANNEL_WILDCARD,
                   evaluator_type=channel_constants.CHANNEL_WILDCARD,
                   exchange_name=channel_constants.CHANNEL_WILDCARD,
                   cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                   symbol=channel_constants.CHANNEL_WILDCARD,
                   time_frame=channel_constants.CHANNEL_WILDCARD,
                   origin_consumer=None):
        for consumer in self.channel.get_filtered_consumers(matrix_id=matrix_id,
                                                            evaluator_name=evaluator_name,
                                                            evaluator_type=evaluator_type,
                                                            exchange_name=exchange_name,
                                                            cryptocurrency=cryptocurrency,
                                                            symbol=symbol,
                                                            time_frame=time_frame,
                                                            origin_consumer=origin_consumer):
            await consumer.queue.put({
                "matrix_id": matrix_id,
                "evaluator_name": evaluator_name,
                "evaluator_type": evaluator_type,
                "exchange_name": exchange_name,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "time_frame": time_frame,
                "data": data
            })


class EvaluatorsChannel(evaluator_channels.EvaluatorChannel):
    PRODUCER_CLASS = EvaluatorsChannelProducer
    CONSUMER_CLASS = EvaluatorsChannelConsumer

    MATRIX_ID_KEY = "matrix_id"
    EVALUATOR_NAME_KEY = "evaluator_name"
    EVALUATOR_TYPE_KEY = "evaluator_type"
    EXCHANGE_NAME_KEY = "exchange_name"
    CRYPTOCURRENCY_KEY = "cryptocurrency"
    SYMBOL_KEY = "symbol"
    TIME_FRAME_KEY = "time_frame"

    def __init__(self, matrix_id):
        super().__init__(matrix_id)
        self.logger = logging.get_logger(f"{self.__class__.__name__}")

    # noinspection PyMethodOverriding
    async def new_consumer(self,
                           callback: object,
                           size: int = 0,
                           priority_level: int = evaluator_channels.EvaluatorChannel.DEFAULT_PRIORITY_LEVEL,
                           matrix_id: str = channel_constants.CHANNEL_WILDCARD,
                           evaluator_name: str = channel_constants.CHANNEL_WILDCARD,
                           evaluator_type: object = channel_constants.CHANNEL_WILDCARD,
                           exchange_name: str = channel_constants.CHANNEL_WILDCARD,
                           cryptocurrency: str = channel_constants.CHANNEL_WILDCARD,
                           symbol: str = channel_constants.CHANNEL_WILDCARD,
                           time_frame=channel_constants.CHANNEL_WILDCARD) -> EvaluatorsChannelConsumer:
        consumer = EvaluatorsChannelConsumer(callback, size=size, priority_level=priority_level)
        await self._add_new_consumer_and_run(consumer,
                                             matrix_id=matrix_id,
                                             evaluator_name=evaluator_name,
                                             evaluator_type=evaluator_type,
                                             exchange_name=exchange_name,
                                             cryptocurrency=cryptocurrency,
                                             symbol=symbol,
                                             time_frame=time_frame)
        return consumer

    def get_filtered_consumers(self,
                               matrix_id=channel_constants.CHANNEL_WILDCARD,
                               evaluator_name=channel_constants.CHANNEL_WILDCARD,
                               evaluator_type=channel_constants.CHANNEL_WILDCARD,
                               exchange_name=channel_constants.CHANNEL_WILDCARD,
                               cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD,
                               time_frame=channel_constants.CHANNEL_WILDCARD,
                               origin_consumer=None):
        return self.get_consumer_from_filters({
            self.MATRIX_ID_KEY: matrix_id,
            self.EVALUATOR_NAME_KEY: evaluator_name,
            self.EVALUATOR_TYPE_KEY: evaluator_type,
            self.EXCHANGE_NAME_KEY: exchange_name,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame,
        },
            origin_consumer=origin_consumer)

    async def _add_new_consumer_and_run(self, consumer,
                                        matrix_id=channel_constants.CHANNEL_WILDCARD,
                                        evaluator_name=channel_constants.CHANNEL_WILDCARD,
                                        evaluator_type=channel_constants.CHANNEL_WILDCARD,
                                        exchange_name=channel_constants.CHANNEL_WILDCARD,
                                        cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD,
                                        time_frame=channel_constants.CHANNEL_WILDCARD):
        consumer_filters: dict = {
            self.MATRIX_ID_KEY: matrix_id,
            self.EVALUATOR_NAME_KEY: evaluator_name,
            self.EVALUATOR_TYPE_KEY: evaluator_type,
            self.EXCHANGE_NAME_KEY: exchange_name,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame
        }

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run()
