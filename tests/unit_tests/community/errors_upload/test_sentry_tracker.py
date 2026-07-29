#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import mock
import pytest

import octobot.community.errors_upload.sentry_tracker as sentry_tracker
import octobot.constants as constants


@pytest.fixture(autouse=True)
def reset_sentry_tracker_state():
    sentry_tracker._activity_tracking_active = False
    sentry_tracker._sentry_initialized = False
    sentry_tracker._tracker_bot_id_set = False
    yield
    sentry_tracker._activity_tracking_active = False
    sentry_tracker._sentry_initialized = False
    sentry_tracker._tracker_bot_id_set = False


class TestInitSentryTracker:
    def test_uses_activity_dsn_when_metrics_enabled(self):
        with mock.patch.object(constants, "ACTIVITY_TRACKER_DSN", "activity-dsn"), \
                mock.patch.object(constants, "ERROR_TRACKER_DSN", "error-dsn"), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init") as init_mock:
            sentry_tracker.init_sentry_tracker(metrics_enabled=True)
        init_mock.assert_called_once()
        assert init_mock.call_args.kwargs["dsn"] == "activity-dsn"
        assert init_mock.call_args.kwargs["default_integrations"] is False
        assert sentry_tracker.activity_tracking_is_active() is True

    def test_uses_error_dsn_when_activity_unavailable(self):
        with mock.patch.object(constants, "ACTIVITY_TRACKER_DSN", None), \
                mock.patch.object(constants, "ERROR_TRACKER_DSN", "error-dsn"), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init") as init_mock:
            sentry_tracker.init_sentry_tracker(metrics_enabled=True)
        assert init_mock.call_args.kwargs["dsn"] == "error-dsn"
        assert "before_send" in init_mock.call_args.kwargs
        assert sentry_tracker.activity_tracking_is_active() is False

    def test_skips_init_when_no_dsn(self):
        with mock.patch.object(constants, "ACTIVITY_TRACKER_DSN", None), \
                mock.patch.object(constants, "ERROR_TRACKER_DSN", None), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init") as init_mock:
            sentry_tracker.init_sentry_tracker(metrics_enabled=True)
        init_mock.assert_not_called()


class TestTrackUsageEvent:
    def test_emits_metric(self):
        with mock.patch.object(sentry_tracker.sentry_sdk.metrics, "count") as count_mock:
            sentry_tracker.track_usage_event("node_first_start", distribution="node")
        count_mock.assert_called_once_with(
            "octobot.usage",
            1,
            attributes={"event": "node_first_start", "distribution": "node"},
        )


class TestUpdateTrackerBotId:
    def test_sets_user_and_tag(self):
        with mock.patch.object(sentry_tracker.sentry_sdk, "set_user") as set_user_mock, \
                mock.patch.object(sentry_tracker.sentry_sdk, "set_tag") as set_tag_mock:
            sentry_tracker.update_tracker_bot_id("bot-id")
        set_user_mock.assert_called_once_with({"id": "bot-id"})
        set_tag_mock.assert_called_once_with("bot_id", "bot-id")
        assert sentry_tracker.has_tracker_bot_id() is True


class TestHasTrackerBotId:
    def test_false_when_not_set(self):
        assert sentry_tracker.has_tracker_bot_id() is False

    def test_true_after_update(self):
        sentry_tracker.update_tracker_bot_id("bot-id")
        assert sentry_tracker.has_tracker_bot_id() is True
