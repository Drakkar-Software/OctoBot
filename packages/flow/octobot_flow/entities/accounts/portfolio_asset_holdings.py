import dataclasses
import typing
import decimal

import octobot_commons.dataclasses
import octobot_commons.constants
import octobot_trading.constants

@dataclasses.dataclass
class PortfolioAssetHolding(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    available: float
    total: float
    value: float = 0
    unlocked_available: typing.Optional[float] = None
    unlocked_total: typing.Optional[float] = None
    unlocked_value: typing.Optional[float] = None

    def to_portfolio_asset_dict(self, zeroize_negative_values: bool) -> dict[str, decimal.Decimal]:
        formatted = {
            octobot_commons.constants.PORTFOLIO_AVAILABLE: decimal.Decimal(str(self.available)),
            octobot_commons.constants.PORTFOLIO_TOTAL: decimal.Decimal(str(self.total)),
        }
        if zeroize_negative_values:
            if formatted[octobot_commons.constants.PORTFOLIO_TOTAL] < octobot_trading.constants.ZERO:
                # total can't be negative
                formatted[octobot_commons.constants.PORTFOLIO_TOTAL] = octobot_trading.constants.ZERO
            if formatted[octobot_commons.constants.PORTFOLIO_AVAILABLE] > formatted[octobot_commons.constants.PORTFOLIO_TOTAL]:
                # available can't be greater than total
                formatted[octobot_commons.constants.PORTFOLIO_AVAILABLE] = formatted[octobot_commons.constants.PORTFOLIO_TOTAL]
        return formatted
