import plotly
from dash.dependencies import Output, Event

from config.cst import PriceStrings
from interfaces.web import app_instance, get_bot
import plotly.graph_objs as go


@app_instance.callback(Output('live-graph', 'figure'),
                       events=[Event('graph-update', 'interval')])
def update_values():
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()

    if len(symbol_evaluator_list) > 0:
        evaluator_thread_manager = symbol_evaluator_list[0].get_evaluator_thread_managers()["binance"]
        df = evaluator_thread_manager[0].get_evaluator().get_data()

        if df is not None:
            X = df[PriceStrings.STR_PRICE_TIME.value]
            Y = df[PriceStrings.STR_PRICE_CLOSE.value]

            data = plotly.graph_objs.Scatter(
                x=X,
                y=Y,
                name='Scatter',
                mode='lines+markers'
            )

            return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(X), max(X)]),
                                                        yaxis=dict(range=[min(Y), max(Y)]), )}

    return {}
