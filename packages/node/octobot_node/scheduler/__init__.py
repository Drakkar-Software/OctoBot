#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import logging

import octobot_node.scheduler.scheduler as scheduler_lib
import octobot_node.scheduler.workflows

scheduler_logger = logging.getLogger(__name__)

SCHEDULER: scheduler_lib.Scheduler = scheduler_lib.Scheduler()


def is_enabled() -> bool:
    return SCHEDULER.is_enabled()


def initialize_scheduler():
    scheduler_logger.info("Initializing scheduler")
    SCHEDULER.create()
    octobot_node.scheduler.workflows.register_workflows()
    SCHEDULER.start()
