#  Drakkar-Software OctoBot
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

from tools.logging.logging_util import get_logger

from config import EVALUATION_SAVING_COLUMN_SEPARATOR, EVALUATION_SAVING_ROW_SEPARATOR, \
    EVALUATION_SAVING_FILE_ENDING


class MatrixExporter:
    def __init__(self, matrix, symbol):
        self.matrix = matrix
        self.symbol = symbol
        self.logger = get_logger(self.__class__.__name__)
        self.evaluation_save_file = self._get_evaluation_save_file_name()
        self.is_evaluation_save_file_initialised = False

    def save(self):
        try:
            if not self.is_evaluation_save_file_initialised:
                with open(self.evaluation_save_file, 'w+') as eval_file:
                    eval_file.write(self._get_init_evaluation_save_file())
                    eval_file.write(self._get_formatted_matrix())
            else:
                with open(self.evaluation_save_file, 'a') as eval_file:
                    eval_file.write(self._get_formatted_matrix())
        except PermissionError as e:
            self.logger.error(f"Impossible to save evaluation on {self.evaluation_save_file}: {e}")

    def _get_formatted_matrix(self):
        formatted_matrix = ""
        for eval_dict in self.matrix.matrix.values():
            for eval_name, eval_results in eval_dict.items():
                if isinstance(eval_results, dict):
                    for eval_result in eval_results.values():
                        formatted_matrix = f"{formatted_matrix}{EVALUATION_SAVING_COLUMN_SEPARATOR}{eval_result}"
                else:
                    formatted_matrix = f"{formatted_matrix}{EVALUATION_SAVING_COLUMN_SEPARATOR}{eval_results}"
        return formatted_matrix[len(EVALUATION_SAVING_COLUMN_SEPARATOR):] + EVALUATION_SAVING_ROW_SEPARATOR

    def _get_init_evaluation_save_file(self):
        # create file 1st line
        line = ""
        for eval_type, eval_dict in self.matrix.matrix.items():
            for eval_name, eval_results in eval_dict.items():
                if isinstance(eval_results, dict):
                    for eval_key in eval_results.keys():
                        line = f"{line}{EVALUATION_SAVING_COLUMN_SEPARATOR}" \
                               f"{eval_type.value}/{eval_name}/{eval_key.value}"
                else:
                    line = f"{line}{EVALUATION_SAVING_COLUMN_SEPARATOR}{eval_type.value}/{eval_name}"
        self.is_evaluation_save_file_initialised = True
        # remove first separator
        return line[len(EVALUATION_SAVING_COLUMN_SEPARATOR):] + EVALUATION_SAVING_ROW_SEPARATOR

    def _get_evaluation_save_file_name(self):
        return f"{self.symbol.replace('/','-')}{EVALUATION_SAVING_FILE_ENDING}"
