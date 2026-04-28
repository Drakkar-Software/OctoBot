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
import mock

import pytest

import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.dsl_interpreter.operators.process_bound_operator_mixin as process_bound_operator_mixin
import octobot_commons.errors as commons_errors
import octobot_commons.process_util as process_util


class _BareOperator(dsl_interpreter_operator.Operator):
    @staticmethod
    def get_name() -> str:
        return "bare_process_bound_test"


class _BoundOperator(
    dsl_interpreter_operator.Operator,
    process_bound_operator_mixin.ProcessBoundOperatorMixin,
):
    @staticmethod
    def get_name() -> str:
        return "bound_process_bound_test"


class TestProcessBoundOperatorMixinInit:
    def test_pid_starts_none(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        assert bound.pid is None


class TestIsProcessRunning:
    def test_false_when_pid_not_set(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        assert bound.is_process_running() is False

    def test_delegates_to_process_util(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        bound.pid = 12345
        with mock.patch.object(process_util, "pid_is_running", return_value=True) as running_mock:
            assert bound.is_process_running() is True
        running_mock.assert_called_once_with(12345)


class TestRequestGracefulStop:
    def test_raises_when_pid_not_set(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        with pytest.raises(commons_errors.DSLInterpreterError, match="No process id set"):
            bound.request_graceful_stop()

    def test_delegates_to_process_util(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        bound.pid = 99
        expected = {"status": "stopped", "signal": "sigterm"}
        with mock.patch.object(
            process_util,
            "request_graceful_stop_via_sigterm",
            return_value=expected,
        ) as stop_mock:
            result = bound.request_graceful_stop(logger=mock.sentinel.log)
        assert result == expected
        stop_mock.assert_called_once_with(99, logger=mock.sentinel.log)


class TestSpawnSubprocess:
    def test_sets_self_pid_from_child_and_returns_popen(self):
        bound = process_bound_operator_mixin.ProcessBoundOperatorMixin()
        fake_popen = mock.Mock()
        fake_popen.pid = 777
        with mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
            return_value=fake_popen,
        ) as spawn_mock:
            returned = bound.spawn_subprocess(
                ["/bin/true"],
                working_directory="/tmp/wd",
                environment={"A": "1"},
                hide_console_window=True,
            )
        assert returned is fake_popen
        assert bound.pid == 777
        spawn_mock.assert_called_once_with(
            ["/bin/true"],
            working_directory="/tmp/wd",
            environment={"A": "1"},
            hide_console_window=True,
        )


class TestRejectUserPathSegment:
    def test_accepts_simple_relative_path(self):
        process_bound_operator_mixin.ProcessBoundOperatorMixin.reject_user_path_segment("bots/mybot")

    def test_raises_on_parent_directory_parts(self):
        with pytest.raises(commons_errors.DSLInterpreterError, match="parent directory"):
            process_bound_operator_mixin.ProcessBoundOperatorMixin.reject_user_path_segment("a/../b")


class TestFindFirstFreeListenPortAfterBase:
    def test_returns_base_when_free(self):
        mixin = process_bound_operator_mixin.ProcessBoundOperatorMixin
        with mock.patch.object(mixin, "_tcp_port_is_free", return_value=True):
            listen_port = mixin.find_first_free_listen_port_after_base("127.0.0.1", 50000)
        assert listen_port == 50000

    def test_skips_until_first_free_port(self):
        mixin = process_bound_operator_mixin.ProcessBoundOperatorMixin
        with mock.patch.object(mixin, "_tcp_port_is_free", side_effect=[False, False, True]):
            listen_port = mixin.find_first_free_listen_port_after_base("127.0.0.1", 50100)
        assert listen_port == 50102

    def test_skips_blocklisted_ports(self):
        mixin = process_bound_operator_mixin.ProcessBoundOperatorMixin
        with mock.patch.object(mixin, "_tcp_port_is_free", return_value=True):
            listen_port = mixin.find_first_free_listen_port_after_base(
                "127.0.0.1",
                50200,
                blocklist=[50200],
            )
        assert listen_port == 50201

    def test_raises_when_scan_exhausted(self):
        mixin = process_bound_operator_mixin.ProcessBoundOperatorMixin
        with mock.patch.object(mixin, "_tcp_port_is_free", return_value=False):
            with pytest.raises(commons_errors.DSLInterpreterError, match="No free listen port"):
                mixin.find_first_free_listen_port_after_base("127.0.0.1", 50300, max_offset=2)


class TestBindAddressForEnvAndProbeHosts:
    def test_defaults_bind_and_probe_to_loopback(self):
        resolved_bind, probe_bind = (
            process_bound_operator_mixin.ProcessBoundOperatorMixin.bind_address_for_env_and_probe_hosts({})
        )
        assert resolved_bind == "127.0.0.1"
        assert probe_bind == "127.0.0.1"

    def test_any_bind_uses_loopback_probe(self):
        resolved_bind, probe_bind = (
            process_bound_operator_mixin.ProcessBoundOperatorMixin.bind_address_for_env_and_probe_hosts(
                {"bind_host": "0.0.0.0"}
            )
        )
        assert resolved_bind == "0.0.0.0"
        assert probe_bind == "127.0.0.1"

    def test_custom_bind_listen_key(self):
        resolved_bind, probe_bind = (
            process_bound_operator_mixin.ProcessBoundOperatorMixin.bind_address_for_env_and_probe_hosts(
                {"listen_addr": "10.0.0.5"},
                bind_listen_key="listen_addr",
            )
        )
        assert resolved_bind == "10.0.0.5"
        assert probe_bind == "10.0.0.5"


class TestSpawnManagedSubprocessStatic:
    def test_delegates_to_process_util(self):
        sentinel_popen = mock.sentinel.proc
        argv = ["a", "b"]
        with mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
            return_value=sentinel_popen,
        ) as spawn_mock:
            result = process_bound_operator_mixin.ProcessBoundOperatorMixin.spawn_managed_subprocess(
                argv,
                working_directory="/proj",
                environment=None,
                hide_console_window=False,
            )
        assert result is sentinel_popen
        spawn_mock.assert_called_once_with(
            argv,
            working_directory="/proj",
            environment=None,
            hide_console_window=False,
        )


class TestIsProcessBound:
    def test_true_for_operator_using_mixin(self):
        assert process_bound_operator_mixin.is_process_bound(_BoundOperator()) is True

    def test_false_for_operator_without_mixin(self):
        assert process_bound_operator_mixin.is_process_bound(_BareOperator()) is False

