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

from interfaces.web.models.configuration import get_symbol_list, get_full_exchange_list, get_current_exchange
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
            success, reply = start_backtesting_using_specific_files(files)

        if success:
            return get_rest_reply(jsonify(reply))
        else:
            return get_rest_reply(reply, 500)

    elif request.method == 'GET':
        if request.args:
            target = request.args["update_type"]
            if target == "backtesting_report":
                backtesting_report = get_backtesting_report()
                return jsonify(backtesting_report)
            elif target == "backtesting_status":
                backtesting_status, progress = get_backtesting_status()
                status = {"status": backtesting_status, "progress": progress}
                return jsonify(status)

        else:
            return render_template('backtesting.html',
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
        if request.args:
            target = request.args["action_type"]
            if target == "symbol_list":
                exchange = request.args.get('exchange')
                return jsonify(sorted(get_symbol_list([exchange])))

        current_exchange = get_current_exchange()
        return render_template('data_collector.html',
                               data_files=get_data_files_with_description(),
                               ccxt_exchanges=sorted(get_full_exchange_list()),
                               current_exchange=get_current_exchange(),
                               full_symbol_list=sorted(get_symbol_list([current_exchange])),
                               alert={})
