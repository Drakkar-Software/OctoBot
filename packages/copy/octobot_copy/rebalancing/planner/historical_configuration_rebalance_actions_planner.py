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

import octobot_trading.constants as trading_constants

import octobot_copy.constants as copy_constants
import octobot_copy.enums as rebalancer_enums
import octobot_copy.rebalancing.planner.base_rebalance_actions_planner as rebalance_actions_planner_module


class HistoricalConfigurationRebalanceActionsPlanner(
    rebalance_actions_planner_module.BaseRebalanceActionsPlanner,
):
    def _apply_synchronization_policy_to_removed_coins(
        self,
        removed_coins: list,
        trading_config: typing.Optional[dict],
        available_traded_bases: typing.AbstractSet[str],
    ) -> list:
        """
        Override to handle previous & historical configs.
        """
        policy = self.client.synchronization_policy
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            return self._extend_removed_coins_index_from_previous_config(
                removed_coins, trading_config, available_traded_bases
            )
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE:
            return self._extend_removed_coins_from_historical_config(
                removed_coins, trading_config, available_traded_bases
            )
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_DYNAMIC_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            return self._removed_coins_dynamic_index_as_soon_as_possible(available_traded_bases)
        self.logger.error(f"Unknown synchronization policy: {self.client.synchronization_policy}")
        return []

    def _resolve_target_config_for_distribution(
        self,
        trading_config: typing.Optional[dict],
        traded_bases: set[str],
        adapt_to_holdings: bool,
        force_latest: bool,
    ) -> dict:
        """
        Override to handle historical configs.
        """
        if not (
            (adapt_to_holdings or force_latest)
            and self.client.synchronization_policy
            == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
        ):
            return trading_config or {}
        if adapt_to_holdings:
            return self._get_currently_applied_historical_config_according_to_holdings(
                trading_config or {}, traded_bases
            )
        try:
            target_config = self.client.get_historical_configs(
                0, self._exchange_interface.get_time()
            )[0]
            self.logger.info(
                f"Updated {self.client.client_name} to use latest distribution: "
                f"{self.client.get_ideal_distribution(target_config)}."
            )
        except IndexError:
            target_config = trading_config or {}
        return target_config

    def _extend_removed_coins_index_from_previous_config(
        self,
        removed_coins: list,
        trading_config: typing.Optional[dict],
        available_traded_bases: typing.AbstractSet[str],
    ) -> list:
        del available_traded_bases
        previous_trading_config = self.client.get_previous_config()
        if not (previous_trading_config and trading_config):
            return removed_coins
        current_coins = [
            asset[rebalancer_enums.DistributionKeys.NAME]
            for asset in (self.client.get_ideal_distribution(trading_config or {}) or [])
        ]
        return list(set(removed_coins + [
            asset[rebalancer_enums.DistributionKeys.NAME]
            for asset in previous_trading_config[copy_constants.CONFIG_INDEX_CONTENT]
            if asset[rebalancer_enums.DistributionKeys.NAME] not in current_coins
                and (
                    asset[rebalancer_enums.DistributionKeys.NAME]
                    != self._exchange_interface.portfolio.reference_market
                )
        ]))

    def _extend_removed_coins_from_historical_config(
        self,
        removed_coins: list,
        trading_config: typing.Optional[dict],
        available_traded_bases: typing.AbstractSet[str],
    ) -> list:
        del available_traded_bases
        historical_configs = self.client.get_historical_configs(
            0, self._exchange_interface.get_time()
        )
        if not (historical_configs and trading_config):
            return removed_coins
        current_coins = [
            asset[rebalancer_enums.DistributionKeys.NAME]
            for asset in (self.client.get_ideal_distribution(trading_config or {}) or [])
        ]
        removed_coins_from_historical_configs = set()
        for historical_config in historical_configs:
            for asset in historical_config[copy_constants.CONFIG_INDEX_CONTENT]:
                asset_name = asset[rebalancer_enums.DistributionKeys.NAME]
                if asset_name not in current_coins and asset_name != self._exchange_interface.portfolio.reference_market:
                    removed_coins_from_historical_configs.add(asset_name)
        return list(removed_coins_from_historical_configs.union(removed_coins))

    def _get_currently_applied_historical_config_according_to_holdings(
        self, config: dict, traded_bases: set[str]
    ) -> dict:
        if self._is_target_config_applied(config, traded_bases):
            self.logger.info(f"Using {self.client.client_name} latest config.")
            return config
        historical_configs = self.client.get_historical_configs(
            0, self._exchange_interface.get_time()
        )
        if not historical_configs or (
            len(historical_configs) == 1 and (
                self.client.get_ideal_distribution(historical_configs[0]) == self.client.get_ideal_distribution(config)
                and historical_configs[0][copy_constants.CONFIG_REBALANCE_TRIGGER_MIN_PERCENT] == config[copy_constants.CONFIG_REBALANCE_TRIGGER_MIN_PERCENT]
            )
        ):
            self.logger.info(f"Using {self.client.client_name} latest config as no historical configs are available.")
            return config
        for hist_rank, historical_config in enumerate(historical_configs):
            if self._is_target_config_applied(historical_config, traded_bases):
                self.logger.info(
                    f"Using [N-{hist_rank}] {self.client.client_name} historical config distribution: "
                    f"{self.client.get_ideal_distribution(historical_config)}."
                )
                return historical_config
        self.logger.info(
            f"No suitable {self.client.client_name} config found: using latest distribution: "
            f"{self.client.get_ideal_distribution(config)}."
        )
        return config

    def _is_target_config_applied(self, config: dict, traded_bases: set[str]) -> bool:
        full_assets_distribution = self.client.get_ideal_distribution(config)
        if not full_assets_distribution:
            return False
        assets_distribution = [
            asset
            for asset in full_assets_distribution
            if asset[rebalancer_enums.DistributionKeys.NAME] in traded_bases
        ]
        if len(assets_distribution) != len(full_assets_distribution):
            missing_assets = [
                asset[rebalancer_enums.DistributionKeys.NAME]
                for asset in full_assets_distribution
                if asset not in assets_distribution
            ]
            self.logger.warning(
                f"Ignored {self.client.client_name} config candidate as {len(missing_assets)} configured assets "
                f"{missing_assets} are missing from {self._exchange_interface.exchange_name} traded pairs."
            )
            return False

        total_ratio = decimal.Decimal(sum(
            asset[rebalancer_enums.DistributionKeys.VALUE]
            for asset in assets_distribution
        ))
        if total_ratio == trading_constants.ZERO:
            return False
        min_trigger_ratio = self._get_config_min_ratio(config)
        for asset_distrib in assets_distribution:
            base_target_ratio = decimal.Decimal(str(asset_distrib[rebalancer_enums.DistributionKeys.VALUE])) / total_ratio
            if self.client.reference_market_ratio < trading_constants.ONE:
                target_ratio = base_target_ratio * self.client.reference_market_ratio
            else:
                target_ratio = base_target_ratio
            coin_ratio = self._exchange_interface.portfolio.get_holdings_ratio(
                asset_distrib[rebalancer_enums.DistributionKeys.NAME], traded_symbols_only=True,
                include_assets_in_open_orders=False,
            )
            if not (target_ratio - min_trigger_ratio <= coin_ratio <= target_ratio + min_trigger_ratio):
                return False
        return True

    def _get_config_min_ratio(self, config: dict) -> decimal.Decimal:
        ratio = None
        rebalance_trigger_profiles = config.get(copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILES, None)
        if rebalance_trigger_profiles:
            selected_rebalance_trigger_profile_name = config.get(copy_constants.CONFIG_SELECTED_REBALANCE_TRIGGER_PROFILE, None)
            selected_profile = [
                p for p in rebalance_trigger_profiles
                if p[copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILE_NAME] == selected_rebalance_trigger_profile_name
            ]
            if selected_profile:
                selected_rebalance_trigger_profile = selected_profile[0]
                ratio = selected_rebalance_trigger_profile[copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILE_MIN_PERCENT]
        if ratio is None:
            ratio = config.get(copy_constants.CONFIG_REBALANCE_TRIGGER_MIN_PERCENT)
        if ratio is None:
            return self.client.rebalance_trigger_min_ratio
        return decimal.Decimal(str(ratio)) / trading_constants.ONE_HUNDRED
