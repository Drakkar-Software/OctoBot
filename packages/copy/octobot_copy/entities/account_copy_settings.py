import dataclasses
import decimal

import octobot_commons.dataclasses as commons_dataclasses
import octobot_copy.enums as copy_enums


@dataclasses.dataclass
class AccountCopySettings(commons_dataclasses.MinimizableDataclass):
    synchronization_policy: copy_enums.SynchronizationPolicy = (
        copy_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    )
    # Minimum ratio of the portfolio that must be rebalanced to trigger a rebalance
    rebalance_trigger_min_ratio: decimal.Decimal = decimal.Decimal("0.05") # 5%
    # Minimum ratio of quote(ref market) in portfolio to trigger a rebalance
    quote_asset_rebalance_ratio_threshold: decimal.Decimal = decimal.Decimal("0.1") # 10%
    # Percentage of the portfolio to trade (distributed among targeted coins).
    reference_market_ratio: decimal.Decimal = decimal.Decimal("1") # 100%
     # When True, coins in portfolio that are not in targeted coins will be sold to free up funds for the rebalance.
    sell_untargeted_traded_coins: bool = True
    # Min order size safety factor: ideal amount must be at least this multiple of the exchange min cost
    min_order_size_margin: decimal.Decimal = decimal.Decimal("2")
    # Allow skipping assets that don't meet minimum order size requirements instead of aborting portfolio rebalancing
    allow_skip_asset: bool = False


    def __post_init__(self):
        if self.synchronization_policy:
            self.synchronization_policy = copy_enums.SynchronizationPolicy(self.synchronization_policy)
        if self.rebalance_trigger_min_ratio:
            self.rebalance_trigger_min_ratio = decimal.Decimal(str(self.rebalance_trigger_min_ratio))
        if self.quote_asset_rebalance_ratio_threshold:
            self.quote_asset_rebalance_ratio_threshold = decimal.Decimal(str(self.quote_asset_rebalance_ratio_threshold))
        if self.reference_market_ratio:
            self.reference_market_ratio = decimal.Decimal(str(self.reference_market_ratio))
        if self.min_order_size_margin:
            self.min_order_size_margin = decimal.Decimal(str(self.min_order_size_margin))
