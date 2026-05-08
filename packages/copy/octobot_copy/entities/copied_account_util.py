import typing
import decimal

import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants

import octobot_copy.enums as copy_enums
import octobot_copy.rebalancing.planner.distributions as planner_distributions


def copied_asset_ratio_by_name(
    copied_account: protocol_models.CopiedAccount,
) -> dict[str, decimal.Decimal]:
    return {
        asset.name: decimal.Decimal(str(asset.ratio))
        for asset in (copied_account.copied_assets or [])
    }


def copied_asset_total_by_name(
    copied_account: protocol_models.CopiedAccount,
) -> dict[str, decimal.Decimal]:
    return {
        asset.name: decimal.Decimal(str(asset.total))
        for asset in (copied_account.copied_assets or [])
    }


def sort_historical_snapshots(
    copied_account: protocol_models.CopiedAccount,
) -> None:
    if copied_account.historical_snapshots:
        copied_account.historical_snapshots = sorted(
            copied_account.historical_snapshots,
            key=lambda x: x.updated_at,
            reverse=True,
        )

def create_assets_distribution(
    copied_account: protocol_models.CopiedAccount,
) -> list[dict[str, typing.Any]]:
    amounts: list[tuple[str, decimal.Decimal]] = []
    for asset in (copied_account.copied_assets or []):
        allocation_ratio = decimal.Decimal(str(asset.ratio))
        if allocation_ratio > trading_constants.ZERO:
            amounts.append((asset.name, allocation_ratio))
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