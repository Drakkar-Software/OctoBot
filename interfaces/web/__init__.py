import copy

import dash
import time

import flask

server_instance = flask.Flask(__name__)
app_instance = dash.Dash(__name__, server=server_instance)
bot_instance = None
global_config = None

matrix_history = []
symbol_data_history = {}


def __init__(bot, config):
    global bot_instance
    bot_instance = bot

    global global_config
    global_config = config


def add_to_matrix_history(matrix):
    matrix_history.append({
        "matrix": copy.deepcopy(matrix.get_matrix()),
        "timestamp": time.time()
    })


def add_to_symbol_data_history(symbol, data, time_frame):
    if not symbol in symbol_data_history:
        symbol_data_history[symbol] = []

    symbol_data_history[symbol].append({
        "data": data,
        "timestamp": time.time(),
        "time_frame": time_frame
    })


def get_matrix_history():
    return matrix_history


def get_symbol_data_history():
    return symbol_data_history


def get_bot():
    return bot_instance


def load_callbacks():
    from .controller import update_values, update_strategy_values, update_symbol_dropdown, update_evaluator_dropdown
