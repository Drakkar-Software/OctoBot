#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import typing

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models

import octobot_flow.entities


def build_updated_account(
    account: protocol_models.Account,
    assets: list[protocol_models.DetailedAssetsForTradingType],
) -> protocol_models.Account:
    account_updates: dict[str, typing.Any] = {
        "updated_at": timestamp_util.utc_now_datetime(),
    }
    if assets:
        account_updates["assets"] = assets
    return account.model_copy(update=account_updates)


def build_global_view_account_refresh_result(
    user_id: str,
    context: octobot_flow.entities.GlobalViewAccountContext,
    exchange_refresh_result: octobot_flow.entities.ExchangeAccountRefreshResult,
) -> octobot_flow.entities.GlobalViewAccountRefreshResult:
    updated_account = build_updated_account(context.account, exchange_refresh_result.assets)
    return octobot_flow.entities.GlobalViewAccountRefreshResult(
        updated_account=updated_account,
        changed_order_ids=exchange_refresh_result.changed_order_ids,
        open_orders=exchange_refresh_result.open_orders,
        trades=exchange_refresh_result.trades,
        positions=exchange_refresh_result.positions,
    )
