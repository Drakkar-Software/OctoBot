import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt

from config.cst import CONFIG_CRYPTO_CURRENCIES
from interfaces import get_bot


def create_dashboard(web_app):

    # Get default values
    try:
        first_exchange = next(iter(get_bot().get_exchanges_list().keys()))
    except StopIteration:
        first_exchange = ""

    try:
        first_cryptocurrency = next(iter(web_app.config[CONFIG_CRYPTO_CURRENCIES].keys()))
    except StopIteration:
        first_cryptocurrency = ""

    web_app.app.layout = html.Div(children=[
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
            interval=10 * 1000
        ),

        html.Div([
            html.Label('Exchange'),
            dcc.Dropdown(id='exchange-name',
                         options=[{'label': s, 'value': s}
                                  for s in get_bot().get_exchanges_list().keys()],
                         value=first_exchange,
                         multi=False,
                         ),
            html.Label('Currency'),
            dcc.Dropdown(id='cryptocurrency-name',
                         options=[{'label': s, 'value': s}
                                  for s in web_app.config[CONFIG_CRYPTO_CURRENCIES].keys()],
                         value=first_cryptocurrency
                         if web_app.config[CONFIG_CRYPTO_CURRENCIES] else "",
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
            interval=10 * 1000
        ),
    ])
