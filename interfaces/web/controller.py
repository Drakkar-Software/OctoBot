import time

import dash
import plotly
from dash.dependencies import Output, Event

from config.cst import PriceStrings
from interfaces.web import app_instance, get_bot
import plotly.graph_objs as go

from tools.evaluators_util import check_valid_eval_note


@app_instance.callback(Output('live-graph', 'figure'),
                       [dash.dependencies.Input('cryptocurrency-name', 'value')],
                       events=[Event('graph-update', 'interval')])
def update_values(cryptocurrency_name):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()

    # temp
    if cryptocurrency_name not in symbol_evaluator_list:
        cryptocurrency_name = "Bitcoin"

    if len(symbol_evaluator_list) > 0:
        evaluator_thread_manager = symbol_evaluator_list[cryptocurrency_name].get_evaluator_thread_managers()["binance"]

        # temp
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


@app_instance.callback(Output('strategy-live-graph', 'figure'),
                       [dash.dependencies.Input('cryptocurrency-name', 'value')],
                       events=[Event('strategy-graph-update', 'interval')])
def update_strategy_values(strategy_name):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    # temp
    cryptocurrency_name = "Bitcoin"

    if len(symbol_evaluator_list) > 0:
        strategies_eval_list = symbol_evaluator_list[cryptocurrency_name].get_strategies_eval_list(exchange_list["binance"])
        eval_note = strategies_eval_list[0].get_eval_note()

        if check_valid_eval_note(eval_note):
            data = plotly.graph_objs.Scatter(
                x=time.time(),
                y=eval_note,
                name='Scatter',
                mode='lines+markers'
            )

            return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[0, time.time()]),
                                                        yaxis=dict(range=[-1, 1]), )}

    return {}
