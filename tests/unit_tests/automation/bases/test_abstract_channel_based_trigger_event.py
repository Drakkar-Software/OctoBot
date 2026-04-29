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
import asyncio

import pytest
from mock import patch, AsyncMock, Mock

from octobot.automation.bases.abstract_channel_based_trigger_event import (
    AbstractChannelBasedTriggerEvent,
)
import octobot.errors as errors

TRADING_API_PATCH = "octobot.automation.bases.abstract_channel_based_trigger_event.trading_api"


class TriggerWithBaseRegisterConsumer(AbstractChannelBasedTriggerEvent):
    """Uses base _register_exchange_channel_consumer for testing."""

    @staticmethod
    def get_description() -> str:
        return "Trigger with base register"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def channel_callback(self, *args, **kwargs):
        pass

    async def register_consumers(self, exchange_id: str):
        consumer = Mock()
        consumer.stop = AsyncMock()
        return [consumer]


class ConcreteChannelBasedTrigger(AbstractChannelBasedTriggerEvent):
    @staticmethod
    def get_description() -> str:
        return "Concrete channel trigger"

    def get_user_inputs(self, UI, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        pass

    async def channel_callback(self, *args, **kwargs):
        pass

    async def _register_exchange_channel_consumer(self):
        pass


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestAbstractChannelBasedTriggerEvent:
    def test_init(self):
        trigger = ConcreteChannelBasedTrigger()
        assert trigger._trigger_event is not None
        assert trigger._consumers == []
        assert trigger._registered_consumer is False
        assert trigger._waiter_future is None
        assert trigger.should_stop is False

    async def test_register_consumers_raises_not_implemented_on_base(self):
        class IncompleteTrigger(AbstractChannelBasedTriggerEvent):
            @staticmethod
            def get_description() -> str:
                return "Incomplete"

            def get_user_inputs(self, UI, inputs, step_name): return {}

            def apply_config(self, config): pass

            async def channel_callback(self, *args, **kwargs): pass

        trigger = IncompleteTrigger()
        with pytest.raises(NotImplementedError):
            await trigger.register_consumers("exchange_id")

    async def test_trigger_sets_future_result(self):
        trigger = ConcreteChannelBasedTrigger()
        trigger._waiter_future = asyncio.get_event_loop().create_future()
        assert not trigger._waiter_future.done()
        trigger.trigger("test description")
        assert trigger._waiter_future.done()
        assert trigger._waiter_future.result() == "test description"

    async def test_clear_future_cancels_future(self):
        trigger = ConcreteChannelBasedTrigger()
        trigger._waiter_future = asyncio.get_event_loop().create_future()
        assert not trigger._waiter_future.done()
        trigger.clear_future()
        assert trigger._waiter_future.cancelled()

    async def test_get_next_event_returns_description_when_future_is_set(self):
        trigger = ConcreteChannelBasedTrigger()
        trigger._registered_consumer = True

        async def set_result_soon():
            await asyncio.sleep(0)
            trigger.trigger("threshold exceeded")

        asyncio.create_task(set_result_soon())
        result = await trigger._get_next_event()
        assert result == "threshold exceeded"

    async def test_get_next_event_returns_none_when_future_is_cancelled(self):
        trigger = ConcreteChannelBasedTrigger()
        trigger._registered_consumer = True

        async def cancel_soon():
            await asyncio.sleep(0)
            trigger.clear_future()

        asyncio.create_task(cancel_soon())
        try:
            await trigger._get_next_event()
        except errors.AutomationStopped:
            pass

    async def test_get_next_event_registers_consumer_on_first_call(self):
        trigger = ConcreteChannelBasedTrigger()
        assert trigger._registered_consumer is False

        with patch.object(trigger, "_register_exchange_channel_consumer", new_callable=AsyncMock) as mock_register:
            with patch.object(trigger, "check_initial_event", new_callable=AsyncMock):
                async def set_result_soon():
                    await asyncio.sleep(0)
                    trigger.trigger("test")

                asyncio.create_task(set_result_soon())
                await trigger._get_next_event()
                mock_register.assert_awaited_once()

    async def test_check_initial_event_default_is_noop(self):
        """Base class check_initial_event does nothing and does not raise."""
        trigger = ConcreteChannelBasedTrigger()
        await trigger.check_initial_event()
        # Should complete without error

    async def test_check_initial_event_called_on_first_get_next_event(self):
        """check_initial_event is called after _register_exchange_channel_consumer on first _get_next_event call."""
        trigger = ConcreteChannelBasedTrigger()
        assert trigger._registered_consumer is False

        with patch.object(trigger, "_register_exchange_channel_consumer", new_callable=AsyncMock):
            with patch.object(trigger, "check_initial_event", new_callable=AsyncMock) as mock_check:
                async def set_result_soon():
                    await asyncio.sleep(0)
                    trigger.trigger("test")

                asyncio.create_task(set_result_soon())
                await trigger._get_next_event()
                mock_check.assert_awaited_once()

    async def test_check_initial_event_skipped_when_already_registered(self):
        """check_initial_event is not called when _register_exchange_channel_consumer is already True."""
        trigger = ConcreteChannelBasedTrigger()
        trigger._registered_consumer = True

        with patch.object(trigger, "_register_exchange_channel_consumer", new_callable=AsyncMock) as mock_register:
            with patch.object(trigger, "check_initial_event", new_callable=AsyncMock) as mock_check:
                async def set_result_soon():
                    await asyncio.sleep(0)
                    trigger.trigger("test")

                asyncio.create_task(set_result_soon())
                await trigger._get_next_event()
                mock_register.assert_not_awaited()
                mock_check.assert_not_awaited()

    async def test_check_initial_event_trigger_resolves_get_next_event(self):
        """If check_initial_event calls trigger(), _get_next_event returns immediately."""
        trigger = ConcreteChannelBasedTrigger()
        assert trigger._registered_consumer is False

        async def trigger_during_check():
            trigger.trigger("initial event detected")

        with patch.object(trigger, "_register_exchange_channel_consumer", new_callable=AsyncMock):
            with patch.object(trigger, "check_initial_event", side_effect=trigger_during_check):
                result = await trigger._get_next_event()
                assert result == "initial event detected"

    async def test_stop_cleans_up_consumers(self):
        trigger = ConcreteChannelBasedTrigger()
        trigger._consumers = []
        await trigger.stop()
        assert trigger._consumers == []
        assert trigger._registered_consumer is False


class TestRegisterExchangeChannelConsumer:
    """Tests for _register_exchange_channel_consumer."""

    async def test_sets_registered_consumer_to_true(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "exchange_1"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        assert trigger._registered_consumer is True

    async def test_exchange_and_exchange_id_uses_get_exchange_manager_from_name_and_id(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "exchange_1"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        mock_trading_api.get_exchange_manager_from_exchange_name_and_id.assert_called_once_with(
            "binance", "exchange_1"
        )
        mock_trading_api.get_exchange_manager_from_exchange_id.assert_not_called()
        mock_trading_api.get_exchange_managers_from_exchange_name.assert_not_called()

    async def test_exchange_id_only_uses_get_exchange_manager_from_exchange_id(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange_id = "exchange_1"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        mock_trading_api.get_exchange_manager_from_exchange_id.assert_called_once_with("exchange_1")
        mock_trading_api.get_exchange_manager_from_exchange_name_and_id.assert_not_called()
        mock_trading_api.get_exchange_managers_from_exchange_name.assert_not_called()

    async def test_exchange_only_single_manager_succeeds(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_name.return_value = [mock_exchange_manager]
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        mock_trading_api.get_exchange_managers_from_exchange_name.assert_called_once_with("binance")
        mock_trading_api.get_exchange_manager_from_exchange_id.assert_not_called()

    async def test_exchange_only_multiple_managers_raises_value_error(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        mock_exchange_manager_1 = Mock()
        mock_exchange_manager_2 = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_name.return_value = [
                mock_exchange_manager_1,
                mock_exchange_manager_2,
            ]
            with pytest.raises(ValueError, match="Expected 1 exchange manager for exchange binance, got 2"):
                await trigger._register_exchange_channel_consumer()

    async def test_no_exchange_nor_exchange_id_registers_for_all_exchange_ids(self):
        trigger = TriggerWithBaseRegisterConsumer()
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_ids.return_value = ["id_1", "id_2"]
            mock_trading_api.get_exchange_manager_from_exchange_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        mock_trading_api.get_exchange_ids.assert_called_once()
        assert mock_trading_api.get_exchange_manager_from_exchange_id.call_count == 2
        mock_trading_api.get_exchange_manager_from_exchange_id.assert_any_call("id_1")
        mock_trading_api.get_exchange_manager_from_exchange_id.assert_any_call("id_2")

    async def test_symbol_not_in_trading_pairs_raises_value_error(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "exchange_1"
        trigger.symbol = "BTC/USDT"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_trading_pairs.return_value = ["ETH/USDT", "SOL/USDT"]
            with pytest.raises(ValueError, match="Symbol BTC/USDT not found on binance"):
                await trigger._register_exchange_channel_consumer()

    async def test_symbol_in_trading_pairs_calls_register_consumers(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "exchange_1"
        trigger.symbol = "BTC/USDT"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_trading_pairs.return_value = ["BTC/USDT", "ETH/USDT"]
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        mock_trading_api.get_trading_pairs.assert_called_once_with(mock_exchange_manager)
        assert len(trigger._consumers) == 1

    async def test_extends_consumers_from_register_consumers(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "exchange_1"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer()

        assert len(trigger._consumers) == 1
        assert trigger._consumers[0].stop is not None

    async def test_parameters_override_instance_attributes(self):
        trigger = TriggerWithBaseRegisterConsumer()
        trigger.exchange = "binance"
        trigger.exchange_id = "wrong_id"
        mock_exchange_manager = Mock()

        with patch(TRADING_API_PATCH) as mock_trading_api:
            mock_trading_api.get_exchange_manager_from_exchange_name_and_id.return_value = mock_exchange_manager
            mock_trading_api.get_exchange_manager_id.return_value = "exchange_1"
            await trigger._register_exchange_channel_consumer(
                exchange="kraken",
                exchange_id="kraken_1",
            )

        mock_trading_api.get_exchange_manager_from_exchange_name_and_id.assert_called_once_with(
            "kraken", "kraken_1"
        )

