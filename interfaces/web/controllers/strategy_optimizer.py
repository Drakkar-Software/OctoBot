from flask import render_template

from interfaces.web import server_instance

from interfaces.web.models.strategy_optimizer import get_strategies_list, get_current_strategy, get_time_frames_list, \
    get_evaluators_list, get_risks_list


@server_instance.route("/strategy-optimizer")
def strategy_optimizer():
    return render_template('strategy-optimizer.html',
                           strategies=get_strategies_list(),
                           current_strategy=get_current_strategy(),
                           time_frames=get_time_frames_list(),
                           evaluators=get_evaluators_list(),
                           risks=get_risks_list())

