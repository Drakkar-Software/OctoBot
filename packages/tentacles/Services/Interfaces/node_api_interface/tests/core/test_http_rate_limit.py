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
from fastapi import HTTPException, status

import octobot_commons.in_process_rate_limit as in_process_rate_limit

try:
    import tentacles.Services.Interfaces.node_api_interface.core.http_rate_limit as http_rate_limit
except ImportError:
    from core import http_rate_limit  # type: ignore[no-redef]

_DEFAULT_DETAIL = "Too many requests. Try again later."
_CLIENT_IP = "1.2.3.4"


class CountedError(Exception):
    pass


class OtherError(Exception):
    pass


def _limiter(max_failures=2, *, rate_limited_detail=_DEFAULT_DETAIL):
    policy = in_process_rate_limit.FailureWindowPolicy(
        name="client_ip",
        max_failures=max_failures,
        window_seconds=60.0,
    )
    return http_rate_limit.HTTPRateLimiter(
        (policy,),
        rate_limited_detail=rate_limited_detail,
    )


def _decorated_handler(limiter, inner_handler):
    return http_rate_limit.http_failure_rate_limited(
        limiter,
        get_dimensions=lambda **dimensions: {"client_ip": dimensions["client_ip"]},
        record_failure_on=(CountedError,),
    )(inner_handler)


class TestHTTPRateLimiterRaiseIfRateLimited:
    def test_raises_429_with_default_detail(self):
        limiter = _limiter(max_failures=2)
        limiter.record_failure(client_ip=_CLIENT_IP)
        limiter.record_failure(client_ip=_CLIENT_IP)
        with pytest.raises(HTTPException) as exc_info:
            limiter.raise_if_rate_limited(client_ip=_CLIENT_IP)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc_info.value.detail == _DEFAULT_DETAIL

    def test_raises_429_with_detail_override(self):
        limiter = _limiter(max_failures=2)
        limiter.record_failure(client_ip=_CLIENT_IP)
        limiter.record_failure(client_ip=_CLIENT_IP)
        with pytest.raises(HTTPException) as exc_info:
            limiter.raise_if_rate_limited(client_ip=_CLIENT_IP, detail="Custom")
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc_info.value.detail == "Custom"

    def test_no_op_when_not_limited(self):
        limiter = _limiter(max_failures=2)
        limiter.raise_if_rate_limited(client_ip=_CLIENT_IP)


class TestHttpFailureRateLimited:
    def test_returns_wrapped_result_when_not_limited(self):
        limiter = _limiter(max_failures=2)

        def inner(client_ip: str = _CLIENT_IP):
            return "ok"

        handler = _decorated_handler(limiter, inner)
        assert handler(client_ip=_CLIENT_IP) == "ok"
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is False

    def test_skips_wrapped_when_already_limited(self):
        limiter = _limiter(max_failures=2)
        limiter.record_failure(client_ip=_CLIENT_IP)
        limiter.record_failure(client_ip=_CLIENT_IP)
        inner_mock = mock.Mock()

        def inner(client_ip: str = _CLIENT_IP):
            inner_mock()
            return "ok"

        handler = _decorated_handler(limiter, inner)
        with pytest.raises(HTTPException) as exc_info:
            handler(client_ip=_CLIENT_IP)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        inner_mock.assert_not_called()

    def test_records_failure_on_listed_exception(self):
        limiter = _limiter(max_failures=2)

        def inner(client_ip: str = _CLIENT_IP):
            raise CountedError("fail")

        handler = _decorated_handler(limiter, inner)
        with pytest.raises(CountedError):
            handler(client_ip=_CLIENT_IP)
        with pytest.raises(CountedError):
            handler(client_ip=_CLIENT_IP)
        with pytest.raises(HTTPException):
            handler(client_ip=_CLIENT_IP)

    def test_does_not_record_failure_on_unlisted_exception(self):
        limiter = _limiter(max_failures=2)
        limiter.record_failure(client_ip=_CLIENT_IP)

        def inner(client_ip: str = _CLIENT_IP):
            raise OtherError("fail")

        handler = _decorated_handler(limiter, inner)
        with pytest.raises(OtherError):
            handler(client_ip=_CLIENT_IP)
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is False

    def test_records_success_on_normal_return(self):
        limiter = _limiter(max_failures=3)
        limiter.record_failure(client_ip=_CLIENT_IP)
        limiter.record_failure(client_ip=_CLIENT_IP)
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is False

        def inner(client_ip: str = _CLIENT_IP):
            return "ok"

        handler = _decorated_handler(limiter, inner)
        assert handler(client_ip=_CLIENT_IP) == "ok"
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is False
        for _ in range(3):
            limiter.record_failure(client_ip=_CLIENT_IP)
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is True

    def test_get_dimensions_receives_bound_defaults(self):
        limiter = _limiter(max_failures=2)
        captured_dimensions = {}

        def inner(client_ip: str = "9.9.9.9"):
            return "ok"

        def get_dimensions(**dimensions):
            captured_dimensions["client_ip"] = dimensions["client_ip"]
            return {"client_ip": dimensions["client_ip"]}

        handler = http_rate_limit.http_failure_rate_limited(
            limiter,
            get_dimensions=get_dimensions,
            record_failure_on=(CountedError,),
        )(inner)
        handler()
        assert captured_dimensions["client_ip"] == "9.9.9.9"


class TestRunWithFailureRateLimit:
    def test_records_failure_when_predicate_matches(self):
        limiter = _limiter(max_failures=2)

        def action():
            raise CountedError("fail")

        with pytest.raises(CountedError):
            http_rate_limit.run_with_failure_rate_limit(
                limiter,
                dimensions={"client_ip": _CLIENT_IP},
                action=action,
                should_record_failure=lambda err: isinstance(err, CountedError),
            )
        with pytest.raises(CountedError):
            http_rate_limit.run_with_failure_rate_limit(
                limiter,
                dimensions={"client_ip": _CLIENT_IP},
                action=action,
                should_record_failure=lambda err: isinstance(err, CountedError),
            )
        with pytest.raises(HTTPException):
            http_rate_limit.run_with_failure_rate_limit(
                limiter,
                dimensions={"client_ip": _CLIENT_IP},
                action=action,
                should_record_failure=lambda err: isinstance(err, CountedError),
            )

    def test_skips_failure_recording_when_predicate_false(self):
        limiter = _limiter(max_failures=2)
        limiter.record_failure(client_ip=_CLIENT_IP)

        def action():
            raise OtherError("fail")

        with pytest.raises(OtherError):
            http_rate_limit.run_with_failure_rate_limit(
                limiter,
                dimensions={"client_ip": _CLIENT_IP},
                action=action,
                should_record_failure=lambda err: isinstance(err, CountedError),
            )
        assert limiter.is_rate_limited(client_ip=_CLIENT_IP) is False
