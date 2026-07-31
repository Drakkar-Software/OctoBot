# pylint: disable=C0103
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
import contextlib
import multiprocessing
import os
import time
import typing

import octobot_commons.errors as errors


_LOCKS = {}
_ELEMENTS = {}


class FilesystemBasedLockTimeoutError(errors.ProcessError):
    """Raised when async_filesystem_based_lock cannot be acquired within the timeout."""


def register_lock_and_shared_elements(
    name: str, lock: multiprocessing.RLock, shared_elements: dict
):
    """
    Add elements to the globally available elements
    """
    _LOCKS[name] = lock
    _ELEMENTS.update(shared_elements)


def unregister_lock_and_shared_elements(
    name: str, shared_elements=None
) -> multiprocessing.RLock:
    """
    Remove elements to the globally available elements
    """
    if shared_elements is None:
        _ELEMENTS.clear()
    else:
        for key in shared_elements:
            _ELEMENTS.pop(key)
    return _LOCKS.pop(name)


@contextlib.contextmanager
def registered_lock_and_shared_elements(
    name: str, lock: multiprocessing.RLock, shared_elements: dict
):
    """
    Add and remove elements to the globally available elements
    """
    try:
        register_lock_and_shared_elements(name, lock, shared_elements)
        yield lock
    finally:
        unregister_lock_and_shared_elements(name, shared_elements)


def get_lock(name: str) -> multiprocessing.RLock:
    """
    Returns a shared lock
    """
    return _LOCKS[name]


def get_shared_element(shared_elements_name: str) -> multiprocessing.RLock:
    """
    Returns a shared element
    """
    return _ELEMENTS[shared_elements_name]


def _is_stale_lock_file(lock_file_path: str, stale_lock_max_age_seconds: float) -> bool:
    if stale_lock_max_age_seconds <= 0:
        return False
    try:
        lock_age_seconds = time.time() - os.path.getmtime(lock_file_path)
    except FileNotFoundError:
        return False
    return lock_age_seconds > stale_lock_max_age_seconds


def _remove_stale_lock_file_if_needed(
    lock_file_path: str, stale_lock_max_age_seconds: float
) -> None:
    if _is_stale_lock_file(lock_file_path, stale_lock_max_age_seconds):
        try:
            os.remove(lock_file_path)
        except FileNotFoundError:
            pass


def _ensure_lock_file_parent_directory(lock_file_path: str) -> None:
    lock_directory = os.path.dirname(lock_file_path)
    if lock_directory:
        os.makedirs(lock_directory, exist_ok=True)


def _open_lock_file_exclusive(lock_file_path: str) -> typing.IO:
    lock_file_descriptor = os.open(
        lock_file_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
    )
    lock_file = os.fdopen(lock_file_descriptor, "w")
    lock_file.write(f"pid={os.getpid()} acquired_at={time.time()}\n")
    lock_file.flush()
    return lock_file


def _raise_lock_timeout_error(acquire_timeout_seconds: float) -> None:
    raise FilesystemBasedLockTimeoutError(
        f"Could not acquire filesystem lock within {acquire_timeout_seconds} seconds"
    ) from None


async def _acquire_filesystem_based_lock(
    lock_file_path: str,
    *,
    acquire_timeout_seconds: float,
    stale_lock_max_age_seconds: float,
    retry_interval_seconds: float,
) -> typing.IO:
    _ensure_lock_file_parent_directory(lock_file_path)
    deadline = time.monotonic() + acquire_timeout_seconds
    while True:
        _remove_stale_lock_file_if_needed(lock_file_path, stale_lock_max_age_seconds)
        try:
            return _open_lock_file_exclusive(lock_file_path)
        except FileExistsError:
            if time.monotonic() >= deadline:
                _raise_lock_timeout_error(acquire_timeout_seconds)
            await asyncio.sleep(retry_interval_seconds)


def _release_filesystem_based_lock(
    lock_file: typing.Optional[typing.IO], lock_file_path: str
) -> None:
    if lock_file is not None:
        lock_file.close()
    try:
        os.remove(lock_file_path)
    except FileNotFoundError:
        pass


@contextlib.asynccontextmanager
async def async_filesystem_based_lock(
    lock_file_path: str,
    *,
    acquire_timeout_seconds: float = 300,
    stale_lock_max_age_seconds: float = 1800,
    retry_interval_seconds: float = 0.5,
):
    """
    Async cross-process lock using atomic exclusive file creation.
    """
    lock_file = None
    try:
        lock_file = await _acquire_filesystem_based_lock(
            lock_file_path,
            acquire_timeout_seconds=acquire_timeout_seconds,
            stale_lock_max_age_seconds=stale_lock_max_age_seconds,
            retry_interval_seconds=retry_interval_seconds,
        )
        yield
    finally:
        _release_filesystem_based_lock(lock_file, lock_file_path)
