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

import mock
import pytest
from fastapi import HTTPException

from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.recover_passphrase import (
    get_recover_passphrase_rate_limiter,
)

_MONOTONIC_PATCH = "octobot_commons.in_process_rate_limit.time.monotonic"
_TIME_PATCH = "tentacles.Services.Interfaces.node_api_interface.core.http_rate_limit.time.time"


def test_ip_bucket_limits_after_five_failures():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xabc"
    for _ in range(5):
        limiter.record_failure(client_ip="1.2.3.4", address=address)
    assert limiter.is_rate_limited(client_ip="1.2.3.4", address=address) is True


def test_address_bucket_limits_after_ten_failures():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xdef"
    for index in range(10):
        limiter.record_failure(client_ip=f"10.0.0.{index}", address=address)
    assert limiter.is_rate_limited(client_ip="10.0.0.99", address=address) is True


def test_success_resets_buckets():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xabc"
    for _ in range(4):
        limiter.record_failure(client_ip="1.2.3.4", address=address)
    limiter.record_success(client_ip="1.2.3.4", address=address)
    assert limiter.is_rate_limited(client_ip="1.2.3.4", address=address) is False


def test_raise_if_rate_limited_unblock_at_uses_address_window():
    limiter = get_recover_passphrase_rate_limiter()
    limiter.reset_all()
    address = "0xdef"
    with mock.patch(_MONOTONIC_PATCH, return_value=0.0):
        for index in range(10):
            limiter.record_failure(client_ip=f"10.0.0.{index}", address=address)
    with mock.patch(_MONOTONIC_PATCH, return_value=0.0), mock.patch(
        _TIME_PATCH,
        return_value=1000.0,
    ):
        with pytest.raises(HTTPException) as exc_info:
            limiter.raise_if_rate_limited(client_ip="10.0.0.99", address=address)
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["unblock_at"] == 4600
