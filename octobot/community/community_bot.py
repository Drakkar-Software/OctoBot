# pylint: disable=E0711, E0702
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
import typing
import contextlib

import octobot_commons.cache_util as cache_util
import octobot.community.errors as errors
import octobot.community.supabase_backend.enums as supabase_enums
import octobot.community.models.formatters as formatters
import octobot.constants
import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import octobot.automation

if typing.TYPE_CHECKING:
    import octobot.community.authentication as community_authentication


_STOPPED_STRATEGY_EXECUTION_LOG_MAX_PERIOD = 60


def suppressed_local_env_bot_error(f):
    async def _suppressed_local_env_bot_error_wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except errors.BotError as err:
            if octobot.constants.IS_CLOUD_ENV:
                # this is not normal: propagate the error
                raise err
            else:
                # this can happen in local environment, just log it
                CommunityBot.get_logger().info(f"Skipped bot update: {err}")
    return _suppressed_local_env_bot_error_wrapper


@contextlib.contextmanager
def caught_global_exceptions(operation_name: str):
    try:
        yield
    except Exception as err:
        CommunityBot.get_logger().exception(err, True, f"Error when running {operation_name}: {err}")


def initialized_bot_id(f):
    @suppressed_local_env_bot_error
    async def _initialized_bot_id_wrapper(self, *args, **kwargs):
        if not self.authenticator.user_account.bot_id:
            raise errors.BotError(self.authenticator.user_account.NO_SELECTED_BOT_DESC)
        return await f(self, *args, **kwargs)
    return _initialized_bot_id_wrapper


class CommunityBot:
    """
    Bot utility methods to update the community bot representation in database
    """
    # deployment error statuses that should be cleared by the bot during startup
    CLEARABLE_DEPLOYMENT_ERROR_STATUSES: list[supabase_enums.BotDeploymentErrorsStatuses] = [
        supabase_enums.BotDeploymentErrorsStatuses.MISSING_API_KEY_TRADING_RIGHTS,
        supabase_enums.BotDeploymentErrorsStatuses.INVALID_EXCHANGE_CREDENTIALS,
        supabase_enums.BotDeploymentErrorsStatuses.MISSING_MINIMAL_FUNDS,
        supabase_enums.BotDeploymentErrorsStatuses.INTERNAL_SERVER_ERROR,
    ]

    def __init__(self, authenticator: "community_authentication.CommunityAuthentication"):
        self.authenticator: "community_authentication.CommunityAuthentication" = authenticator

    async def should_trade_according_to_products_subscription_and_deployment_error_status(self) -> bool:
        products_subscription = await self._fetch_products_subscription()
        if self._is_product_subscription_desired_status_active(products_subscription):
            # don't fetch deployment error status if bot should not trade
            if not self._is_deployment_error_status_in(
                [supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED]
            ):
                # bot should be running and didn't trigger stop condition yet
                return True
        return False
    
    async def on_started_bot(self):
        if octobot.constants.IS_CLOUD_ENV:
            await self._insert_bot_started_log()
            await self._ensure_clear_deployment_error_status()

    async def on_trading_modes_stopped_and_traders_paused(
        self,
        stop_reason: commons_enums.StopReason,
        execution_details: typing.Optional[octobot.automation.ExecutionDetails],
        schedule_bot_stop: bool,
    ):
        with caught_global_exceptions(
            f"on_trading_modes_stopped_and_traders_paused: {stop_reason=}"
        ):
            if schedule_bot_stop:
                # schedule bot stop: bot will pause trading and be stopped
                await self.schedule_bot_stop(stop_reason)
            elif stop_reason is not None:
                # only update error status: bot will pause trading but remain on
                await self.update_deployment_error_status_for_stop_reason(stop_reason)
        if execution_details is not None:
            with caught_global_exceptions("insert_stopped_strategy_execution_log"):
                await self.insert_stopped_strategy_execution_log(  # pylint: disable=unexpected-keyword-arg
                    execution_details.description,
                    max_period=_STOPPED_STRATEGY_EXECUTION_LOG_MAX_PERIOD # type: ignore
                )

    @initialized_bot_id
    async def schedule_bot_stop(
        self, stop_reason: typing.Optional[commons_enums.StopReason]
    ):
        if stop_reason is not None:
            await self.update_deployment_error_status_for_stop_reason(stop_reason)
        await self._update_product_subscription_desired_status(
            supabase_enums.ProductSubscriptionDesiredStatus.CANCELED
        )

    async def update_deployment_error_status_for_stop_reason(
        self, stop_reason: commons_enums.StopReason
    ):
        await self._update_deployment_error_status(
            formatters.get_deployment_error_status_from_stop_reason(stop_reason)
        )

    @cache_util.prevented_multiple_calls
    async def insert_stopped_strategy_execution_log(self, reason: typing.Optional[str]):
        await self.insert_bot_log(
            supabase_enums.BotLogType.STOPPED_STRATEGY_EXECUTION, {
                supabase_enums.BotLogContentKeys.REASON.value: reason
            }
        )

    @initialized_bot_id
    async def insert_bot_log(
        self, bot_log_type: supabase_enums.BotLogType, content: typing.Optional[dict]
    ):
        await self.authenticator.supabase_client.insert_bot_log(
            self.authenticator.user_account.bot_id,
            bot_log_type,
            content
        )
        self.get_logger().info(
            f"Inserted bot log: {bot_log_type.value}: {content} "
            f"[bot_id={self.authenticator.user_account.bot_id}]"
        )

    def _is_new_bot(self) -> bool:
        try:
            # if portfolio id is not set, it means the bot is new: its portfolio has not yet been created
            return self.authenticator.user_account.get_selected_bot_current_portfolio_id() is None
        except (TypeError, KeyError):
            return True

    def _is_product_subscription_desired_status_active(self, products_subscription: dict) -> bool:
        return (
            products_subscription[supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value] 
            == supabase_enums.ProductSubscriptionDesiredStatus.ACTIVE.value
        )

    def _is_deployment_error_status_in(
        self, error_statuses: list[supabase_enums.BotDeploymentErrorsStatuses]
    ) -> bool:
        deployment_error_status = self.authenticator.user_account.get_selected_bot_deployment_error_status()
        for error_status in error_statuses:
            if deployment_error_status == error_status.value:
                return True
        return False
    
    @suppressed_local_env_bot_error
    async def _insert_bot_started_log(self):
        bot_log_type = (
            supabase_enums.BotLogType.BOT_STARTED if self._is_new_bot()
            else supabase_enums.BotLogType.BOT_RESTARTED
        )
        with caught_global_exceptions("insert_bot_started_log"):
            await self.insert_bot_log(bot_log_type, None)

    @initialized_bot_id
    async def _update_deployment_error_status(self, error_status: supabase_enums.BotDeploymentErrorsStatuses):
        self.get_logger().info(
            f"Updating bot {self.authenticator.user_account.bot_id} deployment error "
            f"status to {error_status.value}"
        )
        try:
            deployment_id = self.authenticator.user_account.get_selected_bot_deployment_id()
        except KeyError:
            raise errors.MissingDeploymentError("No deployment is set for current bot")
        update = {supabase_enums.BotDeploymentKeys.ERROR_STATUS.value: error_status.value}
        await self.authenticator.supabase_client.update_deployment(deployment_id, update)

    @suppressed_local_env_bot_error
    async def _ensure_clear_deployment_error_status(self):
        with caught_global_exceptions("ensure_clear_deployment_error_status"):
            if self._is_deployment_error_status_in(self.CLEARABLE_DEPLOYMENT_ERROR_STATUSES):
                await self._update_deployment_error_status(supabase_enums.BotDeploymentErrorsStatuses.NO_ERROR)

    async def _fetch_products_subscription(self) -> dict:
        products_subscription = await self.authenticator.get_current_bot_products_subscription()
        if products_subscription is None:
            raise errors.MissingProductsSubscriptionError(
                f"No products subscription found for bot {self.authenticator.user_account.bot_id}"
            )
        return products_subscription

    async def _update_product_subscription_desired_status(
        self, desired_status: supabase_enums.ProductSubscriptionDesiredStatus
    ):
        products_subscription = await self._fetch_products_subscription()
        products_subscription_id = products_subscription[supabase_enums.ProductsSubscriptionsKeys.ID.value]
        await self.authenticator.supabase_client.update_bot_products_subscription(
            products_subscription_id,
            {supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value: desired_status.value}
        )
        self.get_logger().info(
            f"Updated product_subscription.desired_status to {desired_status.value} [{products_subscription_id=}]"
        )

    @classmethod
    def get_logger(cls):
        return commons_logging.get_logger(cls.__name__)

    def clear(self):
        self.authenticator = None # type: ignore
