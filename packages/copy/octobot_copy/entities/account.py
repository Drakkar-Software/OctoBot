import dataclasses
import typing
import decimal

import octobot_commons.constants as common_constants
import octobot_trading.constants as trading_constants

import octobot_copy.enums as copy_enums
import octobot_copy.rebalancing.planner.distributions as planner_distributions


@dataclasses.dataclass
class Account:
    # account portfolio: dict of assets with available and total amounts
    content: dict[str, dict[str, decimal.Decimal]] = dataclasses.field(default_factory=dict)
    # account orders, dict keys: trading_enums.ExchangeConstantsOrderColumns
    orders: list[dict[str, typing.Any]] = dataclasses.field(default_factory=list)
    # account positions, dict keys: trading_enums.ExchangeConstantsPositionColumns
    positions: list[dict[str, typing.Any]] = dataclasses.field(default_factory=list)

    def create_assets_distribution(self) -> list[dict[str, typing.Any]]:
        amounts: list[tuple[str, decimal.Decimal]] = []
        for currency, holdings in self.content.items():
            quantity = holdings[common_constants.PORTFOLIO_TOTAL]
            if quantity > trading_constants.ZERO:
                amounts.append((currency, quantity))
        if not amounts:
            return []
        total = sum((quantity for _, quantity in amounts), trading_constants.ZERO)
        if total <= trading_constants.ZERO:
            return []
        distribution: list[dict[str, typing.Any]] = []
        for currency, quantity in amounts:
            percentage = float(
                round(
                    quantity / total * trading_constants.ONE_HUNDRED,
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
