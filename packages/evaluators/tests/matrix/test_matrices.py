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

from octobot_evaluators.api.evaluators import create_matrix
from octobot_evaluators.matrix.matrix import Matrix
from octobot_evaluators.matrix.matrices import Matrices


def cleanup_matrices():
    matrices = Matrices.instance()
    for m_id in list(matrices.matrices):
        Matrices.instance().del_matrix(m_id)


def test_default_matrices():
    cleanup_matrices()
    matrices = Matrices.instance()
    assert matrices.matrices == {}


@pytest.mark.asyncio
async def test_add_matrix():
    matrices = Matrices.instance()
    assert matrices.matrices == {}

    created_matrix: Matrix = Matrix()
    Matrices.instance().add_matrix(created_matrix)

    assert matrices.matrices != {}
    assert created_matrix.matrix_id in matrices.matrices


@pytest.mark.asyncio
async def test_get_matrix():
    matrix_id = create_matrix()

    assert Matrices.instance().get_matrix(matrix_id) is not None

    with pytest.raises(KeyError):
        assert Matrices.instance().get_matrix(matrix_id + "t") is None


@pytest.mark.asyncio
async def test_del_matrix():
    matrices = Matrices.instance()
    matrix_id = create_matrix()

    assert matrix_id in matrices.matrices
    Matrices.instance().del_matrix(matrix_id)
    assert matrix_id not in matrices.matrices
