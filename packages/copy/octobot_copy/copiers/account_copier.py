import time
import typing

import octobot_commons.logging as logging
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.errors as copy_errors
import octobot_copy.exchange as copy_exchange
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_module
import octobot_copy.rebalancing as copy_rebalancing


class AccountCopier:
    """
    Copies a reference spot-style account allocation onto the copier exchange by planning with
    BaseRebalanceActionsPlanner and executing with an AbstractRebalancer.

    Target weights are derived from reference_account (quantity-proportional). Holdings ratios
    and order execution use the live portfolio behind exchange_interface. Callers must ensure
    traded pairs on the copier exchange cover the assets to trade.
    copier_account is reserved for future snapshot/offline use and is not used by the rebalance pipeline.
    copy_settings controls reference_market, rebalance thresholds, and synchronization.
    Reference open orders in reference_account.orders are synched onto the copier after each successful run (spot).
    """

    def __init__(
        self,
        reference_account: copy_entities.Account,
        exchange_interface: copy_exchange.ExchangeInterface,
        copy_settings: copy_entities.AccountCopySettings,
    ) -> None:
        self._reference_account: copy_entities.Account = reference_account
        self._copier_exchange_interface: copy_exchange.ExchangeInterface = exchange_interface
        self._copy_settings: copy_entities.AccountCopySettings = copy_settings
        self._orders_synchronizer: orders_synchronizer_module.OrdersSynchronizer = (
            orders_synchronizer_module.OrdersSynchronizer(
                reference_account,
                exchange_interface,
                copy_settings,
            )
        )

    async def copy_account(self) -> copy_entities.AccountCopyResult:
        await self._resync_if_mirrored_open_order_grace_period_elapsed()
        rebalancer, should_rebalance, details = await self._prepare_rebalance_plan()
        if self._orders_synchronizer.is_mirrored_orphan_grace_invalid_no_compliant_snapshot():
            self._get_logger().info(
                "Forcing rebalance: mirrored orphan grace has no compliant reference snapshot "
                f"on [{self._copier_exchange_interface.exchange_name}]"
            )
            should_rebalance = True
        if self._orders_synchronizer.is_mirrored_orphan_grace_aborted_for_missed_historical_signals():
            self._get_logger().info(
                "Forcing rebalance: mirrored orphan grace aborted for missed historical signals "
                f"on [{self._copier_exchange_interface.exchange_name}]"
            )
            should_rebalance = True
        rebalance_orders: list = []
        try:
            if should_rebalance:
                if self._orders_synchronizer.is_mirrored_orphan_grace_blocking_rebalance():
                    self._get_logger().info(
                        "Skipping rebalance: mirrored open-order grace period is active "
                        f"on [{self._copier_exchange_interface.exchange_name}]"
                    )
                else:
                    self._get_logger().info(
                        f"Executing rebalance on [{self._copier_exchange_interface.exchange_name}]"
                    )
                    await self._orders_synchronizer.cancel_orders_pending_synchronization(None)
                    rebalance_orders = await self._run_rebalance(rebalancer, details)
            else:
                self._get_logger().info("No rebalance needed")
            if rebalance_orders:
                await self._copier_exchange_interface.portfolio.refresh_portfolio()
            synched_orders = await self._synchronize_reference_open_orders()
            all_orders: list = rebalance_orders + synched_orders
            return copy_entities.AccountCopyResult(created_orders=all_orders)
        except (trading_errors.MissingMinimalExchangeTradeVolume, copy_errors.RebalanceAborted) as err:
            self._get_logger().exception(
                err,
                True,
                f"Aborted rebalance on {self._copier_exchange_interface.exchange_name}: {err} ({err.__class__.__name__})",
            )
            return copy_entities.AccountCopyResult(created_orders=[])
        finally:
            self._get_logger().info("Portfolio rebalance process complete")

    async def _resync_if_mirrored_open_order_grace_period_elapsed(self) -> None:
        copy_settings = self._copy_settings
        grace_seconds = copy_settings.mirrored_orphan_cancel_grace_seconds
        grace_started_at = self._orders_synchronizer.get_mirrored_orphan_grace_started_at()
        if (
            grace_seconds > 0
            and grace_started_at is not None
            and grace_started_at > 0
            and (time.time() - grace_started_at) >= grace_seconds
        ):
            self._get_logger().info(
                "Mirrored open-order grace period elapsed before this run; "
                f"aborting grace and resyncing (cancel orphans, refresh portfolio) on "
                f"[{self._copier_exchange_interface.exchange_name}]"
            )
            self._orders_synchronizer.abort_mirrored_orphan_grace()
            await self._orders_synchronizer.cancel_orders_pending_synchronization(None)
            await self._copier_exchange_interface.portfolio.refresh_portfolio()

    async def _synchronize_reference_open_orders(self) -> list[trading_personal_data.Order]:
        return await self._orders_synchronizer.synchronize()

    def get_rebalancer_class(self) -> type[copy_rebalancing.AbstractRebalancer]:
        raise NotImplementedError("get_rebalancer_class is not implemented")

    async def _prepare_rebalance_plan(
        self,
    ) -> tuple[copy_rebalancing.AbstractRebalancer, bool, dict]:
        rebalancing_client = self._create_rebalancing_client()
        planner = self._create_rebalance_actions_planner(rebalancing_client)
        self._sync_planner(planner)
        planner.update_distribution(adapt_to_holdings=False, force_latest=False)
        rebalancer = self._create_rebalancer(planner)
        for coin in planner.targeted_coins:
            await rebalancer.prepare_coin_rebalancing(coin)
        should_rebalance, details = planner.get_rebalance_details()
        return rebalancer, should_rebalance, details

    async def _run_rebalance(
        self,
        rebalancer: copy_rebalancing.AbstractRebalancer,
        details: dict,
    ) -> list[trading_personal_data.Order]:
        orders: list = []
        self._get_logger().info("Step 1/3: ensuring enough funds are available for rebalance")
        await rebalancer.ensure_enough_funds_to_buy_after_selling()
        is_simple_buy_without_selling = rebalancer.can_simply_buy_coins_without_selling(details)
        reference_market = self._copier_exchange_interface.portfolio.reference_market
        if is_simple_buy_without_selling:
            self._get_logger().info(f"Step 2/3: skipped: no coin to sell for {reference_market}")
        else:
            self._get_logger().info(f"Step 2/3: selling coins to free {reference_market}")
            if sell_orders := await rebalancer.sell_targeted_coins_for_reference_market(details, None):
                if not self._copier_exchange_interface.orders.automatically_synchronize_orders():
                    await self._copier_exchange_interface.portfolio.refresh_portfolio()
                orders += sell_orders
        self._get_logger().info(f"Step 3/3: buying coins using {reference_market}")
        if buy_orders := await rebalancer.split_reference_market_into_targeted_coins(
            details,
            is_simple_buy_without_selling,
            None,
        ):
            if not self._copier_exchange_interface.orders.automatically_synchronize_orders():
                await self._copier_exchange_interface.portfolio.refresh_portfolio()
            orders += buy_orders
        return orders

    def _get_synthetic_config(self) -> dict:
        return {
            copy_constants.CONFIG_INDEX_CONTENT: self._reference_account.create_assets_distribution(),
            copy_constants.CONFIG_REBALANCE_TRIGGER_MIN_PERCENT: float(
                self._copy_settings.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED
            ),
        }

    def _get_ideal_distribution(self, config: typing.Optional[dict]) -> typing.Optional[list]:
        if not config:
            return None
        return config.get(copy_constants.CONFIG_INDEX_CONTENT)

    def _create_rebalancing_client(self) -> copy_rebalancing.RebalancingClientInterface:
        return copy_rebalancing.RebalancingClientInterface(
            client_name=self.__class__.__name__,
            min_order_size_margin=self._copy_settings.min_order_size_margin,
            rebalance_trigger_min_ratio=self._copy_settings.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self._copy_settings.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self._copy_settings.reference_market_ratio,
            sell_untargeted_traded_coins=self._copy_settings.sell_untargeted_traded_coins,
            synchronization_policy=self._copy_settings.synchronization_policy,
            allow_skip_asset=self._copy_settings.allow_skip_asset,
            can_include_assets_in_open_orders_in_holdings_ratio=(
                self._copy_settings.can_include_assets_in_open_orders_in_holdings_ratio
            ),
            raise_all_order_errors=True,
            get_config=self._get_synthetic_config,
            get_previous_config=lambda: None, # not implemented for now
            get_historical_configs=lambda _ft, _tt: [], # not implemented for now
            get_ideal_distribution=self._get_ideal_distribution,
        )

    def _create_rebalance_actions_planner(
        self,
        rebalancing_client: copy_rebalancing.RebalancingClientInterface,
    ) -> copy_rebalancing.BaseRebalanceActionsPlanner:
        return copy_rebalancing.BaseRebalanceActionsPlanner(
            exchange_interface=self._copier_exchange_interface,
            client=rebalancing_client,
        )

    def _sync_planner(self, planner: copy_rebalancing.BaseRebalanceActionsPlanner) -> None:
        planner.update(
            min_order_size_margin=self._copy_settings.min_order_size_margin,
            synchronization_policy=self._copy_settings.synchronization_policy,
            rebalance_trigger_min_ratio=self._copy_settings.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self._copy_settings.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self._copy_settings.reference_market_ratio,
            sell_untargeted_traded_coins=self._copy_settings.sell_untargeted_traded_coins,
            allow_skip_asset=self._copy_settings.allow_skip_asset,
            can_include_assets_in_open_orders_in_holdings_ratio=(
                self._copy_settings.can_include_assets_in_open_orders_in_holdings_ratio
            ),
        )

    def _create_rebalancer(
        self,
        planner: copy_rebalancing.BaseRebalanceActionsPlanner,
    ) -> copy_rebalancing.AbstractRebalancer:
        return self.get_rebalancer_class()(
            self._copier_exchange_interface,
            planner,
            {},
        )

    def _get_logger(self) -> logging.BotLogger:
        return logging.get_logger(self.__class__.__name__)
