class OrderNotifier:
    def __init__(self, order):
        self.order = order

    def notify(self):
        order_types = [order.get_order_type() for order in self.order.get_linked_orders()]
        order_types.append(self.order.get_order_type())
        pass

    def respond(self):
        pass
