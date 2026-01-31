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
import multiprocessing
import contextlib


_LOCKS = {}
_ELEMENTS = {}


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
