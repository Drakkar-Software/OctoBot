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
import postgrest
import pytest

from additional_tests.supabase_backend_tests import authenticated_client_1


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_paginated_fetch_cryptocurrencies(authenticated_client_1):
    pages = []

    def cryptocurrencies_request_factory(table: postgrest.AsyncRequestBuilder, select_count):
        pages.append(1)
        return (
            table.select(
                "symbol, last_price",
                count=select_count
            )
        )

    raw_currencies = await authenticated_client_1.paginated_fetch(
        authenticated_client_1,
        "cryptocurrencies",
        cryptocurrencies_request_factory
    )
    assert len(raw_currencies) > 1500
    # ensure at least 2 calls have been performed
    assert 2 <= sum(pages)

