from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/strategy-optimizer")
def strategy_optimizer():
    return render_template('strategy-optimizer.html')
