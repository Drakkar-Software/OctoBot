from flask import render_template, request, jsonify

from interfaces.web import server_instance
from interfaces.web.bot_data_model import get_evaluator_config, update_evaluator_config, get_evaluator_startup_config, \
    reset_evaluator_config
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/config")
@server_instance.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        if update_type == "evaluator_config":
            request_data = request.get_json()
            success = False

            if request_data == "reset":
                success = reset_evaluator_config()
            elif request_data:
                success = update_evaluator_config(request_data)

            if success:
                return get_rest_reply(jsonify(get_evaluator_config()))
            else:
                return get_rest_reply('{"update": "ko"}', 500)
    else:
        return render_template('config.html',
                               get_evaluator_config=get_evaluator_config,
                               get_evaluator_startup_config=get_evaluator_startup_config)
