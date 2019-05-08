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

from config import CONFIG_EXCHANGES, CONFIG_CATEGORY_SERVICES, CONFIG_CATEGORY_NOTIFICATION, CONFIG_TRADING, \
    CONFIG_TRADER, CONFIG_SIMULATOR, CONFIG_CRYPTO_CURRENCIES, GLOBAL_CONFIG_KEY, EVALUATOR_CONFIG_KEY, \
    CONFIG_TRADER_REFERENCE_MARKET, TRADING_CONFIG_KEY, DEACTIVATE_OTHERS
from interfaces.web import server_instance
from interfaces.web.models.configuration import get_strategy_config, update_evaluator_config, \
    get_evaluator_startup_config, get_services_list, get_symbol_list, update_global_config, get_all_symbol_list, \
    get_tested_exchange_list, get_simulated_exchange_list, get_other_exchange_list, get_edited_config, \
    update_trading_config, get_trading_startup_config, reset_trading_history, is_trading_persistence_activated, \
    manage_metrics, get_tentacle_from_string, update_tentacle_config, reset_config_to_default, \
    get_evaluator_detailed_config, REQUIREMENTS_KEY, get_config_activated_trading_mode
from interfaces.web.models.backtesting import get_data_files_with_description
from interfaces.web.util.flask_util import get_rest_reply
from interfaces.trading_util import has_real_and_or_simulated_traders
from backtesting import backtesting_enabled


@server_instance.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        request_data = request.get_json()
        success = True
        response = ""

        if request_data:

            # update trading config if required
            if TRADING_CONFIG_KEY in request_data and request_data[TRADING_CONFIG_KEY]:
                success = success and update_trading_config(request_data[TRADING_CONFIG_KEY])
            else:
                request_data[TRADING_CONFIG_KEY] = ""

            # update evaluator config if required
            if EVALUATOR_CONFIG_KEY in request_data and request_data[EVALUATOR_CONFIG_KEY]:
                deactivate_others = False
                if DEACTIVATE_OTHERS in request_data:
                    deactivate_others = request_data[DEACTIVATE_OTHERS]
                success = success and update_evaluator_config(request_data[EVALUATOR_CONFIG_KEY], deactivate_others)
            else:
                request_data[EVALUATOR_CONFIG_KEY] = ""

            # remove elements from global config if any to remove
            removed_elements_key = "removed_elements"
            if removed_elements_key in request_data and request_data[removed_elements_key]:
                success = success and update_global_config(request_data[removed_elements_key], delete=True)
            else:
                request_data[removed_elements_key] = ""

            # update global config if required
            if GLOBAL_CONFIG_KEY in request_data and request_data[GLOBAL_CONFIG_KEY]:
                success = update_global_config(request_data[GLOBAL_CONFIG_KEY])
            else:
                request_data[GLOBAL_CONFIG_KEY] = ""

            response = {
                "evaluator_updated_config": request_data[EVALUATOR_CONFIG_KEY],
                "trading_updated_config": request_data[TRADING_CONFIG_KEY],
                "global_updated_config": request_data[GLOBAL_CONFIG_KEY],
                removed_elements_key: request_data[removed_elements_key]
            }

        if success:
            return get_rest_reply(jsonify(response))
        else:
            return get_rest_reply('{"update": "ko"}', 500)
    else:
        display_config = get_edited_config()

        # service lists
        service_list, service_name_list = get_services_list()

        return render_template('config.html',

                               config_exchanges=display_config[CONFIG_EXCHANGES],
                               config_trading=display_config[CONFIG_TRADING],
                               config_trader=display_config[CONFIG_TRADER],
                               config_trader_simulator=display_config[CONFIG_SIMULATOR],
                               config_notifications=display_config[CONFIG_CATEGORY_NOTIFICATION],
                               config_services=display_config[CONFIG_CATEGORY_SERVICES],
                               config_symbols=display_config[CONFIG_CRYPTO_CURRENCIES],
                               config_reference_market=display_config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET],

                               real_trader_activated=has_real_and_or_simulated_traders()[0],

                               ccxt_tested_exchanges=get_tested_exchange_list(),
                               ccxt_simulated_tested_exchanges=get_simulated_exchange_list(),
                               ccxt_other_exchanges=sorted(get_other_exchange_list()),
                               services_list=service_list,
                               service_name_list=service_name_list,
                               symbol_list=sorted(get_symbol_list([exchange
                                                                   for exchange in display_config[CONFIG_EXCHANGES]])),
                               full_symbol_list=get_all_symbol_list(),
                               strategy_config=get_strategy_config(),
                               evaluator_startup_config=get_evaluator_startup_config(),
                               trading_startup_config=get_trading_startup_config(),

                               is_trading_persistence_activated=is_trading_persistence_activated(),
                               in_backtesting=backtesting_enabled(display_config)
                               )


@server_instance.route('/config_tentacle', methods=['GET', 'POST'])
def config_tentacle():
    if request.method == 'POST':
        tentacle_name = request.args.get("name")
        action = request.args.get("action")
        success = True
        response = ""
        if action == "update":
            request_data = request.get_json()
            success, response = update_tentacle_config(tentacle_name, request_data)
        elif action == "factory_reset":
            success, response = reset_config_to_default(tentacle_name)
        if success:
            return get_rest_reply(jsonify(response))
        else:
            return get_rest_reply(response, 500)
    else:
        if request.args:
            tentacle_name = request.args.get("name")
            tentacle_class, tentacle_type, tentacle_desc = get_tentacle_from_string(tentacle_name)
            evaluator_config = get_evaluator_detailed_config() if tentacle_type == "strategy" and \
                tentacle_desc[REQUIREMENTS_KEY] == ["*"] else None
            strategy_config = get_strategy_config() if tentacle_type == "trading mode" and \
                len(tentacle_desc[REQUIREMENTS_KEY]) > 1 else None
            evaluator_startup_config = get_evaluator_startup_config() if evaluator_config or strategy_config else None
            return render_template('config_tentacle.html',
                                   name=tentacle_name,
                                   tentacle_type=tentacle_type,
                                   tentacle_class=tentacle_class,
                                   tentacle_desc=tentacle_desc,
                                   evaluator_startup_config=evaluator_startup_config,
                                   strategy_config=strategy_config,
                                   evaluator_config=evaluator_config,
                                   activated_trading_mode=get_config_activated_trading_mode(edited_config=True),
                                   data_files=get_data_files_with_description())
        else:
            return render_template('config_tentacle.html')


@server_instance.route('/metrics_settings', methods=['POST'])
def metrics_settings():
    enable_metrics = request.get_json()
    return get_rest_reply(jsonify(manage_metrics(enable_metrics)))


@server_instance.route('/config_actions', methods=['POST'])
def config_actions():
    action = request.args.get("action")
    if action == "reset_trading_history":
        reset_trading_history()
        return jsonify({
            "title": "Trading history reset",
            "details": "Next trading sessions will not consider past sessions for "
                       "profitability and trading simulator will start using a fresh portfolio."
            })
    return get_rest_reply("No specified action.", code=500)


@server_instance.template_filter()
def is_dict(value):
    return isinstance(value, dict)


@server_instance.template_filter()
def is_list(value):
    return isinstance(value, list)


@server_instance.template_filter()
def is_bool(value):
    return isinstance(value, bool)
