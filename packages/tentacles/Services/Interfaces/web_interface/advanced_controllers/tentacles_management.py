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

import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.models as models
import octobot_commons.authentication as authentication
import octobot.constants as constants


def register(blueprint):
    @blueprint.route("/tentacles")
    @login.active_login_required
    def tentacles():
        return flask.render_template("advanced_tentacles.html",
                                     tentacles=models.get_tentacles())
    
    
    def _handle_package_operation(update_type):
        if update_type == "add_package":
            request_data = flask.request.get_json()
            success = False
            if request_data:
                version = None
                url_key = "url"
                if url_key in request_data:
                    path_or_url = request_data[url_key]
                    version = request_data.get("version", None)
                    action = "register_and_install"
                else:
                    path_or_url, action = next(iter(request_data.items()))
                    path_or_url = path_or_url.strip()
                if action == "register_and_install":
                    installation_result = models.install_packages(
                        path_or_url,
                        version,
                        authenticator=authentication.Authenticator.instance())
                    if installation_result:
                        return util.get_rest_reply(flask.jsonify(installation_result))
                    else:
                        return util.get_rest_reply('Impossible to install the given tentacles package. '
                                                   'Please see logs for more details.', 500)
    
            if not success:
                return util.get_rest_reply('{"operation": "ko"}', 500)
        elif update_type in ["install_packages", "update_packages", "reset_packages"]:
    
            packages_operation_result = {}
            if update_type == "install_packages":
                packages_operation_result = models.install_packages()
            elif update_type == "update_packages":
                packages_operation_result = models.update_packages()
            elif update_type == "reset_packages":
                packages_operation_result = models.reset_packages()
    
            if packages_operation_result:
                return util.get_rest_reply(flask.jsonify(packages_operation_result))
            else:
                action = update_type.split("_")[0]
                return util.get_rest_reply(f'Impossible to {action} packages, check the logs for more information.', 500)
    
    
    def _handle_module_operation(update_type):
        request_data = flask.request.get_json()
        if request_data:
            packages_operation_result = {}
            if update_type == "update_modules":
                packages_operation_result = models.update_modules(request_data)
            elif update_type == "uninstall_modules":
                packages_operation_result = models.uninstall_modules(request_data)
    
            if packages_operation_result is not None:
                return util.get_rest_reply(flask.jsonify(packages_operation_result))
            else:
                action = update_type.split("_")[0]
                return util.get_rest_reply(f'Impossible to {action} module(s), check the logs for more information.', 500)
        else:
            return util.get_rest_reply('{"Need at least one element be selected": "ko"}', 500)
    
    
    def _handle_tentacles_pages_post(update_type):
        if update_type in ["add_package", "install_packages", "update_packages", "reset_packages"]:
            return _handle_package_operation(update_type)
    
        elif update_type in ["update_modules", "uninstall_modules"]:
            return _handle_module_operation(update_type)
    
    
    @blueprint.route('/install_official_tentacle_packages<use_beta_tentacles>', methods=['POST'])
    @login.login_required_when_activated
    def install_official_tentacle_packages(use_beta_tentacles):
        bundle_url = models.get_official_tentacles_url(use_beta_tentacles == "True")
        packages_operation_result = models.install_packages(path_or_url=bundle_url)
        if packages_operation_result:
            return util.get_rest_reply(flask.jsonify(packages_operation_result))
        else:
            return util.get_rest_reply(f'Impossible to install tentacles, check the logs for more information.', 500)
    
    
    @blueprint.route("/tentacle_packages")
    @blueprint.route('/tentacle_packages', methods=['GET', 'POST'])
    @login.active_login_required
    def tentacle_packages():
        if flask.request.method == 'POST':
            if not constants.CAN_INSTALL_TENTACLES:
                return util.get_rest_reply(f'Impossible to install tentacles on this cloud OctoBot.', 500)
            update_type = flask.request.args["update_type"]
            return _handle_tentacles_pages_post(update_type)
    
        else:
            return flask.render_template("advanced_tentacle_packages.html",
                                         get_tentacles_packages=models.get_tentacles_packages)
