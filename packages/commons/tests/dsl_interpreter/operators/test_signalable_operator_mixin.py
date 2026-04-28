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

import octobot_commons.dsl_interpreter as dsl_interpreter


class _TestSignalOperatorA(dsl_interpreter.SignalableOperatorMixin):
    def __init__(self, signals=None):
        super().__init__(signals)

    @staticmethod
    def get_name() -> str:
        return "op_signal_a"


class _TestSignalOperatorB(dsl_interpreter.SignalableOperatorMixin):
    def __init__(self, signals=None):
        super().__init__(signals)

    @staticmethod
    def get_name() -> str:
        return "op_signal_b"


class TestSignalableOperatorMixin:
    def test_matches_operator_signal_false_by_default(self):
        stop = dsl_interpreter.OperatorSignal.STOP.value
        assert _TestSignalOperatorA().matches_operator_signal(stop) is False
        assert _TestSignalOperatorB().matches_operator_signal(stop) is False
        shared_signals = dsl_interpreter.OperatorSignals()
        assert _TestSignalOperatorA(shared_signals).matches_operator_signal(stop) is False
        assert _TestSignalOperatorB(shared_signals).matches_operator_signal(stop) is False

    def test_signal_for_one_operator_does_not_match_other(self):
        stop = dsl_interpreter.OperatorSignal.STOP.value
        shared_signals = dsl_interpreter.OperatorSignals()
        op_signal_a = _TestSignalOperatorA(shared_signals)
        op_signal_b = _TestSignalOperatorB(shared_signals)
        shared_signals.sync({op_signal_a.get_name(): stop})
        assert op_signal_a.matches_operator_signal(stop) is True
        assert op_signal_b.matches_operator_signal(stop) is False
        shared_signals.sync({})
        assert op_signal_a.matches_operator_signal(stop) is False
        assert op_signal_b.matches_operator_signal(stop) is False

    def test_multiple_operator_signals_on_shared_container(self):
        stop = dsl_interpreter.OperatorSignal.STOP.value
        update_config = dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value
        shared_signals = dsl_interpreter.OperatorSignals()
        op_signal_a = _TestSignalOperatorA(shared_signals)
        op_signal_b = _TestSignalOperatorB(shared_signals)
        shared_signals.sync(
            {
                op_signal_a.get_name(): stop,
                op_signal_b.get_name(): update_config,
            }
        )
        assert op_signal_a.matches_operator_signal(stop) is True
        assert op_signal_a.matches_operator_signal(update_config) is False
        assert op_signal_b.matches_operator_signal(update_config) is True
        assert op_signal_b.matches_operator_signal(stop) is False

    def test_should_dispatch_operator_signal_for_result_default_false(self):
        assert _TestSignalOperatorA.should_dispatch_operator_signal_for_result(
            dsl_interpreter.OperatorSignal.STOP.value,
            {},
        ) is False

    def test_operator_signals_sync_replaces_map(self):
        stop = dsl_interpreter.OperatorSignal.STOP.value
        update_config = dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_signals_holder.sync({_TestSignalOperatorA.get_name(): stop})
        assert operator_signals_holder.signal_by_operator == {
            _TestSignalOperatorA.get_name(): stop
        }
        operator_signals_holder.sync({_TestSignalOperatorB.get_name(): update_config})
        assert operator_signals_holder.signal_by_operator == {
            _TestSignalOperatorB.get_name(): update_config
        }
