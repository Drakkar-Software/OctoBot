from flask import render_template, request, jsonify

from interfaces.web import server_instance
from interfaces.web.models.strategy_optimizer import get_strategies_list, get_current_strategy, get_time_frames_list, \
    get_evaluators_list, get_risks_list, start_optimizer, get_optimizer_results, get_optimizer_status, \
    get_optimizer_report
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/strategy-optimizer")
@server_instance.route('/strategy-optimizer', methods=['GET', 'POST'])
def strategy_optimizer():
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
                    return get_rest_reply('{"start_optimizer": "ko: ' + e + '"}', 500)

        if success:
            # TODO
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
                optimizer_status, progress = get_optimizer_status()
                status = {"status": optimizer_status, "progress": progress}
                return jsonify(status)


        else:
            return render_template('strategy-optimizer.html',
                                   strategies=get_strategies_list(),
                                   current_strategy=get_current_strategy(),
                                   time_frames=get_time_frames_list(),
                                   evaluators=get_evaluators_list(),
                                   risks=get_risks_list())

