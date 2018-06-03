class AbstractTradingMode:
    def __init__(self, config):
        self.config = config

        self.decider = None
        self.creator = None

    def set_decider(self, decider):
        self.decider = decider

    def set_creator(self, creator):
        self.creator = creator

    def get_creator(self):
        return self.creator

    def get_decider(self):
        return self.decider
