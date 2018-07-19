from interfaces.web.api import api


@api.route("/orders")
def orders():
    real_open_orders, simulated_open_orders = get_open_orders()
    return render_template('orders.html',
                           real_open_orders=real_open_orders,
                           simulated_open_orders=simulated_open_orders)