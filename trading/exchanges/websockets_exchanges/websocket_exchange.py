class WebSocketExchange:
    def __init__(self, config, exchange_manager, socket_manager):
        self.config = config
        self.exchange_manager = exchange_manager
        self.socket_manager = socket_manager
        self._time_frames = []
        self._traded_pairs = []

        # websocket client
        self.client = None

        # We will need to create the rest client and fetch exchange config
        self.create_client()

    # websocket exchange startup
    def create_client(self):
        self.client = self.socket_manager.get_websocket_client(self.config)

        # init websocket
        self.client.init_web_sockets(self.exchange_manager.get_config_time_frame(),
                                     self.exchange_manager.get_traded_pairs())

        # start the websocket
        self.client.start_sockets()

    def get_client(self):
        return self.client

    def stop(self):
        self.client.stop_sockets()

