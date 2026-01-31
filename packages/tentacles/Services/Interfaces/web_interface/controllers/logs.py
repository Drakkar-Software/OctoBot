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
import flask
import os

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_tentacles_manager.constants as tentacles_manager_constants
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util


def register(blueprint):
    @blueprint.route("/logs")
    @login.login_required_when_activated
    def logs():
        web_interface.flush_errors_count()
        return flask.render_template("logs.html",
                                     logs=web_interface.get_logs(),
                                     notifications=web_interface.get_notifications_history())
    
    
    @blueprint.route("/export_logs")
    @login.login_required_when_activated
    def export_logs():
        # use user folder as the bot always has the right to use it, on failure, try in tentacles folder
        for candidate_path in (commons_constants.USER_FOLDER, tentacles_manager_constants.TENTACLES_PATH):
            temp_file = os.path.abspath(os.path.join(os.getcwd(), candidate_path, "exported_logs"))
            temp_file_with_ext = f"{temp_file}.{models.LOG_EXPORT_FORMAT}"
            try:
                if os.path.isdir(temp_file_with_ext):
                    raise RuntimeError(f"To be able to export logs, please remove or rename the {temp_file_with_ext} directory")
                elif os.path.isfile(temp_file_with_ext):
                    os.remove(temp_file_with_ext)
                file_path = models.export_logs(temp_file)
                return flask_util.send_and_remove_file(file_path, "logs_export.zip")
            except Exception as err:
                logging.get_logger("export_logs").exception(err, True, f"Unexpected error when exporting logs: {err}")
                error = err
        flask.flash(f"Error when exporting logs: {error}.", "danger")
        return flask.redirect(flask.url_for("logs"))
