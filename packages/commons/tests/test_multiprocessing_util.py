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
import os
import time

import pytest

import octobot_commons.multiprocessing_util as multiprocessing_util


class TestAsyncFilesystemBasedLock:
    pytestmark = pytest.mark.asyncio

    async def test_acquire_and_release_removes_lock_file(self, tmp_path):
        lock_file_path = tmp_path / "test.lock"
        async with multiprocessing_util.async_filesystem_based_lock(str(lock_file_path)):
            assert lock_file_path.is_file()
        assert not lock_file_path.exists()

    async def test_second_acquire_waits_until_release(self, tmp_path):
        lock_file_path = tmp_path / "test.lock"
        second_acquire_finished = asyncio.Event()

        async def hold_then_release():
            async with multiprocessing_util.async_filesystem_based_lock(str(lock_file_path)):
                await asyncio.sleep(0.2)

        holder_task = asyncio.create_task(hold_then_release())
        await asyncio.sleep(0.05)

        async def acquire_after_first():
            async with multiprocessing_util.async_filesystem_based_lock(
                str(lock_file_path),
                acquire_timeout_seconds=5,
                retry_interval_seconds=0.05,
            ):
                second_acquire_finished.set()

        second_task = asyncio.create_task(acquire_after_first())
        await asyncio.wait_for(holder_task, timeout=2)
        await asyncio.wait_for(second_task, timeout=2)
        assert second_acquire_finished.is_set()

    async def test_stale_lock_is_removed_and_reacquired(self, tmp_path):
        lock_file_path = tmp_path / "stale.lock"
        lock_file_path.write_text("stale", encoding="utf-8")
        stale_timestamp = time.time() - 7200
        os.utime(lock_file_path, (stale_timestamp, stale_timestamp))
        async with multiprocessing_util.async_filesystem_based_lock(
            str(lock_file_path),
            stale_lock_max_age_seconds=60,
        ):
            assert lock_file_path.is_file()
        assert not lock_file_path.exists()

    async def test_acquire_timeout_raises(self, tmp_path):
        lock_file_path = tmp_path / "busy.lock"
        lock_file_path.write_text("held", encoding="utf-8")
        with pytest.raises(multiprocessing_util.FilesystemBasedLockTimeoutError):
            async with multiprocessing_util.async_filesystem_based_lock(
                str(lock_file_path),
                acquire_timeout_seconds=0.2,
                stale_lock_max_age_seconds=0,
                retry_interval_seconds=0.05,
            ):
                pass
