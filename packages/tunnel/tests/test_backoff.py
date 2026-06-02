import pytest

from octobot_tunnel.client.backoff import Backoff

pytestmark = pytest.mark.asyncio


class TestBackoff:
    def test_initial_backoff_equals_min(self):
        bo = Backoff(retries=0, min_backoff=0.1, max_backoff=15.0)
        delay, should_retry = bo.backoff()
        assert should_retry
        assert 0.1 <= delay <= 0.1 * 1.1

    def test_backoff_doubles(self):
        bo = Backoff(retries=0, min_backoff=0.1, max_backoff=15.0)
        d1, _ = bo.backoff()
        d2, _ = bo.backoff()
        # d2 should be roughly 2*d1 (with up to 10% jitter)
        assert d2 >= d1 * 1.8
        assert d2 <= d1 * 2.0 * 1.1

    def test_jitter_is_between_1_and_1_point_1(self):
        bo = Backoff(retries=0, min_backoff=1.0, max_backoff=100.0)
        for _ in range(50):
            delay, _ = bo.backoff()
            # First call: delay must be 1.0 .. 1.1
            assert 1.0 <= delay <= 1.1
            break  # only check first call

    def test_max_backoff_cap(self):
        bo = Backoff(retries=0, min_backoff=1.0, max_backoff=5.0)
        last = 0.0
        for _ in range(20):
            last, _ = bo.backoff()
        # Should not exceed max_backoff * 1.1 (accounting for jitter)
        assert last <= 5.0 * 1.1

    def test_infinite_retries_never_returns_false(self):
        bo = Backoff(retries=0, min_backoff=0.001, max_backoff=0.01)
        for _ in range(1000):
            _, should_retry = bo.backoff()
            assert should_retry

    def test_limited_retries_exhausted(self):
        bo = Backoff(retries=3, min_backoff=0.001, max_backoff=1.0)
        results = [bo.backoff() for _ in range(5)]
        should_retries = [r[1] for r in results]
        # retries=3: attempts 1,2,3 → True, attempt 4 → True (attempts==retries),
        # attempt 5 (attempts > retries) → False
        assert should_retries[:4] == [True, True, True, True]
        assert should_retries[4] is False

    def test_backoff_sequence_never_decreases_before_cap(self):
        bo = Backoff(retries=0, min_backoff=0.1, max_backoff=1000.0)
        prev = 0.0
        for _ in range(10):
            d, _ = bo.backoff()
            # Allow for jitter; previous * 2 * 0.9 is a loose lower bound
            assert d >= prev * 0.9
            prev = d
