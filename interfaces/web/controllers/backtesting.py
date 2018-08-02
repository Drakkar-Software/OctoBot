from flask import render_template, request, jsonify

from interfaces.web import server_instance
from interfaces.web.models.backtesting import get_data_files_with_description, start_backtesting_using_specific_files, \
    get_backtesting_report,get_backtesting_status
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
def data_collector():
    return render_template('data_collector.html')
