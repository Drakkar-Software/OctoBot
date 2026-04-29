#  Drakkar-Software OctoBot-Tentacles
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

import pytest
import mock

import tentacles.Meta.Keywords.scripting_library.orders.order_types.create_order as create_order
import tentacles.Meta.Keywords.scripting_library.orders.order_types.trailing_limit_order as trailing_limit_order

from tentacles.Meta.Keywords.scripting_library.tests import event_loop, null_context


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_trailing_limit(null_context):
    with mock.patch.object(create_order, "create_order_instance", mock.AsyncMock()) as create_order_instance:
        await trailing_limit_order.trailing_limit(null_context, "side", "symbol", "amount", "target_position",
                                                  "offset", "min_offset", "max_offset", "slippage_limit", "time_limit",
                                                  "reduce_only", "post_only",
                                                  "tag", "group", "wait_for")
        create_order_instance.assert_called_once_with(
            null_context, side="side", symbol="symbol", order_amount="amount", order_target_position="target_position",
            order_type_name="trailing_limit", order_min_offset="min_offset", order_max_offset="max_offset",
            order_offset="offset", slippage_limit="slippage_limit", time_limit="time_limit", reduce_only="reduce_only",
            post_only="post_only", tag="tag", group="group", wait_for="wait_for")
