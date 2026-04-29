#  Drakkar-Software OctoBot-Backtesting
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
import abc 
import octobot_commons.logging as logging


class DataConverter:
    def __init__(self, backtesting_file_to_convert):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.file_to_convert = backtesting_file_to_convert
        self.converted_file = ""

    @abc.abstractmethod
    async def can_convert(self) -> bool:
        raise NotImplementedError("can_convert is not implemented")

    @abc.abstractmethod
    async def convert(self) -> bool:
        """
        Converts self.backtesting_file_to_convert and saves the output into self.converted_file_path
        :return: True when conversion is successful, False otherwise
        """
        raise NotImplementedError("convert is not implemented")
