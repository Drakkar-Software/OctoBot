from dash.dependencies import Output, Event, Input

from config.cst import EvaluatorMatrixTypes, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, CONFIG_TIME_FRAME, \
    TimeFrames
from interfaces.web import app_instance, global_config, get_bot
from interfaces.web.graph_update import get_evaluator_graph_in_matrix_history, get_currency_graph_update


@app_instance.callback(Output('live-graph', 'figure'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value')],
                       events=[Event('graph-update', 'interval')])
def update_values(exchange_name, cryptocurrency_name, symbol, time_frame):
    return get_currency_graph_update(cryptocurrency_name,
                                     exchange_name,
                                     symbol,
                                     time_frame)


@app_instance.callback(Output('strategy-live-graph', 'figure'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value'),
                        Input('evaluator-name', 'value')],
                       events=[Event('strategy-graph-update', 'interval')])
def update_strategy_values(exchange_name, cryptocurrency_name, symbol, time_frame, evaluator_name):
    return get_evaluator_graph_in_matrix_history(cryptocurrency_name,
                                                 exchange_name,
                                                 EvaluatorMatrixTypes.STRATEGIES,
                                                 evaluator_name)


@app_instance.callback(Output('symbol', 'options'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value')])
def update_symbol_dropdown(exchange_name, cryptocurrency_name):
    exchange = get_bot().get_exchanges_list()[exchange_name]
    symbol_list = []

    for symbol in global_config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency_name][CONFIG_CRYPTO_PAIRS]:
        if exchange.symbol_exists(symbol):
            symbol_list.append({
                "label": symbol,
                "value": symbol
            })

    return symbol_list


@app_instance.callback(Output('time-frame', 'options'),
                       [Input('exchange-name', 'value'),
                        Input('symbol', 'value')])
def update_symbol_dropdown(exchange_name, symbol):
    exchange = get_bot().get_exchanges_list()[exchange_name]

    time_frame_list = []
    for time_frame in global_config[CONFIG_TIME_FRAME]:
        if exchange.time_frame_exists(TimeFrames(time_frame).value):
            time_frame_list.append({
                "label": time_frame,
                "value": time_frame
            })
    return time_frame_list


@app_instance.callback(Output('evaluator-name', 'options'),
                       [Input('cryptocurrency-name', 'value'),
                        Input('exchange-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value')])
def update_evaluator_dropdown(cryptocurrency_name, exchange_name, symbol, time_frame):
    symbol_evaluator = get_bot().get_symbol_evaluator_list()[cryptocurrency_name]
    exchange = get_bot().get_exchanges_list()[exchange_name]

    evaluator_list = []
    evaluator_name_list = []
    for strategies in symbol_evaluator.get_strategies_eval_list(exchange):
        if strategies.get_name() not in evaluator_name_list:
            evaluator_name_list.append(strategies.get_name())
            evaluator_list.append({
                "label": strategies.get_name(),
                "value": strategies.get_name()
            })

    return evaluator_list
