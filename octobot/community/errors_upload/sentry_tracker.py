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
import sentry_sdk

import octobot_commons.constants
import octobot_commons.logging

import octobot.constants


def init_sentry_tracker():
    """
    Will upload errors to octobot.constants.ERROR_TRACKER_DSN if its value is set
    """
    logger = octobot_commons.logging.get_logger("sentry_tracker")
    if not octobot.constants.ERROR_TRACKER_DSN:
        logger.debug(f"Error tracker disabled")
        return
    environment = "cloud" if octobot.constants.IS_CLOUD_ENV else "self hosted"
    app_name = f"{octobot.constants.PROJECT_NAME} open source"
    sentry_sdk.init(
        dsn=octobot.constants.ERROR_TRACKER_DSN,

        # Percent of error events to send to the server.
        # 0.5 would be 50%. Defaults to 1.0.
        sample_rate=1,

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=0,

        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        release=octobot.constants.LONG_VERSION,

        include_local_variables=False,   # careful not to upload sensitive data
        max_breadcrumbs=5,  # breadcrumbs from multiple tasks and activities are mixed, only take the last ones

        environment=environment,
        before_send=_before_send,
    )
    logger.info(
        f"Initialized error tracking with environment: {environment}, "
        f"release: {octobot.constants.LONG_VERSION}, dns: {octobot.constants.ERROR_TRACKER_DSN}"
    )
    sentry_sdk.set_context("app", {
        "app_start_time": str(round(time.time())),
        "app_name": app_name,
    })
    sentry_sdk.set_tag("app", app_name)
    if octobot.constants.COMMUNITY_BOT_ID:
        sentry_sdk.set_tag("bot_id", octobot.constants.COMMUNITY_BOT_ID)


def flush_tracker():
    if octobot.constants.ERROR_TRACKER_DSN:
        delay = 2
        octobot_commons.logging.get_logger("sentry_tracker").info(f"Flushing trackers: shutting down in {delay} seconds ...")
        sentry_sdk.flush()
        # let trackers upload errors
        time.sleep(delay)


def _get_log_prefix() -> str:
    return f"[{octobot.constants.COMMUNITY_BOT_ID}] " if octobot.constants.COMMUNITY_BOT_ID else "[self-hosted]"

def _before_send(event: dict, hint: dict):
    if event.get("extra", {}).get(octobot_commons.constants.IS_EXCEPTION_DESC, False):
        # error already sent with exception
        return

    # do not include log_prefix in log entry message
    try:
        message = event["logentry"]["message"]
        log_prefix = _get_log_prefix()
        if log_prefix and message.startswith(log_prefix):
            event["logentry"]["message"] = message[len(log_prefix):]
    except KeyError:
        pass

    return event
