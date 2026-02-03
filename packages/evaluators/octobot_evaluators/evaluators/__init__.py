#  Drakkar-Software OctoBot-Evaluators
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
import octobot_evaluators.enums
from octobot_evaluators.evaluators import abstract_evaluator
from octobot_evaluators.evaluators.abstract_evaluator import (
    AbstractEvaluator,
)

from octobot_evaluators.evaluators import evaluator_factory
from octobot_evaluators.evaluators import realtime_evaluator
from octobot_evaluators.evaluators import social_evaluator
from octobot_evaluators.evaluators import TA_evaluator
from octobot_evaluators.evaluators import scripted_evaluator
from octobot_evaluators.evaluators import abstract_util
from octobot_evaluators.evaluators import strategy_evaluator

from octobot_evaluators.evaluators.evaluator_factory import (
    create_evaluator,
    create_and_start_all_type_evaluators,
    create_evaluators,
    create_temporary_evaluator_with_local_config,
)
from octobot_evaluators.evaluators.realtime_evaluator import (
    RealTimeEvaluator,
)
from octobot_evaluators.evaluators.social_evaluator import (
    SocialEvaluator,
)
from octobot_evaluators.evaluators.TA_evaluator import (
    TAEvaluator,
)
from octobot_evaluators.evaluators.scripted_evaluator import (
    ScriptedEvaluator,
)
from octobot_evaluators.evaluators.abstract_util import (
    AbstractUtil,
)
from octobot_evaluators.evaluators.strategy_evaluator import (
    StrategyEvaluator,
)


EvaluatorClassTypes = {
    octobot_evaluators.enums.EvaluatorMatrixTypes.TA.value: TAEvaluator,
    octobot_evaluators.enums.EvaluatorMatrixTypes.SOCIAL.value: SocialEvaluator,
    octobot_evaluators.enums.EvaluatorMatrixTypes.REAL_TIME.value: RealTimeEvaluator,
    octobot_evaluators.enums.EvaluatorMatrixTypes.SCRIPTED.value: ScriptedEvaluator,
    octobot_evaluators.enums.EvaluatorMatrixTypes.STRATEGIES.value: StrategyEvaluator
}

evaluator_class_str_to_matrix_type_dict = {
    "TAEvaluator": octobot_evaluators.enums.EvaluatorMatrixTypes.TA,
    "SocialEvaluator": octobot_evaluators.enums.EvaluatorMatrixTypes.SOCIAL,
    "RealTimeEvaluator": octobot_evaluators.enums.EvaluatorMatrixTypes.REAL_TIME,
    "ScriptedEvaluator": octobot_evaluators.enums.EvaluatorMatrixTypes.SCRIPTED,
    "StrategyEvaluator": octobot_evaluators.enums.EvaluatorMatrixTypes.STRATEGIES
}

__all__ = [
    "RealTimeEvaluator",
    "AbstractEvaluator",
    "SocialEvaluator",
    "TAEvaluator",
    "ScriptedEvaluator",
    "AbstractUtil",
    "StrategyEvaluator",
    "EvaluatorClassTypes",
    "create_evaluator",
    "create_and_start_all_type_evaluators",
    "create_evaluators",
    "create_temporary_evaluator_with_local_config",
    "evaluator_class_str_to_matrix_type_dict",
]
