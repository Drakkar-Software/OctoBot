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

import octobot_backtesting.constants as constants
import octobot_backtesting.data as data
import octobot_backtesting.enums as enums


async def get_file_description(file_name, data_path=constants.BACKTESTING_FILE_PATH) -> dict:
    description = await data.get_file_description(path.join(data_path, file_name))
    if description:
        return {
            enums.DataFormatKeys.SYMBOLS.value: description[enums.DataFormatKeys.SYMBOLS.value],
            enums.DataFormatKeys.EXCHANGE.value: description[enums.DataFormatKeys.EXCHANGE.value],
            enums.DataFormatKeys.DATE.value: data.get_date(int(description[enums.DataFormatKeys.TIMESTAMP.value])),
            enums.DataFormatKeys.TIMESTAMP.value: int(description[enums.DataFormatKeys.TIMESTAMP.value]),
            enums.DataFormatKeys.START_TIMESTAMP.value: int(description[enums.DataFormatKeys.START_TIMESTAMP.value]),
            enums.DataFormatKeys.END_TIMESTAMP.value: int(description[enums.DataFormatKeys.END_TIMESTAMP.value]),
            enums.DataFormatKeys.START_DATE.value: data.get_date(
                                        int(description[enums.DataFormatKeys.START_TIMESTAMP.value])).split(" at ")[0],
            enums.DataFormatKeys.END_DATE.value: data.get_date(
                                        int(description[enums.DataFormatKeys.END_TIMESTAMP.value])).split(" at ")[0],
            enums.DataFormatKeys.TIME_FRAMES.value: [tf.value
                                                     for tf in description[enums.DataFormatKeys.TIME_FRAMES.value]],
            enums.DataFormatKeys.CANDLES_LENGTH.value: description[enums.DataFormatKeys.CANDLES_LENGTH.value],
            enums.DataFormatKeys.TYPE.value: "OctoBot data file"
        }
    else:
        return description


def get_all_available_data_files(data_path=constants.BACKTESTING_FILE_PATH) -> list:
    return data.get_all_available_data_files(data_path)


def delete_data_file(file_name, data_path=constants.BACKTESTING_FILE_PATH) -> tuple:
    return data.delete_data_file(data_path, file_name)
