#  Drakkar-Software OctoBot-Flow

import datetime

import octobot_flow.constants as flow_constants
import octobot_flow.logic.accounts.portfolio_history as portfolio_history_module
import octobot_protocol.models as protocol_models


def _snapshot(timestamp: datetime.datetime, total: float) -> protocol_models.PortfolioHistoricalValue:
    return protocol_models.PortfolioHistoricalValue(
        timestamp=timestamp,
        total=total,
    )


class TestMergeSnapshotLatest:
    def test_every_call_replaces_latest_entry(self):
        first_time = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
        second_time = datetime.datetime(2026, 1, 1, 12, 5, tzinfo=datetime.UTC)
        merged_values = portfolio_history_module.merge_snapshot(
            [_snapshot(first_time, 100.0)],
            _snapshot(second_time, 110.0),
            second_time,
        )
        assert len(merged_values) == 2
        assert merged_values[-1].total == 110.0
        assert merged_values[0].total == 100.0


class TestMergeSnapshot12hCadence:
    def test_refresh_within_12h_does_not_add_second_twelve_hour_entry(self):
        first_time = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
        second_time = datetime.datetime(2026, 1, 1, 15, 0, tzinfo=datetime.UTC)
        merged_values = portfolio_history_module.merge_snapshot(
            [_snapshot(first_time, 100.0)],
            _snapshot(second_time, 105.0),
            second_time,
        )
        assert len(merged_values) == 2
        assert merged_values[0].timestamp == first_time
        assert merged_values[-1].timestamp == second_time


class TestMergeSnapshot12hElapsed:
    def test_appends_new_twelve_hour_snapshot_after_interval(self):
        first_time = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
        second_time = first_time + datetime.timedelta(
            seconds=flow_constants.PORTFOLIO_HISTORY_SNAPSHOT_INTERVAL_SECONDS
        )
        merged_values = portfolio_history_module.merge_snapshot(
            [_snapshot(first_time, 100.0)],
            _snapshot(second_time, 120.0),
            second_time,
        )
        assert len(merged_values) == 3
        assert merged_values[0].timestamp == first_time
        assert merged_values[1].timestamp == second_time
        assert merged_values[-1].timestamp == second_time


class TestMergeSnapshotUnit:
    def test_unit_preserved_by_caller_not_merge_snapshot(self):
        evaluation_time = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
        merged_values = portfolio_history_module.merge_snapshot(
            [],
            _snapshot(evaluation_time, 50.0),
            evaluation_time,
        )
        assert merged_values[0].total == 50.0
