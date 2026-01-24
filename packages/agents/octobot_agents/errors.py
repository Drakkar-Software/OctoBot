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

class AgentError(Exception):
    """Base exception for all octobot_agents errors."""
    pass


class TeamConfigurationError(AgentError):
    """Raised when a team is misconfigured."""
    pass


class MissingManagerError(TeamConfigurationError):
    """Raised when a team requires a manager but none is provided."""
    pass


class MissingRequiredInputError(AgentError):
    """Raised when required input data is missing."""
    pass


class AgentConfigurationError(AgentError):
    """Raised when an agent is misconfigured."""
    pass


class StorageError(AgentError):
    """Raised when there's an error with storage operations."""
    pass


class UnsupportedStorageTypeError(StorageError):
    """Raised when an unsupported storage type is requested."""
    pass
