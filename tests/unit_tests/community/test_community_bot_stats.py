#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import mock
import pytest

import asyncio

import octobot_commons.authentication as authentication

import octobot_trading.api as trading_api

import octobot.community.community_bot_stats as community_bot_stats_module
import octobot.task_manager as task_manager_module


class TestUpdateAuthenticatedBot:
    @pytest.mark.asyncio
    async def test_updates_when_logged_in(self):
        octobot_api = mock.Mock()
        stats = community_bot_stats_module.CommunityBotStats(octobot_api)
        authenticator = mock.Mock()
        authenticator.is_logged_in.return_value = True
        authenticator.update_bot_config_and_stats = mock.AsyncMock()
        with mock.patch.object(
            authentication.Authenticator,
            "instance",
            return_value=authenticator,
        ), mock.patch.object(stats, "_get_profitability", return_value=12.5):
            await stats._update_authenticated_bot()
        authenticator.update_bot_config_and_stats.assert_awaited_once_with(12.5)

    @pytest.mark.asyncio
    async def test_skips_when_not_logged_in(self):
        octobot_api = mock.Mock()
        stats = community_bot_stats_module.CommunityBotStats(octobot_api)
        authenticator = mock.Mock()
        authenticator.is_logged_in.return_value = False
        authenticator.update_bot_config_and_stats = mock.AsyncMock()
        with mock.patch.object(authentication.Authenticator, "instance", return_value=authenticator):
            await stats._update_authenticated_bot()
        authenticator.update_bot_config_and_stats.assert_not_called()


class TestStopTask:
    @pytest.mark.asyncio
    async def test_clears_keep_running(self):
        stats = community_bot_stats_module.CommunityBotStats(mock.Mock())
        assert stats.keep_running is True
        await stats.stop_task()
        assert stats.keep_running is False


class TestGetProfitability:
    def test_computes_weighted_percentage(self):
        octobot_api = mock.Mock()
        octobot_api.get_exchange_manager_ids.return_value = ["ex-1"]
        exchange_manager = mock.Mock()
        stats = community_bot_stats_module.CommunityBotStats(octobot_api)
        with mock.patch.object(
            trading_api,
            "get_exchange_managers_from_exchange_ids",
            return_value=[exchange_manager],
        ), mock.patch.object(trading_api, "is_exchange_trading", return_value=True), mock.patch.object(
            trading_api,
            "get_profitability_stats",
            return_value=(10.0, None, None, None, None),
        ), mock.patch.object(trading_api, "get_origin_portfolio_value", return_value=100.0):
            assert stats._get_profitability() == pytest.approx(10.0)


class TestStartToolsTasksCommunityBotStats:
    @pytest.mark.asyncio
    async def test_schedules_task_when_gate_enabled(self):
        async def community_task():
            await asyncio.sleep(0)

        octobot_mock = mock.Mock()
        octobot_mock.community_bot_stats.task_enabled = True
        octobot_mock.community_bot_stats.start_community_task = mock.Mock(return_value=community_task())
        task_manager = task_manager_module.TaskManager(octobot_mock)
        task_manager.init_async_loop()
        await task_manager.start_tools_tasks()
        octobot_mock.community_bot_stats.start_community_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_task_when_gate_disabled(self):
        octobot_mock = mock.Mock()
        octobot_mock.community_bot_stats.task_enabled = False
        octobot_mock.community_bot_stats.start_community_task = mock.Mock(return_value=mock.AsyncMock())
        task_manager = task_manager_module.TaskManager(octobot_mock)
        task_manager.init_async_loop()
        await task_manager.start_tools_tasks()
        octobot_mock.community_bot_stats.start_community_task.assert_not_called()
