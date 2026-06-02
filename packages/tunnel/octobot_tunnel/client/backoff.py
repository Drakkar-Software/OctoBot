import random


class Backoff:
    """
    Exponential backoff with 10% random jitter, matching the Go client.

    Set retries=0 to retry forever.
    """

    def __init__(self, retries: int, min_backoff: float, max_backoff: float):
        self._retries = retries
        self._min_backoff = min_backoff
        self._max_backoff = max_backoff
        self._attempts = 0
        self._last_backoff = 0.0

    def backoff(self) -> tuple[float, bool]:
        """Return (delay_seconds, should_retry)."""
        if self._retries != 0 and self._attempts > self._retries:
            return 0.0, False
        self._attempts += 1
        delay = self._next_wait()
        self._last_backoff = delay
        return delay, True

    def _next_wait(self) -> float:
        if self._last_backoff == 0.0:
            b = self._min_backoff
        else:
            b = self._last_backoff * 2.0
        if b > self._max_backoff:
            b = self._max_backoff
        jitter = 1.0 + random.random() * 0.1
        return b * jitter
