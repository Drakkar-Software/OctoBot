#  Drakkar-Software OctoBot-Sync
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

"""E2E tests — error sharing via sync server + real S3.

These tests require S3_ENDPOINT to be set in the environment; they are
automatically skipped otherwise.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("S3_ENDPOINT"),
    reason="S3_ENDPOINT not set — skipping e2e tests",
)


async def test_placeholder_e2e_skipped():
    """Placeholder: real e2e tests require S3 infrastructure."""
    pass
