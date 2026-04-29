#  Drakkar-Software OctoBot-Tentacles-Manager
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


class Uploader:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.logger = logging.get_logger(self.__class__.__name__)

    @abc.abstractmethod
    async def upload_file(self, upload_path: str, file_path: str):
        raise NotImplementedError("upload_file is not implemented")

    @abc.abstractmethod
    async def upload_folder(self, upload_path: str, folder_path: str):
        raise NotImplementedError("upload_folder is not implemented")