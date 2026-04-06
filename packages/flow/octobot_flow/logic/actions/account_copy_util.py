import decimal
import typing

import octobot_commons.constants as common_constants
import octobot_commons.symbols as symbol_util
import octobot_commons.logging as logging

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities

import octobot_flow.constants as flow_constants
import octobot_flow.entities



def reference_exchange_elements_to_account(
    elements: octobot_flow.entities.ReferenceExchangeAccountElements,
    fetched_exchange_data: octobot_flow.entities.FetchedExchangeData,
    reference_market: str,
) -> copy_entities.Account:
    content: dict[str, dict[str, decimal.Decimal]] = {}
    value_by_asset = {}
    for asset, values in elements.portfolio.content.items():
        content[asset] = {
            key: decimal.Decimal(str(amount)) for key, amount in values.items()
        }
        if asset == reference_market:
            value_by_asset[asset] = decimal.Decimal(str(values[common_constants.PORTFOLIO_TOTAL]))
        else:
            try:
                if price := fetched_exchange_data.get_last_price(
                    symbol_util.merge_currencies(asset, reference_market)
                ):
                    value_by_asset[asset] = decimal.Decimal(str(values[common_constants.PORTFOLIO_TOTAL])) * price
                else:
                    logging.get_logger("account_copy_util").error(
                        f"No ticker price found for {symbol_util.merge_currencies(asset, reference_market)}. "
                        f"Portfolio ratios will be inaccurate."
                    )
            except KeyError as err:
                logging.get_logger("account_copy_util").error(
                    f"Impossible to evaluate {symbol_util.merge_currencies(asset, reference_market)} price: "
                    f"no fetched ticker price ({err})"
                )
    total_value = sum(value_by_asset.values())
    for asset, values in elements.portfolio.content.items():
        content[asset][copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO] = value_by_asset[asset] / total_value
    return copy_entities.Account(content=content, orders=elements.orders.open_orders)


def create_account_copy_settings(
    automation: octobot_flow.entities.AutomationDetails,
) -> copy_entities.AccountCopySettings:
    grace_seconds = flow_constants.DEFAULT_COPY_TRADING_ORPHAN_CANCEL_GRACE_SECONDS
    threshold = flow_constants.DEFAULT_COPY_TRADING_ORPHAN_GRACE_ABORT_THRESHOLD
    copy_details = automation.execution.copy_details
    return copy_entities.AccountCopySettings(
        mirrored_orphan_cancel_grace_seconds=grace_seconds,
        mirrored_orphan_grace_abort_threshold=threshold,
        mirrored_orphan_grace_pair_ratio_max_delta=(
            flow_constants.DEFAULT_COPY_TRADING_ORPHAN_GRACE_PAIR_RATIO_MAX_DELTA
        ),
        mirrored_orphan_grace_started_at=copy_details.open_orders_grace_period_started_at,
    )
