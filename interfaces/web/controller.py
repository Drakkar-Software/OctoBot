import time

import dash
import plotly
import plotly.graph_objs as go
from dash.dependencies import Output, Event

from config.cst import PriceStrings, EvaluatorMatrixTypes
from evaluator.Strategies import TempFullMixedStrategiesEvaluator
from evaluator.evaluator_matrix import EvaluatorMatrix
from interfaces.web import app_instance, get_bot


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
    # temp
    cryptocurrency_name = "Bitcoin"

    return get_evaluator_graph_in_matrix_history(cryptocurrency_name,
                                          "binance",
                                          EvaluatorMatrixTypes.STRATEGIES,
                                          TempFullMixedStrategiesEvaluator.get_name())


def get_evaluator_graph_in_matrix_history(cryptocurrency_name,
                                          exchange_name,
                                          evaluator_type,
                                          evaluator_name,
                                          time_frame=None):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    if len(symbol_evaluator_list) > 0:
        matrix_inst = symbol_evaluator_list[cryptocurrency_name].get_matrix(exchange_list[exchange_name])

        formatted_matrix_history = {
            "timestamps": [],
            "evaluator_data": []
        }

        for matrix in matrix_inst.get_matrix_history().get_history():
            eval_note = EvaluatorMatrix.get_eval_note(matrix["matrix"], evaluator_type, evaluator_name, time_frame)
            if eval_note is not None:
                formatted_matrix_history["evaluator_data"].append(eval_note)
                formatted_matrix_history["timestamps"].append(matrix["timestamp"])

        data = plotly.graph_objs.Scatter(
            x=formatted_matrix_history["timestamps"],
            y=formatted_matrix_history["evaluator_data"],
            name='Scatter',
            mode='lines+markers'
        )

        return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[get_bot().get_start_time(), time.time()]),
                                                    yaxis=dict(range=[-1, 1]), )}
    return None
