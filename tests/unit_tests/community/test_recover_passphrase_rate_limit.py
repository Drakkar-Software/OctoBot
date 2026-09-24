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

from octobot.community.wallet_backend.recover_passphrase_rate_limit import (
    RecoverPassphraseRateLimiter,
)


def test_ip_bucket_limits_after_five_failures():
    limiter = RecoverPassphraseRateLimiter()
    address = "0xabc"
    for _ in range(5):
        limiter.record_failure("1.2.3.4", address)
    assert limiter.is_rate_limited("1.2.3.4", address) is True


def test_address_bucket_limits_after_ten_failures():
    limiter = RecoverPassphraseRateLimiter()
    address = "0xdef"
    for i in range(10):
        limiter.record_failure(f"10.0.0.{i}", address)
    assert limiter.is_rate_limited("10.0.0.99", address) is True


def test_success_resets_buckets():
    limiter = RecoverPassphraseRateLimiter()
    address = "0xabc"
    for _ in range(4):
        limiter.record_failure("1.2.3.4", address)
    limiter.record_success("1.2.3.4", address)
    assert limiter.is_rate_limited("1.2.3.4", address) is False
