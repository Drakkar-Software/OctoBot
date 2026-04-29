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
import dataclasses
import typing


@dataclasses.dataclass
class ExchangeCredentialsData:
    # CEXes
    api_key: typing.Optional[str] = None
    secret: typing.Optional[str] = None
    password: typing.Optional[str] = None
    uid: typing.Optional[str] = None
    # Oauth
    auth_token: typing.Optional[str] = None
    auth_token_header_prefix: typing.Optional[str] = None
    # DEXes
    wallet_address: typing.Optional[str] = None
    private_key: typing.Optional[str] = None

    def has_credentials(self) -> bool:
        return bool(
            (self.api_key and self.secret)  # CEX
            or (self.wallet_address and self.private_key)  # DEX
        )

