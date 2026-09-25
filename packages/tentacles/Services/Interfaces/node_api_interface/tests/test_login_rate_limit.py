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

from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.login import (
    get_login_rate_limiter,
)


def test_ip_bucket_limits_after_ten_failures():
    limiter = get_login_rate_limiter()
    limiter.reset_all()
    for _ in range(10):
        limiter.record_failure(client_ip="1.2.3.4")
    assert limiter.is_rate_limited(client_ip="1.2.3.4") is True


def test_success_clears_ip_bucket():
    limiter = get_login_rate_limiter()
    limiter.reset_all()
    for _ in range(9):
        limiter.record_failure(client_ip="1.2.3.4")
    limiter.record_success(client_ip="1.2.3.4")
    assert limiter.is_rate_limited(client_ip="1.2.3.4") is False
