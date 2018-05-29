import logging
import threading
from time import sleep

import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt

from config.cst import CONFIG_CRYPTO_CURRENCIES, CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_WEB_IP, CONFIG_WEB_PORT
from interfaces import get_bot
from interfaces.web import app_instance, load_callbacks, load_routes


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None

    def run(self):

        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        # Define the WSGI application object
        self.app = app_instance

        self.app.layout = html.Div(children=[
            html.H1('OctoBot Dashboard'),

            dcc.Graph(id='portfolio-value-graph', animate=True),

            dt.DataTable(
                rows=[{}],
                row_selectable=False,
                filterable=True,
                sortable=True,
                editable=False,
                selected_row_indices=[],
                id='datatable-portfolio'
            ),
            dcc.Interval(
                id='portfolio-update',
                interval=3 * 1000
            ),

            html.Div([
                html.Label('Exchange'),
                dcc.Dropdown(id='exchange-name',
                             options=[{'label': s, 'value': s}
                                      for s in get_bot().get_exchanges_list().keys()],
                             value=next(iter(get_bot().get_exchanges_list().keys())),
                             multi=False,
                             ),
                html.Label('Currency'),
                dcc.Dropdown(id='cryptocurrency-name',
                             options=[{'label': s, 'value': s}
                                      for s in self.config[CONFIG_CRYPTO_CURRENCIES].keys()],
                             value=next(iter(self.config[CONFIG_CRYPTO_CURRENCIES].keys())),
                             multi=False,
                             ),
                html.Label('Symbol'),
                dcc.Dropdown(id='symbol',
                             options=[],
                             value="BTC/USDT",
                             multi=False,
                             ),
                html.Label('TimeFrame'),
                dcc.Dropdown(id='time-frame',
                             options=[],
                             value=None,
                             multi=False,
                             ),
                html.Label('Evaluator'),
                dcc.Dropdown(id='evaluator-name',
                             options=[],
                             value="",
                             multi=False,
                             ),
            ],
                style={'columnCount': 1, 'marginLeft': 25, 'marginRight': 25, 'marginTop': 25, 'marginBottom': 25}),

            dcc.Graph(id='live-graph', animate=True),
            dcc.Interval(
                id='graph-update',
                interval=3 * 1000
            ),

            dcc.Graph(id='strategy-live-graph', animate=True),
            dcc.Interval(
                id='strategy-graph-update',
                interval=3 * 1000
            ),
        ])

        load_callbacks()
        load_routes()
        self.app.run_server(host=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP],
                            port=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT],
                            debug=False,
                            threaded=True)

    def stop(self):
        # func = request.environ.get('werkzeug.server.shutdown')
        # if func is None:
        #     raise RuntimeError('Not running with the Werkzeug Server')
        # func()
        pass
