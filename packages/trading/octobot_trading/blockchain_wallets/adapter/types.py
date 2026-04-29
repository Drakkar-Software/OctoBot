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
import decimal
import typing

import octobot_commons.dataclasses
import octobot_trading.constants


@dataclasses.dataclass
class Balance(octobot_commons.dataclasses.FlexibleDataclass):
    free: decimal.Decimal
    used: decimal.Decimal = octobot_trading.constants.ZERO
    total: decimal.Decimal = octobot_trading.constants.ZERO

    def __post_init__(self):
        if self.total == octobot_trading.constants.ZERO:
            # ensure total is always synchronized even if only free is provided
            self.sync_total()

    def sync_total(self):
        self.total = self.free + self.used


@dataclasses.dataclass
class Fee(octobot_commons.dataclasses.FlexibleDataclass):
    currency: str
    cost: decimal.Decimal
    rate: typing.Optional[decimal.Decimal] = None


@dataclasses.dataclass
class Transaction(octobot_commons.dataclasses.FlexibleDataclass):
    txid: str
    timestamp: int
    address_from: str
    network: str
    address_to: str
    amount: decimal.Decimal
    currency: str
    id: str = ""
    fee: typing.Optional[Fee] = None
    status: str = ""
    tag: str = ""
    type: str = ""
    comment: str = ""
    internal: bool = False

    def __post_init__(self):
        if isinstance(self.fee, dict):
            self.fee = Fee.from_dict(self.fee)


@dataclasses.dataclass
class DepositAddress(octobot_commons.dataclasses.FlexibleDataclass):
    currency: str
    network: str
    address: str
    tag: str = ""
