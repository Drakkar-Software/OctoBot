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
import asyncio
import sys
import time

import mock
import pytest

import octobot_commons.managed_child_process_registry as managed_child_process_registry
import octobot_commons.process_util as process_util
import octobot_commons.singleton.singleton_class as singleton_class


@pytest.fixture(autouse=True)
def reset_managed_child_process_registry():
    yield
    singleton_class.Singleton._instances.pop(
        managed_child_process_registry.ManagedChildProcessRegistry,
        None,
    )


class TestManagedChildProcessRegistryInstance:
    def test_instance_returns_same_object(self):
        first = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        second = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        assert first is second


class TestManagedChildProcessRegistryRegister:
    def test_register_ignores_non_positive_pid(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        registry.register(0)
        registry.register(-3)
        assert registry.snapshot_running_pids() == frozenset()

    def test_register_adds_pid_to_snapshot(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        with mock.patch.object(
            managed_child_process_registry.process_util,
            "pid_is_running",
            return_value=True,
        ):
            registry.register(101)
            assert registry.snapshot_running_pids() == frozenset({101})

    def test_register_is_idempotent(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        with mock.patch.object(
            managed_child_process_registry.process_util,
            "pid_is_running",
            return_value=True,
        ):
            registry.register(202)
            registry.register(202)
            assert registry.snapshot_running_pids() == frozenset({202})


class TestManagedChildProcessRegistryUnregister:
    def test_unregister_removes_pid(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        with mock.patch.object(process_util, "pid_is_running", return_value=True):
            registry.register(303)
            registry.unregister(303)
        assert registry.snapshot_running_pids() == frozenset()

    def test_unregister_unknown_pid_is_no_op(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        registry.unregister(99999)
        assert registry.snapshot_running_pids() == frozenset()


class TestManagedChildProcessRegistrySnapshotRunningPids:
    def test_lazy_prunes_dead_pids(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        with mock.patch.object(process_util, "pid_is_running", return_value=True):
            registry.register(404)
        with mock.patch.object(process_util, "pid_is_running", return_value=False):
            assert registry.snapshot_running_pids() == frozenset()
        assert registry.snapshot_running_pids() == frozenset()


class TestManagedChildProcessRegistryGracefulStopAll:
    @pytest.mark.asyncio
    async def test_stops_spawned_child_via_sigterm(self, tmp_path):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        child = process_util.spawn_managed_subprocess(
            [
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ],
            working_directory=str(tmp_path),
        )
        try:
            assert child.pid in registry.snapshot_running_pids()
            outcomes = await registry.graceful_stop_all(timeout_seconds=15.0)
            assert outcomes[child.pid] in {"stopped", "already_stopped"}
            deadline = time.monotonic() + 15.0
            while child.poll() is None and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
            assert child.poll() is not None
            assert child.pid not in registry.snapshot_running_pids()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)

    @pytest.mark.asyncio
    async def test_force_kills_child_when_graceful_stop_times_out(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        force_kill_requested = False

        def pid_is_running_side_effect(_pid):
            return not force_kill_requested

        def request_force_kill_side_effect(_pid, *, logger=None):
            nonlocal force_kill_requested
            force_kill_requested = True
            return {"status": "force_killed"}

        with (
            mock.patch.object(
                managed_child_process_registry.process_util,
                "pid_is_running",
                side_effect=pid_is_running_side_effect,
            ),
            mock.patch.object(
                managed_child_process_registry.process_util,
                "request_graceful_stop_via_sigterm",
                return_value={"status": "stopped", "signal": "sigterm"},
            ),
            mock.patch.object(
                managed_child_process_registry.process_util,
                "request_force_kill",
                side_effect=request_force_kill_side_effect,
            ) as force_kill_mock,
        ):
            registry.register(777)
            outcomes = await registry.graceful_stop_all(
                timeout_seconds=0.1,
                poll_interval=0.01,
            )
        assert outcomes[777] == "force_killed"
        force_kill_mock.assert_called_once_with(777, logger=registry._logger)
        assert registry.snapshot_running_pids() == frozenset()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_registered_children(self):
        registry = managed_child_process_registry.ManagedChildProcessRegistry.instance()
        outcomes = await registry.graceful_stop_all(timeout_seconds=1.0)
        assert outcomes == {}
