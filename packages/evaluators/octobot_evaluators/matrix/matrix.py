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
import uuid

import octobot_commons.tree as tree


class Matrix:
    """
    Matrix dataclass store tentacles data in a BaseTree
    """
    __slots__ = ['matrix_id', 'matrix']

    def __init__(self):
        """
        Initialize the matrix as an BaseTree instance
        """
        self.matrix_id = str(uuid.uuid4())
        self.matrix = tree.BaseTree()

    def set_node_value(self, value, value_type, value_path, timestamp=0, description=None, metadata=None):
        """
        Set the node value at node path
        :param value_path: the node path
        :param value_type: the node type
        :param value: the node value
        :param timestamp: the value modification timestamp.
        :param description: the node description
        :param metadata: the node metadata
        """
        self.matrix.set_node_at_path(value, value_type, value_path, timestamp=timestamp, description=description, metadata=metadata)

    def get_node_children_at_path(self, node_path, starting_node=None):
        """
        Get the node children list
        :param node_path: the node path
        :param starting_node: the node to start the relative path
        :return: the list of node children
        """
        try:
            return list(self.matrix.get_node(node_path, starting_node=starting_node).children.values())
        except tree.NodeExistsError:
            return []

    def get_node_children_by_names_at_path(self, node_path, starting_node=None):
        """
        Get the node children dict with node name as key
        :param node_path: the node path
        :param starting_node: the node to start the relative path
        :return: the dict of node children
        """
        try:
            return {key: val
                    for key, val in self.matrix.get_node(node_path, starting_node=starting_node).children.items()}
        except tree.NodeExistsError:
            return {}

    def get_node_at_path(self, node_path, starting_node=None):
        """
        Get the BaseTreeNode at path
        :param node_path: the node path
        :param starting_node: the node to start the relative path
        :return: the node instance at path
        """
        try:
            return self.matrix.get_node(node_path, starting_node=starting_node)
        except tree.NodeExistsError:
            return None

    def delete_node_at_path(self, node_path, starting_node=None):
        """
        Delete the BaseTreeNode at path
        :param node_path: the node path
        :param starting_node: the node to start the relative path
        :return: the deleted node
        """
        try:
            return self.matrix.delete_node(node_path, starting_node=starting_node)
        except tree.NodeExistsError:
            return None
