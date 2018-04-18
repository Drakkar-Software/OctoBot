import logging
import sys
import traceback
from logging.config import fileConfig

import ccxt
from botcore.config.config import load_config

from config.cst import *
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_threads_manager import EvaluatorThreadsManager
from evaluator.symbol_evaluator import Symbol_Evaluator
from interfaces.web.app import WebApp
from tools import Notification
from tools.performance_analyser import PerformanceAnalyser
from trading import Exchange
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator
from services import ServiceCreator

"""Main CryptoBot class:
- Create all indicators and thread for each cryptocurrencies in config
"""


class Crypto_Bot:
    """
    Constructor :
    - Load configs
    """
    def __init__(self):
        # Logger
        fileConfig('config/logging_config.ini')
        self.logger = logging.getLogger(self.__class__.__name__)
        sys.excepthook = self.log_uncaught_exceptions

        # Version
        self.logger.info("Version : " + VERSION)

        # Config
        self.logger.info("Load config file...")
        self.config = load_config()

        # Advanced
        AdvancedManager.create_class_list(self.config)

        # Interfaces
        self.web_app = WebApp(self.config)
        if self.web_app.enabled():
            self.web_app.start()

        # Debug tools
        self.performance_analyser = None
        if CONFIG_DEBUG_OPTION_PERF in self.config and self.config[CONFIG_DEBUG_OPTION_PERF]:
            self.performance_analyser = PerformanceAnalyser()

        # TODO : CONFIG TEMP LOCATION
        self.time_frames = [TimeFrames.THIRTY_MINUTES, TimeFrames.ONE_HOUR, TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY]
        self.exchanges = [ccxt.binance]

        # Notifier
        self.notifier = Notification(self.config)

        # Add services to self.config[CONFIG_CATEGORY_SERVICES]
        ServiceCreator.create_services(self.config)

        self.symbols_threads_manager = []
        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.exchanges_list = {}
        self.symbol_evaluator_list = []
        self.dispatchers_list = []

    def create_exchange_traders(self):
        for exchange_type in self.exchanges:
            exchange_inst = Exchange(self.config, exchange_type)

            # create trader instance for this exchange
            exchange_trader = Trader(self.config, exchange_inst)
            exchange_trader_simulator = TraderSimulator(self.config, exchange_inst)

            self.exchanges_list[exchange_type.__name__] = exchange_inst
            self.exchange_traders[exchange_type.__name__] = exchange_trader
            self.exchange_trader_simulators[exchange_type.__name__] = exchange_trader_simulator

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        # create dispatchers
        self.dispatchers_list = EvaluatorCreator.create_dispatchers(self.config)

        # create Social and TA evaluators
        for crypto_currency, crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].items():

            # create symbol evaluator
            symbol_evaluator = Symbol_Evaluator(self.config, crypto_currency, self.dispatchers_list)
            symbol_evaluator.set_notifier(self.notifier)
            symbol_evaluator.set_traders(self.exchange_traders)
            symbol_evaluator.set_trader_simulators(self.exchange_trader_simulators)
            self.symbol_evaluator_list.append(symbol_evaluator)

            # create TA evaluators
            for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:

                for exchange_type in self.exchanges:
                    exchange = self.exchanges_list[exchange_type.__name__]

                    if exchange.enabled():

                        # Verify that symbol exists on this exchange
                        if exchange.symbol_exists(symbol):
                            self.create_symbol_threads_managers(symbol,
                                                                exchange,
                                                                symbol_evaluator)

                        # notify that exchange doesn't support this symbol
                        else:
                            self.logger.warning(exchange_type.__name__ + " doesn't support " + symbol)

    def create_symbol_threads_managers(self, symbol, exchange, symbol_evaluator):
        # Create real time TA evaluators
        real_time_ta_eval_list = EvaluatorCreator.create_real_time_ta_evals(self.config,
                                                                            exchange,
                                                                            symbol)
        for time_frame in self.time_frames:
            if exchange.time_frame_exists(time_frame.value):
                self.symbols_threads_manager.append(EvaluatorThreadsManager(self.config,
                                                                            symbol,
                                                                            time_frame,
                                                                            symbol_evaluator,
                                                                            exchange,
                                                                            real_time_ta_eval_list))

    def start_threads(self):
        if self.performance_analyser:
            self.performance_analyser.start()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.start_threads()

        for manager in self.symbols_threads_manager:
            manager.start_threads()

        for thread in self.dispatchers_list:
            thread.start()

        self.logger.info("Evaluation threads started...")

    def join_threads(self):
        for manager in self.symbols_threads_manager:
            manager.join_threads()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.join_threads()

        for trader in self.exchange_traders:
            self.exchange_traders[trader].stop_order_listeners()

        for trader_simulator in self.exchange_trader_simulators:
            self.exchange_trader_simulators[trader_simulator].stop_order_listeners()

        for thread in self.dispatchers_list:
            thread.join()

        if self.performance_analyser:
            self.performance_analyser.join()

    def stop_threads(self):
        self.logger.info("Stopping threads ...")
        for manager in self.symbols_threads_manager:
            manager.stop_threads()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.stop_threads()

        for trader in self.exchange_traders:
            self.exchange_traders[trader].stop_order_listeners()

        for trader_simulator in self.exchange_trader_simulators:
            self.exchange_trader_simulators[trader_simulator].stop_order_listeners()

        for thread in self.dispatchers_list:
            thread.stop()

        if self.performance_analyser:
            self.performance_analyser.stop()

        if self.web_app.enabled():
            self.web_app.stop()

    @staticmethod
    def log_uncaught_exceptions(ex_cls, ex, tb):
        logging.exception(''.join(traceback.format_tb(tb)))
        logging.exception('{0}: {1}'.format(ex_cls, ex))
