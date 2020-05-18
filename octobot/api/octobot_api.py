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
from octobot.constants import CONFIG_KEY, TENTACLES_SETUP_CONFIG_KEY
from octobot.commands import stop_bot as command_stop, restart_bot as command_restart


class OctoBotAPI:

    def __init__(self, octobot):
        self._octobot = octobot

    def is_initialized(self) -> bool:
        return self._octobot.initialized

    def get_exchange_manager_ids(self) -> list:
        return self._octobot.exchange_producer.exchange_manager_ids

    def get_global_config(self) -> dict:
        return self._octobot.config

    def get_startup_config(self) -> object:
        return self._octobot.get_startup_config(CONFIG_KEY)

    def get_edited_config(self) -> object:
        return self._octobot.get_edited_config(CONFIG_KEY)

    def get_startup_tentacles_config(self) -> object:
        return self._octobot.get_startup_config(TENTACLES_SETUP_CONFIG_KEY)

    def get_edited_tentacles_config(self) -> object:
        return self._octobot.get_edited_config(TENTACLES_SETUP_CONFIG_KEY)

    def get_trading_mode(self) -> object:
        return self._octobot.get_trading_mode()

    def get_tentacles_setup_config(self) -> object:
        return self._octobot.tentacles_setup_config

    def get_start_time(self) -> float:
        return self._octobot.start_time

    def get_matrix_id(self) -> str:
        return self._octobot.evaluator_producer.matrix_id

    def get_aiohttp_session(self) -> object:
        return self._octobot.get_aiohttp_session()

    def run_in_main_asyncio_loop(self, coroutine):
        return self._octobot.run_in_main_asyncio_loop(coroutine)

    def run_in_async_executor(self, coroutine):
        return self._octobot.task_manager.run_in_async_executor(coroutine)

    def stop_tasks(self) -> None:
        self._octobot.task_manager.stop_tasks()

    def stop_bot(self) -> None:
        command_stop(self._octobot)

    @staticmethod
    def restart_bot() -> None:
        command_restart()
