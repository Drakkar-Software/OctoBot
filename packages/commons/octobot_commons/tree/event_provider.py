#  Drakkar-Software OctoBot-Commons
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
import concurrent.futures

import octobot_commons.singleton as singleton
import octobot_commons.logging as logging
import octobot_commons.tree.event_tree as event_tree
import octobot_commons.tree.base_tree as base_tree


def _create_tree_if_missing(func):
    """
    Create the required node if missing and then recalls the function
    """

    def wrapper(self, bot_id, *args, **kwargs):
        try:
            return func(self, bot_id, *args, **kwargs)
        except KeyError:
            self.create_event_tree(bot_id)
            return func(self, bot_id, *args, **kwargs)

    return wrapper


class EventProvider(singleton.Singleton):
    def __init__(self):
        self.logger = logging.get_logger(self.__class__.__name__)
        self._event_tree_by_bot_id = {}

    @_create_tree_if_missing
    def get_or_create_event(self, bot_id, path, allow_creation=True):
        """
        Return the event at the given path for the given bot_id (or create it)
        """
        try:
            return self._event_tree_by_bot_id[bot_id].get_node(path)
        except base_tree.NodeExistsError:
            if allow_creation:
                self.create_event_at_path(bot_id, path, triggered=False)
                return self._event_tree_by_bot_id[bot_id].get_node(path)
            raise

    @_create_tree_if_missing
    def trigger_event(self, bot_id, path, allow_creation=True):
        """
        Trigger the event at the given path for the given bot_id (or create it)
        """
        try:
            self._event_tree_by_bot_id[bot_id].get_node(path).trigger()
        except base_tree.NodeExistsError:
            if allow_creation:
                self.create_event_at_path(bot_id, path, triggered=True)
                self._event_tree_by_bot_id[bot_id].get_node(path).trigger()

    @_create_tree_if_missing
    def create_event_at_path(self, bot_id, path, triggered=False):
        """
        Create a new event at the given path for the given bot_id
        """
        return self._event_tree_by_bot_id[bot_id].create_node_at_path(path, triggered)

    def create_event_tree(self, bot_id):
        """
        Create a new event tree for the given bot_id
        """
        self._event_tree_by_bot_id[bot_id] = event_tree.EventTree()

    def remove_event_tree(self, bot_id):
        """
        Removes the event tree for the given bot_id
        """
        self._event_tree_by_bot_id.pop(bot_id, None)

    async def wait_for_event(self, bot_id, path, timeout) -> bool:
        """
        Wait for the event at the given path for the given bot_id.
        Returns instantly if the path doesn't lead to an event or if timeout is 0
        :return: False if the event is not triggered after timeout
        """
        try:
            event = self.get_or_create_event(bot_id, path, allow_creation=False)
            if timeout == 0:
                return event.is_triggered()
            if not event.is_triggered():
                await asyncio.wait_for(event.wait(), timeout)
        except base_tree.NodeExistsError:
            # nothing to wait for
            pass
        except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
            return False
        return True


def get_exchange_path(exchange, topic, symbol=None, time_frame=None):
    """
    Return a path associated to the given exchange and topic
    as well as symbol and timeframe if provided
    """
    node_path = [exchange, topic]
    if symbol is not None:
        node_path.append(symbol)
    if time_frame is not None:
        node_path.append(time_frame)
    return node_path
