from flask import jsonify

from interfaces.trading_util import get_open_orders
from . import api


@api.route("/orders")
def orders():
    real_open_orders, simulated_open_orders = get_open_orders()
    return jsonify({"real_open_orders": real_open_orders, "simulated_open_orders": simulated_open_orders})
