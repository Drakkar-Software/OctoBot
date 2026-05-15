#  Drakkar-Software OctoBot-Node
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

import octobot_flow.enums

class WorkflowError(Exception):
    """Base class for all workflow errors"""


class WorkflowInputError(WorkflowError):
    """Raised when a workflow input is invalid"""
    

class WorkflowActionExecutionError(WorkflowError):
    ERROR_MESSAGE: str = octobot_flow.enums.ActionErrorStatus.INTERNAL_ERROR.value
    """Raised when a workflow action execution fails"""
    

class WorkflowPriorityActionExecutionError(WorkflowActionExecutionError):
    """Raised when a workflow priority action execution fails"""
    

class WorkflowDAGDependenciesError(WorkflowActionExecutionError):
    ERROR_MESSAGE: str = octobot_flow.enums.ActionErrorStatus.ACTION_DEPENDENCY_ERROR.value
    """Raised when a workflow DAG dependencies issue is detected"""


class UserActionError(Exception):
    """Raised when a user action fails"""


class InvalidUserActionPayloadError(UserActionError):
    """Raised when a user action payload is missing required fields or has an unexpected shape."""


class UnsupportedUserActionConfigurationTypeError(UserActionError):
    """Raised when a user action configuration type is not supported by the node."""


class UnsupportedAutomationConfigurationTypeError(UserActionError):
    """Raised when an automation configuration type is not supported by the node."""


class AccountContextMissingError(UserActionError):
    """Raised when required account context identifiers are missing (public key, wallet key, account id)."""


class AccountNotFoundError(UserActionError):
    """Raised when fetching an account via AccountProvider fails."""


class AutomationStrategyNotFoundError(UserActionError):
    """Raised when the referenced strategy does not exist in StrategyProvider."""


class AutomationStrategyVersionMismatchError(UserActionError):
    """Raised when the stored strategy version does not match the automation reference."""


class InvalidAutomationConfigurationError(UserActionError):
    """Raised when the automation configuration is invalid or cannot be translated to actions."""


class ActiveAutomationWorkflowNotFoundError(UserActionError):
    """Raised when no pending/enqueued automation workflow matches the stop request (parent id / wallet filter)."""


class AmbiguousActiveAutomationWorkflowError(UserActionError):
    """Raised when more than one active automation workflow matches the stop request (parent id / wallet filter)."""
