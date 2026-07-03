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
import asyncio

import mock
import pytest

import octobot.task_manager as task_manager_module


class TestStopTasksForceExit:
    def test_force_timeout_calls_os_exit(self):
        octobot_mock = mock.Mock()
        octobot_mock.community_handler = None

        task_manager = task_manager_module.TaskManager(octobot_mock)
        task_manager.async_loop = mock.Mock()

        with mock.patch("octobot_commons.asyncio_tools.run_coroutine_in_asyncio_loop") as run_coroutine_mock:
            run_coroutine_mock.side_effect = asyncio.TimeoutError
            with mock.patch("os._exit") as os_exit_mock:
                with mock.patch("asyncio.run_coroutine_threadsafe"):
                    task_manager.stop_tasks(force=True)
                os_exit_mock.assert_called_once_with(1)

    def test_non_force_timeout_calls_sys_exit(self):
        octobot_mock = mock.Mock()
        octobot_mock.community_handler = None

        task_manager = task_manager_module.TaskManager(octobot_mock)
        task_manager.async_loop = mock.Mock()

        with mock.patch("octobot_commons.asyncio_tools.run_coroutine_in_asyncio_loop") as run_coroutine_mock:
            run_coroutine_mock.side_effect = asyncio.TimeoutError
            with mock.patch("os._exit") as os_exit_mock:
                with pytest.raises(SystemExit) as exit_info:
                    task_manager.stop_tasks(force=False)
                os_exit_mock.assert_not_called()
                assert exit_info.value.code == -1
