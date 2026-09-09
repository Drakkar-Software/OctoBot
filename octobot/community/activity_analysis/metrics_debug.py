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
import functools
import typing

import octobot_commons.logging as logging

import octobot.constants as constants


_LOGGER = logging.get_logger("activity_analysis")


def log_activity(action: str, **details) -> None:
    if not constants.ENABLE_ACTIVITY_METRICS_DEBUG_LOGS:
        return
    detail_parts = " ".join(f"{detail_key}={detail_value}" for detail_key, detail_value in details.items())
    _LOGGER.info(
        "Activity metrics %s %s",
        action,
        detail_parts,
    )


def wrapped_exception(
    func: typing.Callable[..., None],
) -> typing.Callable[..., None]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        try:
            func(*args, **kwargs)
        except Exception as err:
            _LOGGER.exception(
                err,
                True,
                f"Activity metrics hook failed hook={func.__name__}: {err}",
            )
    return wrapper


def wrapped_exception_async(
    func: typing.Callable[..., typing.Awaitable[None]],
) -> typing.Callable[..., typing.Awaitable[None]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> None:
        try:
            await func(*args, **kwargs)
        except Exception as err:
            _LOGGER.exception(
                err,
                True,
                f"Activity metrics hook failed hook={func.__name__}: {err}",
            )
    return wrapper
