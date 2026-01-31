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
import os.path as path
import typing

import octobot_backtesting.converters as converters
import octobot_commons.tentacles_management as tentacles_management


async def convert_data_file(data_file_path) -> typing.Optional[str]:
    if data_file_path and path.isfile(data_file_path):
        converter_classes = tentacles_management.get_all_classes_from_parent(converters.DataConverter)
        for converter_class in converter_classes:
            converter = converter_class(data_file_path)
            if await converter.can_convert():
                if await converter.convert():
                    return converter.converted_file
    return None
