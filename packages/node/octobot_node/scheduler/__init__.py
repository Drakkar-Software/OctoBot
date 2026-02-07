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

from tentacles.Services.Interfaces.node_api.core.config import settings
from octobot_node.scheduler.scheduler import Scheduler
from octobot_node.scheduler.consumer import SchedulerConsumer

scheduler_logger = logging.getLogger(__name__)

SCHEDULER: Scheduler = Scheduler()
SCHEDULER.create()
CONSUMER: SchedulerConsumer = SchedulerConsumer(SCHEDULER)

# Import tasks to register them with the scheduler
from octobot_node.scheduler import tasks  # noqa: F401

# Start the consumer automatically when the module is imported
if settings.SCHEDULER_WORKERS > 0:
    CONSUMER.start()
