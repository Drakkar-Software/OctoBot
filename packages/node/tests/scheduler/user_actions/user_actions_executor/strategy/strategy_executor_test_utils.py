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

_SAMPLE_TIMESTAMP = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)


def minimal_strategy(
    *,
    strategy_id: str,
    name: str = "Test strategy",
    version: str = "1.0.0",
) -> protocol_models.Strategy:
    configuration = protocol_models.GenericProcessConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
        profile_data={},
    )
    return protocol_models.Strategy(
        id=strategy_id,
        version=version,
        name=name,
        reference_market="USDT",
        created_at=_SAMPLE_TIMESTAMP,
        updated_at=_SAMPLE_TIMESTAMP,
        configuration=protocol_models.StrategyConfiguration(configuration),
    )
