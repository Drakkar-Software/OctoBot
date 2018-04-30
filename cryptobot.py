import logging

import ccxt

from backtesting.backtesting import Backtesting
from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import *
from evaluator.Updaters.symbol_time_frames_updater import SymbolTimeFramesDataUpdaterThread
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_threads_manager import EvaluatorThreadsManager
from evaluator.symbol_evaluator import SymbolEvaluator
from interfaces.web.app import WebApp
from services import ServiceCreator
from tools import Notification
from tools.performance_analyser import PerformanceAnalyser
from trading import Exchange
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator

"""Main CryptoBot class:
- Create all indicators and thread for each cryptocurrencies in config """


class CryptoBot:
    """
    Constructor :
    - Load configs
    """

    def __init__(self, config):
        self.config = config

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

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

        self.time_frames = Exchange.get_config_time_frame(self.config)

        # Add services to self.config[CONFIG_CATEGORY_SERVICES]
        ServiceCreator.create_services(self.config)

        # Notifier
        self.config[CONFIG_NOTIFICATION_INSTANCE] = Notification(self.config)

        # Notify starting
        self.config[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STARTING_MESSAGE)

        self.symbols_threads_manager = []
        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.exchanges_list = {}
        self.symbol_evaluator_list = []
        self.dispatchers_list = []
        self.symbol_time_frame_updater_threads = []

    def create_exchange_traders(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                # Backtesting Exchange
                if Backtesting.enabled(self.config):
                    exchange_inst = ExchangeSimulator(self.config, exchange_type)
                else:
                    # True Exchange
                    exchange_inst = Exchange(self.config, exchange_type)

                # create trader instance for this exchange
                exchange_trader = Trader(self.config, exchange_inst)
                exchange_trader_simulator = TraderSimulator(self.config, exchange_inst)

                self.exchanges_list[exchange_inst.get_name()] = exchange_inst
                self.exchange_traders[exchange_inst.get_name()] = exchange_trader
                self.exchange_trader_simulators[exchange_inst.get_name()] = exchange_trader_simulator
            else:
                self.logger.error("{0} exchange not found".format(exchange_class_string))

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        # create dispatchers
        self.dispatchers_list = EvaluatorCreator.create_dispatchers(self.config)

        # update crypto_currencies according to backtesting data if necessary
        if Backtesting.enabled(self.config):
            Backtesting.update_config_crypto_currencies(self.config, self.exchanges_list.values())

        # create Social and TA evaluators
        for crypto_currency, crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].items():

            # create symbol evaluator
            symbol_evaluator = SymbolEvaluator(self.config, crypto_currency, self.dispatchers_list)
            symbol_evaluator.set_traders(self.exchange_traders)
            symbol_evaluator.set_trader_simulators(self.exchange_trader_simulators)
            self.symbol_evaluator_list.append(symbol_evaluator)

            # create TA evaluators
            for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:

                for exchange in self.exchanges_list.values():
                    if exchange.enabled():

                        # Verify that symbol exists on this exchange
                        if exchange.symbol_exists(symbol):
                            self._create_symbol_threads_managers(symbol,
                                                                 exchange,
                                                                 symbol_evaluator)

                        # notify that exchange doesn't support this symbol
                        else:
                            self.logger.warning("{0} doesn't support {1}".format(exchange.get_name(), symbol))

    def _create_symbol_threads_managers(self, symbol, exchange, symbol_evaluator):
        # Create real time TA evaluators
        real_time_ta_eval_list = EvaluatorCreator.create_real_time_ta_evals(self.config,
                                                                            exchange,
                                                                            symbol)
        symbol_time_frame_updater_thread = SymbolTimeFramesDataUpdaterThread()
        for time_frame in self.time_frames:
            if exchange.time_frame_exists(time_frame.value):
                self.symbols_threads_manager.append(EvaluatorThreadsManager(self.config,
                                                                            symbol,
                                                                            time_frame,
                                                                            symbol_time_frame_updater_thread,
                                                                            symbol_evaluator,
                                                                            exchange,
                                                                            real_time_ta_eval_list))
        self.symbol_time_frame_updater_threads.append(symbol_time_frame_updater_thread)

    def start_threads(self):
        if self.performance_analyser:
            self.performance_analyser.start()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.start_threads()

        for manager in self.symbols_threads_manager:
            manager.start_threads()

        for thread in self.symbol_time_frame_updater_threads:
            thread.start()

        for thread in self.dispatchers_list:
            thread.start()

        self.logger.info("Evaluation threads started...")

    def join_threads(self):
        for manager in self.symbols_threads_manager:
            manager.join_threads()

        for thread in self.symbol_time_frame_updater_threads:
            thread.join()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.join_threads()

        for trader in self.exchange_traders:
            self.exchange_traders[trader].join_order_manager()

        for trader_simulator in self.exchange_trader_simulators:
            self.exchange_trader_simulators[trader_simulator].join_order_manager()

        for thread in self.dispatchers_list:
            thread.join()

        if self.performance_analyser:
            self.performance_analyser.join()

    def stop_threads(self):
        # Notify stopping
        self.config[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STOPPING_MESSAGE)

        self.logger.info("Stopping threads ...")

        for thread in self.symbol_time_frame_updater_threads:
            thread.stop()

        for manager in self.symbols_threads_manager:
            manager.stop_threads()

        for symbol_evaluator in self.symbol_evaluator_list:
            symbol_evaluator.stop_threads()

        for trader in self.exchange_traders:
            self.exchange_traders[trader].stop_order_manager()

        for trader_simulator in self.exchange_trader_simulators:
            self.exchange_trader_simulators[trader_simulator].stop_order_manager()

        for thread in self.dispatchers_list:
            thread.stop()

        if self.performance_analyser:
            self.performance_analyser.stop()

        if self.web_app.enabled():
            self.web_app.stop()
