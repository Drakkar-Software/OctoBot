#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import dataclasses

import octobot_commons.dataclasses.minimizable_dataclass


@dataclasses.dataclass
class SignalPriorityAction(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    id: str
    dsl_script: str
    await_execution_result: bool = True
