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


class RebalancingClientInterface:
    def __init__(
        self,
        *,
        client_name: str,
        reference_market: str,
        min_order_size_margin: decimal.Decimal,
        get_config: typing.Callable[[], typing.Optional[dict]],
        get_previous_config: typing.Callable[[], typing.Optional[dict]],
        get_historical_configs: typing.Callable[[float, float], list],
        get_ideal_distribution: typing.Callable[[dict], typing.Optional[list]],
        get_allow_skip_asset: typing.Callable[[], bool],
    ) -> None:
        # static values
        self.client_name: str = client_name
        self.reference_market: str = reference_market
        self.min_order_size_margin: decimal.Decimal = min_order_size_margin

        # dynamic values
        self.get_config = get_config
        self.get_previous_config = get_previous_config
        self.get_historical_configs = get_historical_configs
        self.get_ideal_distribution = get_ideal_distribution
        self.get_allow_skip_asset = get_allow_skip_asset

    @property
    def allow_skip_asset(self) -> bool:
        # implemented as property in case the actual value changes dynamically
        return self.get_allow_skip_asset()
