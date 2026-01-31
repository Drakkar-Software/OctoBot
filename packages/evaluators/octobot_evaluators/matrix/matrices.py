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
import octobot_commons.logging as logging
import octobot_commons.singleton as singleton

import octobot_evaluators.matrix as matrix 


class Matrices(singleton.Singleton):
    def __init__(self):
        self.matrices: dict = {}

    def add_matrix(self, matrix) -> None:
        if matrix.matrix_id not in self.matrices:
            self.matrices[matrix.matrix_id] = matrix

    def get_matrix(self, matrix_id) -> matrix.Matrix:
        return self.matrices[matrix_id]

    def del_matrix(self, matrix_id) -> None:
        try:
            if self.matrices[matrix_id]:
                self.matrices.pop(matrix_id, None)
        except KeyError:
            logging.get_logger(self.__class__.__name__).warning(f"Can't del matrix with id {matrix_id}")
