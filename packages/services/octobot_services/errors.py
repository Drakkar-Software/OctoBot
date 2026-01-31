#  Drakkar-Software OctoBot-Trading
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


class UnavailableInBacktestingError(Exception):
    """
    Raised when accessing a service that is not available in backtesting
    """


class CreationError(Exception):
    """
    Raised when accessing a service that failed to be successfully created
    """


class InvalidRequestError(Exception):
    """
    Raised when an invalid request is submitted to a service
    """


class RateLimitError(Exception):
    """
    Raised when an the rate limit has been reached for the given request
    """
