#  Drakkar-Software OctoBot-Trading
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
import copy
import dataclasses
import decimal
import typing

import octobot_commons.logging as commons_logging
import octobot_commons.constants as commons_constants
import octobot_trading.personal_data as personal_data
import octobot_trading.constants as constants


@dataclasses.dataclass
class SubPortfolioData:
    bot_id: typing.Optional[str]
    portfolio_id: typing.Optional[str]
    priority_key: float
    content: dict[str, dict[str, decimal.Decimal]]  # current content of the sub-portfolio
    unit: typing.Optional[str]
    allowed_filling_assets: list[str] = dataclasses.field(default_factory=list) # assets to use to fill missing funds
    forbidden_filling_assets: list[str] = dataclasses.field(default_factory=list) # assets NOT to use to fill missing funds
    # deltas to be applied on top of the current content of the sub-portfolio from get_content_after_deltas()
    funds_deltas: dict[str, dict[str, decimal.Decimal]] = dataclasses.field(default_factory=dict)
    # funds that are missing from this portfolio. Populated after portfolio has been resolved
    missing_funds: dict[str, decimal.Decimal] = dataclasses.field(default_factory=dict)
    # funds that are locked (maybe in orders) from this portfolio
    locked_funds_by_asset: dict[str, decimal.Decimal] = dataclasses.field(default_factory=dict)


    def get_content_after_deltas(self) -> dict[str, dict[str, decimal.Decimal]]:
        """
        Computes the updated portfolio from delta available and total
        """
        updated_content = copy.deepcopy(self.content)
        for asset, delta_values in self.funds_deltas.items():
            if asset in updated_content:
                updated_content[asset][commons_constants.PORTFOLIO_TOTAL] += (
                    delta_values[commons_constants.PORTFOLIO_TOTAL]
                )
                updated_content[asset][commons_constants.PORTFOLIO_AVAILABLE] += (
                    delta_values[commons_constants.PORTFOLIO_AVAILABLE]
                )
            else:
                updated_content[asset] = {
                    commons_constants.PORTFOLIO_TOTAL: delta_values[commons_constants.PORTFOLIO_TOTAL],
                    commons_constants.PORTFOLIO_AVAILABLE: delta_values[commons_constants.PORTFOLIO_AVAILABLE],
                }
            for key in (commons_constants.PORTFOLIO_TOTAL, commons_constants.PORTFOLIO_AVAILABLE):
                if updated_content[asset][key] < constants.ZERO:
                    commons_logging.get_logger(__name__).warning(
                        f"{asset} portfolio {key} value: {updated_content[asset][key]} is < 0. Replacing with zero."
                    )
                    updated_content[asset][key] = constants.ZERO
        return updated_content

    def get_content_from_total_deltas_and_locked_funds(self) -> dict[str, dict[str, decimal.Decimal]]:
        """
        Only uses PORTFOLIO_TOTAL deltas and computes available values from locked_funds_by_asset
        """
        return get_content_with_available_after_deltas(
            self.content, self.funds_deltas, self.locked_funds_by_asset
        )

    def is_similar_to(self, other) -> bool:
        return (
            other
            and personal_data.filter_empty_values(self.content) == personal_data.filter_empty_values(other.content)
        )


def get_content_with_available_after_deltas(
    content: dict[str, dict[str, decimal.Decimal]], 
    deltas: dict[str, dict[str, decimal.Decimal]],
    locked_funds_by_asset: typing.Optional[dict[str, decimal.Decimal]] = None,
) -> dict[str, dict[str, decimal.Decimal]]:
    updated_content = get_content_after_deltas(content, deltas, apply_available_deltas=False)
    update_available_considering_locked_funds(updated_content, locked_funds_by_asset)
    return updated_content


def get_content_after_deltas(
    content: dict[str, dict[str, decimal.Decimal]], deltas: dict[str, dict[str, decimal.Decimal]], apply_available_deltas: bool = False
) -> dict[str, dict[str, decimal.Decimal]]:
    updated_content = copy.deepcopy(content)
    for asset, delta_values in deltas.items():
        if asset in updated_content:
            updated_content[asset][commons_constants.PORTFOLIO_TOTAL] += (
                delta_values[commons_constants.PORTFOLIO_TOTAL]
            )
            if apply_available_deltas:
                updated_content[asset][commons_constants.PORTFOLIO_AVAILABLE] += (
                    delta_values[commons_constants.PORTFOLIO_AVAILABLE]
                )
        else:
            updated_content[asset] = {
                commons_constants.PORTFOLIO_TOTAL: delta_values[commons_constants.PORTFOLIO_TOTAL]
            }
            if apply_available_deltas:
                updated_content[asset][commons_constants.PORTFOLIO_AVAILABLE] = (
                    delta_values[commons_constants.PORTFOLIO_AVAILABLE]
                )
    return updated_content


def update_available_considering_locked_funds(
    content: typing.Optional[dict[str, dict[str, decimal.Decimal]]],
    locked_funds_by_asset: typing.Optional[dict[str, decimal.Decimal]] = None,
) -> None:
    locked_funds_by_asset = locked_funds_by_asset or {}
    for asset, values in content.items():
        locked_funds = locked_funds_by_asset.get(asset, constants.ZERO)
        if locked_funds == constants.ZERO:
            values[commons_constants.PORTFOLIO_AVAILABLE] = values[commons_constants.PORTFOLIO_TOTAL]
        else:
            if locked_funds > values[commons_constants.PORTFOLIO_TOTAL]:
                delta = locked_funds - values[commons_constants.PORTFOLIO_TOTAL]
                error_details = (
                    f"{asset} available funds after applying {locked_funds} "
                    f"locked funds to total holdings of {values[commons_constants.PORTFOLIO_TOTAL]} (delta={delta * decimal.Decimal('-1')}). "
                    f"Available value will be set to 0."
                )
                if delta < values[commons_constants.PORTFOLIO_TOTAL] * decimal.Decimal("0.05"):
                    # delta < 5% of total: log warning: this is likely due to locked funds for open order fees, just warn
                    commons_logging.get_logger(__name__).warning(f"Tiny negative {error_details}")
                else:
                    # large negative: this should not happen,log error
                    commons_logging.get_logger(__name__).error(f"Unexpected: large negative {error_details}")
            values[commons_constants.PORTFOLIO_AVAILABLE] = values[commons_constants.PORTFOLIO_TOTAL] - locked_funds
