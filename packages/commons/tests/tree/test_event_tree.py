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
import pytest

import octobot_commons.tree as tree
import octobot_commons.asyncio_tools as asyncio_tools


@pytest.fixture
def event_tree():
    return tree.EventTree()


@pytest.fixture
def event_tree_node():
    return tree.EventTreeNode()


def test_event_tree_create_node_at_path(event_tree):
    assert event_tree.root.children == {}
    event_tree.create_node_at_path(["1"], True)
    assert isinstance(event_tree.get_node(["1"]), tree.EventTreeNode)
    assert event_tree.get_node(["1"]).is_triggered()
    event_tree.create_node_at_path(["2", "abtc"], False)
    assert not event_tree.get_node(["2", "abtc"]).is_triggered()
    assert isinstance(event_tree.get_node(["1"]), tree.EventTreeNode)
    assert isinstance(event_tree.get_node(["2", "abtc"]), tree.EventTreeNode)


def test_event_tree_node_trigger(event_tree_node):
    assert not event_tree_node.is_triggered()
    event_tree_node.trigger()
    assert event_tree_node.is_triggered()


def test_event_tree_node_bind_parent(event_tree_node):
    parent_node = tree.EventTreeNode()
    event_tree_node.bind_parent(parent_node)
    assert event_tree_node.get_parent() is parent_node
    parent_node.children["d"] = event_tree_node
    assert not event_tree_node.is_triggered()
    assert not parent_node.is_triggered()
    event_tree_node.trigger()
    assert event_tree_node.is_triggered()
    assert parent_node.is_triggered()


@pytest.mark.asyncio
async def test_event_tree_node_wait(event_tree_node):
    waiter = asyncio.create_task(asyncio.wait_for(event_tree_node.wait(), 0.1))
    for _ in range(10):
        # let async loop end task if necessary
        await asyncio_tools.wait_asyncio_next_cycle()
    assert not event_tree_node.is_triggered()
    assert not waiter.done()
    event_tree_node.trigger()
    assert not waiter.done()
    # need 2 cycles to both end the waiter and end the wait_for
    for _ in range(2):
        await asyncio_tools.wait_asyncio_next_cycle()
    assert waiter.done()


def test_event_tree_node_set_child(event_tree_node):
    assert event_tree_node.children == {}
    node = tree.EventTreeNode()
    event_tree_node.set_child("hi", node)
    assert event_tree_node.children == {
        "hi": node
    }


def test_event_tree_node_pop_child(event_tree_node):
    assert event_tree_node.children == {}
    node = tree.EventTreeNode()
    event_tree_node.set_child("hi", node)
    assert event_tree_node.pop_child("hi", None) is node
    assert event_tree_node.children == {}
    assert event_tree_node.pop_child("hi", None) is None
    assert event_tree_node.children == {}


def test_event_tree_node_on_child_change(event_tree_node):
    assert not event_tree_node.is_triggered()
    event_tree_node.on_child_change()
    # no child, need manual trigger
    assert not event_tree_node.is_triggered()
    event_tree_node.trigger()
    assert event_tree_node.is_triggered()
    event_tree_node.on_child_change()
    # still triggered
    assert event_tree_node.is_triggered()

    parent_node = tree.EventTreeNode()
    parent_node.children["a"] = event_tree_node
    assert not parent_node.is_triggered()
    event_tree_node.bind_parent(parent_node)
    assert parent_node.is_triggered()

    event_tree_node.clear()
    assert not event_tree_node.is_triggered()
    assert not parent_node.is_triggered()

    other_child = tree.EventTreeNode()
    parent_node.children["b"] = other_child
    other_child.bind_parent(parent_node)
    assert not parent_node.is_triggered()

    event_tree_node.trigger()
    assert not other_child.is_triggered()
    assert not parent_node.is_triggered()

    other_child.trigger()
    assert event_tree_node.is_triggered()
    assert parent_node.is_triggered()

    other_child.clear()
    assert event_tree_node.is_triggered()
    assert not parent_node.is_triggered()


def test_event_tree_node_get_path_to_root(event_tree_node):
    assert event_tree_node.children == {}
    assert event_tree_node.get_path_to_root() == []
    parent = tree.EventTreeNode()
    event_tree_node.bind_parent(parent)
    parent.set_child("hi", event_tree_node)
    assert event_tree_node.get_path_to_root() == ["hi"]
    parent_2 = tree.EventTreeNode()
    parent.bind_parent(parent_2)
    parent_2.set_child("hello", parent)
    assert event_tree_node.get_path_to_root() == ["hello", "hi"]
    assert parent.get_path_to_root() == ["hello"]
    assert parent_2.get_path_to_root() == []
    other_child = tree.EventTreeNode()
    other_child.bind_parent(parent)
    parent.set_child("ho", other_child)
    assert event_tree_node.get_path_to_root() == ["hello", "hi"]
    assert other_child.get_path_to_root() == ["hello", "ho"]


def test_event_tree_node_get_child_key(event_tree_node):
    with pytest.raises(KeyError):
        event_tree_node.get_child_key("dd")
    other = tree.EventTreeNode()
    event_tree_node.children["dd"] = other
    assert event_tree_node.get_child_key(other) == "dd"
