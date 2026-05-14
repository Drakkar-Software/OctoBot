import dataclasses

import typing
import octobot_commons.dataclasses.minimizable_dataclass
import octobot_node.models as models


@dataclasses.dataclass
class UserActionPostActions(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    to_create_automation_task: typing.Optional[models.Task] = None
