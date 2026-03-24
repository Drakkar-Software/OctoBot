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
        get_holdings_ratio: typing.Callable[..., decimal.Decimal],
        get_config: typing.Callable[[], typing.Optional[dict]],
        get_previous_config: typing.Callable[[], typing.Optional[dict]],
        get_historical_configs: typing.Callable[[float, float], list],
        get_ideal_distribution: typing.Callable[[dict], typing.Optional[list]],
        get_client_name: typing.Callable[[], str],
    ) -> None:
        self.get_holdings_ratio = get_holdings_ratio
        self.get_config = get_config
        self.get_previous_config = get_previous_config
        self.get_historical_configs = get_historical_configs
        self.get_ideal_distribution = get_ideal_distribution
        self.get_client_name = get_client_name
