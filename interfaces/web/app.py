import logging
import threading

import dash_core_components as dcc
import dash_html_components as html
from dash import dash
from flask import request
from config.cst import CONFIG_ENABLED_OPTION


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None

    def enabled(self):
        if "interfaces" in self.config \
                and "web" in self.config["interfaces"] \
                and self.config["interfaces"]["web"][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False

    def run(self):
        self.app = dash.Dash()
        # temp
        self.app.css.append_css({
            "external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"
        })
        self.app.layout = html.Div([
            # Page Header
            html.Div([
                html.H1('CryptoBot')
            ]),

            # Dropdown Grid
            html.Div([
                html.Div([
                    # Select Symbol Dropdown
                    html.Div([
                        html.Div('Select Symbol', className='three columns'),
                        html.Div(dcc.Dropdown(id='division-selector'),
                                 className='nine columns')
                    ]),
                ], className='six columns'),

                # Empty
                html.Div(className='six columns'),
            ], className='twleve columns'),

        ])

        self.app.use_reloader = False
        self.app.run_server(host="127.0.0.1", port=8050, debug=False)

    def stop(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            self.logger.warning("Not running with the Werkzeug Server")
        func()

