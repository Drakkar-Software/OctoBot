import dataclasses
import typing
import decimal

import octobot_commons.constants as common_constants
import octobot_commons.dataclasses as commons_dataclasses
import octobot_trading.constants as trading_constants

import octobot_copy.enums as copy_enums
import octobot_copy.rebalancing.planner.distributions as planner_distributions
import octobot_copy.constants as copy_constants


@dataclasses.dataclass
class Account(commons_dataclasses.MinimizableDataclass):
    updated_at: float = 0
    # account portfolio: dict of assets with allocation_ratio, available and total amounts
    # the allocation_ratio key is used to compute the distribution allocation
    content: dict[str, dict[str, decimal.Decimal]] = dataclasses.field(default_factory=dict)
    # account enriched orders formatted as trading_storage.orders_storage._format_order
    orders: list[dict[str, typing.Any]] = dataclasses.field(default_factory=list)
    # account positions, dict keys: trading_enums.ExchangeConstantsPositionColumns
    positions: list[dict[str, typing.Any]] = dataclasses.field(default_factory=list)
    # list of historical snapshots of the account, sorted by updated_at (most recent first) 
    historical_snapshots: list["Account"] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.content = {
            asset: {
                key: decimal.Decimal(str(value)) for key, value in holdings.items()
            }
            for asset, holdings in self.content.items()
        }
        if self.historical_snapshots:
            if isinstance(self.historical_snapshots[0], dict):
                snapshots = [
                    Account.from_dict(snapshot) for snapshot in self.historical_snapshots
                ]
            else:
                snapshots = self.historical_snapshots
            self.historical_snapshots = sorted(
                snapshots, key=lambda x: x.updated_at, reverse=True
            )

    def create_assets_distribution(self) -> list[dict[str, typing.Any]]:
        amounts: list[tuple[str, decimal.Decimal]] = []
        for currency, holdings in self.content.items():
            allocation_ratio = holdings[copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO]
            if allocation_ratio > trading_constants.ZERO:
                amounts.append((currency, allocation_ratio))
        if not amounts:
            return []
        total = sum((allocation_ratio for _, allocation_ratio in amounts), trading_constants.ZERO)
        if total <= trading_constants.ZERO:
            return []
        distribution: list[dict[str, typing.Any]] = []
        for currency, allocation_ratio in amounts:
            percentage = float(
                round(
                    allocation_ratio / total * trading_constants.ONE_HUNDRED,
                    planner_distributions.MAX_DISTRIBUTION_AFTER_COMMA_DIGITS,
                )
            )
            if percentage:
                distribution.append(
                    {
                        copy_enums.DistributionKeys.NAME.value: currency,
                        copy_enums.DistributionKeys.VALUE.value: percentage,
                        copy_enums.DistributionKeys.PRICE.value: None,
                    }
                )
        return distribution
