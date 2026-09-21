#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

from unittest import mock

import pytest
from fastapi import HTTPException

from tentacles.Services.Interfaces.node_api_interface.api.recover_passphrase_rate_limit import (
    enforce_recover_passphrase_rate_limit,
    reset_recover_passphrase_rate_limits_for_tests,
)


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_recover_passphrase_rate_limits_for_tests()
    yield
    reset_recover_passphrase_rate_limits_for_tests()


def test_rate_limit_allows_under_threshold():
    request = mock.MagicMock()
    request.client = mock.MagicMock(host="127.0.0.1")
    for _ in range(10):
        enforce_recover_passphrase_rate_limit(request)


def test_rate_limit_blocks_after_threshold():
    request = mock.MagicMock()
    request.client = mock.MagicMock(host="10.0.0.5")
    for _ in range(10):
        enforce_recover_passphrase_rate_limit(request)
    with pytest.raises(HTTPException) as err:
        enforce_recover_passphrase_rate_limit(request)
    assert err.value.status_code == 429
