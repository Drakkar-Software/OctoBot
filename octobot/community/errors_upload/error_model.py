#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import traceback


class Error:
    """
    Error is the error data wrapper use to upload errors to the error server
    """

    def __init__(self, error: Exception, title: str, timestamp: float, metrics_id: str):
        self.error: Exception = error
        self.title: str = str(title)
        self.first_timestamp: float = timestamp
        self.last_timestamp: float = timestamp
        self.count: int = 1
        self.metrics_id: str = metrics_id
        self.type: str = self.error.__class__.__name__ if self.error else ""
        self.stacktrace: list = traceback.format_exception(
            etype=type(self.error), value=self.error, tb=self.error.__traceback__
        )[1:] if self.error and isinstance(self.error, Exception) else []

    def to_dict(self) -> dict:
        """
        Return the dict serialization of self
        """
        return {
            "title": self.title,
            "type": self.type,
            "stacktrace": self.stacktrace,
            "firsttimestamp": self.first_timestamp,
            "lasttimestamp": self.last_timestamp,
            "count": self.count,
            "metricsid": self.metrics_id,
        }

    def is_equivalent(self, other) -> bool:
        return (self.error is other.error or
                (type(self.error) is type(other.error)
                 and self.error.args == other.error.args)) and \
               self.title == other.title and \
               self.metrics_id == other.metrics_id and \
               self.type == other.type and \
               self.stacktrace == other.stacktrace

    def merge_equivalent(self, other):
        self.count += other.count
        if other.last_timestamp > self.last_timestamp:
            self.last_timestamp = other.last_timestamp
