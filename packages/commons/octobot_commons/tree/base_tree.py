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


class BaseTreeNode:
    """
    Node element of a BaseTree
    """

    __slots__ = [
        "node_value",
        "node_value_time",
        "node_type",
        "node_description",
        "node_metadata",
        "children",
    ]

    def __init__(self, node_value, node_type, **_):
        self.node_value = node_value
        self.node_value_time = None
        self.node_type = node_type
        self.node_description = None
        self.node_metadata = {}
        self.children = {}

    def set_child(self, key, child):
        """
        Set a child at the given key
        """
        self.children[key] = child

    def pop_child(self, key, default):
        """
        Pop the child the given key
        """
        return self.children.pop(key, default)


class NodeExistsError(Exception):
    """
    Node doesn't exist error
    """


class BaseTree:
    """
    Tree based on BaseTreeNode
    """

    TREE_NODE_CLASS = BaseTreeNode
    __slots__ = ["root"]

    def __init__(self):
        """
        Init the root node
        """
        self.root = self.TREE_NODE_CLASS(None, None)

    def set_node(self, value, node_type, node, timestamp=0):
        """
        Set the node attributes
        Can raise an exception if the node doesn't exists
        :param value: the node 'node_value' attribute to set
        :param node_type: the node 'node_type' attribute to set
        :param node: the node to update
        :param timestamp: the value modification timestamp.
        """
        self._set_node(node, value, node_type, timestamp=timestamp)

    # pylint: disable=too-many-arguments
    def set_node_at_path(
        self, value, node_type, path, timestamp=0, description=None, metadata=None
    ):
        """
        Set the node attributes
        Creates the node if it doesn't exists
        :param value: the node 'node_value' attribute to set
        :param node_type: the node 'node_type' attribute to set
        :param path: the node path (as a list of string)
        :param timestamp: the value modification timestamp.
        :param description: the node 'node_description' attribute to set
        :param metadata: the node 'node_metadata' attribute to set
        For example:
        - If you created a first node with the path ["my-parent-node"]
        - You can create a child node of my-parent-node by using ["my-parent-node", "my-new-child-node"] as `path`
        :return: void
        """
        self._set_node(
            self.get_or_create_node(path),
            value,
            node_type,
            timestamp=timestamp,
            description=description,
            metadata=metadata,
        )

    def get_node(self, path, starting_node=None):
        """
        Get the node at the specified path
        :param path: the node path (as a list of string).
        For example:
        - If you created a first node with the path ["my-parent-node"]
        - You can create a child node of my-parent-node by using ["my-parent-node", "my-new-child-node"] as `path`
        :param starting_node: the node to start the relative path
        :return: the node instance or raise a NodeExistsError if the node doesn't exists
        """
        try:
            return self._get_node(path, starting_node=starting_node)
        except KeyError:
            raise NodeExistsError

    def clear(self):
        """
        Clears the whole tree
        """
        self.root = self.TREE_NODE_CLASS(None, None)

    def delete_node(self, path, starting_node=None):
        """
        Delete the node at the specified path
        :param path: the node path (as a list of string).
        For example:
        - If you created a first node with the path ["my-parent-node"]
        - You can create a child node of my-parent-node by using ["my-parent-node", "my-new-child-node"] as `path`
        :param starting_node: the node to start the relative path
        :return: the deleted node or raise a NodeExistsError if the node doesn't exists
        """
        try:
            deleted_node = self._delete_node(path, starting_node=starting_node)
            if deleted_node is None:
                raise NodeExistsError
            return deleted_node
        except KeyError:
            raise NodeExistsError

    def get_or_create_node(self, path, starting_node=None, **kwargs):
        """
        Get the node at the specified path
        Creates the node if it doesn't exists
        :param path: the node path (as a list of string).
        For example:
        - If you created a first node with the path ["my-parent-node"]
        - You can create a child node of my-parent-node by using ["my-parent-node", "my-new-child-node"] as `path`
        :param starting_node: the node to start the relative path
        :return: the node instance
        """
        try:
            return self._get_node(path, starting_node=starting_node)
        except KeyError:
            return self._create_node_path(path, starting_node=starting_node, **kwargs)

    def get_nested_children_with_path(self, path=None, select_leaves_only=True):
        """
        Returns a generator iterating over the nodes children, including nested children. Children are yielded
        together with their node path using a depth-first search (the most nested children are returned first)
        :param path: the path (as a list of string) to the node
        :param select_leaves_only: when True (default), only nodes that don't have children are returned
        :return: a generator of (node, path) tuples
        """
        path = path or []
        return self._get_nested_children_with_path(path, select_leaves_only)

    def _get_nested_children_with_path(self, parent_path, select_leaves_only):
        children_keys = self.get_children_keys(parent_path)
        node = self.get_node(parent_path)
        if not children_keys or not select_leaves_only:
            yield node, parent_path
        for key in children_keys:
            path = list(parent_path)
            path.append(key)
            yield from self._get_nested_children_with_path(path, select_leaves_only)

    def get_children_keys(self, path):
        """
        Return the node's children keys
        Can raise a KeyError if the path does not exists
        :param path: the path (as a list of string) to the node
        :return: children keys as a list
        """
        return list(self.get_node(path).children)

    def _get_node(self, path, starting_node=None):
        """
        Return the node corresponding to the path
        Can raise a KeyError if the path does not exists
        :param path: the path (as a list of string) to the node
        :param starting_node: the node to start the path, root if None
        :return: BaseTreeNode at path
        """
        current_node = self.root if starting_node is None else starting_node
        for key in path:
            current_node = current_node.children[key]
        return current_node

    def _delete_node(self, path, starting_node=None):
        """
        Return the node corresponding to the path
        Can raise a KeyError if the path does not exists
        :param path: the path (as a list of string) to the node
        :param starting_node: the node to start the path, root if None
        :return: BaseTreeNode at path
        """
        current_node = self.root if starting_node is None else starting_node
        for key in path[:-1]:
            current_node = current_node.children[key]
        return current_node.pop_child(path[-1], None)

    def _create_node_path(self, path, starting_node=None, **kwargs):
        """
        Expensive method that creates the path to the selected node
        :param path: path (as a list of string) to the selected node
        :param starting_node: the node to start the path, root if None
        :return: the created node path
        """
        current_node = self.root if starting_node is None else starting_node
        for key in path:
            try:
                current_node = current_node.children[key]
            except KeyError:
                # create a new node as the current node child
                # us it as the new node
                current_node = self.child_factory(current_node, key, **kwargs)

        return current_node

    def child_factory(self, node, key, **kwargs):
        """
        Create a new child an associate it to the given key
        """
        node.set_child(key, self.TREE_NODE_CLASS(None, None, **kwargs))
        return node.children[key]

    # pylint: disable=too-many-arguments
    def _set_node(
        self,
        node,
        value=None,
        node_type=None,
        timestamp=0,
        description=None,
        metadata=None,
    ):
        """
        Sets the node attributes
        :param node: the node instance to update
        :param value: the node instance 'node_value' attribute to set (is ignored if None)
        :param node_type: the node instance 'node_type' attribute to set (is ignored if None)
        :param timestamp: the value modification timestamp.
        :param description: the node instance 'node_description' attribute to set (is ignored if None)
        :param metadata: the node instance 'node_metadata' attribute to set (is ignored if None)
        """
        if value is not None:
            node.node_value = value

        if node_type is not None:
            node.node_type = node_type

        # set the node value modification timestamp
        node.node_value_time = timestamp

        if description is not None:
            node.node_description = description

        if metadata is not None:
            node.node_metadata = metadata
