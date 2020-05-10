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
from octobot_backtesting.api.backtesting import get_backtesting_data_files

from octobot.api.backtesting import create_independent_backtesting, initialize_and_run_independent_backtesting, \
    join_independent_backtesting, stop_independent_backtesting, log_independent_backtesting_report
from octobot.commands import stop_bot
from octobot.octobot import OctoBot


class OctoBotBacktestingFactory(OctoBot):
    def __init__(self, config, log_report=True, run_on_common_part_only=True):
        super().__init__(config)
        self.independent_backtesting = None
        self.log_report = log_report
        self.run_on_common_part_only = run_on_common_part_only

    async def initialize(self):
        try:
            await self.initializer.create()
            self.independent_backtesting = create_independent_backtesting(
                self.config,
                self.tentacles_setup_config,
                get_backtesting_data_files(self.config),
                run_on_common_part_only=self.run_on_common_part_only)
            await initialize_and_run_independent_backtesting(self.independent_backtesting, log_errors=False)
            await join_independent_backtesting(self.independent_backtesting)
            if self.log_report:
                log_independent_backtesting_report(self.independent_backtesting)
            await stop_independent_backtesting(self.independent_backtesting, memory_check=False)
        except Exception as e:
            self.logger.error(f"Error when starting backtesting: {e}")
        finally:
            self.task_manager.stop_tasks()
