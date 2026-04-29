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
import asyncio
import copy
import json
import os.path as path
import os
import time

import aiohttp

import octobot_commons.logging as logging
import octobot_commons.databases as databases

import octobot_backtesting.enums as enums
import octobot_backtesting.constants as constants
import octobot_backtesting.data as data
import octobot_backtesting.importers as importers


class DataCollector:
    IMPORTER = importers.DataImporter

    def __init__(self, config,
                 path=constants.BACKTESTING_FILE_PATH,
                 data_format=enums.DataFormats.REGULAR_COLLECTOR_DATA):
        self.config = copy.deepcopy(config)
        self.path = path
        self.logger = logging.get_logger(self.__class__.__name__)

        self.should_stop = False
        self.file_name = data.get_backtesting_file_name(self.__class__,
                                                        self.get_file_identifier,
                                                        data_format=data_format)

        self.database = None
        self.aiohttp_session = None
        self.file_path = None
        self.temp_file_path = None
        self.finished = False
        self.in_progress = False
        self._ensure_file_path()
        self.set_file_path()

    async def initialize(self) -> None:
        pass

    def get_file_identifier(self):
        return time.time()

    async def stop(self, **kwargs) -> None:
        self.should_stop = True

    async def start(self) -> None:
        raise NotImplementedError("Start is not implemented")

    def is_in_progress(self):
        return self.in_progress

    def is_finished(self):
        return self.finished

    def _ensure_file_path(self):
        if not path.isdir(self.path):
            os.makedirs(self.path)

    def set_file_path(self) -> None:
        self.file_path = path.join(self.path, self.file_name) if self.path else self.file_name
        self.temp_file_path = self.file_path + constants.BACKTESTING_DATA_FILE_TEMP_EXT

    def create_database(self) -> None:
        if not self.database:
            self.database = databases.SQLiteDatabase(self.temp_file_path)

    def finalize_database(self):
        os.rename(self.temp_file_path, self.file_path)

    def create_aiohttp_session(self) -> None:
        if not self.aiohttp_session:
            self.aiohttp_session = aiohttp.ClientSession()

    async def stop_aiohttp_session(self) -> None:
        if self.aiohttp_session:
            await self.aiohttp_session.close()

    async def execute_request(self, url, params=None, headers=None):
        response = await self.aiohttp_session.get(url, params=params, headers=headers)
        if response.status != 200:
            if response.status == 502:  # bad gateway (should retry)
                self.logger.warning("Got a bad gateway error, retrying...")
                await asyncio.sleep(60)
                return await self.execute_request(url, params=params, headers=headers)
            else:
                try:
                    message = json.loads(await response.text())['message']
                except json.JSONDecodeError:
                    message = await response.text()
                self.logger.error(f"Error when requesting url {url} / "
                                  f"message : {message} / "
                                  f"code : {response.status} / "
                                  f"reason : {response.reason}")
            return None
        try:
            return json.loads(await response.text())
        except aiohttp.ClientPayloadError as e:
            self.logger.error(f"Failed to extract payload text : {e}")
            return None

    async def fetch_with_continuation(self, continuation_url_key, json_answer, headers, callback):
        if continuation_url_key in json_answer:
            answer = await self.execute_request(json_answer[continuation_url_key], headers=headers)
            if answer is None:
                return

            await callback(answer["data"])

            await self.fetch_with_continuation(continuation_url_key, answer, headers, callback)
