from flask import render_template, request, jsonify

from interfaces.web import server_instance
from interfaces.web.util.flask_util import get_rest_reply
from interfaces.web.models.tentacles import get_tentacles_packages, \
    get_tentacles, get_tentacles_package_description, \
    register_and_install


@server_instance.route("/tentacles")
def tentacles():
    return render_template('tentacles.html')


@server_instance.route("/tentacle_manager")
@server_instance.route('/tentacle_manager', methods=['GET', 'POST'])
def tentacle_manager():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        if update_type == "add_package":
            request_data = request.get_json()
            success = False

            if len(request_data) > 0:
                path_or_url, action = next(iter(request_data.items()))
                path_or_url = path_or_url.strip()
                if action == "description":
                    package_description = get_tentacles_package_description(path_or_url)
                    if package_description:
                        return get_rest_reply(jsonify(package_description))
                    else:
                        return get_rest_reply('{"Impossible to find tentacles package information.": "ko"}', 500)
                elif action == "register_and_install":
                    installation_result = register_and_install(path_or_url)
                    if installation_result:
                        return get_rest_reply(jsonify(installation_result))
                    else:
                        return get_rest_reply('{"Impossible to install the given tentacles package, check the logs '
                                              'for more information.": "ko"}', 500)

            if not success:
                return get_rest_reply('{"operation": "ko"}', 500)

    else:
        return render_template('tentacle_manager.html',
                               get_tentacles_packages=get_tentacles_packages,
                               get_tentacles=get_tentacles)
