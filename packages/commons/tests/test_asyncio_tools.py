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
import pytest

import octobot_commons.asyncio_tools as asyncio_tools

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_without_error_container():
    # will not propagate exception
    asyncio.get_event_loop().call_soon(_exception_raiser)


async def test_with_error_container():
    error_container = asyncio_tools.ErrorContainer()
    error_container.print_received_exceptions = False
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    # will propagate exception
    asyncio.get_event_loop().call_soon(_exception_raiser)
    with pytest.raises(AssertionError):
        # ensure exception is caught
        await asyncio.create_task(error_container.check())


async def test_with_error_container_2_exceptions():
    error_container = asyncio_tools.ErrorContainer()
    error_container.print_received_exceptions = False
    asyncio.get_event_loop().set_exception_handler(error_container.exception_handler)
    # will propagate exception
    asyncio.get_event_loop().call_soon(_exception_raiser)
    asyncio.get_event_loop().call_soon(_exception_raiser)
    with pytest.raises(AssertionError):
        # ensure exception is caught
        await asyncio.create_task(error_container.check())


async def test_gather_waiting_for_all_before_raising():
    # Test successful case: all coroutines complete successfully
    async def success_coro_1():
        await asyncio.sleep(0.01)
        return 1
    
    async def success_coro_2():
        await asyncio.sleep(0.01)
        return 2
    
    results = await asyncio_tools.gather_waiting_for_all_before_raising(
        success_coro_1(), success_coro_2()
    )
    assert results == [1, 2]
    
    # Test failure case: one coroutine raises an exception
    # All coroutines should complete before the exception is raised
    completion_order = []
    
    async def failing_coro():
        await asyncio.sleep(0.02)
        completion_order.append("failing")
        raise ValueError("Test error")
    
    async def slow_success_coro():
        await asyncio.sleep(0.1)
        completion_order.append("slow_success")
        return "success"
    
    async def fast_success_coro():
        await asyncio.sleep(0.01)
        completion_order.append("fast_success")
        return "fast"
    
    with pytest.raises(ValueError, match="Test error"):
        await asyncio_tools.gather_waiting_for_all_before_raising(
            failing_coro(), slow_success_coro(), fast_success_coro()
        )
    
    # Verify all coroutines completed before exception was raised
    assert len(completion_order) == 3
    assert "fast_success" in completion_order
    assert "failing" in completion_order
    assert "slow_success" in completion_order
    
    # Test multiple exceptions: should raise the first one encountered
    completion_order.clear()
    
    async def failing_coro_1():
        await asyncio.sleep(0.02)
        completion_order.append("failing_1")
        raise ValueError("First error")
    
    async def failing_coro_2():
        await asyncio.sleep(0.1)
        completion_order.append("failing_2")
        raise RuntimeError("Second error")
    
    async def success_coro():
        await asyncio.sleep(0.01)
        completion_order.append("success")
        return "ok"
    
    with pytest.raises(ValueError, match="First error"):
        await asyncio_tools.gather_waiting_for_all_before_raising(
            failing_coro_1(), failing_coro_2(), success_coro()
        )
    
    # Verify all coroutines completed
    assert len(completion_order) == 3


async def test_RLock_valid_setup():
    lock_1 = asyncio_tools.RLock()
    lock_2 = asyncio_tools.RLock()

    passed_a = passed_b = passed_c = passed_d = passed_e = False
    async with lock_1:
        passed_a = True
        async with lock_1:
            passed_b = True
            assert lock_1._depth == 2
            async with lock_2:
                passed_c = True
                async with lock_2:
                    assert lock_2._depth == 2
                    passed_d = True
                    async with lock_1:
                        assert lock_1._task is asyncio.current_task()
                        assert lock_2._task is asyncio.current_task()
                        assert lock_1._depth == 3
                        passed_e = True
                    assert lock_1._depth == 2
    assert lock_1._depth == 0
    assert lock_2._depth == 0
    assert lock_1._locked is False
    assert lock_2._locked is False
    assert lock_1._task is None
    assert lock_2._task is None
    assert all((passed_a, passed_b, passed_c, passed_d, passed_e))


async def test_RLock_multiple_tasks():
    lock = asyncio_tools.RLock()
    started = {
        "a": False,
        "b": False,
        "c": False,
    }
    passed = {
        "a": False,
        "b": False,
        "c": False,
    }
    released = {
        "a": False,
        "b": False,
        "c": False,
    }

    async def passing_task(identifier, is_waiting):
        started[identifier] = True
        async with lock:
            if is_waiting:
                await asyncio_tools.wait_asyncio_next_cycle()
            assert lock._depth == 1
            assert lock._task == asyncio.current_task()
            passed[identifier] = True
        released[identifier] = True

    asyncio.create_task(passing_task("a", True))
    asyncio.create_task(passing_task("b", False))
    asyncio.create_task(passing_task("c", False))

    # tasks did not run yet
    assert all(v is False for v in started.values())

    # let the loop run once
    await asyncio_tools.wait_asyncio_next_cycle()

    # all tasks started
    assert started == {
        "a": True,
        "b": True,
        "c": True,
    }
    # "a" waits for next cycle, others wait for lock that "a" got
    assert passed == {
        "a": False,
        "b": False,
        "c": False,
    }
    assert released == {
        "a": False,
        "b": False,
        "c": False,
    }
    await asyncio_tools.wait_asyncio_next_cycle()
    # "a" release the lock, "b" can get it
    assert passed == {
        "a": True,
        "b": True,
        "c": False,
    }
    assert released == {
        "a": True,
        "b": True,
        "c": False,
    }
    # "b" release the lock, "c" can get it
    await asyncio_tools.wait_asyncio_next_cycle()

    assert all(v is True for v in passed.values())
    assert all(v is True for v in released.values())


async def test_RLock_error_setup_1():
    lock = asyncio_tools.RLock()

    passed_a = passed_b = False

    # _depth is too high: lock is not cleared
    async with lock:
        passed_a = True
        lock._depth += 1
        async with lock:
            passed_b = True
            assert lock._depth == 3
    assert lock._depth == 1
    assert lock._task is asyncio.current_task()
    assert lock._locked is True

    assert all((passed_a, passed_b))


async def test_RLock_error_setup_2():
    lock = asyncio_tools.RLock()
    lock._depth = 1

    # a lock can't have a non 0 depth when firstly acquired
    with pytest.raises(RuntimeError):
        async with lock:
            pass


def _exception_raiser():
    raise RuntimeError("error")
