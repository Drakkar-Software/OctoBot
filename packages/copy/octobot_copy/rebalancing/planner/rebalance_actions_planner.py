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

import octobot_commons.list_util as list_util
import octobot_commons.logging as logging
import octobot_trading.constants as trading_constants

import octobot_copy.constants as copy_constants
import octobot_copy.enums as rebalancer_enums
import octobot_copy.exchange.exchange_interface as exchange_interface
import octobot_copy.rebalancing.planner.distributions as planner_distributions
import octobot_copy.rebalancing.rebalancing_client_interface as rebalancing_client_interface


class RebalanceActionsPlanner:
    def __init__(
        self,
        exchange: exchange_interface.ExchangeInterface,
        client: rebalancing_client_interface.RebalancingClientInterface,
    ):
        self._exchange: exchange_interface.ExchangeInterface = exchange
        self.client: rebalancing_client_interface.RebalancingClientInterface = client

        self.ratio_per_asset: dict = {}
        self.total_ratio_per_asset: decimal.Decimal = trading_constants.ZERO

        self._targeted_coins: list[str] = []
        self._disabled_symbol_bases: frozenset = frozenset()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)

    @property
    def targeted_coins(self) -> list[str]:
        return self._targeted_coins

    @targeted_coins.setter
    def targeted_coins(self, value: list[str]) -> None:
        self._targeted_coins = list_util.deduplicate(value)

    def get_rebalance_details(self) -> typing.Tuple[bool, dict]:
        """
        Main method to get the rebalance details.
        """
        rebalance_details = self._empty_rebalance_details()
        should_rebalance = False
        available_traded_bases = set(
            symbol.base
            for symbol in self._exchange.public_data.get_traded_symbols()
        )

        if self.client.synchronization_policy in (
            rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE,
            rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_DYNAMIC_INDEX_COINS_AS_SOON_AS_POSSIBLE,
        ):
            should_rebalance = self._register_removed_coin(rebalance_details, available_traded_bases)
        should_rebalance = self._register_coins_update(rebalance_details) or should_rebalance
        should_rebalance = self._register_quote_asset_rebalance(rebalance_details) or should_rebalance
        if (
            should_rebalance
            and self.client.synchronization_policy
            == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
        ):
            self.update_distribution(force_latest=True)
            rebalance_details = self._empty_rebalance_details()
            self._register_removed_coin(rebalance_details, available_traded_bases)
            self._register_coins_update(rebalance_details)
            self._register_quote_asset_rebalance(rebalance_details)

        if not rebalance_details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value]:
            self._resolve_swaps(rebalance_details)
            for origin, target in rebalance_details[rebalancer_enums.RebalanceDetails.SWAP.value].items():
                origin_ratio = round(
                    rebalance_details[rebalancer_enums.RebalanceDetails.REMOVE.value][origin]
                    * trading_constants.ONE_HUNDRED,
                    3
                )
                target_ratio = round(
                    rebalance_details[rebalancer_enums.RebalanceDetails.ADD.value].get(
                        target,
                        rebalance_details[rebalancer_enums.RebalanceDetails.BUY_MORE.value].get(
                            target, trading_constants.ZERO
                        )
                    ) * trading_constants.ONE_HUNDRED,
                    3
                ) or "???"
                self.logger.info(
                    f"Swapping {origin} (holding ratio: {origin_ratio}%) for {target} (to buy ratio: {target_ratio}%) "
                    f"on [{self._exchange.exchange_name}]: ratios are similar enough to allow swapping."
                )
        return (
            should_rebalance or rebalance_details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value],
            rebalance_details,
        )

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
    ) -> None:
        self.client.update(
            min_order_size_margin=min_order_size_margin,
            synchronization_policy=synchronization_policy,
            rebalance_trigger_min_ratio=rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=reference_market_ratio,
            sell_untargeted_traded_coins=sell_untargeted_traded_coins,
            allow_skip_asset=allow_skip_asset,
        )

    def update_distribution(self, adapt_to_holdings: bool = False, force_latest: bool = False) -> None:
        """
        Refresh the target distribution state
        """
        distribution = self._get_supported_distribution(adapt_to_holdings, force_latest)
        self.ratio_per_asset = {
            asset[rebalancer_enums.DistributionKeys.NAME]: asset
            for asset in distribution
        }
        self.total_ratio_per_asset = decimal.Decimal(sum(
            asset[rebalancer_enums.DistributionKeys.VALUE]
            for asset in self.ratio_per_asset.values()
        ))
        self._targeted_coins = self._get_filtered_traded_coins()

    def get_target_ratio(self, currency) -> decimal.Decimal:
        if currency in self.ratio_per_asset:
            try:
                return (
                    decimal.Decimal(str(
                        self.ratio_per_asset[currency][rebalancer_enums.DistributionKeys.VALUE]
                    )) / self.total_ratio_per_asset
                )
            except (decimal.DivisionByZero, decimal.InvalidOperation):
                pass
        return trading_constants.ZERO

    def get_removed_coins_from_config(self, available_traded_bases) -> list:
        """
        Get the coins that should be removed from the config.
        Mainly used when a target configuration changed and some coins are no longer in the target.
        """
        removed_coins = []
        trading_config = self.client.get_config()
        if self.client.get_ideal_distribution(trading_config or {}) and self.client.sell_untargeted_traded_coins:
            removed_coins = [
                coin
                for coin in available_traded_bases
                if coin not in self._targeted_coins
                and coin != self._exchange.private_data.reference_market
            ]
        if self.client.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE:
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
                        != self._exchange.private_data.reference_market
                    )
            ]))
        if self.client.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE:
            historical_configs = self.client.get_historical_configs(
                0, self._exchange.public_data.get_time()
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
                    if asset_name not in current_coins and asset_name != self._exchange.private_data.reference_market:
                        removed_coins_from_historical_configs.add(asset_name)
            return list(removed_coins_from_historical_configs.union(removed_coins))
        if self.client.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_DYNAMIC_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            return [
                coin for coin in available_traded_bases
                if coin not in self._targeted_coins and coin != self._exchange.private_data.reference_market
            ]
        self.logger.error(f"Unknown synchronization policy: {self.client.synchronization_policy}")
        return []

    def _get_adjusted_target_ratio(self, currency: str) -> decimal.Decimal:
        """
        Get the adjusted target ratio for a given currency relatively to the reference market ratio.
        """
        base_ratio = self.get_target_ratio(currency)
        if self.client.reference_market_ratio < trading_constants.ONE:
            return base_ratio * self.client.reference_market_ratio
        return base_ratio

    def _get_coins_to_consider_for_ratio(self) -> list:
        """
        Get the coins that should be considered for the ratio, including the reference market.
        """
        return self._targeted_coins + [self._exchange.private_data.reference_market]

    def _empty_rebalance_details(self) -> dict:
        return {
            rebalancer_enums.RebalanceDetails.SELL_SOME.value: {},
            rebalancer_enums.RebalanceDetails.BUY_MORE.value: {},
            rebalancer_enums.RebalanceDetails.REMOVE.value: {},
            rebalancer_enums.RebalanceDetails.ADD.value: {},
            rebalancer_enums.RebalanceDetails.SWAP.value: {},
            rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value: False,
        }

    def _register_coins_update(self, rebalance_details: dict) -> bool:
        """
        Register the coins that are beyond the target ratio: 
        - some should be added
        - some should be bought
        - some should be sold
        """
        should_rebalance = False
        for coin in self._targeted_coins:
            target_ratio = self._get_adjusted_target_ratio(coin)
            coin_ratio = self._exchange.private_data.get_holdings_ratio(
                coin, traded_symbols_only=True, include_assets_in_open_orders=True
            )
            beyond_ratio = True
            if coin_ratio == trading_constants.ZERO and target_ratio > trading_constants.ZERO:
                rebalance_details[rebalancer_enums.RebalanceDetails.ADD.value][coin] = target_ratio
                should_rebalance = True
            elif coin_ratio < target_ratio - self.client.rebalance_trigger_min_ratio:
                rebalance_details[rebalancer_enums.RebalanceDetails.BUY_MORE.value][coin] = target_ratio
                should_rebalance = True
            elif coin_ratio > target_ratio + self.client.rebalance_trigger_min_ratio:
                rebalance_details[rebalancer_enums.RebalanceDetails.SELL_SOME.value][coin] = target_ratio
                should_rebalance = True
            else:
                beyond_ratio = False
            if beyond_ratio:
                allowance = round(self.client.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED, 2)
                self.logger.info(
                    f"{coin} is beyond the target ratio of {round(target_ratio * trading_constants.ONE_HUNDRED, 2)}[+/-{allowance}]%, "
                    f"ratio: {round(coin_ratio * trading_constants.ONE_HUNDRED, 2)}%. A rebalance is required."
                )
        return should_rebalance

    def _register_removed_coin(self, rebalance_details: dict, available_traded_bases: set[str]) -> bool:
        """
        Register the coins that are no longer in the target and should be sold.
        """
        should_rebalance = False
        for coin in self.get_removed_coins_from_config(available_traded_bases):
            if coin in available_traded_bases:
                coin_ratio = self._exchange.private_data.get_holdings_ratio(
                    coin, traded_symbols_only=True, include_assets_in_open_orders=True
                )
                if coin_ratio >= copy_constants.MIN_RATIO_TO_SELL:
                    rebalance_details[rebalancer_enums.RebalanceDetails.REMOVE.value][coin] = coin_ratio
                    self.logger.info(
                        f"{coin} (holdings: {round(coin_ratio * trading_constants.ONE_HUNDRED, 3)}%) is not in target "
                        f"anymore. A rebalance is required."
                    )
                    should_rebalance = True
            else:
                if coin in self._disabled_symbol_bases:
                    self.logger.info(
                        f"Ignoring {coin} holding: {coin} is not in target anymore but is disabled."
                    )
                else:
                    self.logger.error(
                        f"Ignoring {coin} holding: Can't sell {coin} as it is not in any trading pair"
                        f" but is not in target anymore. This is unexpected"
                    )
        return should_rebalance

    def _register_quote_asset_rebalance(self, rebalance_details: dict) -> bool:
        """
        Returns True if the rebalance is required due to a high non-targeted quote asset holdings ratio.
        """
        non_targeted_quote_assets_ratio = self._get_non_targeted_quote_assets_ratio()
        if self._should_rebalance_due_to_non_targeted_quote_assets_ratio(
            non_targeted_quote_assets_ratio, rebalance_details
        ):
            rebalance_details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value] = True
            self.logger.info(
                f"Rebalancing due to a high non-targeted quote asset holdings ratio: "
                f"{round(non_targeted_quote_assets_ratio * trading_constants.ONE_HUNDRED, 2)}%, quote rebalance "
                f"threshold = {self.client.quote_asset_rebalance_ratio_threshold * trading_constants.ONE_HUNDRED}%"
            )
            return True
        return False

    def _should_rebalance_due_to_non_targeted_quote_assets_ratio(
        self, non_targeted_quote_assets_ratio: decimal.Decimal, rebalance_details: dict
    ) -> bool:
        total_added_ratio = (
            self._sum_ratios(rebalance_details, rebalancer_enums.RebalanceDetails.ADD.value)
            + self._sum_ratios(rebalance_details, rebalancer_enums.RebalanceDetails.BUY_MORE.value)
        )

        if (
            total_added_ratio * (trading_constants.ONE - copy_constants.QUOTE_ASSET_TO_TARGETED_SWAP_RATIO_THRESHOLD)
            <= non_targeted_quote_assets_ratio
            <= total_added_ratio * (trading_constants.ONE + copy_constants.QUOTE_ASSET_TO_TARGETED_SWAP_RATIO_THRESHOLD)
        ):
            total_removed_ratio = (
                self._sum_ratios(rebalance_details, rebalancer_enums.RebalanceDetails.REMOVE.value)
                + self._sum_ratios(rebalance_details, rebalancer_enums.RebalanceDetails.SELL_SOME.value)
            )
            if total_removed_ratio == trading_constants.ZERO:
                return False
        min_ratio = min(
            min(
                self.get_target_ratio(coin)
                for coin in self._targeted_coins
            ) if self._targeted_coins else self.client.quote_asset_rebalance_ratio_threshold,
            self.client.quote_asset_rebalance_ratio_threshold
        )
        return non_targeted_quote_assets_ratio >= min_ratio

    @staticmethod
    def _sum_ratios(rebalance_details: dict, key: str) -> decimal.Decimal:
        return decimal.Decimal(str(sum(
            ratio
            for ratio in rebalance_details[key].values()
        ))) if rebalance_details[key] else trading_constants.ZERO

    def _get_non_targeted_quote_assets_ratio(self) -> decimal.Decimal:
        total = trading_constants.ZERO
        for quote in set(
            symbol.quote
            for symbol in self._exchange.public_data.get_traded_symbols()
            if symbol.quote not in self._targeted_coins
        ):
            ratio = self._exchange.private_data.get_holdings_ratio(
                quote, traded_symbols_only=True, include_assets_in_open_orders=True
            )
            if quote == self._exchange.private_data.reference_market and self.client.reference_market_ratio > trading_constants.ZERO:
                reference_market_keep_ratio = trading_constants.ONE - self.client.reference_market_ratio
                ratio = max(trading_constants.ZERO, ratio - reference_market_keep_ratio)
            total += ratio
        return decimal.Decimal(str(total))

    def _resolve_swaps(self, details: dict):
        """
        Resolve swaps between added and removed coins, when swaps are possible
        """
        removed = details[rebalancer_enums.RebalanceDetails.REMOVE.value]
        details[rebalancer_enums.RebalanceDetails.SWAP.value] = {}
        if details[rebalancer_enums.RebalanceDetails.SELL_SOME.value]:
            return
        added = {
            **details[rebalancer_enums.RebalanceDetails.ADD.value],
            **details[rebalancer_enums.RebalanceDetails.BUY_MORE.value],
        }
        if len(removed) == len(added) == copy_constants.ALLOWED_1_TO_1_SWAP_COUNTS:
            for removed_coin, removed_ratio, added_coin, added_ratio in zip(
                removed, removed.values(), added, added.values()
            ):
                added_holding_ratio = self._exchange.private_data.get_holdings_ratio(
                    added_coin, traded_symbols_only=True, coins_whitelist=self._get_coins_to_consider_for_ratio()
                )
                required_added_ratio = added_ratio - added_holding_ratio
                if (
                    removed_ratio - self.client.rebalance_trigger_min_ratio
                    < required_added_ratio
                    < removed_ratio + self.client.rebalance_trigger_min_ratio
                ):
                    details[rebalancer_enums.RebalanceDetails.SWAP.value][removed_coin] = added_coin
                else:
                    details[rebalancer_enums.RebalanceDetails.SWAP.value] = {}
                    return

    def _get_filtered_traded_coins(self) -> list[str]:
        coins = set(
            symbol.base
            for symbol in self._exchange.public_data.get_traded_symbols()
            if symbol.base in self.ratio_per_asset and symbol.quote == self._exchange.private_data.reference_market
        )
        if self._exchange.private_data.reference_market in self.ratio_per_asset and coins:
            coins.add(self._exchange.private_data.reference_market)
        return sorted(list(coins))

    def _get_currently_applied_historical_config_according_to_holdings(
        self, config: dict, traded_bases: set[str]
    ) -> dict:
        if self._is_target_config_applied(config, traded_bases):
            self.logger.info(f"Using {self.client.client_name} latest config.")
            return config
        historical_configs = self.client.get_historical_configs(
            0, self._exchange.public_data.get_time()
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
                f"{missing_assets} are missing from {self._exchange.exchange_name} traded pairs."
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
            coin_ratio = self._exchange.private_data.get_holdings_ratio(
                asset_distrib[rebalancer_enums.DistributionKeys.NAME], traded_symbols_only=True,
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

    def _get_supported_distribution(self, adapt_to_holdings: bool, force_latest: bool) -> list:
        """
        Returns the configured distribution if any. This configured distribution might be choosen from
        historical configs if the current content does not match the configured distribution and the
        SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE synchronization policy is used.

        Use a uniform distribution over all the exchange's traded pairs if no configured distribution is found.

        :param adapt_to_holdings: Whether to adapt the distribution to the current holdings.
        This means selecting the closest historical config according to the current holdings.
        :param force_latest: Whether to force the use of the latest distribution.
        """
        trading_config = self.client.get_config()
        if detailed_distribution := self.client.get_ideal_distribution(trading_config or {}):
            traded_bases = set(
                symbol.base
                for symbol in self._exchange.public_data.get_traded_symbols()
            )
            traded_bases.add(self._exchange.private_data.reference_market)
            if (
                (adapt_to_holdings or force_latest)
                and self.client.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
            ):
                if adapt_to_holdings:
                    target_config = self._get_currently_applied_historical_config_according_to_holdings(
                        trading_config or {}, traded_bases
                    )
                else:
                    try:
                        target_config = self.client.get_historical_configs(
                            0, self._exchange.public_data.get_time()
                        )[0]
                        self.logger.info(
                            f"Updated {self.client.client_name} to use latest distribution: "
                            f"{self.client.get_ideal_distribution(target_config)}."
                        )
                    except IndexError:
                        target_config = trading_config or {}
                detailed_distribution = self.client.get_ideal_distribution(target_config)
                if not detailed_distribution:
                    raise ValueError(f"No distribution found in historical target config: {target_config}")
            distribution = [
                asset
                for asset in detailed_distribution
                if asset[rebalancer_enums.DistributionKeys.NAME] in traded_bases
            ]
            if removed_assets := [
                asset[rebalancer_enums.DistributionKeys.NAME]
                for asset in detailed_distribution
                if asset not in distribution
            ]:
                self.logger.info(
                    f"Ignored {len(removed_assets)} assets {removed_assets} from configured "
                    f"distribution as absent from traded pairs."
                )
            return distribution
        return planner_distributions.get_uniform_distribution([
            symbol.base
            for symbol in self._exchange.public_data.get_traded_symbols()
        ])
