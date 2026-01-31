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


class ConfigError(Exception):
    """
    Config related Exception
    """


class RemoteConfigError(ConfigError):
    """
    Fetched config related Exception
    """


class NoProfileError(Exception):
    """
    Profile related Exception: raised when the current profile can't be found and default profile can't be loaded
    """


class ProfileConflictError(Exception):
    """
    Profile related Exception: raised when the current profile can't be renamed as expected
    """


class ProfileRemovalError(Exception):
    """
    Profile related Exception: raised when the current profile can't be can't be removed
    """


class ProfileImportError(Exception):
    """
    Profile related Exception: raised when the imported profile is invalid
    """


class ConfigEvaluatorError(Exception):
    """
    Evaluator config related Exception
    """


class ConfigTradingError(Exception):
    """
    Trading config related Exception
    """


class TentacleNotFound(Exception):
    """
    Tentacle not found related Exception
    """


class UninitializedCache(Exception):
    """
    Raised when a cache is requested but has not yet been initialized
    """


class NoCacheValue(Exception):
    """
    Raised when a cache value is selected but is not available in database
    """


class UncachableValue(Exception):
    """
    Raised when a cache value is selected but is not available in database
    """


class DatabaseNotFoundError(Exception):
    """
    Raised when a database can't be found
    """


class MissingDataError(Exception):
    """
    Raised when there is not enough available candles
    """


class MissingExchangeDataError(Exception):
    """
    Raised when there is no available data for this exchange
    """


class ExecutionAborted(Exception):
    """
    Raised when the current execution should be aborted
    """


class LogicalOperatorError(Exception):
    """
    Raised when a logical operation is invalid
    """


class UnsupportedError(Exception):
    """
    Raised when an unsupported message is received
    """


class InvalidUserInputError(Exception):
    """
    Raised when a user input in invalid
    """


class MissingSignalBuilder(Exception):
    """
    Raised when a signal builder is not found
    """


class DSLInterpreterError(Exception):
    """
    Raised when a DSL interpreter error occurs
    """


class UnsupportedOperatorError(DSLInterpreterError):
    """
    Raised when an unknown operator is encountered
    """


class InvalidParametersError(DSLInterpreterError):
    """
    Raised when the parameters of an operator are invalid
    """
