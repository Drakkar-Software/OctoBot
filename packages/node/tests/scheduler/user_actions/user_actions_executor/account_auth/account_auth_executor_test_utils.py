#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import datetime

import octobot_protocol.models as protocol_models

from ..account import account_executor_test_utils


WALLET_ADDRESS = account_executor_test_utils.WALLET_ADDRESS
wrap_configuration = account_executor_test_utils.wrap_configuration


def minimal_account_authentication(
    *,
    auth_id: str,
    api_key: str = "test-api-key",
    api_secret: str = "test-api-secret",
    api_passphrase: str | None = None,
    updated_at: datetime.datetime | None = None,
) -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id=auth_id,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        updated_at=updated_at,
    )
