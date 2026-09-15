#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import datetime

import octobot_flow.constants as flow_constants
import octobot_protocol.models as protocol_models


def merge_snapshot(
    existing_values: list[protocol_models.PortfolioHistoricalValue],
    new_snapshot: protocol_models.PortfolioHistoricalValue,
    evaluation_time: datetime.datetime,
) -> list[protocol_models.PortfolioHistoricalValue]:
    """
    Keep 12h-spaced snapshots plus a always-updated latest entry.
    Persisted shape: twelve_hour_snapshots + [latest].
    """
    if not existing_values:
        return [new_snapshot]

    twelve_hour_snapshots = (
        [existing_values[0]]
        if len(existing_values) == 1
        else list(existing_values[:-1])
    )
    interval_seconds = flow_constants.PORTFOLIO_HISTORY_SNAPSHOT_INTERVAL_SECONDS
    last_twelve_hour_snapshot = twelve_hour_snapshots[-1]
    elapsed_since_last_twelve_hour_snapshot = (
        evaluation_time - last_twelve_hour_snapshot.timestamp
    ).total_seconds()
    if elapsed_since_last_twelve_hour_snapshot >= interval_seconds:
        twelve_hour_snapshots.append(new_snapshot)
    return twelve_hour_snapshots + [new_snapshot]
