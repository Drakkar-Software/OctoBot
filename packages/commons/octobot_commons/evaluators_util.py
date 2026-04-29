# pylint: disable=R0913
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

import octobot_commons.constants as constants

UNSET_EVAL_TYPE = "unset_eval_type_param"


def check_valid_eval_note(
    eval_note,
    eval_type=UNSET_EVAL_TYPE,
    expected_eval_type=None,
    eval_time=None,
    expiry_delay=None,
    current_time=None,
):
    """
    Will also test evaluation type if if eval_type is provided.
    :param eval_note: The evaluation value
    :param eval_type:  The evaluation type
    :param expected_eval_type: The expected type. Default is EVALUATOR_EVAL_DEFAULT_TYPE
    :param eval_time:  The evaluation time
    :param expiry_delay: The allowed evaluation delay
    :param current_time: The current time
    :return: True when evaluation value is valid
    """
    if eval_type != UNSET_EVAL_TYPE and (
        eval_type != expected_eval_type or expected_eval_type is None
    ):
        return False
    return (
        eval_note is not None
        and eval_note is not constants.START_PENDING_EVAL_NOTE
        and (eval_time is None or eval_time + expiry_delay - current_time > 0)
    )
