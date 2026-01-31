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
import pytest

from octobot_commons.tree import BaseTree, NodeExistsError


def test_base_tree_init():
    assert BaseTree()


def test_base_tree_get_new_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    assert base_tree.root.children == {"test": created_node}


def test_base_tree_get_existing_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    get_node_result = base_tree.get_or_create_node(["test"])
    assert created_node is get_node_result


def test_base_tree_get_not_existing_node():
    base_tree = BaseTree()
    with pytest.raises(NodeExistsError):
        assert base_tree.get_node(["test"]) is None


def test_base_tree_delete_existing_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    delete_node_result = base_tree.delete_node(["test"])
    assert created_node is delete_node_result
    with pytest.raises(NodeExistsError):
        base_tree.get_node(["test"])


def test_base_tree_delete_not_existing_node():
    base_tree = BaseTree()
    with pytest.raises(NodeExistsError):
        base_tree.delete_node(["test"])


def test_base_tree_get_new_relative_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    relative_created_node = base_tree.get_or_create_node(["test-relative"], starting_node=created_node)
    get_node_result = base_tree.get_or_create_node(["test", "test-relative"])
    assert relative_created_node is get_node_result


def test_base_tree_get_relative_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    relative_created_node = base_tree.get_or_create_node(["test", "test-relative"])
    get_node_result = base_tree.get_or_create_node(["test-relative"], starting_node=created_node)
    assert relative_created_node is get_node_result


def test_base_tree_delete_relative_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    relative_created_node = base_tree.get_or_create_node(["test", "test-relative"])
    delete_node_result = base_tree.delete_node(["test-relative"], starting_node=created_node)
    assert relative_created_node is delete_node_result
    assert base_tree.get_node(["test"]) is created_node
    with pytest.raises(NodeExistsError):
        base_tree.get_node(["test", "test-relative"])


def test_base_tree_set_node():
    base_tree = BaseTree()
    created_node = base_tree.get_or_create_node(["test"])
    base_tree.set_node(1, None, created_node)
    assert created_node.node_value == 1
    assert created_node.node_type is None
    base_tree.set_node(5, None, created_node, timestamp=10)
    assert created_node.node_value == 5
    assert created_node.node_type is None
    assert created_node.node_value_time == 10


def test_base_tree_set_node_at_path():
    base_tree = BaseTree()
    base_tree.set_node_at_path("test-string", "test-type", ["test", "test2", "test3"])
    assert base_tree.get_or_create_node(["test"])
    assert base_tree.get_or_create_node(["test", "test2"])
    assert base_tree.get_or_create_node(["test", "test2", "test3"])
    assert base_tree.get_or_create_node(["test"]).children
    assert base_tree.get_or_create_node(["test", "test2"]).children
    assert not base_tree.get_or_create_node(["test", "test2", "test3"]).children
    assert base_tree.get_or_create_node(["test", "test2", "test3"]).node_value == "test-string"
    assert base_tree.get_or_create_node(["test", "test2", "test3"]).node_type == "test-type"


def test_get_children_keys():
    base_tree = BaseTree()
    base_tree.set_node_at_path("test-string", "test-type", ["test", "test2", "test3"])
    base_tree.set_node_at_path("test-string_2", None, ["test", "test2", "test3_2"])
    base_tree.set_node_at_path("test-string_3", None, ["test", "test2"])
    base_tree.set_node_at_path("test-string_4", None, ["test", "test3"])
    assert base_tree.get_children_keys([]) == ["test"]
    assert base_tree.get_children_keys(["test"]) == ["test2", "test3"]
    assert base_tree.get_children_keys(["test", "test2"]) == ["test3", "test3_2"]
    with pytest.raises(NodeExistsError):
        assert base_tree.get_children_keys(["test", "testXXXX"]) == ["test3"]


def test_get_nested_children_with_path():
    base_tree = BaseTree()
    base_tree.set_node_at_path("test-string", "test-type", ["test", "test2", "test3"])
    base_tree.set_node_at_path("test-string_2", None, ["test", "test2", "test3_2"])
    base_tree.set_node_at_path("test-string_3", None, ["test", "test2"])
    base_tree.set_node_at_path("test-string_4", None, ["test", "test3"])
    assert [(n.node_value, p) for n, p in base_tree.get_nested_children_with_path()] == [
        ("test-string", ["test", "test2", "test3"]),
        ("test-string_2", ["test", "test2", "test3_2"]),
        ("test-string_4", ["test", "test3"])
    ]
    assert [(n.node_value, p) for n, p in base_tree.get_nested_children_with_path(select_leaves_only=False)] == [
        (None, []),
        (None, ['test']),
        ("test-string_3", ["test", "test2"]),
        ("test-string", ["test", "test2", "test3"]),
        ("test-string_2", ["test", "test2", "test3_2"]),
        ("test-string_4", ["test", "test3"])
    ]
    assert [(n.node_value, p) for n, p in base_tree.get_nested_children_with_path(path=["test", "test2"],
                                                                                   select_leaves_only=False)] == [
        ("test-string_3", ["test", "test2"]),
        ("test-string", ["test", "test2", "test3"]),
        ("test-string_2", ["test", "test2", "test3_2"])
    ]
