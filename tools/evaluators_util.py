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

import math

from config import START_PENDING_EVAL_NOTE, EVALUATOR_EVAL_DEFAULT_TYPE


UNSET_EVAL_TYPE = "unset_eval_type_param"


# Will also test evaluation type if if eval_type is provided.
# Default expected_eval_type is EVALUATOR_EVAL_DEFAULT_TYPE
def check_valid_eval_note(eval_note, eval_type=UNSET_EVAL_TYPE, expected_eval_type=EVALUATOR_EVAL_DEFAULT_TYPE):
    if eval_type != UNSET_EVAL_TYPE and eval_type != expected_eval_type:
        return False
    return eval_note and eval_note is not START_PENDING_EVAL_NOTE and not math.isnan(eval_note)
