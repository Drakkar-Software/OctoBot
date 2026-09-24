#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import dataclasses
import threading
import time

_IP_MAX_FAILURES = 5
_IP_WINDOW_SECONDS = 15 * 60
_ADDRESS_MAX_FAILURES = 10
_ADDRESS_WINDOW_SECONDS = 60 * 60


@dataclasses.dataclass
class _FailureBucket:
    failure_count: int = 0
    window_start: float = 0.0


class RecoverPassphraseRateLimiter:
    """In-process dual-bucket rate limiter for passphrase recovery attempts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ip_buckets: dict[str, _FailureBucket] = {}
        self._address_buckets: dict[str, _FailureBucket] = {}

    def reset_all(self) -> None:
        with self._lock:
            self._ip_buckets.clear()
            self._address_buckets.clear()

    def _normalize_address(self, address: str) -> str:
        return address.lower()

    def _is_limited(
        self,
        buckets: dict[str, _FailureBucket],
        key: str,
        max_failures: int,
        window_seconds: float,
    ) -> bool:
        now = time.monotonic()
        bucket = buckets.get(key)
        if bucket is None or now - bucket.window_start >= window_seconds:
            buckets[key] = _FailureBucket(failure_count=0, window_start=now)
            return False
        return bucket.failure_count >= max_failures

    def is_rate_limited(self, client_ip: str, address: str) -> bool:
        normalized_address = self._normalize_address(address)
        with self._lock:
            if self._is_limited(
                self._ip_buckets, client_ip, _IP_MAX_FAILURES, _IP_WINDOW_SECONDS
            ):
                return True
            return self._is_limited(
                self._address_buckets,
                normalized_address,
                _ADDRESS_MAX_FAILURES,
                _ADDRESS_WINDOW_SECONDS,
            )

    def record_failure(self, client_ip: str, address: str) -> None:
        normalized_address = self._normalize_address(address)
        now = time.monotonic()
        with self._lock:
            for buckets, key, window_seconds in (
                (self._ip_buckets, client_ip, _IP_WINDOW_SECONDS),
                (self._address_buckets, normalized_address, _ADDRESS_WINDOW_SECONDS),
            ):
                bucket = buckets.get(key)
                if bucket is None or now - bucket.window_start >= window_seconds:
                    bucket = _FailureBucket(failure_count=0, window_start=now)
                    buckets[key] = bucket
                bucket.failure_count += 1

    def record_success(self, client_ip: str, address: str) -> None:
        normalized_address = self._normalize_address(address)
        with self._lock:
            self._ip_buckets.pop(client_ip, None)
            self._address_buckets.pop(normalized_address, None)


_recover_passphrase_rate_limiter = RecoverPassphraseRateLimiter()


def get_recover_passphrase_rate_limiter() -> RecoverPassphraseRateLimiter:
    return _recover_passphrase_rate_limiter
