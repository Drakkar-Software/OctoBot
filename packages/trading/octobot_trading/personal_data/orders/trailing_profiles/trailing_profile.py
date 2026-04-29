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
import octobot_commons.dataclasses

import octobot_trading.personal_data.orders.trailing_profiles.trailing_profile_types as trailing_profile_types

@dataclasses.dataclass
class TrailingProfile(octobot_commons.dataclasses.FlexibleDataclass):

    @staticmethod
    def get_type() -> trailing_profile_types.TrailingProfileTypes:
        raise NotImplementedError("get_name is not implemented")

    def update_and_get_trailing_price(self, updated_price: decimal.Decimal) -> decimal.Decimal:
        raise NotImplementedError("update_and_get_trailing_price is not implemented")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
