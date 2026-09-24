#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

try:
    from core.in_process_rate_limit import (  # type: ignore[no-redef]
        FailureWindowPolicy,
        InProcessFailureRateLimiter,
    )
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.core.in_process_rate_limit import (
        FailureWindowPolicy,
        InProcessFailureRateLimiter,
    )

_RECOVER_CLIENT_IP_POLICY = FailureWindowPolicy(
    name="client_ip",
    max_failures=5,
    window_seconds=15 * 60,
)
_RECOVER_ADDRESS_POLICY = FailureWindowPolicy(
    name="address",
    max_failures=10,
    window_seconds=60 * 60,
    normalize_key=str.lower,
)


def _build_recover_passphrase_limiter() -> InProcessFailureRateLimiter:
    return InProcessFailureRateLimiter(
        (_RECOVER_CLIENT_IP_POLICY, _RECOVER_ADDRESS_POLICY),
    )


class RecoverPassphraseRateLimiter:
    """Passphrase recovery budgets wired to the generic in-process limiter."""

    def __init__(
        self,
        limiter: InProcessFailureRateLimiter | None = None,
    ) -> None:
        self._limiter = limiter or _build_recover_passphrase_limiter()

    def reset_all(self) -> None:
        self._limiter.reset_all()

    def is_rate_limited(self, client_ip: str, address: str) -> bool:
        return self._limiter.is_rate_limited(client_ip=client_ip, address=address)

    def record_failure(self, client_ip: str, address: str) -> None:
        self._limiter.record_failure(client_ip=client_ip, address=address)

    def record_success(self, client_ip: str, address: str) -> None:
        self._limiter.record_success(client_ip=client_ip, address=address)


_recover_passphrase_rate_limiter = RecoverPassphraseRateLimiter()


def get_recover_passphrase_rate_limiter() -> RecoverPassphraseRateLimiter:
    return _recover_passphrase_rate_limiter
