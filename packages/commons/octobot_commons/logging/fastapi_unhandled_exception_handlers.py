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

import logging as stdlib_logging
import typing

import octobot_commons.logging.logging_util as logging_util

_fastapi_available = False

try:
    import starlette.requests
    import starlette.responses
    _fastapi_available = True
except ImportError:
    pass

if typing.TYPE_CHECKING:
    from fastapi import FastAPI


def register_unhandled_exception_handler(app: "FastAPI", logger_name: str) -> None:
    """Log unhandled API exceptions to OctoBot logging and return HTTP 500."""
    if not _fastapi_available:
        stdlib_logging.getLogger(__name__).warning(
            "FastAPI is not installed; unhandled exception handler was not registered for %r",
            logger_name,
        )
        return

    logger = logging_util.get_logger(logger_name)

    async def unhandled_exception_handler(
        request: starlette.requests.Request,
        exc: Exception,
    ) -> starlette.responses.JSONResponse:
        logger.exception(
            exc,
            True,
            f"Unhandled API error: {request.method} {request.url.path}",
        )
        return starlette.responses.JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    app.add_exception_handler(Exception, unhandled_exception_handler)
