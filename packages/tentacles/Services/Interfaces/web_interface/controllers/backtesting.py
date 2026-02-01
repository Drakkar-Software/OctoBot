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
import werkzeug

import octobot_commons.time_frame_manager as time_frame_manager

import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.errors as errors


def register(blueprint):
    @blueprint.route("/backtesting")
    @blueprint.route('/backtesting', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def backtesting():
        if not models.is_backtesting_enabled():
            return flask.redirect(flask.url_for("home"))
        if flask.request.method == 'POST':
            try:
                action_type = flask.request.args["action_type"]
                success = False
                reply = "Action failed"
                if action_type == "start_backtesting":
                    data = flask.request.get_json()
                    source = flask.request.args["source"]
                    auto_stop = flask.request.args.get("auto_stop", False)
                    run_on_common_part_only = flask.request.args.get("run_on_common_part_only", "true") == "true"
                    reset_tentacle_config = flask.request.args.get("reset_tentacle_config", False)
                    success, reply = models.start_backtesting_using_specific_files(
                        data["files"],
                        source,
                        reset_tentacle_config,
                        run_on_common_part_only,
                        start_timestamp=data.get("start_timestamp", None),
                        end_timestamp=data.get("end_timestamp", None),
                        enable_logs=data.get("enable_logs", False),
                        auto_stop=auto_stop,
                        collector_start_callback=web_interface.send_data_collector_status,
                        start_callback=web_interface.send_backtesting_status)
                elif action_type == "start_backtesting_with_current_bot_data":
                    data = flask.request.get_json()
                    source = flask.request.args["source"]
                    auto_stop = flask.request.args.get("auto_stop", False)
                    exchange_id = data.get("exchange_id", None)
                    trading_type = data.get("exchange_type", None)
                    profile_id = data.get("profile_id", None)
                    name = data.get("name", None)
                    reset_tentacle_config = flask.request.args.get("reset_tentacle_config", False)
                    success, reply = models.start_backtesting_using_current_bot_data(
                        data.get("data_source", models.CURRENT_BOT_DATA),
                        exchange_id,
                        source,
                        reset_tentacle_config,
                        start_timestamp=data.get("start_timestamp", None),
                        end_timestamp=data.get("end_timestamp", None),
                        trading_type=trading_type,
                        profile_id=profile_id,
                        enable_logs=data.get("enable_logs", False),
                        auto_stop=auto_stop,
                        name=name,
                        collector_start_callback=web_interface.send_data_collector_status,
                        start_callback=web_interface.send_backtesting_status
                    )
                elif action_type == "stop_backtesting":
                    success, reply = models.stop_previous_backtesting()
                if success:
                    return util.get_rest_reply(flask.jsonify(reply))
                else:
                    return util.get_rest_reply(reply, 500)

            except errors.MissingExchangeId:
                return util.get_rest_reply(errors.MissingExchangeId.EXPLANATION, 500)

        elif flask.request.method == 'GET':
            if flask.request.args:
                target = flask.request.args["update_type"]
                if target == "backtesting_report":
                    source = flask.request.args["source"]
                    backtesting_report = models.get_backtesting_report(source)
                    return flask.jsonify(backtesting_report)

            else:
                return flask.render_template('backtesting.html',
                                             activated_trading_mode=models.get_config_activated_trading_mode(),
                                             data_files=models.get_data_files_with_description())


    @blueprint.route("/backtesting_run_id")
    @login.login_required_when_activated
    def backtesting_run_id():
        trading_mode = models.get_config_activated_trading_mode()
        run_id = models.get_latest_backtesting_run_id(trading_mode)
        return flask.jsonify(run_id)

    @blueprint.route("/social_data_collector")
    @blueprint.route('/social_data_collector', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def social_data_collector():
        if not models.is_backtesting_enabled():
            return flask.redirect(flask.url_for("home"))
        if flask.request.method == 'POST':
            action_type = flask.request.args["action_type"]
            success = False
            reply = "Action failed"
            if action_type == "start_collector":
                details = flask.request.get_json()
                success, reply = models.collect_social_data_file(
                    details["social_name"],
                    details["sources"],
                    details.get("startTimestamp"),
                    details.get("endTimestamp")
                )
                if success:
                    web_interface.send_social_data_collector_status()
            elif action_type == "stop_collector":
                success, reply = models.stop_social_data_collector()
            if success:
                return util.get_rest_reply(flask.jsonify(reply))
            else:
                return util.get_rest_reply(reply, 500)

        elif flask.request.method == 'GET':
            if flask.request.args:
                action_type_key = "action_type"
                if action_type_key in flask.request.args:
                    target = flask.request.args[action_type_key]
                    if target == "available_services":
                        return flask.jsonify(models.get_available_social_services())
                    elif target == "service_sources":
                        service_name = flask.request.args.get('service_name')
                        return flask.jsonify(models.get_service_sources(service_name))
                    elif target == "status":
                        status, progress = models.get_social_data_collector_status()
                        return flask.jsonify({"status": status, "progress": progress})

            # Render the social data collector page
            origin_page = None
            if flask.request.args:
                from_key = "from"
                if from_key in flask.request.args:
                    origin_page = flask.request.args[from_key]

            available_services = models.get_available_social_services()
            return flask.render_template('social_data_collector.html',
                                         available_services=available_services,
                                         origin_page=origin_page,
                                         alert={})


    @blueprint.route("/data_collector")
    @blueprint.route('/data_collector', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def data_collector():
        if not models.is_backtesting_enabled():
            return flask.redirect(flask.url_for("home"))
        if flask.request.method == 'POST':
            action_type = flask.request.args["action_type"]
            success = False
            reply = "Action failed"
            if action_type == "delete_data_file":
                file = flask.request.get_json()
                success, reply = models.get_delete_data_file(file)
            elif action_type == "start_collector":
                details = flask.request.get_json()
                success, reply = models.collect_data_file(details["exchange"], details["symbols"], details["time_frames"],
                                                          details["startTimestamp"], details["endTimestamp"])
                if success:
                    web_interface.send_data_collector_status()
            elif action_type == "stop_collector":
                success, reply = models.stop_data_collector()
            elif action_type == "import_data_file":
                if flask.request.files:
                    file = flask.request.files['file']
                    name = werkzeug.utils.secure_filename(flask.request.files['file'].filename)
                    success, reply = models.save_data_file(name, file)
                    alert = {"success": success, "message": reply}
                else:
                    alert = {}
                current_exchange = models.get_current_exchange()

                # here return template to force page reload because of file upload via input form
                return flask.render_template('data_collector.html',
                                             data_files=models.get_data_files_with_description(),
                                             other_ccxt_exchanges=sorted(models.get_other_history_exchange_list()),
                                             full_candle_history_ccxt_exchanges=models.get_full_candle_history_exchange_list(),
                                             current_exchange=models.get_current_exchange(),
                                             full_symbol_list=sorted(models.get_symbol_list([current_exchange])),
                                             available_timeframes_list=[timeframe.value for timeframe in
                                                                        time_frame_manager.sort_time_frames(
                                                                            models.get_timeframes_list([current_exchange]))],
                                             alert=alert)
            if success:
                return util.get_rest_reply(flask.jsonify(reply))
            else:
                return util.get_rest_reply(reply, 500)

        elif flask.request.method == 'GET':
            origin_page = None
            if flask.request.args:
                action_type_key = "action_type"
                if action_type_key in flask.request.args:
                    target = flask.request.args[action_type_key]
                    if target == "symbol_list":
                        exchange = flask.request.args.get('exchange')
                        return flask.jsonify(sorted(models.get_symbol_list([exchange])))
                    elif target == "available_timeframes_list":
                        exchange = flask.request.args.get('exchange')
                        return flask.jsonify([timeframe.value for timeframe in
                                              time_frame_manager.sort_time_frames(
                                                  models.get_timeframes_list([exchange]))])
                from_key = "from"
                if from_key in flask.request.args:
                    origin_page = flask.request.args[from_key]

            current_exchange = models.get_current_exchange()
            return flask.render_template('data_collector.html',
                                         data_files=models.get_data_files_with_description(),
                                         other_ccxt_exchanges=sorted(models.get_other_history_exchange_list()),
                                         full_candle_history_ccxt_exchanges=models.get_full_candle_history_exchange_list(),
                                         current_exchange=models.get_current_exchange(),
                                         full_symbol_list=sorted(models.get_symbol_list([current_exchange])),
                                         available_timeframes_list=[timeframe.value for timeframe in
                                                                    time_frame_manager.sort_time_frames(
                                                                        models.get_timeframes_list([current_exchange]))],
                                         origin_page=origin_page,
                                         alert={})
