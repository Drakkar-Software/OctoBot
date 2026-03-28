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


class RebalancingClientInterface:
    def __init__(
        self,
        *,
        client_name: str,
        min_order_size_margin: decimal.Decimal,
        rebalance_trigger_min_ratio: decimal.Decimal,
        quote_asset_rebalance_ratio_threshold: decimal.Decimal,
        reference_market_ratio: decimal.Decimal,
        sell_untargeted_traded_coins: bool,
        synchronization_policy: copy_enums.SynchronizationPolicy,
        allow_skip_asset: bool,
        can_include_assets_in_open_orders_in_holdings_ratio: bool,
        raise_all_order_errors: bool,
        get_config: typing.Callable[[], typing.Optional[dict]],
        get_previous_config: typing.Callable[[], typing.Optional[dict]],
        get_historical_configs: typing.Callable[[float, float], list],
        get_ideal_distribution: typing.Callable[[dict], typing.Optional[list]],
    ) -> None:
        # static values
        self.client_name: str = client_name
        self.min_order_size_margin: decimal.Decimal = min_order_size_margin
        self.rebalance_trigger_min_ratio: decimal.Decimal = rebalance_trigger_min_ratio
        self.quote_asset_rebalance_ratio_threshold: decimal.Decimal = (
            quote_asset_rebalance_ratio_threshold
        )
        self.reference_market_ratio: decimal.Decimal = reference_market_ratio
        self.sell_untargeted_traded_coins: bool = sell_untargeted_traded_coins
        self.synchronization_policy: copy_enums.SynchronizationPolicy = synchronization_policy
        self.allow_skip_asset: bool = allow_skip_asset
        self.can_include_assets_in_open_orders_in_holdings_ratio: bool = can_include_assets_in_open_orders_in_holdings_ratio
        self.raise_all_order_errors: bool = raise_all_order_errors

        # dynamic values
        self.get_config = get_config
        self.get_previous_config = get_previous_config
        self.get_historical_configs = get_historical_configs
        self.get_ideal_distribution = get_ideal_distribution

    def update(
        self,
        *,
        min_order_size_margin: decimal.Decimal,
        synchronization_policy: typing.Any,
        rebalance_trigger_min_ratio: decimal.Decimal,
        quote_asset_rebalance_ratio_threshold: decimal.Decimal,
        reference_market_ratio: decimal.Decimal,
        sell_untargeted_traded_coins: bool,
        allow_skip_asset: bool,
        can_include_assets_in_open_orders_in_holdings_ratio: bool,
        raise_all_order_errors: bool = False,
    ) -> None:
        self.min_order_size_margin = min_order_size_margin
        self.synchronization_policy = synchronization_policy
        self.rebalance_trigger_min_ratio = rebalance_trigger_min_ratio
        self.quote_asset_rebalance_ratio_threshold = quote_asset_rebalance_ratio_threshold
        self.reference_market_ratio = reference_market_ratio
        self.sell_untargeted_traded_coins = sell_untargeted_traded_coins
        self.allow_skip_asset = allow_skip_asset
        self.can_include_assets_in_open_orders_in_holdings_ratio = (
            can_include_assets_in_open_orders_in_holdings_ratio
        )
        self.raise_all_order_errors = raise_all_order_errors
    