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

import octobot.constants as constants
import octobot.commands as commands
import octobot_commons.constants as commons_constants
import octobot.automation as automation
import octobot_commons.singleton as singleton
import octobot_commons.enums as commons_enums


class OctoBotAPIProvider(singleton.Singleton):
    def __init__(self):
        self.octobot_api_by_bot_id: dict[str, "OctoBotAPI"] = {}

    def get_api(self, bot_id: str) -> "OctoBotAPI":
        return self.octobot_api_by_bot_id[bot_id]

    def register_api(self, bot_id: str, octobot_api: "OctoBotAPI"):
        self.octobot_api_by_bot_id[bot_id] = octobot_api

    def unregister_api(self, bot_id: str):
        self.octobot_api_by_bot_id.pop(bot_id)


class OctoBotAPI:

    def __init__(self, octobot):
        self._octobot = octobot
        OctoBotAPIProvider.instance().register_api(self._octobot.bot_id, self)

    def is_initialized(self) -> bool:
        return self._octobot.initialized

    def get_exchange_manager_ids(self) -> list:
        return self._octobot.exchange_producer.exchange_manager_ids

    def get_global_config(self) -> dict:
        return self._octobot.config

    def get_startup_config(self, dict_only=True):
        return self._octobot.get_startup_config(constants.CONFIG_KEY, dict_only=dict_only)

    def get_edited_config(self, dict_only=True):
        return self._octobot.get_edited_config(constants.CONFIG_KEY, dict_only=dict_only)

    def get_startup_tentacles_config(self):
        return self._octobot.get_startup_config(constants.TENTACLES_SETUP_CONFIG_KEY)

    def get_edited_tentacles_config(self):
        return self._octobot.get_edited_config(constants.TENTACLES_SETUP_CONFIG_KEY)

    def set_edited_tentacles_config(self, config):
        self._octobot.set_edited_config(constants.TENTACLES_SETUP_CONFIG_KEY, config)

    def get_trading_mode(self):
        return self._octobot.get_trading_mode()

    def get_tentacles_setup_config(self):
        return self._octobot.tentacles_setup_config

    def get_startup_messages(self) -> list:
        return self._octobot.startup_messages

    def get_start_time(self) -> float:
        return self._octobot.start_time

    def get_bot_id(self) -> str:
        return self._octobot.bot_id

    def get_matrix_id(self) -> str:
        return self._octobot.evaluator_producer.matrix_id

    def get_aiohttp_session(self) -> object:
        return self._octobot.get_aiohttp_session()

    def get_automation(self) -> automation.Automation:
        return self._octobot.automation

    def get_interface(self, interface_class):
        for interface in self._octobot.interface_producer.interfaces:
            if isinstance(interface, interface_class):
                return interface

    def run_in_main_asyncio_loop(
        self, coroutine, log_exceptions=True, timeout=commons_constants.DEFAULT_FUTURE_TIMEOUT
    ):
        return self._octobot.run_in_main_asyncio_loop(
            coroutine, log_exceptions=log_exceptions, timeout=timeout
        )

    def run_in_async_executor(self, coroutine):
        return self._octobot.task_manager.run_in_async_executor(coroutine)

    async def stop_all_trading_modes_and_pause_traders(
        self,
        stop_reason: commons_enums.StopReason,
        execution_details: typing.Optional[automation.ExecutionDetails],
        schedule_bot_stop: bool,
    ):
        stop_details = f"Error status: {stop_reason.value}: {execution_details=}"
        if self._octobot.exchange_producer.are_all_trading_modes_stoppped_and_traders_paused():
            self._octobot.logger.debug(
                f"Skipping stop all trading modes and pause traders request. {stop_details}"
            )
            return
        try:
            self._octobot.logger.info(
                f"Scheduling bot stop. {stop_details}"
            )
            await self._octobot.exchange_producer.stop_all_trading_modes_and_pause_traders(execution_details)
        except Exception as err:
            self._octobot.logger.exception(err, True, f"Error when stopping trading modes: {err}")
        await self._octobot.community_auth.community_bot.on_trading_modes_stopped_and_traders_paused(
            stop_reason,
            execution_details,
            schedule_bot_stop,
        )

    def stop_tasks(self) -> None:
        self._octobot.task_manager.stop_tasks()

    def stop_bot(self) -> None:
        commands.stop_bot(self._octobot)

    @staticmethod
    def restart_bot() -> None:
        commands.restart_bot()

    def update_bot(self) -> None:
        commands.update_bot(self)

    def clear(self):
        OctoBotAPIProvider.instance().unregister_api(self._octobot.bot_id)
