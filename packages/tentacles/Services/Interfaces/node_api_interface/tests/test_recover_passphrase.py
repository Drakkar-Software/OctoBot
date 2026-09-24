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

from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.recover_passphrase import (
    get_recover_passphrase_rate_limiter,
)


def test_ip_bucket_limits_after_five_failures():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xabc"
    for _ in range(5):
        limiter.record_failure(client_ip="1.2.3.4", address=address)
    assert limiter.is_rate_limited(client_ip="1.2.3.4", address=address) is True


def test_address_bucket_limits_after_ten_failures():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xdef"
    for i in range(10):
        limiter.record_failure(client_ip=f"10.0.0.{i}", address=address)
    assert limiter.is_rate_limited(client_ip="10.0.0.99", address=address) is True


def test_success_resets_buckets():
    limiter = get_recover_passphrase_rate_limiter()
    address = "0xabc"
    for _ in range(4):
        limiter.record_failure(client_ip="1.2.3.4", address=address)
    limiter.record_success(client_ip="1.2.3.4", address=address)
    assert limiter.is_rate_limited(client_ip="1.2.3.4", address=address) is False
