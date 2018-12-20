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

from . import advanced
from interfaces.web.util.flask_util import get_rest_reply


@advanced.route("/strategy-optimizer")
@advanced.route('/strategy-optimizer', methods=['GET', 'POST'])
def strategy_optimizer():
    from interfaces.web.models.strategy_optimizer import get_strategies_list, get_current_strategy, \
        get_time_frames_list, \
        get_evaluators_list, get_risks_list, start_optimizer, get_optimizer_results, get_optimizer_status, \
        get_optimizer_report, get_current_run_params, get_trading_mode

    if request.method == 'POST':
        update_type = request.args["update_type"]
        request_data = request.get_json()
        success = False
        reply = "Operation OK"

        if request_data:
            if update_type == "start_optimizer":
                try:
                    strategy = request_data["strategy"][0]
                    time_frames = request_data["time_frames"]
                    evaluators = request_data["evaluators"]
                    risks = request_data["risks"]
                    success, reply = start_optimizer(strategy, time_frames, evaluators, risks)
                except Exception as e:
                    return get_rest_reply('{"start_optimizer": "ko: ' + str(e) + '"}', 500)

        if success:
            return get_rest_reply(jsonify(reply))
        else:
            return get_rest_reply(reply, 500)

    elif request.method == 'GET':
        if request.args:
            target = request.args["update_type"]
            if target == "optimizer_results":
                optimizer_results = get_optimizer_results()
                return jsonify(optimizer_results)
            if target == "optimizer_report":
                optimizer_report = get_optimizer_report()
                return jsonify(optimizer_report)
            elif target == "optimizer_status":
                optimizer_status, progress, overall_progress, errors = get_optimizer_status()
                status = {"status": optimizer_status, "progress": progress,
                          "overall_progress": overall_progress, "errors": errors}
                return jsonify(status)
            if target == "strategy_params":
                strategy_name = request.args["strategy_name"]
                params = {
                    "time_frames": list(get_time_frames_list(strategy_name)),
                    "evaluators": list(get_evaluators_list(strategy_name))
                }
                return jsonify(params)

        else:
            current_strategy = get_current_strategy()
            return render_template('advanced_strategy_optimizer.html',
                                   strategies=get_strategies_list(),
                                   current_strategy=current_strategy,
                                   time_frames=get_time_frames_list(current_strategy),
                                   evaluators=get_evaluators_list(current_strategy),
                                   risks=get_risks_list(),
                                   trading_mode=get_trading_mode(),
                                   run_params=get_current_run_params())
