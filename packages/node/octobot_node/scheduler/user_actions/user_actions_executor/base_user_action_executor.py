#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import abc

import octobot_protocol.models as protocol_models
import octobot_commons.logging as logging

import octobot_node.scheduler.user_actions.user_action_post_actions as user_action_post_actions


class UserActionExecutor(abc.ABC):
    """
    Template for executing a user action: mark running, run subclass logic, set outcome on ``user_action``.

    The user-action workflow persists the final ``UserAction``; subclasses map failures via
    :meth:`_build_failure_user_action_result`.
    """

    def __init__(self, user_id: str):
        self._user_id = user_id
        self.post_actions: user_action_post_actions.UserActionPostActions = user_action_post_actions.UserActionPostActions()

    def _get_error_message(self, exc: BaseException) -> str:
        """
        Default classification when a channel executor does not recognize ``exc``.

        Returns the protocol enum *value* for ``internal_error``, which is identical for
        account and automation result payloads.
        """
        del exc
        return protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR.value

    @abc.abstractmethod
    def _build_failure_user_action_result(
        self,
        user_action: protocol_models.UserAction,
        exc: BaseException,
    ) -> protocol_models.UserActionResult:
        """Build the protocol ``UserActionResult`` to attach when execution raises."""

    @abc.abstractmethod
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        """Subclass work: perform the action and set terminal success on ``user_action`` before return."""

    async def before_execute(self, user_action: protocol_models.UserAction) -> None:
        # Step: mark running before subclass work; workflow output will persist final state.
        user_action.status = protocol_models.UserActionStatus.RUNNING

    async def after_execute(self, user_action: protocol_models.UserAction) -> None:
        pass

    def _apply_execution_failure(
        self,
        user_action: protocol_models.UserAction,
        exc: BaseException,
    ) -> None:
        # Step: mark failed and attach subclass-built result payload.
        user_action.status = protocol_models.UserActionStatus.FAILED
        user_action.result = self._build_failure_user_action_result(user_action, exc)

    async def execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        # Step: register running state, run subclass body, set failure or success on ``user_action`` for workflow output.
        logger = logging.get_logger(self.__class__.__name__)
        logger.info(f"Executing user action: {user_action.id}: {user_action.model_dump_json(exclude_defaults=True)}")
        await self.before_execute(user_action)
        try:
            await self._do_execute(user_action)
            logger.info(f"User action executed successfully: {user_action.id}")
        except Exception as exc:
            logger.error(
                f"User action execution failed: {user_action.id}: {exc} ({exc.__class__.__name__})"
            )
            self._apply_execution_failure(user_action, exc)
            raise
        finally:
            await self.after_execute(user_action)
