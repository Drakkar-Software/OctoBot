import ccxt
from flask import render_template, request, jsonify

from config.cst import CONFIG_EXCHANGES
from interfaces import get_bot

from interfaces.web import server_instance
from interfaces.web.models.configuration import get_evaluator_config, update_evaluator_config, \
    get_evaluator_startup_config, get_services_list, get_symbol_list
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/config")
@server_instance.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        if update_type == "evaluator_config":
            request_data = request.get_json()
            success = False

            if request_data:
                success = update_evaluator_config(request_data)

            if success:
                return get_rest_reply(jsonify(get_evaluator_config()))
            else:
                return get_rest_reply('{"update": "ko"}', 500)
    else:
        g_config = get_bot().get_config()
        return render_template('config.html',
                               ccxt_exchanges=ccxt.exchanges,
                               services_list=get_services_list(),
                               symbol_list=get_symbol_list([exchange for exchange in g_config[CONFIG_EXCHANGES]]),
                               get_evaluator_config=get_evaluator_config,
                               get_evaluator_startup_config=get_evaluator_startup_config)
