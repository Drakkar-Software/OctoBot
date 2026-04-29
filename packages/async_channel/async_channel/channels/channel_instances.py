#  Drakkar-Software Async-Channel
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
"""
This module defines created Channels interaction methods
"""
import typing
import async_channel.util.logging_util as logging

if typing.TYPE_CHECKING:
    import async_channel.channels.channel


class ChannelInstances:
    """
    Singleton that contains Channel instances
    Singleton implementation from https://stackoverflow.com/questions/51245056/singleton-is-not-working-in-cython
    """

    _instances = {}

    @classmethod
    def instance(cls, *args, **kwargs) -> "ChannelInstances":
        """
        Create the instance if not already created
        Return the class instance
        :param args: the constructor arguments
        :param kwargs: the constructor optional arguments
        :return: the class only instance
        """
        if cls not in cls._instances:
            cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]

    def __init__(self):
        self.channels: dict[
            str, dict[str, "async_channel.channels.channel.Channel"]
        ] = {}


def set_chan_at_id(
    chan: "async_channel.channels.channel.Channel", name: str
) -> "async_channel.channels.channel.Channel":
    """
    Add a new async_channel to the channels instances dictionary at chan.id
    :param chan: the channel instance
    :param name: the channel name
    """
    chan_name = chan.get_name() if name else name

    try:
        chan_instance = ChannelInstances.instance().channels[chan.chan_id]
    except KeyError:
        ChannelInstances.instance().channels[chan.chan_id] = {}
        chan_instance = ChannelInstances.instance().channels[chan.chan_id]

    if chan_name not in chan_instance:
        chan_instance[chan_name] = chan
        return chan
    raise ValueError(f"Channel {chan_name} already exists.")


def get_channels(chan_id: str) -> dict[str, "async_channel.channels.channel.Channel"]:
    """
    Get async_channel instances by async_channel id
    :param chan_id: the channel id
    :return: the channel instances at async_channel id
    """
    try:
        return ChannelInstances.instance().channels[chan_id]
    except KeyError as exception:
        raise KeyError(f"Channels not found with chan_id: {chan_id}") from exception


def del_channel_container(chan_id: str) -> None:
    """
    Delete all async_channel id instances
    :param chan_id: the channel id
    """
    ChannelInstances.instance().channels.pop(chan_id, None)


def get_chan_at_id(
    chan_name: str, chan_id: str
) -> "async_channel.channels.channel.Channel":
    """
    Get the channel instance that matches the name and the id
    :param chan_name: the channel name
    :param chan_id: the channel id
    :return: the channel instance if any
    """
    try:
        return ChannelInstances.instance().channels[chan_id][chan_name]
    except KeyError as exception:
        raise KeyError(
            f"Channel {chan_name} not found with chan_id: {chan_id}"
        ) from exception


def del_chan_at_id(chan_name: str, chan_id: str) -> None:
    """
    Delete the channel instance that matches the name and the id
    :param chan_name: the channel name
    :param chan_id: the channel id
    """
    try:
        ChannelInstances.instance().channels[chan_id].pop(chan_name, None)
    except KeyError:
        logging.get_logger(ChannelInstances.__name__).warning(
            f"Can't del chan {chan_name} with chan_id: {chan_id}"
        )
