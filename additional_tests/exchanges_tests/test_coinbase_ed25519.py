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
import pytest

import additional_tests.exchanges_tests.test_coinbase as test_coinbase

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestCoinbaseEd25519AuthenticatedExchange(test_coinbase.TestCoinbaseAuthenticatedExchange):
    # same as regular coinbase exchange test except that it is using the Ed25519 api key format
    # (after organizations/ and -----BEGIN EC PRIVATE)
    CREDENTIALS_EXCHANGE_NAME = "coinbase_ED25519"
