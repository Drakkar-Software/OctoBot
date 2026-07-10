#  Drakkar-Software OctoBot-Tentacles
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

import octobot_commons.logging as bot_logging


class AbstractTunnelBackend:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.logger = bot_logging.get_logger(self.__class__.__name__)

    @abc.abstractmethod
    async def open(self, local_host: str, local_port: int) -> str:
        """
        Expose (local_host, local_port) through this backend.
        :return: the URL other parties can reach this target through.
        """
        raise NotImplementedError("open not implemented")

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError("close not implemented")
