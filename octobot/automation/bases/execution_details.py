#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing


class ExecutionDetails:
    def __init__(
        self,
        timestamp: float,
        description: typing.Optional[str],
        source: typing.Optional["ExecutionDetails"]
    ):
        self.timestamp: float = timestamp
        self.description: typing.Optional[str] = description
        self.source: typing.Optional[ExecutionDetails] = None

    def get_initial_execution_details(self) -> "ExecutionDetails":
        source = self
        while source.source is not None:
            source = source.source
        return source

    def __str__(self):
        return (
            self.description if self.description else f"Execution at {self.timestamp}"
        )

    def __repr__(self):
        return self.__str__()
