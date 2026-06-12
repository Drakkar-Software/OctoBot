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
import dataclasses
import typing

import octobot_commons.dataclasses as commons_dataclasses


def eval_note_type_as_str(eval_note_type: typing.Any) -> typing.Optional[str]:
    if eval_note_type is None:
        return None
    if isinstance(eval_note_type, str):
        return eval_note_type
    if isinstance(eval_note_type, type):
        return eval_note_type.__name__
    return str(eval_note_type)


@dataclasses.dataclass
class EvaluatorResult(commons_dataclasses.MinimizableDataclass):
    symbol: typing.Optional[str]
    time_frame: typing.Optional[str]
    evaluator_name: str
    evaluator_type: str
    cryptocurrency: typing.Optional[str]
    eval_note: typing.Optional[typing.Any] = None
    eval_note_type: typing.Optional[str] = None
    eval_time: float = 0
    eval_note_description: typing.Optional[str] = None
    eval_note_metadata: typing.Optional[typing.Any] = None
