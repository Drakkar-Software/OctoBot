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
import traceback


class Error:
    """
    Error is the error data wrapper use to upload errors to the error server
    """

    def __init__(self, error: Exception, title: str, timestamp: float, metrics_id: str):
        self.error: Exception = error
        self.title: str = title
        self.timestamps: list = [timestamp]
        self.metrics_id: str = metrics_id
        self.type: str = self.error.__class__.__name__ if self.error else ""
        self.stacktrace: list = traceback.format_exception(
            etype=type(self.error), value=self.error, tb=self.error.__traceback__
        )[1:] if self.error else []

    def to_dict(self) -> dict:
        """
        Return the dict serialization of self
        """
        return {
            "title": self.title,
            "type": self.type,
            "stacktrace": self.stacktrace,
            "timestamps": self.timestamps,
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
        self.timestamps += other.timestamps
