from unittest import mock

from octobot.community.wallet_backend import setup_timing


def test_get_wallet_setup_succeeded_timestamp_returns_earliest():
    events = [
        mock.MagicMock(event="wallet_setup_succeeded", timestamp=2000.0),
        mock.MagicMock(event="wallet_setup_attempt", timestamp=1000.0),
        mock.MagicMock(event="wallet_setup_succeeded", timestamp=1500.0),
    ]
    with mock.patch(
        "octobot.community.wallet_backend.setup_timing.node_journal.read_events",
        return_value=events,
    ):
        assert setup_timing.get_wallet_setup_succeeded_timestamp() == 1500.0


def test_get_wallet_setup_succeeded_timestamp_returns_none_when_missing():
    with mock.patch(
        "octobot.community.wallet_backend.setup_timing.node_journal.read_events",
        return_value=[],
    ):
        assert setup_timing.get_wallet_setup_succeeded_timestamp() is None
