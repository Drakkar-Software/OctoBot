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
import octobot_evaluators.matrix as matrix


def get_matrix(matrix_id) -> matrix.Matrix:
    return matrix.Matrices.instance().get_matrix(matrix_id)


def del_matrix(matrix_id) -> matrix.Matrix:
    return matrix.Matrices.instance().del_matrix(matrix_id)


def get_node_children_by_names(matrix) -> dict:
    return matrix.get_node_children_by_names_at_path([])


def get_children_list(matrix_node) -> dict:
    return matrix_node.children

def has_children(matrix_node) -> bool:
    return bool(matrix_node.children)

def get_value(matrix_node) -> object:
    return matrix_node.node_value

def get_description(matrix_node) -> object:
    return matrix_node.node_description

def get_metadata(matrix_node) -> object:
    return matrix_node.node_metadata

def get_type(matrix_node) -> object:
    return matrix_node.node_type

def get_time(matrix_node) -> object:
    return matrix_node.node_value_time
