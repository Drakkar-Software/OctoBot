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
from werkzeug.utils import secure_filename

from interfaces.web import server_instance
from interfaces.web.models.backtesting import get_data_files_with_description, start_backtesting_using_specific_files, \
    get_backtesting_report, get_backtesting_status, get_delete_data_file, collect_data_file, save_data_file

from interfaces.web.models.configuration import get_symbol_list, get_full_exchange_list, get_current_exchange, \
    get_config_activated_trading_mode
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/backtesting")
@server_instance.route('/backtesting', methods=['GET', 'POST'])
def backtesting():
    if request.method == 'POST':
        action_type = request.args["action_type"]
        success = False
        reply = "Action failed"
        if action_type == "start_backtesting":
            files = request.get_json()
            source = request.args["source"]
            reset_tentacle_config = request.args["reset_tentacle_config"] if "reset_tentacle_config" in request.args \
                else False
            success, reply = start_backtesting_using_specific_files(files, source, reset_tentacle_config)

        if success:
            return get_rest_reply(jsonify(reply))
        else:
            return get_rest_reply(reply, 500)

    elif request.method == 'GET':
        if request.args:
            target = request.args["update_type"]
            if target == "backtesting_report":
                source = request.args["source"]
                backtesting_report = get_backtesting_report(source)
                return jsonify(backtesting_report)
            elif target == "backtesting_status":
                backtesting_status, progress = get_backtesting_status()
                status = {"status": backtesting_status, "progress": progress}
                return jsonify(status)

        else:
            return render_template('backtesting.html',
                                   activated_trading_mode=get_config_activated_trading_mode(),
                                   data_files=get_data_files_with_description())


@server_instance.route("/data_collector")
@server_instance.route('/data_collector', methods=['GET', 'POST'])
def data_collector():
    if request.method == 'POST':
        action_type = request.args["action_type"]
        success = False
        reply = "Action failed"
        if action_type == "delete_data_file":
            file = request.get_json()
            success, reply = get_delete_data_file(file)
        elif action_type == "start_collector":
            details = request.get_json()
            success, reply = collect_data_file(details["exchange"], details["symbol"])
        elif action_type == "import_data_file":
            if request.files:
                file = request.files['file']
                name = secure_filename(request.files['file'].filename)
                success, reply = save_data_file(name, file)
                alert = {"success": success, "message": reply}
            else:
                alert = {}
            current_exchange = get_current_exchange()

            # here return template to force page reload because of file upload via input form
            return render_template('data_collector.html',
                                   data_files=get_data_files_with_description(),
                                   ccxt_exchanges=sorted(get_full_exchange_list()),
                                   current_exchange=get_current_exchange(),
                                   full_symbol_list=sorted(get_symbol_list([current_exchange])),
                                   alert=alert)
        if success:
            return get_rest_reply(jsonify(reply))
        else:
            return get_rest_reply(reply, 500)

    elif request.method == 'GET':
        origin_page = None
        if request.args:
            action_type_key = "action_type"
            if action_type_key in request.args:
                target = request.args[action_type_key]
                if target == "symbol_list":
                    exchange = request.args.get('exchange')
                    return jsonify(sorted(get_symbol_list([exchange])))
            from_key = "from"
            if from_key in request.args:
                origin_page = request.args[from_key]

        current_exchange = get_current_exchange()
        return render_template('data_collector.html',
                               data_files=get_data_files_with_description(),
                               ccxt_exchanges=sorted(get_full_exchange_list()),
                               current_exchange=get_current_exchange(),
                               full_symbol_list=sorted(get_symbol_list([current_exchange])),
                               origin_page=origin_page,
                               alert={})
