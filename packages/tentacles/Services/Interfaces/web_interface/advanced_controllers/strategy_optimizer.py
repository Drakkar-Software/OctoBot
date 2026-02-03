#  Drakkar-Software OctoBot-Interfaces
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
import flask

import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.login as login


def register(blueprint):
    # strategy optimize is disabled
    return

    @blueprint.route("/strategy-optimizer")
    @blueprint.route('/strategy-optimizer', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def strategy_optimizer():
        if not models.is_backtesting_enabled():
            return flask.redirect(flask.url_for("home"))
        if flask.request.method == 'POST':
            update_type = flask.request.args["update_type"]
            request_data = flask.request.get_json()
            success = False
            reply = "Operation OK"

            if update_type == "cancel_optimizer":
                try:
                    success, reply = models.cancel_optimizer()
                except Exception as e:
                    return util.get_rest_reply('{"start_optimizer": "ko: ' + str(e) + '"}', 500)
            elif request_data:
                if update_type == "start_optimizer":
                    try:
                        strategy = request_data["strategy"][0]
                        time_frames = request_data["time_frames"]
                        evaluators = request_data["evaluators"]
                        risks = request_data["risks"]
                        success, reply = models.start_optimizer(strategy, time_frames, evaluators, risks)
                    except Exception as e:
                        return util.get_rest_reply('{"start_optimizer": "ko: ' + str(e) + '"}', 500)

            if success:
                return util.get_rest_reply(flask.jsonify(reply))
            else:
                return util.get_rest_reply(reply, 500)

        elif flask.request.method == 'GET':
            if flask.request.args:
                target = flask.request.args["update_type"]
                if target == "optimizer_results":
                    optimizer_results = models.get_optimizer_results()
                    return flask.jsonify(optimizer_results)
                if target == "optimizer_report":
                    optimizer_report = models.get_optimizer_report()
                    return flask.jsonify(optimizer_report)
                if target == "strategy_params":
                    strategy_name = flask.request.args["strategy_name"]
                    params = {
                        "time_frames": list(models.get_time_frames_list(strategy_name)),
                        "evaluators": list(models.get_evaluators_list(strategy_name))
                    }
                    return flask.jsonify(params)
            else:
                trading_mode = models.get_config_activated_trading_mode()
                strategies = models.get_strategies_list(trading_mode)
                current_strategy = strategies[0] if strategies else ""
                return flask.render_template('advanced_strategy_optimizer.html',
                                             strategies=strategies,
                                             current_strategy=current_strategy,
                                             time_frames=models.get_time_frames_list(current_strategy),
                                             evaluators=models.get_evaluators_list(current_strategy),
                                             risks=models.get_risks_list(),
                                             trading_mode=trading_mode.get_name() if trading_mode else None,
                                             run_params=models.get_current_run_params())
