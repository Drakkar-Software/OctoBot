import ccxt
from flask import render_template, request, jsonify

from config.cst import CONFIG_EXCHANGES, CONFIG_CATEGORY_SERVICES, CONFIG_CATEGORY_NOTIFICATION, \
    CONFIG_TRADER, CONFIG_SIMULATOR, CONFIG_CRYPTO_CURRENCIES
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
        user_exchanges = [e for e in g_config[CONFIG_EXCHANGES]]
        return render_template('config.html',

                               config_exchanges=g_config[CONFIG_EXCHANGES],
                               config_trader=g_config[CONFIG_TRADER],
                               config_trader_simulator=g_config[CONFIG_SIMULATOR],
                               config_notifications=g_config[CONFIG_CATEGORY_NOTIFICATION],
                               config_services=g_config[CONFIG_CATEGORY_SERVICES],
                               config_symbols=g_config[CONFIG_CRYPTO_CURRENCIES],

                               ccxt_exchanges=list(set(ccxt.exchanges) - set(user_exchanges)),
                               services_list=get_services_list(),
                               symbol_list=get_symbol_list([exchange for exchange in g_config[CONFIG_EXCHANGES]]),
                               get_evaluator_config=get_evaluator_config,
                               get_evaluator_startup_config=get_evaluator_startup_config)
