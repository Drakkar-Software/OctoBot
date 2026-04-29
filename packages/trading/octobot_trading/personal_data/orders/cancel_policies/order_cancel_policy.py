#  Drakkar-Software OctoBot-Trading
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
import dataclasses
import octobot_commons.logging


@dataclasses.dataclass
class OrderCancelPolicy:
    """
    should_cancel return True when cancel this policy condition is met.
    """

    def should_cancel(self, order) -> bool:
        raise NotImplementedError("should_cancel is not implemented")

    @classmethod
    def get_logger(cls) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(cls.__name__)
