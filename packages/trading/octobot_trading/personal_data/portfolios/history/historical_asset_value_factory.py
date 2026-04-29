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
import decimal


def create_historical_asset_value_from_dict_like_object(historical_asset_class, asset_values):
    return historical_asset_class(
        asset_values[historical_asset_class.TIMESTAMP_KEY],
        {
            currency: decimal.Decimal(f"{value}")
            for currency, value in asset_values[historical_asset_class.VALUES_KEY].items()
        }
    )
