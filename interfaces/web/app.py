import logging
import threading

import dash_core_components as dcc
import dash_html_components as html
from flask import request

from config.cst import CONFIG_CRYPTO_CURRENCIES
from interfaces.web import app_instance, load_callbacks, get_bot


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.server = None
        self.app = None

    def run(self):
        # Define the WSGI application object
        self.app = app_instance
        self.server = self.app.server

        self.app.layout = html.Div(children=[
            html.H1('CryptoBot'),
            html.Div([
                html.Label('Exchange'),
                dcc.Dropdown(id='strategy-name',
                             options=[],
                             value="binance",
                             multi=False,
                             ),
                html.Label('Currency'),
                dcc.Dropdown(id='cryptocurrency-name',
                             options=[{'label': s, 'value': s}
                                      for s in self.config[CONFIG_CRYPTO_CURRENCIES].keys()],
                             value=list(self.config[CONFIG_CRYPTO_CURRENCIES].keys())[0],
                             multi=False,
                             ),
                html.Label('Strategy'),
                dcc.Dropdown(id='strategy-name',
                             options=[],
                             value="TempFullMixedStrategiesEvaluator",
                             multi=False,
                             ),
                html.Label('Risk'),
                dcc.Slider(
                    min=0.1,
                    max=1,
                    value=0.5,
                    step=0.05,
                    marks={0.1: 'Risk minimized', 1: 'Risk maximized'},
                ),
            ],
                style={'columnCount': 2, 'marginLeft': 25, 'marginRight': 25}),

            dcc.Graph(id='live-graph', animate=True),
            dcc.Interval(
                id='graph-update',
                interval=1 * 10000
            ),

            dcc.Graph(id='strategy-live-graph', animate=True),
            dcc.Interval(
                id='strategy-graph-update',
                interval=1 * 10000
            ),
        ])

        load_callbacks()
        self.app.run_server(host='localhost', port=5000, debug=False, threaded=True)

    def stop(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            self.logger.warning("Not running with the Werkzeug Server")
        func()
