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

from abc import ABCMeta

from config import TENTACLE_UTIL_FOLDER, TENTACLES_EVALUATOR_PATH
from tentacles_management.abstract_tentacle import AbstractTentacle


class AbstractUtil(AbstractTentacle):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @classmethod
    def get_tentacle_folder(cls) -> str:
        return TENTACLES_EVALUATOR_PATH

    @classmethod
    def get_config_tentacle_type(cls) -> str:
        return TENTACLE_UTIL_FOLDER
