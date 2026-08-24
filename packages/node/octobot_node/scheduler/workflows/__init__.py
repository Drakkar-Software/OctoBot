#  Drakkar-Software OctoBot-Node
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


def register_workflows() -> None:
    import octobot_node.scheduler.workflows.automation_workflow
    import octobot_node.scheduler.workflows.user_action_workflow
    import octobot_node.scheduler.workflows.dbos_cleanup_workflow
    import octobot_node.scheduler.workflows.global_view_workflow
    import octobot_node.scheduler.workflows.portfolio_history_workflow
