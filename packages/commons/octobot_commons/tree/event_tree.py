# pylint: disable=R1725,W0221
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

import octobot_commons.tree.base_tree as base_tree
import octobot_commons.logging as logging


class EventTreeNode(base_tree.BaseTreeNode):
    """
    Node element of an EventTreeNode. self.node_value is an asyncio.Event() that is triggered when all of its children
    are triggered or is manually triggered. Adding an unset child will clear self. Children updates will overwrite
    any manual trigger
    """

    __slots__ = [
        "_parent",
        "_logger",
    ]

    def __init__(self, *_, triggered=False, **__):
        super().__init__(asyncio.Event(), asyncio.Event)
        if triggered:
            self._trigger()
        self._parent = None
        self._logger = logging.get_logger(self.__class__.__name__)

    def bind_parent(self, parent):
        """
        Set the parent node and propagate the local state to the parent node
        """
        self._parent = parent
        self._propagate()

    def is_triggered(self):
        """
        Return True if the local event is set
        """
        return self.node_value.is_set()

    async def wait(self):
        """
        Wait till the local event is triggered
        """
        await self.node_value.wait()

    def trigger(self):
        """
        Trigger the local event, propagate to the parent if any change
        """
        if not self.is_triggered():
            self._trigger_and_log()
            self._propagate()

    def _trigger_and_log(self):
        """
        Set the event and log
        """
        self._trigger()
        path_to_root = self.get_path_to_root()
        if path_to_root:
            self._logger.debug(f"Event triggered for {'|'.join(path_to_root)}")

    def _trigger(self):
        """
        Set the event and log
        """
        self.node_value.set()

    def _clear(self):
        """
        Clear the event and log
        """
        self.node_value.clear()
        path_to_root = self.get_path_to_root()
        if path_to_root:
            self._logger.debug(f"Event cleared for {'|'.join(path_to_root)}")

    def get_parent(self):
        """
        Return self._parent
        """
        return self._parent

    def get_path_to_root(self):
        """
        Return the path to self from the root event
        """
        node = self
        path = []
        while node.get_parent() is not None:
            parent = node.get_parent()
            try:
                path = [parent.get_child_key(node)] + path
            except KeyError:
                return path
            node = parent
        return path

    def get_child_key(self, child_to_find):
        """
        Return the key of the given child in the current children
        """
        for key, child in self.children.items():
            if child is child_to_find:
                return key
        raise KeyError(child_to_find)

    def clear(self):
        """
        Clear the local event, propagate to the parent if any change
        """
        if self.is_triggered():
            self._clear()
            self._propagate()

    def set_child(self, key, child):
        """
        Set a child at the given key
        """
        super(EventTreeNode, self).set_child(key, child)
        self.on_child_change()

    def pop_child(self, key, default):
        """
        Pop the child the given key
        """
        node = super(EventTreeNode, self).pop_child(key, default)
        self.on_child_change()
        return node

    def _untriggered_children(self):
        """
        Return the list of children events that are not triggered
        """
        return [key for key, child in self.children.items() if not child.is_triggered()]

    def on_child_change(self):
        """
        Trigger or clear the local event depending on children states
        then propagate to the parent if any change
        """
        if not self.children:
            # do not change event when no children
            return
        should_be_triggered = True
        untriggered_children = self._untriggered_children()
        if untriggered_children:
            should_be_triggered = False
            if not self.is_triggered():
                self._logger.debug(
                    f"Waiting children trigger for {'|'.join(self.get_path_to_root())}. "
                    f"Untriggered children: {untriggered_children}"
                )
        if should_be_triggered != self.is_triggered():
            if self.is_triggered():
                self._clear()
            else:
                self._trigger_and_log()
            self._propagate()

    def _propagate(self):
        """
        Calls parent's on_child_change
        """
        if self._parent is not None:
            self._parent.on_child_change()


class EventTree(base_tree.BaseTree):
    """
    Tree based on EventTreeNode where each node's event is synchronized with its children to be triggered when all
    of its children are triggered. Adding an untriggered child will untrigger the parent node.
    """

    TREE_NODE_CLASS = EventTreeNode

    def create_node_at_path(self, path, triggered):
        """
        Set the node attributes
        Creates the node if it doesn't exist
        :param path: the node path (as a list of string)
        :param triggered: if the created node event should be initially triggered
        For example:
        - If you created a first node with the path ["my-parent-node"]
        - You can create a child node of my-parent-node by using ["my-parent-node", "my-new-child-node"] as `path`
        :return: void
        """
        self._set_node(self.get_or_create_node(path, triggered=triggered))

    def child_factory(self, node, key, triggered=False, **kwargs):
        """
        Create a new child an associate it to the given key
        """
        new_child = super(EventTree, self).child_factory(
            node, key, triggered=triggered, **kwargs
        )
        new_child.bind_parent(node)
        return new_child
