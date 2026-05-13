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

import octobot_protocol.models as protocol_models

WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def exchange_account_payload() -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        trading_type=protocol_models.TradingType.SPOT,
        exchange="binanceus",
        remote_account_id="remote-1",
        api_key="k",
        api_secret="s",
    )


def minimal_exchange_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=True,
        details=protocol_models.AccountDetails(
            actual_instance=exchange_account_payload(),
        ),
    )


def minimal_blockchain_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Blockchain test account",
        is_simulated=False,
        details=protocol_models.AccountDetails(
            actual_instance=protocol_models.BlockchainAccount(
                account_type=protocol_models.AccountType.BLOCKCHAIN,
                blockchain="ethereum",
                wallet_address="0x1234567890123456789012345678901234567890",
            ),
        ),
    )


def wrap_configuration(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())
