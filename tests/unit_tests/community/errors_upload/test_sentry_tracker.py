#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import mock
import pytest

import octobot_commons.constants as commons_constants

import octobot.community.errors_upload.sentry_tracker as sentry_tracker
import octobot.constants as constants


@pytest.fixture(autouse=True)
def reset_sentry_tracker_state():
    sentry_tracker._sentry_initialized = False
    yield
    sentry_tracker._sentry_initialized = False


class TestInitSentryTracker:
    def test_initializes_when_error_dsn_set(self):
        with mock.patch.object(constants, "ERROR_TRACKER_DSN", "error-dsn"), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init") as init_mock:
            sentry_tracker.init_sentry_tracker()
        init_mock.assert_called_once()
        assert init_mock.call_args.kwargs["dsn"] == "error-dsn"
        assert init_mock.call_args.kwargs["before_send"] is sentry_tracker._before_send

    def test_skips_init_when_error_dsn_unset(self):
        with mock.patch.object(constants, "ERROR_TRACKER_DSN", None), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init") as init_mock:
            sentry_tracker.init_sentry_tracker()
        init_mock.assert_not_called()


class TestFlushTracker:
    def test_no_op_when_not_initialized(self):
        with mock.patch.object(sentry_tracker.sentry_sdk, "flush") as flush_mock:
            sentry_tracker.flush_tracker()
        flush_mock.assert_not_called()

    def test_flushes_when_initialized(self):
        with mock.patch.object(constants, "ERROR_TRACKER_DSN", "error-dsn"), \
                mock.patch.object(sentry_tracker.sentry_sdk, "init"), \
                mock.patch.object(sentry_tracker.sentry_sdk, "flush") as flush_mock, \
                mock.patch.object(sentry_tracker.time, "sleep"):
            sentry_tracker.init_sentry_tracker()
            sentry_tracker.flush_tracker()
        flush_mock.assert_called_once()


class TestBeforeSend:
    def test_drops_event_when_exception_desc_extra(self):
        event = {
            "extra": {commons_constants.IS_EXCEPTION_DESC: True},
            "logentry": {"message": "ignored"},
        }
        assert sentry_tracker._before_send(event, {}) is None

    def test_strips_self_hosted_log_prefix(self):
        event = {"logentry": {"message": "[self-hosted] something failed"}}
        with mock.patch.object(sentry_tracker, "_get_log_prefix", return_value="[self-hosted] "):
            result = sentry_tracker._before_send(event, {})
        assert result["logentry"]["message"] == "something failed"

    def test_strips_community_bot_log_prefix(self):
        event = {"logentry": {"message": "[bot-1] trade error"}}
        with mock.patch.object(sentry_tracker, "_get_log_prefix", return_value="[bot-1] "):
            result = sentry_tracker._before_send(event, {})
        assert result["logentry"]["message"] == "trade error"

    def test_returns_event_when_logentry_missing(self):
        event = {"extra": {}}
        assert sentry_tracker._before_send(event, {}) is event
