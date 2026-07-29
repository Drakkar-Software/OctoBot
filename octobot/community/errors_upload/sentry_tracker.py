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
import time
import typing

import sentry_sdk

import octobot_commons.constants
import octobot_commons.logging

import octobot.constants


_sentry_initialized = False
_activity_tracking_active = False
_tracker_bot_id_set: bool = False


def init_sentry_tracker(metrics_enabled: bool) -> None:
    """
    Initialize Sentry when ACTIVITY_TRACKER_DSN (metrics enabled) or ERROR_TRACKER_DSN is set.
    Tracker DSN takes priority when metrics are enabled.
    """
    global _activity_tracking_active, _sentry_initialized
    logger = octobot_commons.logging.get_logger("sentry_tracker")

    activity_dsn = octobot.constants.ACTIVITY_TRACKER_DSN
    error_dsn = octobot.constants.ERROR_TRACKER_DSN
    use_activity_dsn = bool(activity_dsn and metrics_enabled)
    active_dsn = activity_dsn if use_activity_dsn else error_dsn

    if not active_dsn:
        logger.debug("Sentry tracker disabled: no applicable DSN")
        _activity_tracking_active = False
        _sentry_initialized = False
        return

    if _sentry_initialized:
        _activity_tracking_active = use_activity_dsn
        return

    environment = "cloud" if octobot.constants.IS_CLOUD_ENV else "self hosted"
    app_name = f"{octobot.constants.PROJECT_NAME} open source"
    init_kwargs: dict[str, typing.Any] = {
        "dsn": active_dsn,
        # Percent of error events to send to the server.
        # 0.5 would be 50%. Defaults to 1.0.
        "sample_rate": 1,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        "traces_sample_rate": 0,
        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        "release": octobot.constants.LONG_VERSION,
        "include_local_variables": False,  # careful not to upload sensitive data
        # breadcrumbs from multiple tasks and activities are mixed, only take the last ones
        "max_breadcrumbs": 5,
        "environment": environment,
    }
    if use_activity_dsn:
        init_kwargs["sample_rate"] = 0
        # Activity-only: no default integrations (especially LoggingIntegration).
        # Only explicit track_usage_event calls send data.
        init_kwargs["default_integrations"] = False
        init_kwargs["integrations"] = []
    else:
        # Error DSN: auto-capture log errors; strip bot log prefix before upload.
        init_kwargs["before_send"] = _before_send

    sentry_sdk.init(**init_kwargs)
    _activity_tracking_active = use_activity_dsn
    _sentry_initialized = True

    mode = "activity" if use_activity_dsn else "error"
    logger.info(
        f"Initialized {mode} tracking with environment: {environment}, "
        f"release: {octobot.constants.LONG_VERSION}, dsn: {active_dsn}"
    )
    sentry_sdk.set_context("app", {
        "app_start_time": str(round(time.time())),
        "app_name": app_name,
    })
    sentry_sdk.set_tag("app", app_name)


def flush_tracker() -> None:
    if not _sentry_initialized:
        return
    delay = 2
    octobot_commons.logging.get_logger("sentry_tracker").info(
        f"Flushing trackers: shutting down in {delay} seconds ..."
    )
    sentry_sdk.flush()
    time.sleep(delay)


def activity_tracking_is_active() -> bool:
    return _activity_tracking_active


def has_tracker_bot_id() -> bool:
    return _tracker_bot_id_set


def update_tracker_bot_id(bot_id: str) -> None:
    global _tracker_bot_id_set
    _tracker_bot_id_set = True
    sentry_sdk.set_user({"id": bot_id})
    sentry_sdk.set_tag("bot_id", bot_id)


def track_usage_event(event_name: str, **attributes: typing.Any) -> None:
    metric_attributes = {"event": event_name}
    for attribute_key, attribute_value in attributes.items():
        if attribute_value is not None:
            metric_attributes[attribute_key] = str(attribute_value)
    sentry_sdk.metrics.count("octobot.usage", 1, attributes=metric_attributes)
    octobot_commons.logging.get_logger("sentry_tracker").debug(
        "Tracked usage event %s with attributes %s",
        event_name,
        metric_attributes,
    )


def _get_log_prefix() -> str:
    return f"[{octobot.constants.COMMUNITY_BOT_ID}] " if octobot.constants.COMMUNITY_BOT_ID else "[self-hosted]"


def _before_send(event: dict, hint: dict):
    if event.get("extra", {}).get(octobot_commons.constants.IS_EXCEPTION_DESC, False):
        return

    try:
        message = event["logentry"]["message"]
        log_prefix = _get_log_prefix()
        if log_prefix and message.startswith(log_prefix):
            event["logentry"]["message"] = message[len(log_prefix):]
    except KeyError:
        pass

    return event
