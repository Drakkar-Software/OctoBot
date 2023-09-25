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
import time

import mock
import pytest
import asyncio
import websockets

from additional_tests.supabase_backend_tests import authenticated_client_1, authenticated_client_2, \
    authenticated_client_3, get_backend_client_creds, sandboxed_insert
import octobot.community.supabase_backend.enums as enums
import octobot.community.supabase_backend.community_supabase_client as community_supabase_client
import octobot.community.supabase_backend.supabase_realtime_client as supabase_realtime_client


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

PRODUCT_ID = "02ced004-f84b-408c-b863-7920fb1c2a28"
SIGNAL = '{"topic": "moonmoon", "content": {"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "buy", "type": "buy_market", "quantity": 0.004, "target_amount": "5.356892%", "target_position": null, "updated_target_amount": null, "updated_target_position": null, "limit_price": 1001.69, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": false, "post_only": false, "group_id": null, "group_type": null, "tag": "managed_order long entry (id: 143968020)", "order_id": "adc24701-573b-40dd-b6c9-3666cd22f33e", "bundled_with": null, "chained_to": null, "additional_orders": [{"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "sell", "type": "sell_limit", "quantity": 0.004, "target_amount": "5.3574085830652285%", "target_position": 0, "updated_target_amount": null, "updated_target_position": null, "limit_price": 1010.69, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": true, "post_only": false, "group_id": "46a0b2de-5b8f-4a39-89a0-137504f83dfc", "group_type": "BalancedTakeProfitAndStopOrderGroup", "tag": "managed_order long exit (id: 143968020)", "order_id": "5705d395-f970-45d9-9ba8-f63da17f17b2", "bundled_with": null, "chained_to": "adc24701-573b-40dd-b6c9-3666cd22f33e", "additional_orders": [{"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "sell", "type": "stop_loss", "quantity": 0.004, "target_amount": "5.356892%", "target_position": 0, "updated_target_amount": null, "updated_target_position": null, "limit_price": 9990.0, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": true, "post_only": false, "group_id": "46a0b2de-5b8f-4a39-89a0-137504f83dfc", "group_type": "BalancedTakeProfitAndStopOrderGroup", "tag": "managed_order long exit (id: 143968020)", "order_id": "5ad2a999-5ac2-47f0-9b69-c75a36f3858a", "bundled_with": "adc24701-573b-40dd-b6c9-3666cd22f33e", "chained_to": "adc24701-573b-40dd-b6c9-3666cd22f33e", "additional_orders": [], "associated_order_ids": null, "update_with_triggering_order_fees": false}], "associated_order_ids": null, "update_with_triggering_order_fees": true}], "associated_order_ids": null, "update_with_triggering_order_fees": true}}'

SIGNALS_TABLE = "signals"
SECONDARY_TABLE = "todos2"  # any random table that all authenticated users can listen to
SECONDARY_TABLE_INSERT_CONTENT = {"task": "hello !!!"}

VERBOSE = True


async def test_not_listen(authenticated_client_1):
    assert isinstance(authenticated_client_1.realtime, supabase_realtime_client.AuthenticatedSupabaseRealtimeClient)
    # access_token is passed and is a real user auth token (not the anon supabase_key)
    assert len(authenticated_client_1.realtime.access_token) > len(authenticated_client_1.supabase_key)
    # ensure no connection is created as long as subscribe is not called
    assert authenticated_client_1.realtime.channels == []
    assert authenticated_client_1.realtime.socket.closed is True
    assert authenticated_client_1.realtime.socket.connected is False
    assert authenticated_client_1.realtime.socket.ws_connection is None


async def test_listen_one_chan(authenticated_client_1, authenticated_client_2, authenticated_client_3, sandboxed_insert):
    subscribed = {}
    insert_received = {}
    system_received = {}
    await asyncio.gather(*(
        _start_client(client, identifier, insert_received, subscribed, system_received)
        for client, identifier in (
            (authenticated_client_1, "g.dsm          "),
            (authenticated_client_2, "guillaumemdsm  "),
            (authenticated_client_3, "faster.roundup "),
        )
    ))
    timeout = 10
    await asyncio.gather(*(
        asyncio.wait_for(subscribed_event.event.wait(), timeout)
        for subscribed_event in subscribed.values()
        if not subscribed_event.event.is_set()
    ))
    await asyncio.gather(*(
        asyncio.wait_for(system.event.wait(), timeout)
        for system in system_received.values()
        if not system.event.is_set()
    ))
    _print("all subscribed")
    await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
    _print("signal sent")
    await asyncio.gather(*(
        asyncio.wait_for(received.event.wait(), timeout)
        for identifier, received in insert_received.items()
        if "faster.roundup" not in identifier and not received.event.is_set()
    ))
    for identifier, received in insert_received.items():
        if "faster.roundup" in identifier:
            received.mock.assert_not_called()
            assert not received.event.is_set()
        else:
            assert received.event.is_set()
            received.mock.assert_called_once()
            assert received.mock.call_args[0][0]["new"]["signal"] == SIGNAL

async def test_listen_two_chans(authenticated_client_1, authenticated_client_2, authenticated_client_3, sandboxed_insert):
    subscribed_cb_1 = {}
    subscribed_cb_2 = {}
    insert_received_cb_1 = {}
    insert_received_cb_2 = {}
    system_received = {}

    async def start_client_dual_cb(client, identifier):
        verbose = True
        await _start_client(client, identifier, insert_received_cb_1, subscribed_cb_1, system_received)

        async def _insert_cb_2(message):
            if verbose:
                _print(f"> {identifier} {message}")
            insert_received_cb_2[identifier].event.set()
            insert_received_cb_2[identifier].mock(message)

        async def _subscribed_cb_2(result, message):
            if verbose:
                _print(f"{identifier} {result} {message}")
            subscribed_cb_2[identifier].event.set()
            subscribed_cb_2[identifier].mock(result, message)
        insert_received_cb_2[identifier] = EventMockedCallback()
        subscribed_cb_2[identifier] = EventMockedCallback()
        channel_b = await client.realtime.channel("public", "todos2")
        await channel_b.on("INSERT", _insert_cb_2).subscribe(_subscribed_cb_2)
    await asyncio.gather(*(
        start_client_dual_cb(client, identifier)
        for client, identifier in (
            (authenticated_client_1, "g.dsm          "),
            (authenticated_client_2, "guillaumemdsm  "),
            (authenticated_client_3, "faster.roundup "),
        )
    ))
    timeout = 10

    await asyncio.gather(*(
        asyncio.wait_for(subscribed_event.event.wait(), timeout)
        for subscribed_event in list(subscribed_cb_1.values()) + list(subscribed_cb_2.values())
        if not subscribed_event.event.is_set()
    ))
    await asyncio.gather(*(
        asyncio.wait_for(system.event.wait(), timeout)
        for system in system_received.values()
        if not system.event.is_set()
    ))
    _print("all subscribed")
    await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
    await _insert_in_other_table(sandboxed_insert)
    _print("signal sent")
    await asyncio.gather(*(
        asyncio.wait_for(received.event.wait(), timeout)
        for identifier, received in insert_received_cb_1.items()
        if "faster.roundup" not in identifier and not received.event.is_set()
    ))
    await asyncio.gather(*(
        asyncio.wait_for(received.event.wait(), timeout)
        for identifier, received in insert_received_cb_2.items()
        if not received.event.is_set()
    ))
    for identifier, received in insert_received_cb_1.items():
        if "faster.roundup" in identifier:
            received.mock.assert_not_called()
            assert not received.event.is_set()
        else:
            assert received.event.is_set()
            received.mock.assert_called_once()
            assert received.mock.call_args[0][0]["new"]["signal"] == SIGNAL

    for identifier, received in insert_received_cb_2.items():
        assert received.event.is_set()
        received.mock.assert_called_once()
        new_received = received.mock.call_args[0][0]["new"]
        for key, val in SECONDARY_TABLE_INSERT_CONTENT.items():
            # only compare inserted columns (skip id)
            assert new_received[key] == val


async def test_listen_late_signin_then_signout(authenticated_client_1, sandboxed_insert):
    sign_out_timeout = 5
    _print("signing out")
    await _full_realtime_sign_out(authenticated_client_1, sign_out_timeout)
    _print("sign_out done")
    system_received = {}
    subscribed = {}
    insert_received = {}
    await _start_client(
        authenticated_client_1, "g.dsm          ", insert_received, subscribed, system_received,
    )
    received_mock = next(iter(insert_received.values()))
    subscribed_mock = next(iter(subscribed.values()))
    system_received_mock = next(iter(system_received.values()))
    timeout = 10
    if not subscribed_mock.event.is_set():
        await asyncio.wait_for(subscribed_mock.event.wait(), timeout)
    _print("subscribed")
    _print("sending not expected signals")
    for _ in range(5):
        # send 5 signals. As authenticated_client_1 is not authenticated, it does not receive signals
        await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
        await asyncio.sleep(0.1)
    receive_timeout = 1
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(received_mock.event.wait(), receive_timeout)
    _print("signal not received (ok)")
    _print("signin")
    system_received_mock.event.clear()
    system_received_mock.mock.reset_mock()
    await _full_realtime_sign_in(authenticated_client_1, 2, sign_out_timeout)
    _print("signin done")
    # wait for system resp (auth result)
    if not system_received_mock.event.is_set():
        await asyncio.wait_for(system_received_mock.event.wait(), timeout)
        assert system_received_mock.mock.call_args[0][0].payload["status"] == "ok"
    _print("subscribed")
    assert not received_mock.event.is_set()
    _print("sending expected signal")
    await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
    if not received_mock.event.is_set():
        await asyncio.wait_for(received_mock.event.wait(), 3)
    assert received_mock.mock.call_args[0][0]["new"]["signal"] == SIGNAL
    _print("sign_out")
    await _full_realtime_sign_out(authenticated_client_1, sign_out_timeout)
    # wait for system resp (auth result)
    if not system_received_mock.event.is_set():
        await asyncio.wait_for(system_received_mock.event.wait(), timeout)
        assert system_received_mock.mock.call_args[0][0].payload["status"] == "ok"
    received_mock.event.clear()
    _print("sending not expected signals")
    for _ in range(5):
        # send 5 signals. As authenticated_client_1 is not authenticated, it does not receive signals
        await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
        await asyncio.sleep(0.1)
    receive_timeout = 0.5
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(received_mock.event.wait(), receive_timeout)
    _print("signal not received (ok)")


async def test_reconnect(authenticated_client_1, sandboxed_insert):
    subscribed = {}
    insert_received = {}
    system_received = {}
    await _start_client(authenticated_client_1, "g.dsm          ", insert_received, subscribed, system_received)
    subscribed_mock = next(iter(subscribed.values()))
    received_mock = next(iter(insert_received.values()))
    system_received_mock = next(iter(system_received.values()))
    timeout = 10
    await asyncio.wait_for(subscribed_mock.event.wait(), timeout)
    if not system_received_mock.event.is_set():
        await asyncio.wait_for(system_received_mock.event.wait(), timeout)
        assert system_received_mock.mock.call_args[0][0].payload["status"] == "ok"
    _print("all subscribed")
    await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
    _print("signal sent")
    await asyncio.wait_for(received_mock.event.wait(), timeout)
    _print("signal received")
    _print("now disconnect")
    enable_disconnect = []

    async def call_and_raise(msg):
        await origin_method(msg)
        if enable_disconnect:
            enable_disconnect.clear()
            raise websockets.ConnectionClosed(None, None)

    origin_method = authenticated_client_1.realtime.socket._on_message
    with mock.patch.object(
        authenticated_client_1.realtime.socket, "_on_message",
        mock.AsyncMock(side_effect=call_and_raise)
    ) as _on_message_mock:
        conn_1 = authenticated_client_1.realtime.socket.ws_connection
        assert conn_1.open
        received_mock.event.clear()
        subscribed_mock.event.clear()
        system_received_mock.event.clear()
        # trigger _on_message_mock to raise websockets.ConnectionClosed and trigger reconnect
        enable_disconnect.append(True)
        await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
        _print("signal sent")
        await asyncio.wait_for(received_mock.event.wait(), timeout)
        _on_message_mock.assert_awaited_once()
        _print("received signal")
        _print("waiting for subscribe (done after reconnect)")
        await asyncio.wait_for(subscribed_mock.event.wait(), timeout)
        await asyncio.wait_for(system_received_mock.event.wait(), timeout)
        assert conn_1.closed
        _print("previous connection closed")
        conn_2 = authenticated_client_1.realtime.socket.ws_connection
        assert conn_2 is not conn_1

        # re disconnect
        assert conn_2.open
        _print("new connection open")
        received_mock.event.clear()
        subscribed_mock.event.clear()
        system_received_mock.event.clear()
        _on_message_mock.reset_mock()
        # trigger _on_message_mock to raise websockets.ConnectionClosed and trigger reconnect
        enable_disconnect.append(True)
        await _send_signal(sandboxed_insert, PRODUCT_ID, SIGNAL)
        _print("signal sent")
        await asyncio.wait_for(received_mock.event.wait(), timeout)
        _on_message_mock.assert_awaited_once()
        _print("received signal")
        _print("waiting for subscribe (done after reconnect)")
        await asyncio.wait_for(subscribed_mock.event.wait(), timeout)
        await asyncio.wait_for(system_received_mock.event.wait(), timeout)
        assert conn_2.closed
        _print("previous connection closed")
        conn_3 = authenticated_client_1.realtime.socket.ws_connection
        assert conn_2 is not conn_3
        assert conn_3.open
        _print("new connection open")


async def _start_client(
    client, identifier,
    on_callback_by_identifier, subscribed_callback_by_identifier, system_received_by_identifier,
    schema="public", table=SIGNALS_TABLE, event="INSERT"
):
    assert client.realtime.socket.ws_connection is None  # ensure connection has not yet been created

    async def insert_cb(message):
        _print(f"> {identifier} {message}")
        on_callback_by_identifier[identifier].event.set()
        on_callback_by_identifier[identifier].mock(message)

    async def subscribe_cb(result, message):
        _print(f"{identifier} {result} {message}")
        subscribed_callback_by_identifier[identifier].event.set()
        subscribed_callback_by_identifier[identifier].mock(result, message)

    async def system_cb(message):
        _print(f"{identifier} {message}")
        system_received_by_identifier[identifier].event.set()
        system_received_by_identifier[identifier].mock(message)

    system_received_by_identifier[identifier] = EventMockedCallback()
    on_callback_by_identifier[identifier] = EventMockedCallback()
    subscribed_callback_by_identifier[identifier] = EventMockedCallback()
    channel = await client.realtime.channel(schema, table)
    await channel.on(event, insert_cb).subscribe(subscribe_cb, system_callback=system_cb)


def _print(*args):
    if VERBOSE:
        print(*args)


async def _full_realtime_sign_out(client, timeout):
    client.sign_out()

    async def wait_for_fully_signed_out():
        while True:
            if not client.is_signed_in() and client.realtime.socket.closed and not client.realtime.socket.connected:
                return
            await asyncio.sleep(0.1)
    await asyncio.wait_for(wait_for_fully_signed_out(), timeout)


async def _full_realtime_sign_in(client, cred_id, timeout):
    await client.sign_in(*get_backend_client_creds(cred_id))

    def _all_chan_joined():
        for channels in client.realtime.socket.channels.values():
            for channel in channels:
                if not channel.is_joined():
                    return False
        for task in client.realtime.update_auth_tasks:
            if not task.done():
                return False
        return True

    async def wait_for_fully_signed_in():
        while True:
            if client.is_signed_in() and \
                    not client.realtime.socket.closed and client.realtime.socket.connected and _all_chan_joined():
                return True
            await asyncio.sleep(0.1)

    await asyncio.wait_for(wait_for_fully_signed_in(), timeout)


async def _insert_in_other_table(sandboxed_insert, table=SECONDARY_TABLE, content=SECONDARY_TABLE_INSERT_CONTENT):
    return await sandboxed_insert.insert(table, content)


async def _send_signal(sandboxed_insert, product_id: str, signal: str):
    return await sandboxed_insert.insert("signals", {
        enums.SignalKeys.TIME.value: community_supabase_client.CommunitySupabaseClient.get_formatted_time(time.time()),
        enums.SignalKeys.PRODUCT_ID.value: product_id,
        enums.SignalKeys.SIGNAL.value: signal,
    })


class EventMockedCallback:
    def __init__(self):
        self.event = asyncio.Event()
        self.mock = mock.Mock()
