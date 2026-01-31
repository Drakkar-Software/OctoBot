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
import typing

MatrixValueType = typing.NewType('MatrixValueType', typing.Union[str, int, float])

START_EVAL_PERTINENCE = 1
MAX_TA_EVAL_TIME_SECONDS = 0.1
EVALUATION_ALLOWED_TIME_DELTA = 10
EVALUATOR_EVAL_DEFAULT_TYPE = float
STRATEGIES_REQUIRED_TIME_FRAME = "required_time_frames"
STRATEGIES_REQUIRED_EVALUATORS = "required_evaluators"
STRATEGIES_COMPATIBLE_EVALUATOR_TYPES = "compatible_evaluator_types"
CONFIG_FORCED_TIME_FRAME = "forced_time_frame"
TENTACLE_DEFAULT_CONFIG = "default_config"

EVALUATOR_CLASS_TYPE_MRO_INDEX = -4

EVALUATORS_CHANNEL: str = "Evaluators"
MATRIX_CHANNEL: str = "Matrix"
MATRIX_CHANNELS: str = "MatrixChannels"

TA_RE_EVALUATION_TRIGGER_UPDATED_DATA = "TA_re_evaluation_trigger_updated_data"
RESET_EVALUATION = "reset_evaluation"
EVALUATOR_CHANNEL_DATA_ACTION = "action"
EVALUATOR_CHANNEL_DATA_EXCHANGE_ID = "exchange_id"
EVALUATOR_CHANNEL_DATA_TIME_FRAMES = "time_frames"
