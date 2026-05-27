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

WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
DEFAULT_EXCHANGE_CONFIG_ID = "test-exchange-config-id"

_ACCOUNT_TS = datetime.datetime(2026, 1, 10, 12, 0, 0, tzinfo=datetime.UTC)
_ACCOUNT_TS_OUT = datetime.datetime(2026, 1, 11, 14, 30, 0, tzinfo=datetime.UTC)


def exchange_config_payload() -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=DEFAULT_EXCHANGE_CONFIG_ID,
        name="binance-main",
        exchange="binanceus",
        sandboxed=False,
    )


def exchange_account_payload() -> protocol_models.ExchangeAccount:
    return protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote-1",
        exchange_config_ids=[DEFAULT_EXCHANGE_CONFIG_ID],
    )


def assets_payload(
    *,
    trading_type: protocol_models.TradingType = protocol_models.TradingType.SPOT,
) -> list[protocol_models.DetailedAssetsForTradingType]:
    return [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=trading_type,
            assets=[
                protocol_models.DetailedAsset(
                    symbol="USDT",
                    total=1000.0,
                    available=1000.0,
                )
            ],
        )
    ]


def authentication_payload(*, auth_id: str = "test-account-id") -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id=auth_id,
        api_key="k",
        api_secret="s",
    )


def minimal_exchange_account(*, account_id: str, is_simulated: bool = True) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Test account",
        is_simulated=is_simulated,
        created_at=_ACCOUNT_TS,
        updated_at=_ACCOUNT_TS,
        assets=assets_payload(),
        specifics=protocol_models.AccountSpecifics(
            actual_instance=exchange_account_payload(),
        ),
    )


def minimal_blockchain_account(*, account_id: str) -> protocol_models.Account:
    return protocol_models.Account(
        id=account_id,
        name="Blockchain test account",
        is_simulated=False,
        created_at=_ACCOUNT_TS,
        updated_at=_ACCOUNT_TS_OUT,
        specifics=protocol_models.AccountSpecifics(
            actual_instance=protocol_models.BlockchainAccount(
                account_type=protocol_models.AccountType.BLOCKCHAIN,
                blockchain="ethereum",
                public_key="0x1234567890123456789012345678901234567890",
            ),
        ),
    )


def wrap_configuration(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def stub_account_provider(account_provider_instance_mock, account: protocol_models.Account) -> None:
    account_provider_instance_mock.return_value.get_item.return_value = account
    account_provider_instance_mock.return_value.get_exchange_config.return_value = exchange_config_payload()

