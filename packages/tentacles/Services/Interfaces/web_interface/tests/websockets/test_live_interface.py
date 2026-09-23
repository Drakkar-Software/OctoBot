#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import json
import threading
import time

import aiohttp
import mock
import pytest
import websockets

import octobot_commons.constants as commons_constants
import octobot_services.interfaces as interfaces
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.tests as web_interface_tests
import tentacles.Services.Interfaces.web_interface.websockets.protocol.wire_protocol as wire_protocol
import octobot.enums


pytestmark = pytest.mark.asyncio


async def _recv_ws_event_with_timeout(websocket, timeout_seconds=5.0) -> dict:
    message = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
    return json.loads(message)


async def _wait_for_web_interface_started(
    web_interface_instance: web_interface.WebInterface,
    max_wait_seconds: float = web_interface_tests.MAX_START_TIME,
) -> None:
    launch_time = time.time()
    while not web_interface_instance.started and time.time() - launch_time < max_wait_seconds:
        await asyncio.sleep(0.3)
    if not web_interface_instance.started:
        raise RuntimeError("Web interface did not start in time")


def _join_web_interface_thread(start_thread: threading.Thread) -> None:
    start_thread.join(timeout=web_interface_tests.WEB_INTERFACE_TEST_THREAD_JOIN_TIMEOUT_SECONDS)
    if start_thread.is_alive():
        raise RuntimeError("Web interface thread did not exit after stop")


class TestWebInterfaceStopWithUvicorn:
    async def test_stop_within_timeout(self):
        async with web_interface_tests.get_web_interface(False, octobot.enums.OctoBotDistribution.DEFAULT) as interface:
            assert interface.started
            await interface.stop()
            assert not interface.started


class TestWebInterfaceRestart:
    async def test_stop_then_start_serves_api_ping(self):
        bot = await web_interface_tests._init_bot(octobot.enums.OctoBotDistribution.DEFAULT)
        interfaces.AbstractInterface.bot_id = bot.bot_id
        interface = web_interface.WebInterface({})
        interface.port = web_interface_tests.get_new_port()
        interface.should_open_web_interface = False
        interface.set_requires_password(False)
        first_exchange = next(iter(bot.config[commons_constants.CONFIG_EXCHANGES]))
        with mock.patch.object(interface, "_register_on_channels", new=mock.AsyncMock()), \
             mock.patch(
                 "tentacles.Services.Interfaces.web_interface.models.get_current_exchange",
                 mock.Mock(return_value=first_exchange),
             ):
            first_start_thread = threading.Thread(
                target=web_interface_tests._start_web_interface,
                args=(interface,),
                name="web-interface-test-first",
            )
            first_start_thread.start()
            await _wait_for_web_interface_started(interface)
            await interface.stop()
            assert not interface.started
            _join_web_interface_thread(first_start_thread)

            second_start_thread = threading.Thread(
                target=web_interface_tests._start_web_interface,
                args=(interface,),
                name="web-interface-test-second",
            )
            second_start_thread.start()
            await _wait_for_web_interface_started(interface)
            assert interface.started
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:{interface.port}/api/ping") as response:
                    assert response.status == 200
            await interface.stop()
            assert not interface.started
            _join_web_interface_thread(second_start_thread)


@pytest.mark.parametrize(
    "namespace,emit_event,expected_event",
    [
        ("/backtesting", "backtesting_status", "backtesting_status"),
        ("/data_collector", "data_collector_status", "data_collector_status"),
        ("/social_data_collector", "social_data_collector_status", "social_data_collector_status"),
        ("/strategy_optimizer", "strategy_optimizer_status", "strategy_optimizer_status"),
        ("/dashboard", "profitability", "profitability"),
    ],
)
class TestWebSocketNamespaceRoundTrip:
    async def test_round_trip(self, namespace, emit_event, expected_event):
        async with web_interface_tests.get_web_interface(False, octobot.enums.OctoBotDistribution.DEFAULT) as interface:
            uri = f"ws://127.0.0.1:{interface.port}{namespace}"
            async with websockets.connect(uri) as websocket:
                if namespace == "/dashboard":
                    await _recv_ws_event_with_timeout(websocket)
                await websocket.send(wire_protocol.encode_ws_event(emit_event))
                frame = await _recv_ws_event_with_timeout(websocket)
                assert frame["event"] == expected_event


class TestWebSocketDashboardServerPush:
    async def test_send_new_trade_delivers_new_data(self):
        async with web_interface_tests.get_web_interface(False, octobot.enums.OctoBotDistribution.DEFAULT) as interface:
            first_exchange = "binance"
            with mock.patch.object(interface, "_register_on_channels", new=mock.AsyncMock()), \
                 mock.patch(
                     "tentacles.Services.Interfaces.web_interface.models.get_current_exchange",
                     mock.Mock(return_value=first_exchange),
                 ), \
                 mock.patch(
                     "octobot_trading.api.get_exchange_manager_from_exchange_id",
                     mock.Mock(return_value=mock.Mock()),
                 ), \
                 mock.patch(
                     "octobot_trading.api.get_open_orders",
                     mock.Mock(return_value=[]),
                 ), \
                 mock.patch(
                     "octobot_trading.api.is_trader_simulated",
                     mock.Mock(return_value=True),
                 ), \
                 mock.patch(
                     "tentacles.Services.Interfaces.web_interface.models.format_trades",
                     mock.Mock(return_value=[]),
                 ), \
                 mock.patch(
                     "tentacles.Services.Interfaces.web_interface.models.format_orders",
                     mock.Mock(return_value=[]),
                 ):
                uri = f"ws://127.0.0.1:{interface.port}/dashboard"
                async with websockets.connect(uri) as websocket:
                    await _recv_ws_event_with_timeout(websocket)
                    web_interface.send_new_trade({"id": "1"}, "exchange-id", "BTC/USDT")
                    frame = await _recv_ws_event_with_timeout(websocket)
                    assert frame["event"] == "new_data"
                    assert "data" in frame["data"]
