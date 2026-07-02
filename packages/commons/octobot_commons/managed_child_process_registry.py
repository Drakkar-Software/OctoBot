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
import threading
import time
import typing

import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging
import octobot_commons.process_util as process_util
import octobot_commons.singleton.singleton_class as singleton_class


class ManagedChildProcessRegistry(singleton_class.Singleton):
    """
    Thread-safe registry of OS pids spawned by spawn_managed_subprocess.
    Used at parent shutdown to SIGTERM (then force-kill) child OctoBot processes.
    """

    def __init__(self) -> None:
        self._pids: set[int] = set()
        self._lock = threading.Lock()
        self._logger = commons_logging.get_logger(self.__class__.__name__)

    def register(self, pid: int) -> None:
        """Record a managed child pid. No-op for pid <= 0."""
        if pid <= 0:
            return
        with self._lock:
            self._pids.add(pid)
            registered_count = len(self._pids)
        self._logger.debug(
            "Registered managed child pid=%s (count=%s)",
            pid,
            registered_count,
        )

    def unregister(self, pid: int) -> None:
        """Remove a pid from the registry. No-op if not present."""
        with self._lock:
            self._pids.discard(pid)
        self._logger.debug("Unregistered managed child pid=%s", pid)

    def snapshot_running_pids(self) -> frozenset[int]:
        """Prune dead pids, return a point-in-time copy of still-running entries."""
        with self._lock:
            dead_pids = {
                pid for pid in self._pids if not process_util.pid_is_running(pid)
            }
            self._pids -= dead_pids
            return frozenset(self._pids)

    async def graceful_stop_all(
        self,
        *,
        timeout_seconds: float,
        poll_interval: float = 0.2,
    ) -> dict[int, str]:
        """SIGTERM all snapshot pids, wait, force-kill survivors. Returns per-pid outcome."""
        pids = self.snapshot_running_pids()
        if not pids:
            return {}

        self._logger.info(
            "Graceful stop for %s managed child process(es): %s",
            len(pids),
            sorted(pids),
        )

        signal_outcomes: dict[int, dict[str, typing.Any]] = {}
        for pid in pids:
            try:
                signal_outcomes[pid] = process_util.request_graceful_stop_via_sigterm(
                    pid,
                    logger=self._logger,
                )
            except commons_errors.ProcessError as err:
                self._logger.warning(
                    "Failed to send SIGTERM to managed child pid=%s: %s",
                    pid,
                    err,
                )
                signal_outcomes[pid] = {"status": "failed", "reason": str(err)}

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not any(process_util.pid_is_running(pid) for pid in pids):
                break
            await asyncio.sleep(poll_interval)

        outcomes: dict[int, str] = {}
        for pid in pids:
            if not process_util.pid_is_running(pid):
                sig_status = signal_outcomes.get(pid, {}).get("status", "stopped")
                outcomes[pid] = (
                    "already_stopped" if sig_status == "already_stopped" else "stopped"
                )
                self.unregister(pid)
                continue
            try:
                process_util.request_force_kill(pid, logger=self._logger)
            except commons_errors.ProcessError as err:
                self._logger.error(
                    "Force kill failed for managed child pid=%s: %s",
                    pid,
                    err,
                )
                outcomes[pid] = "failed"
                continue
            if not process_util.pid_is_running(pid):
                outcomes[pid] = "force_killed"
                self.unregister(pid)
            else:
                self._logger.error(
                    "Managed child pid=%s still running after force kill",
                    pid,
                )
                outcomes[pid] = "failed"

        self._logger.info("Managed child graceful stop outcomes: %s", outcomes)
        return outcomes
