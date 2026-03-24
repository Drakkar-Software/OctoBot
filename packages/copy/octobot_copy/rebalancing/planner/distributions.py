#  Drakkar-Software OctoBot
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
import typing

import octobot_copy.enums as copy_enums
import octobot_trading.constants

MAX_DISTRIBUTION_AFTER_COMMA_DIGITS = 1


def get_uniform_distribution(
    coins,
    price_by_coin: typing.Optional[dict[str, decimal.Decimal]] = None,
) -> typing.List:
    if not coins:
        return []
    ratio = float(
        round(
            octobot_trading.constants.ONE / decimal.Decimal(str(len(coins))) * octobot_trading.constants.ONE_HUNDRED,
            MAX_DISTRIBUTION_AFTER_COMMA_DIGITS,
        )
    )
    if not ratio:
        return []
    return [
        {
            copy_enums.DistributionKeys.NAME.value: coin,
            copy_enums.DistributionKeys.VALUE.value: ratio,
            copy_enums.DistributionKeys.PRICE.value: price_by_coin.get(coin) if price_by_coin else None,
        }
        for coin in coins
    ]
