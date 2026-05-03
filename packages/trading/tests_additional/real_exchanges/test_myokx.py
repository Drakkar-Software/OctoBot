#  Drakkar-Software OctoBot-Trading
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

import tests_additional.real_exchanges.test_okx as test_okx

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestMyOkxRealExchangeTester(test_okx.TestOkxRealExchangeTester):
    EXCHANGE_NAME = "myokx"

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(2400, 2400)
