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
import typing

import octobot_node.enums

_SCHEDULER_QUEUE_SPECS: tuple[
    tuple[octobot_node.enums.SchedulerQueues, dict[str, typing.Any]],
    ...,
] = (
    (octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE, {}),
    (octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE, {}),
    (
        octobot_node.enums.SchedulerQueues.DBOS_CLEANUP_QUEUE,
        {"global_concurrency": 1},
    ),
    (
        octobot_node.enums.SchedulerQueues.GLOBAL_VIEW_QUEUE,
        {"global_concurrency": 1},
    ),
    (
        octobot_node.enums.SchedulerQueues.PORTFOLIO_HISTORY_QUEUE,
        {"global_concurrency": 1},
    ),
)


async def register_scheduler_queues_async() -> None:
    """Register DBOS scheduler queues after launch."""
    import octobot_node.scheduler as scheduler_module

    if scheduler_module.SCHEDULER.INSTANCE is None:
        raise RuntimeError("Scheduler not initialized")
    for queue, register_kwargs in _SCHEDULER_QUEUE_SPECS:
        await scheduler_module.SCHEDULER.INSTANCE.register_queue_async(
            queue.value,
            **register_kwargs,
        )
