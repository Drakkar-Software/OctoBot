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
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.metric_definitions as metric_definitions
import octobot.community.activity_analysis.metrics_config as metrics_config
import octobot.community.activity_analysis.metrics_debug as metrics_debug
import octobot.community.errors_upload.sentry_tracker as sentry_tracker


def init_tracker(metrics_enabled: bool) -> None:
    sentry_tracker.init_sentry_tracker(metrics_enabled=metrics_enabled)


def activity_tracking_is_active() -> bool:
    return sentry_tracker.activity_tracking_is_active()


def update_tracker_bot_id(bot_id: str) -> None:
    sentry_tracker.update_tracker_bot_id(bot_id)


def emit_count(
    config: configuration.Configuration,
    attributes: metric_definitions.MetricAttributes,
) -> None:
    if not metrics_config.metrics_enabled(config):
        metrics_debug.log_activity(
            "emit_count_skipped",
            event=attributes.event.value,
            reason="metrics_disabled",
        )
        return
    metrics_debug.log_activity(
        "emit_count",
        event=attributes.event.value,
        attributes=attributes.to_sentry_dict(sentry_tracker.get_tracker_bot_id()),
    )
    sentry_tracker.track_usage_count(attributes)


def emit_onboarding_duration_gauge(
    config: configuration.Configuration,
    seconds: float,
    attributes: metric_definitions.MetricAttributes,
) -> None:
    if not metrics_config.metrics_enabled(config):
        metrics_debug.log_activity(
            "emit_gauge_skipped",
            event=attributes.event.value,
            reason="metrics_disabled",
            seconds=seconds,
        )
        return
    metrics_debug.log_activity(
        "emit_gauge",
        event=attributes.event.value,
        seconds=seconds,
        attributes=attributes.to_sentry_dict(sentry_tracker.get_tracker_bot_id()),
    )
    sentry_tracker.track_onboarding_duration_gauge(seconds, attributes)
