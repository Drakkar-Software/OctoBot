# pylint: disable=R0913
#  Drakkar-Software OctoBot-Commons
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
import octobot_commons.enums as enums


class PlotSettings:
    def __init__(
        self,
        chart=enums.PlotCharts.MAIN_CHART.value,
        x_multiplier=1000,
        kind="scattergl",
        mode="markers",
        y_data=None,
    ):
        self.chart = chart
        self.x_multiplier = x_multiplier
        self.kind = kind
        self.mode = mode
        self.y_data = y_data
