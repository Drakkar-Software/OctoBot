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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import enum
import typing


class OperatorSignal(enum.StrEnum):
    """
    Canonical operator signal strings. Call sites pass *.value where a plain str API is expected.
    """
    STOP = "STOP"
    UPDATE_CONFIG = "UPDATE_CONFIG"


class OperatorSignals:
    """
    Mutable map of DSL operator name to execution signal string for one interpreter/run.

    ``sync`` clears and replaces ``signal_by_operator`` (same pattern as DSLExecutor before each
    action execution).
    """

    def __init__(self):
        self.signal_by_operator: typing.Dict[str, typing.Any] = {}

    def sync(self, signals: typing.Dict[str, typing.Any]) -> None:
        """
        Replaces signals mapping with the given signals.
        """
        self.signal_by_operator.clear()
        self.signal_by_operator.update(signals)


class SignalableOperatorMixin:
    """
    Mixin for operators whose behavior depends on execution signals keyed by operator name.

    Each instance holds an optional ``OperatorSignals`` shared for the DSL run (typically one per
    interpreter). Callers fill the map via ``OperatorSignals.sync`` (e.g. DSLExecutor before
    interpretation). ``get_name()`` identifies which map entry applies to ``matches_operator_signal``.
    """

    def __init__(self, signals: typing.Optional[OperatorSignals] = None):
        self.signals: typing.Optional[OperatorSignals] = signals

    def matches_operator_signal(self, signal: str) -> bool:
        """Return whether ``self.signals`` maps this operator's name to ``signal``."""
        if self.signals is None:
            return False
        return self.signals.signal_by_operator.get(self.get_name()) == signal # type: ignore

    @classmethod
    def should_dispatch_operator_signal_for_result( # pylint: disable=unused-argument
        cls,
        signal: str,
        re_calling_result: typing.Optional[dict],
    ) -> bool:
        """
        When draining dispatcher-driven operator signals for automation shutdown, whether this
        operator should run its branch for the given previous re-calling payload.
        Default: do nothing; subclasses override.
        """
        return False
