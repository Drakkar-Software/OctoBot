# pylint: disable=E0203
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

import async_channel.channels as channels
import async_channel.enums as channel_enums
import async_channel.constants as channel_constants
import async_channel.consumer as consumers
import async_channel.producer as producers

import octobot_commons.logging as logging

import octobot_evaluators.constants as constants


class EvaluatorChannelConsumer(consumers.Consumer):
    """
    Consumer adapted for EvaluatorChannel
    """


class EvaluatorChannelSupervisedConsumer(consumers.SupervisedConsumer):
    """
    SupervisedConsumer adapted for EvaluatorChannel
    """


class EvaluatorChannelProducer(producers.Producer):
    """
    Producer adapted for EvaluatorChannel
    """


class EvaluatorChannel(channels.Channel):
    PRODUCER_CLASS = EvaluatorChannelProducer
    CONSUMER_CLASS = EvaluatorChannelConsumer
    DEFAULT_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value

    def __init__(self, matrix_id):
        super().__init__()
        self.matrix_id = matrix_id

    def get_consumer_from_filters(self, consumer_filters, origin_consumer=None) -> list:
        """
        Returns the instance filtered consumers list except origin_consumer if provided
        :param consumer_filters: the consumer filters dict
        :param origin_consumer: the consumer behind the call if any else None
        :return: the filtered consumer list
        """
        return [consumer
                for consumer in super(EvaluatorChannel, self).get_consumer_from_filters(consumer_filters)
                if origin_consumer is None or consumer is not origin_consumer]


def set_chan(chan, name) -> None:
    chan_name = chan.get_name() if name else name

    try:
        evaluator_chan = channels.ChannelInstances.instance().channels[chan.matrix_id]
    except KeyError:
        channels.ChannelInstances.instance().channels[chan.matrix_id] = {}
        evaluator_chan = channels.ChannelInstances.instance().channels[chan.matrix_id]

    if chan_name not in evaluator_chan:
        evaluator_chan[chan_name] = chan
    else:
        raise ValueError(f"Channel {chan_name} already exists.")


def get_evaluator_channels(matrix_id) -> dict:
    try:
        return channels.ChannelInstances.instance().channels[matrix_id]
    except KeyError as e:
        raise KeyError(f"Channels not found with matrix_id: {matrix_id}") from e


def del_evaluator_channel_container(matrix_id):
    try:
        channels.ChannelInstances.instance().channels.pop(matrix_id, None)
    except KeyError as e:
        raise KeyError(f"Channels not found with matrix_id: {matrix_id}") from e


def get_chan(chan_name, matrix_id) -> EvaluatorChannel:
    try:
        return channels.ChannelInstances.instance().channels[matrix_id][chan_name]
    except KeyError as e:
        raise KeyError(f"Channel {chan_name} not found with matrix_id: {matrix_id}") from e


def del_chan(chan_name, matrix_id) -> None:
    try:
        channels.ChannelInstances.instance().channels[matrix_id].pop(chan_name, None)
    except KeyError:
        logging.get_logger(EvaluatorChannel.__name__).warning(f"Can't del chan {chan_name} with matrix_id: {matrix_id}")


async def trigger_technical_evaluators_re_evaluation_with_updated_data(matrix_id,
                                                                       evaluator_name,
                                                                       evaluator_type,
                                                                       exchange_name,
                                                                       cryptocurrency,
                                                                       symbol,
                                                                       exchange_id,
                                                                       time_frames
                                                                       ):
    # first reset evaluations to avoid partially updated TA cycle validation
    await get_chan(constants.EVALUATORS_CHANNEL, matrix_id).get_internal_producer().send(
        matrix_id,
        data={
            constants.EVALUATOR_CHANNEL_DATA_ACTION: constants.RESET_EVALUATION,
            constants.EVALUATOR_CHANNEL_DATA_TIME_FRAMES: time_frames
        },
        evaluator_name=evaluator_name,
        evaluator_type=evaluator_type,
        exchange_name=exchange_name,
        cryptocurrency=cryptocurrency,
        symbol=symbol,
        time_frame=channel_constants.CHANNEL_WILDCARD
    )
    await get_chan(constants.EVALUATORS_CHANNEL, matrix_id).get_internal_producer().send(
        matrix_id,
        data={
            constants.EVALUATOR_CHANNEL_DATA_ACTION: constants.TA_RE_EVALUATION_TRIGGER_UPDATED_DATA,
            constants.EVALUATOR_CHANNEL_DATA_EXCHANGE_ID: exchange_id,
            constants.EVALUATOR_CHANNEL_DATA_TIME_FRAMES: time_frames
        },
        evaluator_name=evaluator_name,
        evaluator_type=evaluator_type,
        exchange_name=exchange_name,
        cryptocurrency=cryptocurrency,
        symbol=symbol,
        time_frame=channel_constants.CHANNEL_WILDCARD
    )
