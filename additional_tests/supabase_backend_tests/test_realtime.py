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
import pytest
import asyncio

import octobot_commons.configuration as commons_configuration
import octobot_commons.authentication as authentication
import octobot.community as community
import octobot.community.supabase_backend.enums as supabase_backend_enums
from additional_tests.supabase_backend_tests import authenticated_client_1, authenticated_client_2, \
    authenticated_client_3, _get_backend_client_creds


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_listen_one_chan(authenticated_client_1, authenticated_client_2, authenticated_client_3):
    subscribed = {}
    insert_received = {}
    async def start_client(client, identifier):
        async def insert_cb(message):
            print(f"> {identifier} {message}")
            insert_received[identifier].set()
        async def subscribe_cb(result, message):
            print(f"{identifier} {result} {message}")
            subscribed[identifier].set()
        subscribed[identifier] = asyncio.Event()
        insert_received[identifier] = asyncio.Event()
        channel = await client.realtime.channel("public", "signals")
        await channel.on("INSERT", insert_cb).subscribe(subscribe_cb)
    await asyncio.gather(*(
        start_client(client, identifier)
        for client, identifier in (
            (authenticated_client_1, "g.dsm          "),
            (authenticated_client_2, "guillaumemdsm  "),
            (authenticated_client_3, "faster.roundup "),
        )
    ))
    timeout = 10
    await asyncio.gather(*(
        asyncio.wait_for(subscribed_event.wait(), timeout)
        for subscribed_event in subscribed.values()
        if not subscribed_event.is_set()
    ))
    print("all subscribed")
    product_id = "02ced004-f84b-408c-b863-7920fb1c2a28"
    signal = '{"topic": "moonmoon", "content": {"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "buy", "type": "buy_market", "quantity": 0.004, "target_amount": "5.356892%", "target_position": null, "updated_target_amount": null, "updated_target_position": null, "limit_price": 1001.69, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": false, "post_only": false, "group_id": null, "group_type": null, "tag": "managed_order long entry (id: 143968020)", "order_id": "adc24701-573b-40dd-b6c9-3666cd22f33e", "bundled_with": null, "chained_to": null, "additional_orders": [{"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "sell", "type": "sell_limit", "quantity": 0.004, "target_amount": "5.3574085830652285%", "target_position": 0, "updated_target_amount": null, "updated_target_position": null, "limit_price": 1010.69, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": true, "post_only": false, "group_id": "46a0b2de-5b8f-4a39-89a0-137504f83dfc", "group_type": "BalancedTakeProfitAndStopOrderGroup", "tag": "managed_order long exit (id: 143968020)", "order_id": "5705d395-f970-45d9-9ba8-f63da17f17b2", "bundled_with": null, "chained_to": "adc24701-573b-40dd-b6c9-3666cd22f33e", "additional_orders": [{"action": "create", "symbol": "BTC/USDT:USDT", "exchange": "bybit", "exchange_type": "spot", "side": "sell", "type": "stop_loss", "quantity": 0.004, "target_amount": "5.356892%", "target_position": 0, "updated_target_amount": null, "updated_target_position": null, "limit_price": 9990.0, "updated_limit_price": 0.0, "stop_price": 0.0, "updated_stop_price": 0.0, "current": 1000.69, "updated_current_price": 0.0, "reduce_only": true, "post_only": false, "group_id": "46a0b2de-5b8f-4a39-89a0-137504f83dfc", "group_type": "BalancedTakeProfitAndStopOrderGroup", "tag": "managed_order long exit (id: 143968020)", "order_id": "5ad2a999-5ac2-47f0-9b69-c75a36f3858a", "bundled_with": "adc24701-573b-40dd-b6c9-3666cd22f33e", "chained_to": "adc24701-573b-40dd-b6c9-3666cd22f33e", "additional_orders": [], "associated_order_ids": null, "update_with_triggering_order_fees": false}], "associated_order_ids": null, "update_with_triggering_order_fees": true}], "associated_order_ids": null, "update_with_triggering_order_fees": true}}'
    await authenticated_client_1.send_signal(product_id, signal)
    print("signal sent")
    await asyncio.gather(*(
        asyncio.wait_for(received.wait(), timeout)
        for identifier, received in insert_received.items()
        if "faster.roundup" not in identifier and not received.is_set()
    ))
    for identifier, received in insert_received.items():
        if "faster.roundup" in identifier:
            assert not received.is_set()
        else:
            if not received.is_set():
                await asyncio.wait_for(received.wait(), timeout)
            assert received.is_set()


async def test_listen_two_chans(authenticated_client_1, authenticated_client_2, authenticated_client_3):
    async def start_client(client, identifier):
        async def insert_a_cb(message):
            print(f">A {identifier} {message}")
        async def insert_b_cb(message):
            print(f">B {identifier} {message}")
        async def subscribe_cb(result, message):
            print(f"{identifier} {message}")
        channel_a = await client.realtime.channel("public", "signals")
        await channel_a.on("INSERT", insert_a_cb).subscribe(subscribe_cb)
        channel_b = await client.realtime.channel("public", "todos2")
        await channel_b.on("INSERT", insert_b_cb).subscribe(subscribe_cb)
    await start_client(authenticated_client_1, "g.dsm          ")
    await start_client(authenticated_client_2, "guillaumemdsm  ")
    await start_client(authenticated_client_3, "faster.roundup ")
    await asyncio.sleep(5)


async def test_listen_late_signin(authenticated_client_1):
    authenticated_client_1.sign_out()
    print("sign_out done")
    async def start_client(client, identifier):
        async def insert_cb(message):
            print(f"> {identifier} {message}")
        async def subscribe_cb(result, message):
            print(f"{identifier} {message}")
        channel = await client.realtime.channel("public", "signals")
        await channel.on("INSERT", insert_cb).subscribe(subscribe_cb)
    await start_client(authenticated_client_1, "g.dsm          ")
    await asyncio.sleep(5)
    print("signin")
    await authenticated_client_1.sign_in(*_get_backend_client_creds(1))
    print("signin done")
    await asyncio.sleep(5)
    print("sign_out")
    authenticated_client_1.sign_out()
    await asyncio.sleep(100)
