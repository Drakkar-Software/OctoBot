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
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors

import octobot_copy.constants as copy_constants
import octobot_copy.enums as rebalancer_enums
import octobot_copy.exchange.exchange_interface as exchange_interface
import octobot_copy.rebalancing.planner.distributions as planner_distributions
import octobot_copy.rebalancing.rebalancing_client_interface as rebalancing_client_interface


class BaseRebalanceActionsPlanner:
    def __init__(
        self,
        exchange_interface: exchange_interface.ExchangeInterface,
        client: rebalancing_client_interface.RebalancingClientInterface,
    ):
        self._exchange_interface: exchange_interface.ExchangeInterface = exchange_interface
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
            for symbol in self._exchange_interface.market.get_traded_symbols()
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
            self._log_rebalance_swap_details(rebalance_details)
        return (
            should_rebalance or rebalance_details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value],
            rebalance_details,
        )

    def _log_rebalance_swap_details(self, rebalance_details: dict):
        for origin, target in rebalance_details[rebalancer_enums.RebalanceDetails.SWAP.value].items():
            logged_origin_ratio = round(
                rebalance_details[rebalancer_enums.RebalanceDetails.REMOVE.value][origin]
                * trading_constants.ONE_HUNDRED,
                3
            )
            if not (logged_target_ratio := round(
                rebalance_details[rebalancer_enums.RebalanceDetails.ADD.value].get(
                    target,
                    rebalance_details[rebalancer_enums.RebalanceDetails.BUY_MORE.value].get(
                        target, trading_constants.ZERO
                    )
                ) * trading_constants.ONE_HUNDRED,
                3
            )):
                self.logger.error(f"No target ratio found for {target} in rebalance details: {rebalance_details}")
                logged_target_ratio = "???" # used for logging only
            self.logger.info(
                f"Swapping {origin} (holding ratio: {logged_origin_ratio}%) for {target} (to buy ratio: {logged_target_ratio}%) "
                f"on [{self._exchange_interface.exchange_name}]: ratios are similar enough to allow swapping."
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
        can_include_assets_in_open_orders_in_holdings_ratio: bool,
    ) -> None:
        self.client.update(
            min_order_size_margin=min_order_size_margin,
            synchronization_policy=synchronization_policy,
            rebalance_trigger_min_ratio=rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=reference_market_ratio,
            sell_untargeted_traded_coins=sell_untargeted_traded_coins,
            allow_skip_asset=allow_skip_asset,
            can_include_assets_in_open_orders_in_holdings_ratio=(
                can_include_assets_in_open_orders_in_holdings_ratio
            ),
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

    def _resolve_target_config_for_distribution(
        self,
        trading_config: typing.Optional[dict],
        traded_bases: set[str],
        adapt_to_holdings: bool,
        force_latest: bool,
    ) -> dict:
        return trading_config or {}

    def _removed_coins_dynamic_index_as_soon_as_possible(
        self, available_traded_bases: typing.AbstractSet[str],
    ) -> list:
        return [
            coin for coin in available_traded_bases
            if coin not in self._targeted_coins and coin != self._exchange_interface.portfolio.reference_market
        ]

    def _apply_synchronization_policy_to_removed_coins(
        self,
        removed_coins: list,
        trading_config: typing.Optional[dict],
        available_traded_bases: typing.AbstractSet[str],
    ) -> list:
        policy = self.client.synchronization_policy
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            return removed_coins
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE:
            raise NotImplementedError(f"Use HistoricalConfigurationRebalanceActionsPlanner for {policy}")
        if policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_DYNAMIC_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            return self._removed_coins_dynamic_index_as_soon_as_possible(available_traded_bases)
        self.logger.error(f"Unknown synchronization policy: {self.client.synchronization_policy}")
        return []

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
                and coin != self._exchange_interface.portfolio.reference_market
            ]
        return self._apply_synchronization_policy_to_removed_coins(
            removed_coins, trading_config, available_traded_bases
        )

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
        return self._targeted_coins + [self._exchange_interface.portfolio.reference_market]

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
            coin_ratio = self._exchange_interface.portfolio.get_holdings_ratio(
                coin,
                traded_symbols_only=True,
                include_assets_in_open_orders=(
                    self.client.can_include_assets_in_open_orders_in_holdings_ratio
                ),
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
                coin_ratio = self._exchange_interface.portfolio.get_holdings_ratio(
                    coin,
                    traded_symbols_only=True,
                    include_assets_in_open_orders=(
                        self.client.can_include_assets_in_open_orders_in_holdings_ratio
                    ),
                )
                if coin_ratio >= copy_constants.MIN_RATIO_TO_SELL:
                    if self._removed_index_assets_unsold_are_only_dust({coin: coin_ratio}, []):
                        self.logger.info(
                            f"{coin} is not in target anymore but available holding value is below the exchange "
                            f"minimal order cost; omitting it from the removed-coins sell list."
                        )
                        continue
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

    def _removed_index_assets_unsold_are_only_dust(
        self,
        removed_coins: typing.Mapping[str, typing.Any],
        sold_coins: list,
    ) -> bool:
        ref_market = self._exchange_interface.portfolio.reference_market
        targeted = frozenset(self._targeted_coins)
        for asset in removed_coins:
            if asset in sold_coins:
                continue
            if asset in targeted:
                return False
            if asset == ref_market:
                return False
            symbol = symbol_util.merge_currencies(asset, ref_market)
            try:
                price, _ = self._exchange_interface.market.get_potentially_outdated_price(symbol)
                min_cost_decimal = self._exchange_interface.orders.get_minimal_order_cost(
                    symbol, default_price=float(price)
                )
            except trading_errors.NotSupported:
                return False
            available = self._exchange_interface.portfolio.get_currency_portfolio_available(asset)
            holding_value = available * price
            if holding_value >= min_cost_decimal:
                return False
        return True

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
            for symbol in self._exchange_interface.market.get_traded_symbols()
            if symbol.quote not in self._targeted_coins
        ):
            ratio = self._exchange_interface.portfolio.get_holdings_ratio(
                quote,
                traded_symbols_only=True,
                include_assets_in_open_orders=(
                    self.client.can_include_assets_in_open_orders_in_holdings_ratio
                ),
            )
            if quote == self._exchange_interface.portfolio.reference_market and self.client.reference_market_ratio > trading_constants.ZERO:
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
                added_holding_ratio = self._exchange_interface.portfolio.get_holdings_ratio(
                    added_coin, traded_symbols_only=True, include_assets_in_open_orders=False,
                    coins_whitelist=self._get_coins_to_consider_for_ratio()
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
            for symbol in self._exchange_interface.market.get_traded_symbols()
            if symbol.base in self.ratio_per_asset and symbol.quote == self._exchange_interface.portfolio.reference_market
        )
        if self._exchange_interface.portfolio.reference_market in self.ratio_per_asset and coins:
            coins.add(self._exchange_interface.portfolio.reference_market)
        return sorted(list(coins))

    def _get_supported_distribution(self, adapt_to_holdings: bool, force_latest: bool) -> list:
        """
        Returns the configured distribution if any, resolved via `_resolve_target_config_for_distribution`
        before filtering to traded pairs. Uses a uniform distribution over traded bases if none is configured.

        :param adapt_to_holdings: Passed to `_resolve_target_config_for_distribution` (subclass may use it).
        :param force_latest: Passed to `_resolve_target_config_for_distribution` (subclass may use it).
        """
        initial_target_config = self.client.get_config() or {}
        if detailed_distribution := self.client.get_ideal_distribution(initial_target_config):
            traded_bases = set(
                symbol.base
                for symbol in self._exchange_interface.market.get_traded_symbols()
            )
            traded_bases.add(self._exchange_interface.portfolio.reference_market)
            target_config = self._resolve_target_config_for_distribution(
                initial_target_config, traded_bases, adapt_to_holdings, force_latest
            )
            if target_config is not initial_target_config:
                # update distribution to the new target config
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
            for symbol in self._exchange_interface.market.get_traded_symbols()
        ])
