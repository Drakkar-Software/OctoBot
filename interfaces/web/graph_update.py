import time

import plotly
import plotly.graph_objs as go

from config.cst import PriceStrings, TimeFrames
from evaluator.evaluator_matrix import EvaluatorMatrix
from interfaces.web import get_bot, add_to_matrix_history, get_matrix_history, add_to_symbol_data_history


def get_currency_graph_update(exchange_name, symbol, time_frame):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    if time_frame is not None:
        time_frame = TimeFrames(time_frame)

        if len(symbol_evaluator_list) > 0:
            evaluator_thread_managers = symbol_evaluator_list[symbol].get_evaluator_thread_managers(
                exchange_list[exchange_name])

            for evaluator_thread_manager in evaluator_thread_managers:
                if evaluator_thread_manager.get_evaluator().get_time_frame() == time_frame:
                    df = evaluator_thread_manager.get_evaluator().get_data()

                    if df is not None:
                        add_to_symbol_data_history(symbol, df, time_frame)

                        X = df[PriceStrings.STR_PRICE_TIME.value]
                        Y = df[PriceStrings.STR_PRICE_CLOSE.value]

                        data = plotly.graph_objs.Scatter(
                            x=X,
                            y=Y,
                            name='Scatter',
                            mode='lines+markers'
                        )

                        return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(X), max(X)]),
                                                                    yaxis=dict(range=[min(Y)*0.98, max(Y)*1.02]), )}
    return None


def get_evaluator_graph_in_matrix_history(symbol,
                                          exchange_name,
                                          evaluator_type,
                                          evaluator_name,
                                          time_frame=None):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    if len(symbol_evaluator_list) > 0:
        matrix = symbol_evaluator_list[symbol].get_matrix(exchange_list[exchange_name])
        add_to_matrix_history(matrix)

        formatted_matrix_history = {
            "timestamps": [],
            "evaluator_data": []
        }

        for matrix in get_matrix_history():
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
