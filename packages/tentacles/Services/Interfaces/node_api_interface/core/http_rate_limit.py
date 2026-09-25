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

import functools
import inspect
import typing

from fastapi import HTTPException, status

import octobot_commons.in_process_rate_limit as in_process_rate_limit

FailureWindowPolicy = in_process_rate_limit.FailureWindowPolicy

_T = typing.TypeVar("_T")


class HTTPRateLimiter(in_process_rate_limit.InProcessFailureRateLimiter):
    """HTTP-facing failure rate limiter; raises FastAPI 429 when a budget is exceeded."""

    def __init__(
        self,
        policies: tuple[FailureWindowPolicy, ...],
        *,
        rate_limited_detail: str = "Too many requests. Try again later.",
    ) -> None:
        super().__init__(policies)
        self._rate_limited_detail = rate_limited_detail

    def raise_if_rate_limited(
        self,
        *,
        detail: str | None = None,
        **dimensions: str,
    ) -> None:
        if self.is_rate_limited(**dimensions):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail or self._rate_limited_detail,
            )


def run_with_failure_rate_limit(
    rate_limiter: HTTPRateLimiter,
    *,
    dimensions: dict[str, str],
    action: typing.Callable[[], _T],
    should_record_failure: typing.Callable[[BaseException], bool],
) -> _T:
    """Check budgets, run action, record failure/success on the limiter's policies."""
    rate_limiter.raise_if_rate_limited(**dimensions)
    try:
        result = action()
    except BaseException as err:
        if should_record_failure(err):
            rate_limiter.record_failure(**dimensions)
        raise
    rate_limiter.record_success(**dimensions)
    return result


def http_failure_rate_limited(
    rate_limiter: HTTPRateLimiter,
    *,
    get_dimensions: typing.Callable[..., dict[str, str]],
    record_failure_on: tuple[type[Exception], ...],
) -> typing.Callable[[typing.Callable[..., typing.Any]], typing.Callable[..., typing.Any]]:
    """Decorate a route handler; budgets live on the limiter's policies."""

    def decorator(
        wrapped: typing.Callable[..., typing.Any],
    ) -> typing.Callable[..., typing.Any]:
        signature = inspect.signature(wrapped)

        @functools.wraps(wrapped)
        def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            dimensions = get_dimensions(**bound.arguments)
            return run_with_failure_rate_limit(
                rate_limiter,
                dimensions=dimensions,
                action=lambda: wrapped(*args, **kwargs),
                should_record_failure=lambda err: isinstance(err, record_failure_on),
            )

        return wrapper

    return decorator
