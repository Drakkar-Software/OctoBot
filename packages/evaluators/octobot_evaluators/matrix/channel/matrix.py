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
import octobot_evaluators.constants as constants
import octobot_evaluators.matrix as matrix


class MatrixChannelConsumer(evaluator_channels.EvaluatorChannelConsumer):
    """
    EvaluatorChannelConsumer adapted for MatrixChannel
    """


class MatrixChannelSupervisedConsumer(evaluator_channels.EvaluatorChannelSupervisedConsumer):
    """
    EvaluatorChannelSupervisedConsumer adapted for MatrixChannel
    """


class MatrixChannelProducer(evaluator_channels.EvaluatorChannelProducer):
    """
    EvaluatorChannelProducer adapted for MatrixChannel
    """

    # noinspection PyMethodOverriding
    async def send(self,
                   matrix_id,
                   evaluator_name,
                   evaluator_type,
                   eval_note,
                   eval_note_type=constants.EVALUATOR_EVAL_DEFAULT_TYPE,
                   eval_note_description=None,
                   eval_note_metadata=None,
                   exchange_name=None,
                   cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                   symbol=channel_constants.CHANNEL_WILDCARD,
                   time_frame=None,
                   origin_consumer=None):
        for consumer in self.channel.get_filtered_consumers(matrix_id=matrix_id,
                                                            cryptocurrency=cryptocurrency,
                                                            symbol=symbol,
                                                            time_frame=time_frame,
                                                            evaluator_type=evaluator_type,
                                                            evaluator_name=evaluator_name,
                                                            exchange_name=exchange_name,
                                                            origin_consumer=origin_consumer):
            await consumer.queue.put({
                "matrix_id": matrix_id,
                "evaluator_name": evaluator_name,
                "evaluator_type": evaluator_type,
                "eval_note": eval_note,
                "eval_note_type": eval_note_type,
                "eval_note_description": eval_note_description,
                "eval_note_metadata": eval_note_metadata,
                "exchange_name": exchange_name,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "time_frame": time_frame
            })

    async def send_eval_note(self,
                             matrix_id: str,
                             evaluator_name: str,
                             evaluator_type,
                             eval_note,
                             eval_note_type,
                             eval_note_description=None,
                             eval_note_metadata=None,
                             eval_time: float = 0,
                             exchange_name: str = None,
                             cryptocurrency: str = None,
                             symbol: str = None,
                             time_frame=None,
                             origin_consumer=None,
                             notify: bool = True):
        matrix.set_tentacle_value(
            matrix_id=matrix_id,
            tentacle_type=eval_note_type,
            tentacle_value=eval_note,
            timestamp=eval_time,
            tentacle_path=matrix.get_matrix_default_value_path(
                exchange_name=exchange_name,
                tentacle_type=evaluator_type,
                tentacle_name=evaluator_name,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame
            ),
            description=eval_note_description,
            metadata=eval_note_metadata
        )
        if notify:
            await self.send(matrix_id=matrix_id,
                            evaluator_name=evaluator_name,
                            evaluator_type=evaluator_type,
                            eval_note=eval_note,
                            eval_note_type=eval_note_type,
                            eval_note_description=eval_note_description,
                            eval_note_metadata=eval_note_metadata,
                            exchange_name=exchange_name,
                            cryptocurrency=cryptocurrency,
                            symbol=symbol,
                            time_frame=time_frame,
                            origin_consumer=origin_consumer)


class MatrixChannel(evaluator_channels.EvaluatorChannel):
    FILTER_SIZE = 1
    PRODUCER_CLASS = MatrixChannelProducer
    CONSUMER_CLASS = MatrixChannelConsumer

    MATRIX_ID_KEY = "matrix_id"
    CRYPTOCURRENCY_KEY = "cryptocurrency"
    SYMBOL_KEY = "symbol"
    TIME_FRAME_KEY = "time_frame"
    EVALUATOR_TYPE_KEY = "evaluator_type"
    EXCHANGE_NAME_KEY = "exchange_name"
    EVALUATOR_NAME_KEY = "evaluator_name"

    def __init__(self, matrix_id):
        super().__init__(matrix_id)
        self.logger = logging.get_logger(f"{self.__class__.__name__}")

    # noinspection PyMethodOverriding
    async def new_consumer(self,
                           callback: object,
                           size: int = 0,
                           priority_level: int = evaluator_channels.EvaluatorChannel.DEFAULT_PRIORITY_LEVEL,
                           matrix_id: str = channel_constants.CHANNEL_WILDCARD,
                           cryptocurrency: str = channel_constants.CHANNEL_WILDCARD,
                           symbol: str = channel_constants.CHANNEL_WILDCARD,
                           evaluator_name: str = channel_constants.CHANNEL_WILDCARD,
                           evaluator_type: object = channel_constants.CHANNEL_WILDCARD,
                           exchange_name: str = channel_constants.CHANNEL_WILDCARD,
                           time_frame=channel_constants.CHANNEL_WILDCARD,
                           supervised: bool = False):
        consumer_class = MatrixChannelSupervisedConsumer if supervised else MatrixChannelConsumer
        consumer = consumer_class(callback, size=size, priority_level=priority_level)
        await self._add_new_consumer_and_run(consumer,
                                             matrix_id=matrix_id,
                                             cryptocurrency=cryptocurrency,
                                             symbol=symbol,
                                             evaluator_name=evaluator_name,
                                             evaluator_type=evaluator_type,
                                             exchange_name=exchange_name,
                                             time_frame=time_frame)
        return consumer

    def get_filtered_consumers(self,
                               matrix_id=channel_constants.CHANNEL_WILDCARD,
                               cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD,
                               evaluator_type=channel_constants.CHANNEL_WILDCARD,
                               time_frame=channel_constants.CHANNEL_WILDCARD,
                               evaluator_name=channel_constants.CHANNEL_WILDCARD,
                               exchange_name=channel_constants.CHANNEL_WILDCARD,
                               origin_consumer=None):
        return self.get_consumer_from_filters({
            self.MATRIX_ID_KEY: matrix_id,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame,
            self.EVALUATOR_TYPE_KEY: evaluator_type,
            self.EVALUATOR_NAME_KEY: evaluator_name,
            self.EXCHANGE_NAME_KEY: exchange_name
        },
            origin_consumer=origin_consumer)

    async def _add_new_consumer_and_run(self, consumer,
                                        matrix_id=channel_constants.CHANNEL_WILDCARD,
                                        cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD,
                                        evaluator_name=channel_constants.CHANNEL_WILDCARD,
                                        evaluator_type=channel_constants.CHANNEL_WILDCARD,
                                        exchange_name=channel_constants.CHANNEL_WILDCARD,
                                        time_frame=None):
        consumer_filters: dict = {
            self.MATRIX_ID_KEY: matrix_id,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame,
            self.EVALUATOR_NAME_KEY: evaluator_name,
            self.EXCHANGE_NAME_KEY: exchange_name,
            self.EVALUATOR_TYPE_KEY: evaluator_type
        }

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run()
        self.logger.debug(f"Consumer started for : "
                          f"[matrix_id={matrix_id},"
                          f" cryptocurrency={cryptocurrency},"
                          f" symbol={symbol},"
                          f" time_frame={time_frame},"
                          f" evaluator_name={evaluator_name},"
                          f" exchange_name={exchange_name},"
                          f" evaluator_type={evaluator_type}]")
