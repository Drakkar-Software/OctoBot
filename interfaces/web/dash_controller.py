from dash.dependencies import Output, Event, Input

from config.cst import EvaluatorMatrixTypes, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, CONFIG_TIME_FRAME
from interfaces.web import app_instance, global_config
from interfaces.web.bot_data_model import *


@app_instance.callback(Output('live-graph', 'figure'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value')],
                       events=[Event('graph-update', 'interval')])
def update_values(exchange_name, cryptocurrency_name, symbol, time_frame):
    return get_currency_graph_update(exchange_name,
                                     get_value_from_dict_or_string(symbol),
                                     get_value_from_dict_or_string(time_frame, True))


@app_instance.callback(Output('strategy-live-graph', 'figure'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value'),
                        Input('evaluator-name', 'value')],
                       events=[Event('strategy-graph-update', 'interval')])
def update_strategy_values(exchange_name, cryptocurrency_name, symbol, time_frame, evaluator_name):
    return get_evaluator_graph_in_matrix_history(get_value_from_dict_or_string(symbol),
                                                 exchange_name,
                                                 EvaluatorMatrixTypes.STRATEGIES,
                                                 evaluator_name,
                                                 get_value_from_dict_or_string(time_frame, True))


@app_instance.callback(Output('portfolio-value-graph', 'figure'),
                       [Input('strategy-live-graph', 'figure')])
def update_portfolio_value(strategy_live_graph):
    return get_portfolio_value_in_history()


@app_instance.callback(Output('datatable-portfolio', 'rows'),
                       [Input('strategy-live-graph', 'figure')])
def update_currencies_amounts(strategy_live_graph):
    return get_portfolio_currencies_update()


@app_instance.callback(Output('symbol', 'options'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value')])
def update_symbol_dropdown_options(exchange_name, cryptocurrency_name):
    exchange = get_bot().get_exchanges_list()[exchange_name]
    symbol_list = []

    for symbol in global_config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency_name][CONFIG_CRYPTO_PAIRS]:
        if exchange.symbol_exists(symbol):
            symbol_list.append({
                "label": symbol,
                "value": symbol
            })

    return symbol_list


@app_instance.callback(Output('symbol', 'value'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value')])
def update_symbol_dropdown_value(exchange_name, cryptocurrency_name):
    exchange = get_bot().get_exchanges_list()[exchange_name]

    for symbol in global_config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency_name][CONFIG_CRYPTO_PAIRS]:
        if exchange.symbol_exists(symbol):
            return {
                "label": symbol,
                "value": symbol
            }

    return None


@app_instance.callback(Output('time-frame', 'options'),
                       [Input('exchange-name', 'value'),
                        Input('symbol', 'value')])
def update_time_frame_dropdown_options(exchange_name, symbol):
    exchange = get_bot().get_exchanges_list()[exchange_name]

    time_frame_list = []
    for time_frame in global_config[CONFIG_TIME_FRAME]:
        if exchange.time_frame_exists(TimeFrames(time_frame).value):
            time_frame_list.append({
                "label": time_frame,
                "value": time_frame
            })
    return time_frame_list


@app_instance.callback(Output('time-frame', 'value'),
                       [Input('exchange-name', 'value'),
                        Input('symbol', 'value')])
def update_time_frame_dropdown_options(exchange_name, symbol):
    exchange = get_bot().get_exchanges_list()[exchange_name]

    for time_frame in global_config[CONFIG_TIME_FRAME]:
        if exchange.time_frame_exists(TimeFrames(time_frame).value):
            return {
                "label": time_frame,
                "value": time_frame
            }
    return None


@app_instance.callback(Output('evaluator-name', 'options'),
                       [Input('cryptocurrency-name', 'value'),
                        Input('exchange-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value')])
def update_evaluator_dropdown(cryptocurrency_name, exchange_name, symbol, time_frame):
    symbol_evaluator = get_bot().get_symbol_evaluator_list()[get_value_from_dict_or_string(symbol)]
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
