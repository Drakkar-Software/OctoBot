import ccxt
from flask import render_template, request, jsonify

from config.cst import CONFIG_EXCHANGES, CONFIG_CATEGORY_SERVICES, CONFIG_CATEGORY_NOTIFICATION, \
    CONFIG_TRADER, CONFIG_SIMULATOR, CONFIG_CRYPTO_CURRENCIES, GLOBAL_CONFIG_KEY, EVALUATOR_CONFIG_KEY, \
    CONFIG_TRADER_REFERENCE_MARKET, UPDATED_CONFIG_SEPARATOR
from interfaces import get_bot
from interfaces.web import server_instance
from interfaces.web.models.configuration import get_evaluator_config, update_evaluator_config, \
    get_evaluator_startup_config, get_services_list, get_symbol_list, update_global_config, get_all_symbol_list
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/config")
@server_instance.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        request_data = request.get_json()
        success = False

        if request_data:
            # update global config if required
            if GLOBAL_CONFIG_KEY in request_data and request_data[GLOBAL_CONFIG_KEY]:
                success = update_global_config(request_data[GLOBAL_CONFIG_KEY])

            # update evaluator config if required
            if EVALUATOR_CONFIG_KEY in request_data and request_data[EVALUATOR_CONFIG_KEY]:
                success = update_evaluator_config(request_data[EVALUATOR_CONFIG_KEY])

        if success:
            # TODO
            return get_rest_reply(jsonify(get_evaluator_config()))
        else:
            return get_rest_reply('{"update": "ko"}', 500)
    else:
        g_config = get_bot().get_config()
        user_exchanges = [e for e in g_config[CONFIG_EXCHANGES]]
        full_exchange_list = list(set(ccxt.exchanges) - set(user_exchanges))

        # can't handle exchanges containing UPDATED_CONFIG_SEPARATOR character in their name
        full_exchange_list = [exchange for exchange in full_exchange_list if UPDATED_CONFIG_SEPARATOR not in exchange]

        return render_template('config.html',

                               config_exchanges=g_config[CONFIG_EXCHANGES],
                               config_trader=g_config[CONFIG_TRADER],
                               config_trader_simulator=g_config[CONFIG_SIMULATOR],
                               config_notifications=g_config[CONFIG_CATEGORY_NOTIFICATION],
                               config_services=g_config[CONFIG_CATEGORY_SERVICES],
                               config_symbols=g_config[CONFIG_CRYPTO_CURRENCIES],
                               config_reference_market=g_config[CONFIG_TRADER][CONFIG_TRADER_REFERENCE_MARKET],

                               ccxt_exchanges=sorted(full_exchange_list),
                               services_list=get_services_list(),
                               symbol_list=sorted(get_symbol_list([exchange for exchange in g_config[CONFIG_EXCHANGES]])),
                               full_symbol_list=get_all_symbol_list(),
                               evaluator_config=get_evaluator_config(),
                               evaluator_startup_config=get_evaluator_startup_config()
                               )


@server_instance.template_filter()
def is_dict(value):
    return isinstance(value, dict)


@server_instance.template_filter()
def is_list(value):
    return isinstance(value, list)


@server_instance.template_filter()
def is_bool(value):
    return isinstance(value, bool)
