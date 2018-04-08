from abc import *


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.name = None
        self.client = None
        self.connected = False
        self.config = config
        self.symbol_list = []
        self.balance = {}
        self.open_orders = []
        self.pending_orders = []

    @abstractmethod
    def create_client(self):
        raise NotImplementedError("Create_client not implemented")

    @abstractmethod
    def check_config(self):
        raise NotImplementedError("Check_config not implemented")

    # @return DataFrame of prices
    @abstractmethod
    def get_symbol_prices(self, symbol, time_frame):
        raise NotImplementedError("Get_symbol_prices not implemented")

    @abstractmethod
    def get_symbol_list(self):
        raise NotImplementedError("Get_symbol_list not implemented")

    @abstractmethod
    def update_balance(self, symbol):
        raise NotImplementedError("Update_balance not implemented")

    @abstractmethod
    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        raise NotImplementedError("Update_balance not implemented")

    @abstractmethod
    def get_all_orders(self):
        raise NotImplementedError("Get_all_orders not implemented")

    # Check order status
    @abstractmethod
    def get_order(self, order_id):
        raise NotImplementedError("Get_order not implemented")

    @abstractmethod
    def get_open_orders(self):
        raise NotImplementedError("Get_open_orders not implemented")

    @abstractmethod
    def cancel_order(self, order_id):
        raise NotImplementedError("Cancel_order not implemented")

    @staticmethod
    @abstractmethod
    def get_time_frame_enum():
        raise NotImplementedError("Get_time_frame_enum not implemented")

    @staticmethod
    @abstractmethod
    def get_order_type_enum():
        raise NotImplementedError("Get_order_type_enum not implemented")

    @abstractmethod
    def get_trade_history(self):
        raise NotImplementedError("Get_trade_history not implemented")

    def get_name(self):
        return self.name

    def enabled(self):
        if self.name in self.config["exchanges"]:
            return True
        else:
            return False

    def get_balance(self):
        return self.balance

    def symbol_exists(self, symbol):
        if symbol in self.symbol_list:
            return True
        else:
            return False

    def set_balance(self, symbol, value):
        self.balance[symbol] = value
