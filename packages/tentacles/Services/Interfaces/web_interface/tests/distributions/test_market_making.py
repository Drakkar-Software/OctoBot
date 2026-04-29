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

import tentacles.Services.Interfaces.web_interface.tests.distribution_tester as distribution_tester
import octobot.enums


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


_COMMUNITY_ACCOUNT_REQUIRED_PATHS = [
    "/api/tradingview_confirm_email_content",
]


class TestMarketMakingDistributionPlugin(distribution_tester.AbstractDistributionTester):
    DISTRIBUTION = octobot.enums.OctoBotDistribution.MARKET_MAKING
    # backlist endpoints expecting additional data
    URL_BLACK_LIST = [
        "/tentacle_media", "/export_logs", "/api/first_exchange_details"
    ]
    DOTTED_URLS = ["/robots.txt"]
    VERBOSE = False

    async def test_browse_all_pages_no_required_password(self):
        await self._inner_test_browse_all_pages_no_required_password(_COMMUNITY_ACCOUNT_REQUIRED_PATHS)

    async def test_browse_all_pages_required_password_without_login(self):
        await self._inner_test_browse_all_pages_required_password_without_login([])

    async def test_browse_all_pages_required_password_with_login(self):
        await self.inner_test_browse_all_pages_required_password_with_login(
            _COMMUNITY_ACCOUNT_REQUIRED_PATHS, []
        )
