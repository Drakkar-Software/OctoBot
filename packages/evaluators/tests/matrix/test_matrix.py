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
import pytest

from octobot_evaluators.matrix.matrix import Matrix


def test_default_matrix():
    matrix = Matrix()
    assert matrix.matrix.root.children == {}


@pytest.mark.asyncio
async def test_get_node_at_path():
    matrix = Matrix()
    test_node_path = ["test-path", "test-path-2", "test-path3", 4]
    created_node = matrix.matrix.get_or_create_node(test_node_path)
    assert matrix.get_node_at_path(test_node_path) is created_node


@pytest.mark.asyncio
async def test_set_tentacle_value():
    matrix = Matrix()
    test_node_path = ["test-path", "test-path-2"]
    matrix.set_node_value("test-value", str, test_node_path)
    assert matrix.matrix.get_or_create_node(test_node_path).node_type == str
    assert matrix.matrix.get_or_create_node(test_node_path).node_value == "test-value"


@pytest.mark.asyncio
async def test_get_node_children_at_path():
    matrix = Matrix()
    test_node_1_path = ["test-path-parent", "test-path-child", "test-path-1"]
    test_node_2_path = ["test-path-parent", "test-path-child", "test-path-2"]
    test_node_3_path = ["test-path-parent", "test-path-child", "test-path-3"]
    created_node_1 = matrix.matrix.get_or_create_node(test_node_1_path)
    created_node_2 = matrix.matrix.get_or_create_node(test_node_2_path)
    created_node_3 = matrix.matrix.get_or_create_node(test_node_3_path)
    assert matrix.get_node_children_at_path(["test-path-parent", "test-path-child"]) == [created_node_1,
                                                                                         created_node_2,
                                                                                         created_node_3]


@pytest.mark.asyncio
async def test_get_node_children_by_names_at_path():
    matrix = Matrix()
    test_node_1_path = ["test-path-parent", "test-path-child", "test-path-1"]
    test_node_2_path = ["test-path-parent", "test-path-child", "test-path-2"]
    test_node_3_path = ["test-path-parent", "test-path-child", "test-path-3"]
    test_node_4_path = ["test-path-parent", "test-path-4"]
    test_node_5_path = ["test-path-parent", "test-path-4", "test-path-5"]
    test_node_6_path = ["test-path-parent", "test-path-child", "test-path-2", "test-path-6"]
    created_node_1 = matrix.matrix.get_or_create_node(test_node_1_path)
    created_node_2 = matrix.matrix.get_or_create_node(test_node_2_path)
    created_node_3 = matrix.matrix.get_or_create_node(test_node_3_path)
    created_node_4 = matrix.matrix.get_or_create_node(test_node_4_path)
    created_node_5 = matrix.matrix.get_or_create_node(test_node_5_path)
    created_node_6 = matrix.matrix.get_or_create_node(test_node_6_path)
    assert matrix.get_node_children_by_names_at_path(["test-path-parent", "test-path-child"]) == {
        "test-path-1": created_node_1,
        "test-path-2": created_node_2,
        "test-path-3": created_node_3
    }
