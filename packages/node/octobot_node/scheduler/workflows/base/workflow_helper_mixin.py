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
import dbos as dbos_lib

import octobot_node.scheduler.workflows.params.base_params as base_params


class DBOSWorkflowHelperMixin:
    @staticmethod
    def get_name(workflow_status: dbos_lib.WorkflowStatus) -> str:
        if workflow_status.input:
            for input in list(workflow_status.input.get("args", [])) + list(workflow_status.input.get("kwargs", {}).values()):
                if isinstance(input, base_params.Tracker):
                    return input.name
        raise ValueError(f"No Tracker found in workflow status: {workflow_status}")
        
    @staticmethod
    async def sleep_if_needed(t: base_params.Tracker, delay: float) -> None:
        if delay > 0:
            t.logger.info(f"Sleeping for {delay} seconds ...")
            await dbos_lib.DBOS.sleep_async(delay)
