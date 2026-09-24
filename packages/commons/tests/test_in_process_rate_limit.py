#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.

import octobot_commons.in_process_rate_limit as in_process_rate_limit


def test_generic_limiter_normalizes_keys_per_policy():
    limiter = in_process_rate_limit.InProcessFailureRateLimiter(
        (
            in_process_rate_limit.FailureWindowPolicy(
                name="address",
                max_failures=2,
                window_seconds=60,
                normalize_key=str.lower,
            ),
        ),
    )
    limiter.record_failure(address="0xAbC")
    limiter.record_failure(address="0xabc")
    assert limiter.is_rate_limited(address="0xABC") is True
