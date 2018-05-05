import copy

import dash
import time

import flask
import logging

import cryptobot

server_instance = flask.Flask(__name__)
app_instance = dash.Dash(__name__, sharing=True, server=server_instance, url_base_pathname='/dashboard')
bot_instance = None
global_config = None

# disable Flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

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


def get_bot() -> cryptobot.CryptoBot:
    return bot_instance


def load_callbacks():
    from .dash_controller import update_values, \
        update_strategy_values, \
        update_time_frame_dropdown_options, \
        update_symbol_dropdown_options, \
        update_symbol_dropdown_value, \
        update_evaluator_dropdown, \
        update_currencies_amounts


def load_routes():
    from .flask_controller import index
