import typing

import octobot_commons.logging as logging
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.errors as copy_errors
import octobot_copy.exchange as copy_exchange
import octobot_copy.rebalancing as copy_rebalancing

class AccountCopier:
    """
    Copies a reference spot-style account allocation onto the copier exchange by planning with
    RebalanceActionsPlanner and executing with an AbstractRebalancer.

    Target weights are derived from reference_account (quantity-proportional). Holdings ratios
    and order execution use the live portfolio behind exchange_interface. Callers must ensure
    traded pairs on the copier exchange cover the assets to trade.
    copier_account is reserved for future snapshot/offline use and is not used by the rebalance pipeline.
    copy_settings controls reference_market, rebalance thresholds, and synchronization.
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

    async def execute_rebalance_if_needed(self) -> list[octobot_trading.personal_data.Order]:
        rebalancer, should_rebalance, details = await self._prepare_rebalance_plan()
        if not should_rebalance:
            self._get_logger().info("No rebalance needed")
            return []
        try:
            self._get_logger().info(f"Executing rebalance on [{self._copier_exchange_interface.exchange_name}]")
            return await self._run_rebalance(rebalancer, details)
        except (trading_errors.MissingMinimalExchangeTradeVolume, copy_errors.RebalanceAborted) as err:
            self._get_logger().exception(
                err, True, f"Aborted rebalance on {self._copier_exchange_interface.exchange_name}: {err} ({err.__class__.__name__})"
            )
        finally:
            self._get_logger().info("Portfolio rebalance process complete")
        return []

    def get_rebalancer_class(self) -> type[copy_rebalancing.AbstractRebalancer]:
        raise NotImplementedError("get_rebalancer_class is not implemented")

    async def _prepare_rebalance_plan(
        self,
    ) -> tuple[copy_rebalancing.AbstractRebalancer, bool, dict]:
        rebalancing_client = self._create_rebalancing_client()
        planner = self._create_rebalance_actions_planner(rebalancing_client)
        self._sync_planner(planner)
        planner.update_distribution(adapt_to_holdings=False, force_latest=False)
        rebalancer = self._create_rebalancer(planner, rebalancing_client)
        for coin in planner.targeted_coins:
            await rebalancer.prepare_coin_rebalancing(coin)
        should_rebalance, details = planner.get_rebalance_details()
        return rebalancer, should_rebalance, details

    async def _run_rebalance(
        self,
        rebalancer: copy_rebalancing.AbstractRebalancer,
        details: dict,
    ) -> list[octobot_trading.personal_data.Order]:
        orders: list = []
        self._get_logger().info("Step 1/3: ensuring enough funds are available for rebalance")
        await rebalancer.ensure_enough_funds_to_buy_after_selling()
        is_simple_buy_without_selling = rebalancer.can_simply_buy_coins_without_selling(details)
        if is_simple_buy_without_selling:
            self._get_logger().info(f"Step 2/3: skipped: no coin to sell for {self._copy_settings.reference_market}")
        else:
            self._get_logger().info(f"Step 2/3: selling coins to free {self._copy_settings.reference_market}")
            orders += await rebalancer.sell_targeted_coins_for_reference_market(details, None)
        self._get_logger().info(f"Step 3/3: buying coins using {self._copy_settings.reference_market}")
        orders += await rebalancer.split_reference_market_into_targeted_coins(
            details,
            is_simple_buy_without_selling,
            None,
        )
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
            reference_market=self._copy_settings.reference_market,
            min_order_size_margin=self._copy_settings.min_order_size_margin,
            get_config=self._get_synthetic_config,
            get_previous_config=lambda: None, # not implemented for now
            get_historical_configs=lambda _ft, _tt: [], # not implemented for now
            get_ideal_distribution=self._get_ideal_distribution,
            get_allow_skip_asset=lambda: self._copy_settings.allow_skip_asset,
        )

    def _create_rebalance_actions_planner(
        self,
        rebalancing_client: copy_rebalancing.RebalancingClientInterface,
    ) -> copy_rebalancing.RebalanceActionsPlanner:
        return copy_rebalancing.RebalanceActionsPlanner(
            exchange=self._copier_exchange_interface,
            client=rebalancing_client,
            synchronization_policy=self._copy_settings.synchronization_policy,
            rebalance_trigger_min_ratio=self._copy_settings.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self._copy_settings.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self._copy_settings.reference_market_ratio,
            reference_market=self._copy_settings.reference_market,
            sell_untargeted_traded_coins=self._copy_settings.sell_untargeted_traded_coins,
        )

    def _sync_planner(self, planner: copy_rebalancing.RebalanceActionsPlanner) -> None:
        planner.update(
            synchronization_policy=self._copy_settings.synchronization_policy,
            rebalance_trigger_min_ratio=self._copy_settings.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self._copy_settings.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self._copy_settings.reference_market_ratio,
            reference_market=self._copy_settings.reference_market,
            sell_untargeted_traded_coins=self._copy_settings.sell_untargeted_traded_coins,
        )

    def _create_rebalancer(
        self,
        planner: copy_rebalancing.RebalanceActionsPlanner,
        rebalancing_client: copy_rebalancing.RebalancingClientInterface,
    ) -> copy_rebalancing.AbstractRebalancer:
        return self.get_rebalancer_class()(
            self._copier_exchange_interface,
            rebalancing_client,
            planner,
            {},
        )

    def _get_logger(self) -> logging.BotLogger:
        return logging.get_logger(self.__class__.__name__)
