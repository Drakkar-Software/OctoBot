#  Drakkar-Software OctoBot
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

from flask import render_template, request, jsonify

from interfaces.web import server_instance
from interfaces.web.util.flask_util import get_rest_reply
from interfaces.web.models.tentacles import get_tentacles_packages, \
    get_tentacles, get_tentacles_package_description, \
    register_and_install, install_packages, update_packages, reset_packages, update_modules, uninstall_modules


@server_instance.route("/tentacles")
def tentacles():
    return render_template("tentacles.html",
                           get_tentacles=get_tentacles)


def _handle_package_operation(update_type):
    if update_type == "add_package":
        request_data = request.get_json()
        success = False
        if request_data:
            path_or_url, action = next(iter(request_data.items()))
            path_or_url = path_or_url.strip()
            if action == "description":
                package_description = get_tentacles_package_description(path_or_url)
                if package_description:
                    return get_rest_reply(jsonify(package_description))
                else:
                    return get_rest_reply(f'Impossible to find {path_or_url} tentacles package information.', 500)
            elif action == "register_and_install":
                installation_result = register_and_install(path_or_url)
                if installation_result:
                    return get_rest_reply(jsonify(installation_result))
                else:
                    return get_rest_reply('Impossible to install the given tentacles package, check the logs '
                                          'for more information.', 500)

        if not success:
            return get_rest_reply('{"operation": "ko"}', 500)
    elif update_type in ["install_packages", "update_packages", "reset_packages"]:

        packages_operation_result = {}
        if update_type == "install_packages":
            packages_operation_result = install_packages()
        elif update_type == "update_packages":
            packages_operation_result = update_packages()
        elif update_type == "reset_packages":
            packages_operation_result = reset_packages()

        if packages_operation_result is not None:
            return get_rest_reply(jsonify(packages_operation_result))
        else:
            action = update_type.split("_")[0]
            return get_rest_reply(f'Impossible to {action} packages, check the logs for more information.', 500)


def _handle_module_operation(update_type):
    request_data = request.get_json()
    if request_data:
        packages_operation_result = {}
        if update_type == "update_modules":
            packages_operation_result = update_modules(request_data)
        elif update_type == "uninstall_modules":
            packages_operation_result = uninstall_modules(request_data)

        if packages_operation_result is not None:
            return get_rest_reply(jsonify(packages_operation_result))
        else:
            action = update_type.split("_")[0]
            return get_rest_reply(f'Impossible to {action} module(s), check the logs for more information.', 500)
    else:
        return get_rest_reply('{"Need at least one element be selected": "ko"}', 500)


def _handle_tentacles_pages_post(update_type):
    if update_type in ["add_package", "install_packages", "update_packages", "reset_packages"]:
        return _handle_package_operation(update_type)

    elif update_type in ["update_modules", "uninstall_modules"]:
        return _handle_module_operation(update_type)


@server_instance.route("/tentacle_packages")
@server_instance.route('/tentacle_packages', methods=['GET', 'POST'])
def tentacle_packages():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        return _handle_tentacles_pages_post(update_type)

    else:
        return render_template("tentacle_packages.html",
                               get_tentacles_packages=get_tentacles_packages)
