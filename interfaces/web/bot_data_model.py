import time

import plotly
import plotly.graph_objs as go

from config.cst import TimeFrames, EvaluatorMatrixTypes, PriceIndexes, CONFIG_EVALUATOR, CONFIG_TENTACLES_KEY, \
    TENTACLE_PACKAGE_DESCRIPTION
from evaluator.evaluator_matrix import EvaluatorMatrix
from interfaces import get_reference_market, get_bot, set_default_time_frame, get_default_time_frame
from interfaces.trading_util import get_portfolio_current_value, get_trades_by_times_and_prices
from interfaces.web import add_to_matrix_history, get_matrix_history, add_to_symbol_data_history, \
    add_to_portfolio_value_history, get_portfolio_value_history, TIME_AXIS_TITLE, get_symbol_data_history
from tools.symbol_util import split_symbol
from tools.config_manager import ConfigManager
from tools.tentacle_manager.tentacle_package_manager import TentaclePackageManager
from tools.tentacle_manager.tentacle_package_util import get_is_url, get_package_name, \
    get_octobot_tentacle_public_repo, get_package_description_with_adaptation
from tools.tentacle_manager.tentacle_manager import TentacleManager
from trading.trader.portfolio import Portfolio


def get_value_from_dict_or_string(data, is_time_frame=False):
    if isinstance(data, dict):
        if is_time_frame:
            return TimeFrames(data["value"])
        else:
            return data["value"]
    else:
        if is_time_frame:
            if data is None:
                return get_default_time_frame()
            else:
                return TimeFrames(data)
        else:
            return data


def set_default_time_frame_for_this_symbol(time_frame_value):
    set_default_time_frame(TimeFrames(time_frame_value))


def get_portfolio_currencies_update():
    currencies = []
    bot = get_bot()
    traders = [trader for trader in bot.get_exchange_traders().values()] + \
              [trader for trader in bot.get_exchange_trader_simulators().values()]
    for trader in traders:
        currencies += [
            {
                "Cryptocurrency": [currency],
                "Total (available)": ["{} ({})".format(amounts[Portfolio.TOTAL],
                                                       amounts[Portfolio.AVAILABLE])],
                "Exchange": [trader.exchange.get_name()],
                "Real / Simulator": ["Simulator" if trader.get_simulate() else "Real"]
            }
            for currency, amounts in trader.get_portfolio().get_portfolio().items()]
    return currencies


def update_portfolio_history():
    _, _, real_value, simulated_value = get_portfolio_current_value()

    add_to_portfolio_value_history(real_value, simulated_value)


def get_portfolio_value_in_history():
    at_least_one_simulated = False
    at_least_one_real = False
    min_value = 0
    max_value = 1

    reference_market = get_reference_market()

    portfolio_value_in_history = get_portfolio_value_history()

    if max(portfolio_value_in_history["real_value"]) > 0:
        at_least_one_real = True
    if max(portfolio_value_in_history["simulated_value"]) > 0:
        at_least_one_simulated = True

    real_data = plotly.graph_objs.Scatter(
        x=portfolio_value_in_history["timestamp"],
        y=portfolio_value_in_history["real_value"],
        name='Real Portfolio in {}'.format(reference_market),
        mode='lines'
    )

    simulated_data = plotly.graph_objs.Scatter(
        x=portfolio_value_in_history["timestamp"],
        y=portfolio_value_in_history["simulated_value"],
        name='Simulated Portfolio in {}'.format(reference_market),
        mode='lines'
    )

    # Title
    real_simulated_string = "real" if at_least_one_real or not at_least_one_simulated else ""
    real_simulated_string += " and " if at_least_one_simulated and at_least_one_real else ""
    real_simulated_string += "simulated" if at_least_one_simulated else ""

    # merge two portfolio types
    merged_data = []
    if at_least_one_simulated:
        merged_data.append(simulated_data)
        min_value = min(portfolio_value_in_history["simulated_value"])
        max_value = max(portfolio_value_in_history["simulated_value"])
    if at_least_one_real or not at_least_one_simulated:
        merged_data.append(real_data)
        min_value = min(min_value, min(portfolio_value_in_history["real_value"]))
        max_value = max(max_value, max(portfolio_value_in_history["real_value"]))

    return {'data': merged_data,
            'layout': go.Layout(
                title='Portfolio value ({})'.format(real_simulated_string),
                xaxis=dict(range=[get_bot().get_start_time(), time.time()],
                           title=TIME_AXIS_TITLE),
                yaxis=dict(range=[max(0, min_value * 0.99), max(0.1, max_value * 1.01)],
                           title=reference_market)
            )}


def get_currency_graph_update(exchange_name, symbol, time_frame, cryptocurrency_name):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    if time_frame is not None:
        if len(symbol_evaluator_list) > 0:
            evaluator_thread_managers = symbol_evaluator_list[symbol].get_evaluator_thread_managers(
                exchange_list[exchange_name])

            if time_frame in evaluator_thread_managers:
                evaluator_thread_manager = evaluator_thread_managers[time_frame]
                data = evaluator_thread_manager.get_evaluator().get_data()

                if data is not None:
                    _, pair_tag = split_symbol(symbol)
                    add_to_symbol_data_history(symbol, data, time_frame)
                    data = get_symbol_data_history(symbol, time_frame)

                    # data.loc[:, PriceStrings.STR_PRICE_TIME.value] /= 1000

                    data_x = data[PriceIndexes.IND_PRICE_TIME.value]
                    data_y = data[PriceIndexes.IND_PRICE_CLOSE.value]

                    # Candlestick
                    ohlc_graph = go.Ohlc(x=data[PriceIndexes.IND_PRICE_TIME.value],
                                         open=data[PriceIndexes.IND_PRICE_OPEN.value],
                                         high=data[PriceIndexes.IND_PRICE_HIGH.value],
                                         low=data[PriceIndexes.IND_PRICE_LOW.value],
                                         close=data[PriceIndexes.IND_PRICE_CLOSE.value])

                    real_trades_prices, real_trades_times, simulated_trades_prices, simulated_trades_times = \
                        get_trades_by_times_and_prices()

                    real_trades_points = go.Scatter(
                        x=real_trades_prices,
                        y=real_trades_times,
                        mode='markers',
                        name='markers'
                    )

                    simulated_trades_points = go.Scatter(
                        x=simulated_trades_times,
                        y=simulated_trades_prices,
                        mode='markers',
                        name='markers'
                    )

                    return {'data': [ohlc_graph, real_trades_points, simulated_trades_points],
                            'layout': go.Layout(
                                title="{} real time data (per time frame)".format(cryptocurrency_name),
                                xaxis=dict(range=[min(data_x), max(data_x)],
                                           title=TIME_AXIS_TITLE),
                                yaxis=dict(range=[min(data_y) * 0.98, max(data_y) * 1.02],
                                           title=pair_tag)
                            )}
    return None


def get_evaluator_graph_in_matrix_history(symbol,
                                          exchange_name,
                                          evaluator_type,
                                          evaluator_name,
                                          time_frame,
                                          cryptocurrency_name):
    symbol_evaluator_list = get_bot().get_symbol_evaluator_list()
    exchange_list = get_bot().get_exchanges_list()

    if evaluator_name is not None and exchange_name and len(symbol_evaluator_list) > 0:
        matrix = symbol_evaluator_list[symbol].get_matrix(exchange_list[exchange_name])
        add_to_matrix_history(matrix)

        formatted_matrix_history = {
            "timestamps": [],
            "evaluator_data": []
        }

        for matrix in get_matrix_history():
            if evaluator_type == EvaluatorMatrixTypes.TA:
                eval_note = EvaluatorMatrix.get_eval_note(matrix["matrix"], evaluator_type, evaluator_name, time_frame)
            else:
                eval_note = EvaluatorMatrix.get_eval_note(matrix["matrix"], evaluator_type, evaluator_name)

            if eval_note is not None:
                formatted_matrix_history["evaluator_data"].append(eval_note)
                formatted_matrix_history["timestamps"].append(matrix["timestamp"])

        data = plotly.graph_objs.Scatter(
            x=formatted_matrix_history["timestamps"],
            y=formatted_matrix_history["evaluator_data"],
            name='Scatter',
            mode='lines+markers'
        )

        return {'data': [data],
                'layout': go.Layout(
                    title="{} strategy".format(cryptocurrency_name),
                    xaxis=dict(range=[get_bot().get_start_time(), time.time()],
                               title=TIME_AXIS_TITLE),
                    yaxis=dict(range=[-1.1, 1.1],
                               title="Buy or sell")
                )}
    return None


def get_evaluator_config():
    return get_bot().get_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().get_startup_config()[CONFIG_EVALUATOR]


def reset_evaluator_config():
    return update_evaluator_config(get_evaluator_startup_config())


def update_evaluator_config(new_config):
    current_config = get_bot().get_config()[CONFIG_EVALUATOR]
    try:
        ConfigManager.update_evaluator_config(new_config, current_config)
        return True
    except Exception:
        return False


def get_tentacles_packages():
    default_tentacles_repo_desc_file = get_octobot_tentacle_public_repo()
    default_tentacles_repo = get_octobot_tentacle_public_repo(False)
    packages = {
        default_tentacles_repo: get_package_name(default_tentacles_repo_desc_file,
                                                 get_is_url(default_tentacles_repo_desc_file))
    }
    for tentacle_package in get_bot().get_config()[CONFIG_TENTACLES_KEY]:
        packages[tentacle_package] = get_package_name(tentacle_package, get_is_url(tentacle_package))
    return packages


def get_tentacles_package_description(path_or_url):
    try:
        return get_package_description_with_adaptation(path_or_url)[TENTACLE_PACKAGE_DESCRIPTION]
    except Exception:
        return None


def register_and_install(path_or_url):
    config = get_bot().get_config()
    config[CONFIG_TENTACLES_KEY].append(path_or_url)
    #TODO update config.json
    
    tentacles_manager = TentacleManager(config)
    tentacles_manager.install_tentacle_package(path_or_url, True)
    return True


def get_tentacles():
    return TentaclePackageManager.get_installed_modules()
