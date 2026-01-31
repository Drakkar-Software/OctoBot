#  Drakkar-Software OctoBot-Commons
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
import numpy as np

from octobot_commons.constants import START_PENDING_EVAL_NOTE, INIT_EVAL_NOTE
from octobot_commons.evaluators_util import check_valid_eval_note


def test_check_valid_eval_note():
    assert not check_valid_eval_note(START_PENDING_EVAL_NOTE)
    assert check_valid_eval_note(True)
    assert check_valid_eval_note({"a": 1})
    assert check_valid_eval_note({"a": 1}, eval_time=1, expiry_delay=2, current_time=1)
    assert check_valid_eval_note({"a": 1}, eval_time=1, expiry_delay=2, current_time=2)
    assert not check_valid_eval_note({"a": 1}, eval_time=1, expiry_delay=2, current_time=3)

    assert check_valid_eval_note(INIT_EVAL_NOTE)
    # UNSET_EVAL_TYPE

