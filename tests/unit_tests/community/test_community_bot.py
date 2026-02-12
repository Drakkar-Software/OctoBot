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
import time
import pytest
import mock

import octobot.community.errors as errors
import octobot.community.supabase_backend.enums as supabase_enums
import octobot_commons.enums as commons_enums
import octobot.automation as automation

from octobot.community.community_bot import (
    CommunityBot,
    suppressed_local_env_bot_error,
    caught_global_exceptions,
    _STOPPED_STRATEGY_EXECUTION_LOG_MAX_PERIOD,
)


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def user_account():
    account = mock.Mock()
    account.bot_id = "bot-id"
    account.NO_SELECTED_BOT_DESC = "No selected bot"
    account.get_selected_bot_deployment_id = mock.Mock(return_value="deployment-id")
    account.get_selected_bot_deployment_error_status = mock.Mock(return_value=None)
    account.get_selected_bot_current_portfolio_id = mock.Mock(return_value=None)
    return account


@pytest.fixture
def authenticator(user_account):
    auth = mock.Mock()
    auth.user_account = user_account
    auth.supabase_client = mock.Mock(
        insert_bot_log=mock.AsyncMock(),
        update_deployment=mock.AsyncMock(),
        update_bot_products_subscription=mock.AsyncMock(),
    )
    auth.get_current_bot_products_subscription = mock.AsyncMock(return_value=None)
    return auth


class TestSuppressedLocalEnvBotError:
    async def test_suppresses_bot_error_in_local_env(self):

        @suppressed_local_env_bot_error
        async def wrapped(*args, **kwargs):
            raise errors.BotError("boom")

        logger = mock.Mock()

        with mock.patch("octobot.constants.IS_CLOUD_ENV", False), \
                mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            # should not raise
            await wrapped()

        logger.info.assert_called_once()
        log_msg = logger.info.call_args[0][0]
        assert "Skipped bot update" in log_msg
        assert "boom" in log_msg

    async def test_propagates_bot_error_in_cloud_env(self):
        @suppressed_local_env_bot_error
        async def _raise_bot_error():
            raise errors.BotError("boom")

        with mock.patch("octobot.constants.IS_CLOUD_ENV", True):
            with pytest.raises(errors.BotError):
                await _raise_bot_error()


class TestCaughtGlobalExceptions:
    def test_logs_and_swallows_exceptions(self):
        logger = mock.Mock()

        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            # no exception should escape the context manager
            with caught_global_exceptions("my_operation"):
                raise RuntimeError("failure")

        logger.exception.assert_called_once()
        exc_args = logger.exception.call_args[0]
        assert isinstance(exc_args[0], Exception)
        assert exc_args[1] is True
        assert "Error when running my_operation" in exc_args[2]


class TestInitializedBotId:
    async def test_suppresses_missing_bot_error_in_local_env(self, authenticator):
        authenticator.user_account.bot_id = None
        bot = CommunityBot(authenticator)
        logger = mock.Mock()

        @suppressed_local_env_bot_error
        async def wrapped(*args, **kwargs):
            return await bot.insert_bot_log(*args, **kwargs)

        with mock.patch("octobot.constants.IS_CLOUD_ENV", False), \
                mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            # should not raise even though bot_id is missing
            await wrapped(
                supabase_enums.BotLogType.BOT_STARTED,
                {"key": "value"},
            )

        authenticator.supabase_client.insert_bot_log.assert_not_awaited()
        logger.info.assert_called_once()
        assert "Skipped bot update" in logger.info.call_args[0][0]

    async def test_raises_missing_bot_error_in_cloud_env(self, authenticator):
        @suppressed_local_env_bot_error
        async def wrapped(*args, **kwargs):
            return await bot.insert_bot_log(*args, **kwargs)

        authenticator.user_account.bot_id = None
        bot = CommunityBot(authenticator)

        with mock.patch("octobot.constants.IS_CLOUD_ENV", True):
            with pytest.raises(errors.BotError):
                await wrapped(
                    supabase_enums.BotLogType.BOT_STARTED,
                    {"key": "value"},
                )

        authenticator.supabase_client.insert_bot_log.assert_not_awaited()


class TestShouldTradeAccordingToProductsSubscriptionAndDeploymentErrorStatus:
    async def test_returns_true_for_active_subscription_without_stop_condition(self, authenticator):
        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value:
                supabase_enums.ProductSubscriptionDesiredStatus.ACTIVE.value
        }
        authenticator.get_current_bot_products_subscription = mock.AsyncMock(
            return_value=products_subscription
        )
        bot = CommunityBot(authenticator)

        assert await bot.should_trade_according_to_products_subscription_and_deployment_error_status() is True

    async def test_returns_false_when_stop_condition_triggered(self, authenticator):
        authenticator.user_account.get_selected_bot_deployment_error_status = mock.Mock(
            return_value=supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED.value
        )
        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value:
                supabase_enums.ProductSubscriptionDesiredStatus.ACTIVE.value
        }
        authenticator.get_current_bot_products_subscription = mock.AsyncMock(
            return_value=products_subscription
        )
        bot = CommunityBot(authenticator)

        assert await bot.should_trade_according_to_products_subscription_and_deployment_error_status() is False

    async def test_does_not_check_deployment_status_when_subscription_not_active(self, authenticator):
        bot = CommunityBot(authenticator)

        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value:
                supabase_enums.ProductSubscriptionDesiredStatus.CANCELED.value
        }

        bot._fetch_products_subscription = mock.AsyncMock(return_value=products_subscription)
        bot._is_deployment_error_status_in = mock.Mock(return_value=False)

        assert await bot.should_trade_according_to_products_subscription_and_deployment_error_status() is False
        bot._is_deployment_error_status_in.assert_not_called()


class TestOnStartedBot:
    async def test_calls_startup_helpers_only_in_cloud_env(self, authenticator):
        bot = CommunityBot(authenticator)
        bot._insert_bot_started_log = mock.AsyncMock()
        bot._ensure_clear_deployment_error_status = mock.AsyncMock()

        # cloud: both helpers must be awaited
        with mock.patch("octobot.constants.IS_CLOUD_ENV", True):
            await bot.on_started_bot()
        bot._insert_bot_started_log.assert_awaited_once()
        bot._ensure_clear_deployment_error_status.assert_awaited_once()

        # local: helpers must not be called again
        bot._insert_bot_started_log.reset_mock()
        bot._ensure_clear_deployment_error_status.reset_mock()
        with mock.patch("octobot.constants.IS_CLOUD_ENV", False):
            await bot.on_started_bot()
        bot._insert_bot_started_log.assert_not_awaited()
        bot._ensure_clear_deployment_error_status.assert_not_awaited()


class TestScheduleBotStop:
    async def test_updates_status_and_cancels_subscription_when_reason_provided(self, authenticator):
        bot = CommunityBot(authenticator)

        bot._update_deployment_error_status = mock.AsyncMock()
        bot._update_product_subscription_desired_status = mock.AsyncMock()

        stop_reason = commons_enums.StopReason.MISSING_MINIMAL_FUNDS

        await bot.schedule_bot_stop(stop_reason)

        expected_status = supabase_enums.BotDeploymentErrorsStatuses.MISSING_MINIMAL_FUNDS
        bot._update_deployment_error_status.assert_awaited_once_with(expected_status)
        bot._update_product_subscription_desired_status.assert_awaited_once_with(
            supabase_enums.ProductSubscriptionDesiredStatus.CANCELED
        )

    async def test_does_not_update_deployment_error_when_reason_is_none(self, authenticator):
        bot = CommunityBot(authenticator)

        bot._update_deployment_error_status = mock.AsyncMock()
        bot._update_product_subscription_desired_status = mock.AsyncMock()

        await bot.schedule_bot_stop(None)

        bot._update_deployment_error_status.assert_not_called()
        bot._update_product_subscription_desired_status.assert_awaited_once_with(
            supabase_enums.ProductSubscriptionDesiredStatus.CANCELED
        )

class TestOnTradingModesStoppedAndTradersPaused:
    async def test_schedules_bot_stop_when_schedule_bot_stop_is_true(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.schedule_bot_stop = mock.AsyncMock()
        bot.update_deployment_error_status_for_stop_reason = mock.AsyncMock()
        bot.insert_stopped_strategy_execution_log = mock.AsyncMock()

        await bot.on_trading_modes_stopped_and_traders_paused(commons_enums.StopReason.MISSING_MINIMAL_FUNDS, None, True)

        bot.schedule_bot_stop.assert_awaited_once_with(commons_enums.StopReason.MISSING_MINIMAL_FUNDS)
        bot.update_deployment_error_status_for_stop_reason.assert_not_awaited()
        bot.insert_stopped_strategy_execution_log.assert_not_awaited()

    async def test_updates_deployment_error_status_when_schedule_bot_stop_is_false(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.schedule_bot_stop = mock.AsyncMock()
        bot.update_deployment_error_status_for_stop_reason = mock.AsyncMock()
        bot.insert_stopped_strategy_execution_log = mock.AsyncMock()

        await bot.on_trading_modes_stopped_and_traders_paused(commons_enums.StopReason.MISSING_MINIMAL_FUNDS, None, False)

        bot.schedule_bot_stop.assert_not_awaited()
        bot.update_deployment_error_status_for_stop_reason.assert_awaited_once_with(commons_enums.StopReason.MISSING_MINIMAL_FUNDS)
        bot.insert_stopped_strategy_execution_log.assert_not_awaited()

    async def test_inserts_stopped_strategy_execution_log_when_execution_details_is_provided(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.schedule_bot_stop = mock.AsyncMock()
        bot.update_deployment_error_status_for_stop_reason = mock.AsyncMock()
        bot.insert_stopped_strategy_execution_log = mock.AsyncMock()

        await bot.on_trading_modes_stopped_and_traders_paused(
            commons_enums.StopReason.MISSING_MINIMAL_FUNDS, automation.ExecutionDetails(
                timestamp=1, description="user requested stop", source=None
            ),
            False
        )

        bot.schedule_bot_stop.assert_not_awaited()
        bot.update_deployment_error_status_for_stop_reason.assert_awaited_once_with(commons_enums.StopReason.MISSING_MINIMAL_FUNDS)
        bot.insert_stopped_strategy_execution_log.assert_awaited_once_with("user requested stop", max_period=_STOPPED_STRATEGY_EXECUTION_LOG_MAX_PERIOD)

    async def test_logs_error_when_scheduling_bot_stop_and_log_insert_fails(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.schedule_bot_stop = mock.AsyncMock(side_effect=Exception("boom1"))
        bot.update_deployment_error_status_for_stop_reason = mock.AsyncMock()
        bot.insert_stopped_strategy_execution_log = mock.AsyncMock(side_effect=Exception("boom2"))
        logger = mock.Mock()
        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot.on_trading_modes_stopped_and_traders_paused(
                commons_enums.StopReason.MISSING_MINIMAL_FUNDS,
                automation.ExecutionDetails(
                    timestamp=1, description="user requested stop", source=None
                ),
                True
            )
            assert logger.exception.call_count == 2
            assert logger.exception.mock_calls[0].args[0].args[0] == "boom1"
            assert logger.exception.mock_calls[1].args[0].args[0] == "boom2"

            bot.schedule_bot_stop.assert_awaited_once_with(commons_enums.StopReason.MISSING_MINIMAL_FUNDS)
            bot.update_deployment_error_status_for_stop_reason.assert_not_awaited()
            bot.insert_stopped_strategy_execution_log.assert_awaited_once_with("user requested stop", max_period=_STOPPED_STRATEGY_EXECUTION_LOG_MAX_PERIOD)


class TestUpdateDeploymentErrorStatusForStopReason:
    async def test_updates_deployment_error_status_for_stop_reason(self, authenticator):
        bot = CommunityBot(authenticator)
        bot._update_deployment_error_status = mock.AsyncMock()

        await bot.update_deployment_error_status_for_stop_reason(commons_enums.StopReason.MISSING_MINIMAL_FUNDS)

        bot._update_deployment_error_status.assert_awaited_once_with(
            supabase_enums.BotDeploymentErrorsStatuses.MISSING_MINIMAL_FUNDS
        )   


class TestUpdateDeploymentErrorStatus:
    async def test_updates_supabase_client(self, authenticator):
        bot = CommunityBot(authenticator)
        logger = mock.Mock()

        error_status = supabase_enums.BotDeploymentErrorsStatuses.INVALID_CONFIG

        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot._update_deployment_error_status(error_status)

        authenticator.supabase_client.update_deployment.assert_awaited_once_with(
            "deployment-id",
            {supabase_enums.BotDeploymentKeys.ERROR_STATUS.value: error_status.value},
        )
        logger.info.assert_called_once()

    async def test_raises_when_deployment_missing(self, authenticator):
        authenticator.user_account.get_selected_bot_deployment_id = mock.Mock(side_effect=KeyError())
        bot = CommunityBot(authenticator)

        error_status = supabase_enums.BotDeploymentErrorsStatuses.INVALID_CONFIG

        with mock.patch("octobot.constants.IS_CLOUD_ENV", True):
            with pytest.raises(errors.MissingDeploymentError):
                await bot._update_deployment_error_status(error_status)


class TestEnsureClearDeploymentErrorStatus:
    async def test_clears_known_errors(self, authenticator):
        bot = CommunityBot(authenticator)
        bot._is_deployment_error_status_in = mock.Mock(return_value=True)
        bot._update_deployment_error_status = mock.AsyncMock()
        logger = mock.Mock()

        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot._ensure_clear_deployment_error_status()

        bot._is_deployment_error_status_in.assert_called_once_with(
            CommunityBot.CLEARABLE_DEPLOYMENT_ERROR_STATUSES
        )
        bot._update_deployment_error_status.assert_awaited_once_with(
            supabase_enums.BotDeploymentErrorsStatuses.NO_ERROR
        )

    async def test_does_nothing_when_no_error(self, authenticator):
        bot = CommunityBot(authenticator)
        bot._is_deployment_error_status_in = mock.Mock(return_value=False)
        bot._update_deployment_error_status = mock.AsyncMock()
        logger = mock.Mock()

        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot._ensure_clear_deployment_error_status()

        bot._is_deployment_error_status_in.assert_called_once_with(
            CommunityBot.CLEARABLE_DEPLOYMENT_ERROR_STATUSES
        )
        bot._update_deployment_error_status.assert_not_awaited()


class TestFetchProductsSubscription:
    async def test_raises_when_missing(self, authenticator):
        bot = CommunityBot(authenticator)

        with pytest.raises(errors.MissingProductsSubscriptionError):
            await bot._fetch_products_subscription()


class TestInsertStoppedStrategyExecutionLog:
    async def test_calls_insert_bot_log_with_stopped_strategy_type_and_reason(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.insert_bot_log = mock.AsyncMock()

        await bot.insert_stopped_strategy_execution_log("user requested stop")

        bot.insert_bot_log.assert_awaited_once_with(
            supabase_enums.BotLogType.STOPPED_STRATEGY_EXECUTION,
            {supabase_enums.BotLogContentKeys.REASON.value: "user requested stop"},
        )

    async def test_skips_call_within_max_period(self, authenticator):
        bot = CommunityBot(authenticator)
        bot.insert_bot_log = mock.AsyncMock()

        # no max_period: call re-call instantly
        await bot.insert_stopped_strategy_execution_log("user requested stop")
        bot.insert_bot_log.assert_awaited_once()
        bot.insert_bot_log.reset_mock()

        # max_period: calls are skipped after 1st call
        await bot.insert_stopped_strategy_execution_log("user requested stop", max_period=1)
        bot.insert_bot_log.assert_awaited_once()
        bot.insert_bot_log.reset_mock()
        for _ in range(10):
            await bot.insert_stopped_strategy_execution_log("user requested stop", max_period=1)
            bot.insert_bot_log.assert_not_called()

        with mock.patch("time.time", return_value=time.time() + 1.1):
            await bot.insert_stopped_strategy_execution_log("user requested stop", max_period=1)
            # now that time has passed, the call can be executed again
            bot.insert_bot_log.assert_awaited_once()


class TestInsertBotLog:
    async def test_inserts_log_via_supabase_and_logs(self, authenticator):
        bot = CommunityBot(authenticator)
        logger = mock.Mock()

        with mock.patch("octobot.constants.IS_CLOUD_ENV", True), \
                mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot.insert_bot_log(
                supabase_enums.BotLogType.BOT_STARTED,
                {"key": "value"},
            )

        authenticator.supabase_client.insert_bot_log.assert_awaited_once_with(
            "bot-id",
            supabase_enums.BotLogType.BOT_STARTED,
            {"key": "value"},
        )
        logger.info.assert_called_once()
        assert "Inserted bot log" in logger.info.call_args[0][0]
        assert "bot_id=bot-id" in logger.info.call_args[0][0]


class TestIsNewBot:
    def test_returns_true_when_portfolio_id_is_none(self, authenticator):
        authenticator.user_account.get_selected_bot_current_portfolio_id = mock.Mock(return_value=None)
        bot = CommunityBot(authenticator)

        assert bot._is_new_bot() is True

    def test_returns_false_when_portfolio_id_is_set(self, authenticator):
        authenticator.user_account.get_selected_bot_current_portfolio_id = mock.Mock(
            return_value="portfolio-123"
        )
        bot = CommunityBot(authenticator)

        assert bot._is_new_bot() is False

    def test_returns_true_on_type_error(self, authenticator):
        authenticator.user_account.get_selected_bot_current_portfolio_id = mock.Mock(
            side_effect=TypeError()
        )
        bot = CommunityBot(authenticator)

        assert bot._is_new_bot() is True

    def test_returns_true_on_key_error(self, authenticator):
        authenticator.user_account.get_selected_bot_current_portfolio_id = mock.Mock(
            side_effect=KeyError()
        )
        bot = CommunityBot(authenticator)

        assert bot._is_new_bot() is True


class TestIsProductSubscriptionDesiredStatusActive:
    def test_returns_true_when_desired_status_is_active(self, authenticator):
        bot = CommunityBot(authenticator)
        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value:
                supabase_enums.ProductSubscriptionDesiredStatus.ACTIVE.value
        }

        assert bot._is_product_subscription_desired_status_active(products_subscription) is True

    def test_returns_false_when_desired_status_is_canceled(self, authenticator):
        bot = CommunityBot(authenticator)
        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value:
                supabase_enums.ProductSubscriptionDesiredStatus.CANCELED.value
        }

        assert bot._is_product_subscription_desired_status_active(products_subscription) is False


class TestIsDeploymentErrorStatusIn:
    def test_returns_true_when_status_in_list(self, authenticator):
        authenticator.user_account.get_selected_bot_deployment_error_status = mock.Mock(
            return_value=supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED.value
        )
        bot = CommunityBot(authenticator)

        assert bot._is_deployment_error_status_in(
            [supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED]
        ) is True

    def test_returns_false_when_status_not_in_list(self, authenticator):
        authenticator.user_account.get_selected_bot_deployment_error_status = mock.Mock(
            return_value=supabase_enums.BotDeploymentErrorsStatuses.INVALID_CONFIG.value
        )
        bot = CommunityBot(authenticator)

        assert bot._is_deployment_error_status_in(
            [supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED]
        ) is False

    def test_returns_false_when_deployment_status_is_none(self, authenticator):
        authenticator.user_account.get_selected_bot_deployment_error_status = mock.Mock(
            return_value=None
        )
        bot = CommunityBot(authenticator)

        assert bot._is_deployment_error_status_in(
            [supabase_enums.BotDeploymentErrorsStatuses.STOP_CONDITION_TRIGGERED]
        ) is False


class TestUpdateProductSubscriptionDesiredStatus:
    async def test_fetches_subscription_and_updates_via_supabase(self, authenticator):
        products_subscription = {
            supabase_enums.ProductsSubscriptionsKeys.ID.value: "sub-123",
            supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value: "active",
        }
        authenticator.get_current_bot_products_subscription = mock.AsyncMock(
            return_value=products_subscription
        )
        bot = CommunityBot(authenticator)
        logger = mock.Mock()

        with mock.patch.object(CommunityBot, "get_logger", return_value=logger):
            await bot._update_product_subscription_desired_status(
                supabase_enums.ProductSubscriptionDesiredStatus.CANCELED
            )

        authenticator.supabase_client.update_bot_products_subscription.assert_awaited_once_with(
            "sub-123",
            {supabase_enums.ProductsSubscriptionsKeys.DESIRED_STATUS.value: "canceled"},
        )
        logger.info.assert_called_once()
        assert "Updated product_subscription.desired_status" in logger.info.call_args[0][0]


class TestClear:
    def test_sets_authenticator_to_none(self, authenticator):
        bot = CommunityBot(authenticator)

        bot.clear()

        assert bot.authenticator is None
