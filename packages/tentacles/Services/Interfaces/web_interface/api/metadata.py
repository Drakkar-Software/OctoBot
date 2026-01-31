#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import json
import flask_cors
import cachetools

import octobot.api as octobot_api
import octobot.constants as constants
import octobot_services.interfaces as interfaces
import octobot_commons.constants
import octobot_commons.timestamp_util as timestamp_util


def register(blueprint):
    _LATEST_VERSION_CACHE = cachetools.TTLCache(
        maxsize=1, ttl=octobot_commons.constants.DAYS_TO_SECONDS
    )

    @blueprint.route("/ping")
    @flask_cors.cross_origin()
    def ping():
        start_time = interfaces.get_bot_api().get_start_time()
        return json.dumps(
            f"Running since "
            f"{timestamp_util.convert_timestamp_to_datetime(start_time, '%Y-%m-%d %H:%M:%S', local_timezone=True)}."
        )


    @blueprint.route("/version")
    def version():
        return json.dumps(f"{interfaces.AbstractInterface.project_name} {interfaces.AbstractInterface.project_version}")


    @blueprint.route("/upgrade_version")
    def upgrade_version():
        async def fetch_upgrade_version():
            updater = octobot_api.get_updater()
            return await updater.get_latest_version() if updater and await updater.should_be_updated() else None

        # avoid fetching upgrade version if already fetched in the last day
        try:
            version = _LATEST_VERSION_CACHE["version"]
        except KeyError:
            version = interfaces.run_in_bot_main_loop(fetch_upgrade_version(), timeout=5)
            _LATEST_VERSION_CACHE["version"] = version

        return json.dumps(version)


    @blueprint.route("/user_feedback")
    def user_feedback():
        return json.dumps(constants.OCTOBOT_FEEDBACK_FORM_URL)


    @blueprint.route("/announcements")
    def announcements():
        return ""
        # return json.dumps("external_resources_manager.get_external_resource(
        #     service_constants.EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS,
        #     catch_exception=True)")
