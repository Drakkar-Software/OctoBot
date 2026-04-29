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


def retry_async(get_retries: typing.Callable[..., int]):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = max(0, int(get_retries(*args, **kwargs)))
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt >= retries:
                        raise
                    attempt += 1
                    self_ref = args[0] if args else None
                    if self_ref is not None and hasattr(self_ref, "logger"):
                        self_ref.logger.warning(
                            f"{func.__name__} failed. Retrying ({attempt}/{retries}). Error: {e}"
                        )
        return wrapper
    return decorator
