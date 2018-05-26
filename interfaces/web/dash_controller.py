from dash.dependencies import Output, Event, Input

from config.cst import CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, CONFIG_TIME_FRAME
from interfaces import global_config
from interfaces.web import app_instance
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
                                     get_value_from_dict_or_string(time_frame, True),
                                     cryptocurrency_name)


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
                                                 get_value_from_dict_or_string(evaluator_name),
                                                 get_value_from_dict_or_string(time_frame, True),
                                                 cryptocurrency_name)


@app_instance.callback(Output('portfolio-value-graph', 'figure'),
                       events=[Event('portfolio-update', 'interval')])
def update_portfolio_value():
    update_portfolio_history()
    return get_portfolio_value_in_history()


@app_instance.callback(Output('datatable-portfolio', 'rows'),
                       events=[Event('portfolio-update', 'interval')])
def update_currencies_amounts():
    return get_portfolio_currencies_update()


@app_instance.callback(Output('symbol', 'options'),
                       [Input('exchange-name', 'value'),
                        Input('cryptocurrency-name', 'value')])
def update_symbol_dropdown_options(exchange_name, cryptocurrency_name):
    exchange = get_bot().get_exchanges_list()[exchange_name]
    symbol_list = []

    for symbol in global_config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency_name][CONFIG_CRYPTO_PAIRS]:
        if exchange.get_exchange_manager().symbol_exists(symbol):
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
        if exchange.get_exchange_manager().symbol_exists(symbol):
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
        if exchange.get_exchange_manager().time_frame_exists(TimeFrames(time_frame).value):
            time_frame_list.append({
                "label": time_frame,
                "value": time_frame
            })
    if time_frame_list:
        set_default_time_frame_for_this_symbol(time_frame_list[0]["value"])
    return time_frame_list


@app_instance.callback(Output('time-frame', 'value'),
                       [Input('exchange-name', 'value'),
                        Input('symbol', 'value')])
def update_time_frame_dropdown_value(exchange_name, symbol):
    exchange = get_bot().get_exchanges_list()[exchange_name]

    for time_frame in global_config[CONFIG_TIME_FRAME]:
        if exchange.get_exchange_manager().time_frame_exists(TimeFrames(time_frame).value):
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
def update_evaluator_dropdown_options(cryptocurrency_name, exchange_name, symbol, time_frame):
    symbol_evaluator = get_bot().get_symbol_evaluator_list()[get_value_from_dict_or_string(symbol)]
    exchange = get_bot().get_exchanges_list()[exchange_name]

    time_frame = get_value_from_dict_or_string(time_frame, True)
    evaluator_list = []
    evaluator_name_list = []

    # TA and Real time
    if time_frame in symbol_evaluator.get_evaluator_thread_managers(exchange):
        for ta in symbol_evaluator.get_evaluator_thread_managers(exchange)[time_frame] \
                .get_evaluator().get_ta_eval_list():
            if ta.get_name() not in evaluator_name_list:
                evaluator_name_list.append(ta.get_name())
                evaluator_list.append({
                    "label": ta.get_name(),
                    "value": ta.get_name()
                })

        for real_time in symbol_evaluator.get_evaluator_thread_managers(exchange)[time_frame] \
                .get_evaluator().get_real_time_eval_list():
            if real_time.get_name() not in evaluator_name_list:
                evaluator_name_list.append(real_time.get_name())
                evaluator_list.append({
                    "label": real_time.get_name(),
                    "value": real_time.get_name()
                })
    else:
        print(str(time_frame)+" not in: "+str(symbol_evaluator.get_evaluator_thread_managers(exchange)))

    # Socials
    for social in symbol_evaluator.get_crypto_currency_evaluator().get_social_eval_list():
        if social.get_name() not in evaluator_name_list:
            evaluator_name_list.append(social.get_name())
            evaluator_list.append({
                "label": social.get_name(),
                "value": social.get_name()
            })

    # strategies
    for strategies in symbol_evaluator.get_strategies_eval_list(exchange):
        if strategies.get_name() not in evaluator_name_list:
            evaluator_name_list.append(strategies.get_name())
            evaluator_list.append({
                "label": strategies.get_name(),
                "value": strategies.get_name()
            })

    return evaluator_list


@app_instance.callback(Output('evaluator-name', 'value'),
                       [Input('cryptocurrency-name', 'value'),
                        Input('exchange-name', 'value'),
                        Input('symbol', 'value'),
                        Input('time-frame', 'value')])
def update_evaluator_dropdown_values(cryptocurrency_name, exchange_name, symbol, time_frame):
    symbol_evaluator = get_bot().get_symbol_evaluator_list()[get_value_from_dict_or_string(symbol)]
    exchange = get_bot().get_exchanges_list()[exchange_name]
    first_strategy = next(iter(symbol_evaluator.get_strategies_eval_list(exchange))).get_name()

    return {
        "label": first_strategy,
        "value": first_strategy
    }
