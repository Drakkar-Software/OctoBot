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

import dataclasses
import threading
import time
import typing

# RAM-only counters in this process. Not shared across workers, pods, or nodes.


@dataclasses.dataclass(frozen=True)
class FailureWindowPolicy:
    """One failure-count window for a named request dimension (e.g. client IP)."""

    name: str
    max_failures: int
    window_seconds: float
    normalize_key: typing.Callable[[str], str] = lambda key: key


@dataclasses.dataclass
class _FailureBucket:
    failure_count: int = 0
    window_start: float = 0.0


class InProcessFailureRateLimiter:
    """In-process, multi-dimension failure rate limiter (fixed window per key)."""

    def __init__(self, policies: tuple[FailureWindowPolicy, ...]) -> None:
        if not policies:
            raise ValueError("At least one FailureWindowPolicy is required")
        self._policies = policies
        self._lock = threading.Lock()
        self._stores: dict[str, dict[str, _FailureBucket]] = {
            policy.name: {} for policy in policies
        }

    def reset_all(self) -> None:
        """Clear all failure counters for every policy dimension."""
        with self._lock:
            for store in self._stores.values():
                store.clear()

    def _policy_value(self, policy: FailureWindowPolicy, **dimensions: str) -> str:
        try:
            raw = dimensions[policy.name]
        except KeyError:
            raise KeyError(
                f"Missing rate-limit dimension '{policy.name}'"
            ) from None
        return policy.normalize_key(raw)

    def _is_limited_for_policy(
        self,
        policy: FailureWindowPolicy,
        key: str,
        now: float,
    ) -> bool:
        store = self._stores[policy.name]
        bucket = store.get(key)
        if bucket is None or now - bucket.window_start >= policy.window_seconds:
            store[key] = _FailureBucket(failure_count=0, window_start=now)
            return False
        return bucket.failure_count >= policy.max_failures

    def _remaining_seconds_for_policy(
        self,
        policy: FailureWindowPolicy,
        key: str,
        now: float,
    ) -> float:
        """Read-only: seconds until this policy's window ends, or 0 if not limited."""
        store = self._stores[policy.name]
        bucket = store.get(key)
        if bucket is None:
            return 0.0
        if now - bucket.window_start >= policy.window_seconds:
            return 0.0
        if bucket.failure_count < policy.max_failures:
            return 0.0
        remaining = bucket.window_start + policy.window_seconds - now
        if remaining <= 0.0:
            return 0.0
        return remaining

    def retry_after_seconds(self, **dimensions: str) -> float:
        """Monotonic seconds until the strictest active limit expires; 0 if not limited."""
        now = time.monotonic()
        max_remaining = 0.0
        with self._lock:
            for policy in self._policies:
                key = self._policy_value(policy, **dimensions)
                remaining = self._remaining_seconds_for_policy(policy, key, now)
                max_remaining = max(max_remaining, remaining)
        return max_remaining

    def is_rate_limited(self, **dimensions: str) -> bool:
        """Return True when any policy dimension has reached its failure budget."""
        now = time.monotonic()
        with self._lock:
            for policy in self._policies:
                key = self._policy_value(policy, **dimensions)
                if self._is_limited_for_policy(policy, key, now):
                    return True
        return False

    def record_failure(self, **dimensions: str) -> None:
        """Increment failure counts for all policy dimensions."""
        now = time.monotonic()
        with self._lock:
            for policy in self._policies:
                key = self._policy_value(policy, **dimensions)
                store = self._stores[policy.name]
                bucket = store.get(key)
                if (
                    bucket is None
                    or now - bucket.window_start >= policy.window_seconds
                ):
                    bucket = _FailureBucket(failure_count=0, window_start=now)
                    store[key] = bucket
                bucket.failure_count += 1

    def record_success(self, **dimensions: str) -> None:
        """Clear failure counters for the given dimension keys."""
        with self._lock:
            for policy in self._policies:
                key = self._policy_value(policy, **dimensions)
                self._stores[policy.name].pop(key, None)
