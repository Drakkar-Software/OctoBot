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

import numpy as np


class DataUtil:

    @staticmethod
    def normalize_data(data):
        if data.size > 0:
            return (data - np.mean(data)) / (data.max() - data.min())
        else:
            return data

    @staticmethod
    def drop_nan(data):
        return data[~np.isnan(data)]

    @staticmethod
    def mean(number_list):
        return sum(number_list) / len(number_list) if number_list else 0
