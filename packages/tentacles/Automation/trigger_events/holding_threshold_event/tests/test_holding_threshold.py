#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import asyncio

import mock
import decimal
import pytest

import octobot_commons.enums as commons_enums
import octobot_trading.personal_data

import tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold as holding_threshold


class TestHoldingThreshold:
    """Tests for HoldingThreshold"""

    def _create_trigger(self, asset_name="BTC", amount=10.0, stop_on_inferior=True, exchange="binance"):
        """Create and configure a HoldingThreshold instance."""
        trigger = holding_threshold.HoldingThreshold()
        trigger.apply_config({
            holding_threshold.HoldingThreshold.EXCHANGE: exchange,
            holding_threshold.HoldingThreshold.ASSET_NAME: asset_name,
            holding_threshold.HoldingThreshold.AMOUNT: amount,
            holding_threshold.HoldingThreshold.STOP_ON_INFERIOR: stop_on_inferior,
        })
        return trigger

    def test_initialization(self):
        """Test HoldingThreshold initialization via apply_config"""
        trigger = self._create_trigger(asset_name="BTC", amount=10.5, stop_on_inferior=True)
        assert trigger.asset_name == "BTC"
        assert trigger.amount == decimal.Decimal("10.5")
        assert trigger.stop_on_inferior is True

    def test_initialization_with_decimal(self):
        """Test HoldingThreshold initialization with Decimal amount"""
        trigger = self._create_trigger(asset_name="ETH", amount=5.25, stop_on_inferior=False)
        assert trigger.amount == decimal.Decimal("5.25")

    def test_check_threshold_inferior_true(self):
        """Test _check_threshold when stop_on_inferior is True and condition is met"""
        trigger = self._create_trigger(asset_name="BTC", amount=10.0, stop_on_inferior=True)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")  # Less than 10.0
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is True
            assert reason == "Current BTC holdings of 5.0 are lower than the 10.0 threshold."

    def test_check_threshold_inferior_false(self):
        """Test _check_threshold when stop_on_inferior is True and condition is not met"""
        trigger = self._create_trigger(asset_name="BTC", amount=10.0, stop_on_inferior=True)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("15.0")  # More than 10.0
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is False
            assert reason is None

    def test_check_threshold_superior_true(self):
        """Test _check_threshold when stop_on_inferior is False and condition is met"""
        trigger = self._create_trigger(asset_name="ETH", amount=10.0, stop_on_inferior=False)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="ETH",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("15.0")  # More than 10.0
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is True
            assert reason == "Current ETH holdings of 15.0 are higher than the 10.0 threshold."

    def test_check_threshold_superior_false(self):
        """Test _check_threshold when stop_on_inferior is False and condition is not met"""
        trigger = self._create_trigger(asset_name="ETH", amount=10.0, stop_on_inferior=False)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="ETH",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")  # Less than 10.0
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is False
            assert reason is None

    def test_check_threshold_exact_amount_inferior(self):
        """Test _check_threshold when holdings equal amount and stop_on_inferior is True"""
        trigger = self._create_trigger(asset_name="BTC", amount=10.0, stop_on_inferior=True)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("10.0")  # Equal to 10.0
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is True
            assert reason == "Current BTC holdings of 10.0 are lower than the 10.0 threshold."

    def test_check_threshold_returns_reason_in_tuple(self):
        """Test _check_threshold returns the reason as second element of tuple when met"""
        trigger = self._create_trigger(asset_name="BTC", amount=10.0, stop_on_inferior=True)

        exchange_manager = mock.Mock()
        portfolio_currency = octobot_trading.personal_data.SpotAsset(
            name="BTC",
            available=decimal.Decimal("5.0"),
            total=decimal.Decimal("5.0")
        )
        with mock.patch.object(
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio",
            return_value=portfolio_currency
        ):
            is_met, reason = trigger._check_threshold(exchange_manager)
            assert is_met is True
            assert reason == "Current BTC holdings of 5.0 are lower than the 10.0 threshold."

    @pytest.mark.asyncio
    async def test_check_initial_event_with_exchange_calls_perform_check(self):
        """When exchange is set, check_initial_event resolves the exchange and calls perform_check."""
        trigger = self._create_trigger(exchange="binance")
        mock_exchange_manager = mock.Mock()

        with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_api") as mock_trading_api:
            with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_util") as mock_trading_util:
                mock_trading_api.get_exchange_managers_from_exchange_name.return_value = [mock_exchange_manager]
                mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
                mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
                mock_trading_util.wait_for_topic_init = mock.AsyncMock()

                with mock.patch.object(trigger, "perform_check", new_callable=mock.AsyncMock) as mock_perform_check:
                    await trigger.check_initial_event()

                    mock_trading_api.get_exchange_managers_from_exchange_name.assert_called_once_with("binance")
                    mock_trading_util.wait_for_topic_init.assert_awaited_once_with(
                        mock_exchange_manager,
                        holding_threshold.INITIALIZATION_TIMEOUT,
                        commons_enums.InitializationEventExchangeTopics.BALANCE.value,
                    )
                    mock_perform_check.assert_awaited_once_with(exchange_id="exchange_1")

    @pytest.mark.asyncio
    async def test_check_initial_event_without_exchange_iterates_all(self):
        """When exchange is None, check_initial_event iterates all exchange IDs."""
        trigger = holding_threshold.HoldingThreshold()
        trigger.exchange = None
        trigger.asset_name = "BTC"
        trigger.amount = decimal.Decimal("10.0")
        trigger.stop_on_inferior = True

        mock_manager_1 = mock.Mock()
        mock_manager_2 = mock.Mock()

        with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_api") as mock_trading_api:
            with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_util") as mock_trading_util:
                mock_trading_api.get_exchange_ids.return_value = ["id_1", "id_2"]
                mock_trading_api.get_exchange_manager_from_exchange_id.side_effect = [mock_manager_1, mock_manager_2]
                mock_trading_util.wait_for_topic_init = mock.AsyncMock()

                with mock.patch.object(trigger, "perform_check", new_callable=mock.AsyncMock) as mock_perform_check:
                    await trigger.check_initial_event()

                    mock_trading_api.get_exchange_ids.assert_called_once()
                    assert mock_trading_util.wait_for_topic_init.call_count == 2
                    assert mock_perform_check.await_count == 2
                    mock_perform_check.assert_any_await(exchange_id="id_1")
                    mock_perform_check.assert_any_await(exchange_id="id_2")

    @pytest.mark.asyncio
    async def test_check_initial_event_timeout_skips_perform_check(self):
        """When wait_for_topic_init times out, perform_check is not called."""
        trigger = self._create_trigger(exchange="binance")
        mock_exchange_manager = mock.Mock()
        mock_exchange_manager.exchange_name = "binance"

        with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_api") as mock_trading_api:
            with mock.patch("tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold.trading_util") as mock_trading_util:
                mock_trading_api.get_exchange_managers_from_exchange_name.return_value = [mock_exchange_manager]
                mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
                mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
                mock_trading_util.wait_for_topic_init = mock.AsyncMock(side_effect=asyncio.TimeoutError)

                with mock.patch.object(trigger, "perform_check", new_callable=mock.AsyncMock) as mock_perform_check:
                    await trigger.check_initial_event()

                    mock_perform_check.assert_not_awaited()
