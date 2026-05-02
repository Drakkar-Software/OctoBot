#  Drakkar-Software OctoBot-Tentacles
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
import collections

import pytest
import pytest_asyncio

try:
    from tentacles.Services.Services_bases.gpt_service.rpm_limiter import RPMLimiter, _WINDOW_SECONDS
except ImportError:
    from rpm_limiter import RPMLimiter, _WINDOW_SECONDS


class _FakeClock:
    """Shared monotonic clock state shared between monkeypatched time.monotonic and asyncio.sleep."""
    def __init__(self, start: float = 1000.0):
        self.now = start
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, duration: float) -> None:
        self.sleeps.append(duration)
        self.now += duration


@pytest.fixture
def fake_clock(monkeypatch) -> _FakeClock:
    import time
    clock = _FakeClock()
    monkeypatch.setattr(time, "monotonic", clock.monotonic)
    # Patch asyncio.sleep inside the rpm_limiter module
    try:
        import tentacles.Services.Services_bases.gpt_service.rpm_limiter as mod
    except ImportError:
        import rpm_limiter as mod
    monkeypatch.setattr(mod.asyncio, "sleep", clock.sleep)
    return clock


@pytest.mark.asyncio
async def test_under_cap_no_wait(fake_clock):
    lim = RPMLimiter(rpm=5, name="test")
    for _ in range(5):
        await lim.acquire()
    assert fake_clock.sleeps == [], "no sleeps expected when under the cap"
    assert len(lim._timestamps) == 5


@pytest.mark.asyncio
async def test_at_cap_blocks_until_oldest_evicts(fake_clock):
    # rpm=3: acquire at t=0, +1, +2 — all fit. 4th at same t=2 must wait until oldest+60.
    lim = RPMLimiter(rpm=3, name="test")
    fake_clock.now = 0.0

    fake_clock.now = 0.0; await lim.acquire()
    fake_clock.now = 1.0; await lim.acquire()
    fake_clock.now = 2.0; await lim.acquire()
    # 4th call: oldest is at t=0, window ends at 60. wait = 0+60-2 = 58.
    fake_clock.now = 2.0
    await lim.acquire()

    assert len(fake_clock.sleeps) == 1
    assert abs(fake_clock.sleeps[0] - 58.0) < 0.01, f"expected ~58s, got {fake_clock.sleeps[0]}"


@pytest.mark.asyncio
async def test_sliding_window_partial_release(fake_clock):
    # rpm=2: first at t=0, second at t=30. Third at t=30 — window not fully expired.
    # oldest is t=0, ends at t=60 → wait = 60-30 = 30s.
    lim = RPMLimiter(rpm=2, name="test")
    fake_clock.now = 0.0; await lim.acquire()
    fake_clock.now = 30.0; await lim.acquire()
    fake_clock.now = 30.0; await lim.acquire()

    assert len(fake_clock.sleeps) == 1
    assert abs(fake_clock.sleeps[0] - 30.0) < 0.01, f"expected 30s, got {fake_clock.sleeps[0]}"


@pytest.mark.asyncio
async def test_eviction_drops_stale_timestamps(fake_clock):
    # Acquire 5 times early, jump clock past window, next acquire should be instant.
    lim = RPMLimiter(rpm=10, name="test")
    fake_clock.now = 0.0
    for i in range(5):
        fake_clock.now = float(i)
        await lim.acquire()

    # Jump to t=120 — all previous timestamps are >60s old.
    fake_clock.now = 120.0
    await lim.acquire()

    assert fake_clock.sleeps == [], "stale timestamps should have been evicted — no sleep"
    assert len(lim._timestamps) == 1, "only the latest acquire should remain in the deque"


@pytest.mark.asyncio
async def test_concurrent_acquires_serialize(fake_clock):
    # rpm=2, 5 concurrent acquires at t=0.
    # Execution order (serialized by the lock):
    #   Task1 & Task2: fit under cap — no sleep. deque=[0, 0]
    #   Task3: window full → sleeps 60s (clock→60). Eviction clears both t=0 entries. deque=[60]
    #   Task4: 1 entry in window → fits free. deque=[60, 60]
    #   Task5: window full again → sleeps 60s (clock→120). deque=[120]
    # Total: exactly 2 sleeps, each 60s.
    lim = RPMLimiter(rpm=2, name="test")
    fake_clock.now = 0.0

    tasks = [asyncio.create_task(lim.acquire()) for _ in range(5)]
    await asyncio.gather(*tasks)

    assert len(fake_clock.sleeps) == 2, f"expected 2 sleeps, got {fake_clock.sleeps}"
    for sleep_dur in fake_clock.sleeps:
        assert abs(sleep_dur - 60.0) < 1.0, f"expected ~60s sleep, got {sleep_dur}"


@pytest.mark.asyncio
async def test_rejects_non_positive_rpm():
    with pytest.raises(ValueError, match="0"):
        RPMLimiter(rpm=0)
    with pytest.raises(ValueError, match="-1"):
        RPMLimiter(rpm=-1)


@pytest.mark.asyncio
async def test_logs_when_throttling(fake_clock, caplog):
    import logging
    lim = RPMLimiter(rpm=1, name="mytest")
    fake_clock.now = 0.0
    await lim.acquire()  # fills the slot
    with caplog.at_level(logging.DEBUG):
        await lim.acquire()  # triggers throttle log

    throttle_records = [r for r in caplog.records if "RPM cap hit" in r.message]
    assert throttle_records, "expected a DEBUG log mentioning 'RPM cap hit'"
    assert "mytest" in throttle_records[0].message
