import logging
import time

import ccxt

from backtesting.backtesting import Backtesting
from config.cst import *
from evaluator.Updaters.symbol_time_frames_updater import SymbolTimeFramesDataUpdaterThread
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.cryptocurrency_evaluator import CryptocurrencyEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_threads_manager import EvaluatorThreadsManager
from evaluator.symbol_evaluator import SymbolEvaluator
from services import ServiceCreator
from tools.notifications import Notification
from tools.performance_analyser import PerformanceAnalyser
from tools.time_frame_manager import TimeFrameManager
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.modes import AbstractTradingMode, get_deep_class_from_string
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator

"""Main OctoBot class:
- Create all indicators and thread for each cryptocurrencies in config """


class OctoBot:
    """
    Constructor :
    - Load configs
    """

    def __init__(self, config):
        self.start_time = time.time()
        self.config = config
        self.ready = False

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

        # Advanced
        AdvancedManager.create_class_list(self.config)

        # Debug tools
        self.performance_analyser = None
        if CONFIG_DEBUG_OPTION_PERF in self.config and self.config[CONFIG_DEBUG_OPTION_PERF]:
            self.performance_analyser = PerformanceAnalyser()

        # Init time frames using enabled strategies
        EvaluatorCreator.init_time_frames_from_strategies(self.config)
        self.time_frames = TimeFrameManager.get_config_time_frame(self.config)

        # Init relevant evaluator names list using enabled strategies
        self.relevant_evaluators = EvaluatorCreator.get_relevant_evaluators_from_strategies(self.config)

        # Add services to self.config[CONFIG_CATEGORY_SERVICES]
        ServiceCreator.create_services(self.config)

        # Notifier
        self.config[CONFIG_NOTIFICATION_INSTANCE] = Notification(self.config)

        # Notify starting
        if self.config[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
            self.config[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STARTING_MESSAGE)

        # Backtesting
        self.backtesting_enabled = None

        self.symbol_threads_manager = {}
        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.exchange_trading_mode = {}
        self.exchanges_list = {}
        self.symbol_evaluator_list = {}
        self.crypto_currency_evaluator_list = {}
        self.dispatchers_list = []
        self.symbol_time_frame_updater_threads = []

    def create_exchange_traders(self):
        self.backtesting_enabled = Backtesting.enabled(self.config)

        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                # Backtesting Exchange
                if self.backtesting_enabled:
                    exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=True)
                else:
                    # True Exchange
                    exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False)

                exchange_inst = exchange_manager.get_exchange()
                self.exchanges_list[exchange_inst.get_name()] = exchange_inst

                # create trader instance for this exchange
                exchange_trader = Trader(self.config, exchange_inst)
                self.exchange_traders[exchange_inst.get_name()] = exchange_trader

                # create trader simulator instance for this exchange
                exchange_trader_simulator = TraderSimulator(self.config, exchange_inst)
                self.exchange_trader_simulators[exchange_inst.get_name()] = exchange_trader_simulator

                # create trading mode
                trading_mode_inst = self.get_trading_mode_class()(self.config, exchange_inst)
                self.exchange_trading_mode[exchange_inst.get_name()] = trading_mode_inst
            else:
                self.logger.error("{0} exchange not found".format(exchange_class_string))

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        # create dispatchers
        self.dispatchers_list = EvaluatorCreator.create_dispatchers(self.config)

        # create Social and TA evaluators
        for crypto_currency, crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].items():

            # create crypto_currency evaluator
            crypto_currency_evaluator = CryptocurrencyEvaluator(self.config, crypto_currency,
                                                                self.dispatchers_list, self.relevant_evaluators)
            self.crypto_currency_evaluator_list[crypto_currency] = crypto_currency_evaluator

            # create TA evaluators
            for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:

                # create symbol evaluator
                symbol_evaluator = SymbolEvaluator(self.config, symbol, crypto_currency_evaluator)
                symbol_evaluator.set_traders(self.exchange_traders)
                symbol_evaluator.set_trader_simulators(self.exchange_trader_simulators)

                crypto_currency_evaluator.add_symbol_evaluator(symbol, symbol_evaluator)
                self.symbol_evaluator_list[symbol] = symbol_evaluator

                for exchange in self.exchanges_list.values():
                    if exchange.get_exchange_manager().enabled():

                        # Verify that symbol exists on this exchange
                        if symbol in exchange.get_exchange_manager().get_traded_pairs():
                            self._create_symbol_threads_managers(exchange,
                                                                 symbol_evaluator)

                        # notify that exchange doesn't support this symbol
                        else:
                            if not self.backtesting_enabled:
                                self.logger.warning("{0} doesn't support {1}".format(exchange.get_name(), symbol))

    def _create_symbol_threads_managers(self, exchange, symbol_evaluator):
        # Create real time TA evaluators
        real_time_ta_eval_list = EvaluatorCreator.create_real_time_ta_evals(self.config,
                                                                            exchange,
                                                                            symbol_evaluator.get_symbol(),
                                                                            self.relevant_evaluators)
        symbol_time_frame_updater_thread = SymbolTimeFramesDataUpdaterThread()
        for time_frame in self.time_frames:
            if exchange.get_exchange_manager().time_frame_exists(time_frame.value):
                self.symbol_threads_manager[time_frame] = EvaluatorThreadsManager(self.config,
                                                                                  time_frame,
                                                                                  symbol_time_frame_updater_thread,
                                                                                  symbol_evaluator,
                                                                                  exchange,
                                                                                  self.exchange_trading_mode
                                                                                  [exchange.get_name()],
                                                                                  real_time_ta_eval_list,
                                                                                  self.relevant_evaluators)
        self.symbol_time_frame_updater_threads.append(symbol_time_frame_updater_thread)

    def start_threads(self):
        if self.performance_analyser:
            self.performance_analyser.start()

        for crypto_currency_evaluator in self.crypto_currency_evaluator_list.values():
            crypto_currency_evaluator.start_threads()

        for manager in self.symbol_threads_manager.values():
            manager.start_threads()

        for thread in self.symbol_time_frame_updater_threads:
            thread.start()

        for thread in self.dispatchers_list:
            thread.start()

        self.ready = True
        self.logger.info("Evaluation threads started...")

    def join_threads(self):
        for manager in self.symbol_threads_manager:
            self.symbol_threads_manager[manager].join_threads()

        for thread in self.symbol_time_frame_updater_threads:
            thread.join()

        for crypto_currency_evaluator in self.crypto_currency_evaluator_list.values():
            crypto_currency_evaluator.join_threads()

        for trader in self.exchange_traders.values():
            trader.join_order_manager()

        for trader_simulator in self.exchange_trader_simulators.values():
            trader_simulator.join_order_manager()

        for thread in self.dispatchers_list:
            thread.join()

        if self.performance_analyser:
            self.performance_analyser.join()

    def stop_threads(self):
        # Notify stopping
        if self.config[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
            self.config[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STOPPING_MESSAGE)

        self.logger.info("Stopping threads ...")

        for thread in self.symbol_time_frame_updater_threads:
            thread.stop()

        for manager in self.symbol_threads_manager.values():
            manager.stop_threads()

        for crypto_currency_evaluator in self.crypto_currency_evaluator_list.values():
            crypto_currency_evaluator.stop_threads()

        for trader in self.exchange_traders.values():
            trader.stop_order_manager()

        for trader_simulator in self.exchange_trader_simulators.values():
            trader_simulator.stop_order_manager()

        for thread in self.dispatchers_list:
            thread.stop()

        if self.performance_analyser:
            self.performance_analyser.stop()

        # stop services
        for service_instance in ServiceCreator.get_service_instances(self.config):
            try:
                service_instance.stop()
            except Exception as e:
                raise e

        # stop exchanges threads
        for exchange in self.exchanges_list.values():
            exchange.stop()

        self.logger.info("Threads stopped.")

    def get_trading_mode_class(self):
        if CONFIG_TRADER in self.config and CONFIG_TRADER_MODE in self.config[CONFIG_TRADER]:
            trading_mode_class = get_deep_class_from_string(self.config[CONFIG_TRADER][CONFIG_TRADER_MODE],
                                                            AbstractTradingMode)

            if trading_mode_class is not None:
                return trading_mode_class

        raise Exception("Please specify a valid trading mode in your config file (trader -> mode)")

    def get_symbols_threads_manager(self):
        return self.symbol_threads_manager

    def get_exchange_traders(self):
        return self.exchange_traders

    def get_exchange_trader_simulators(self):
        return self.exchange_trader_simulators

    def get_exchanges_list(self):
        return self.exchanges_list

    def get_symbol_evaluator_list(self):
        return self.symbol_evaluator_list

    def get_crypto_currency_evaluator_list(self):
        return self.crypto_currency_evaluator_list

    def get_dispatchers_list(self):
        return self.dispatchers_list

    def get_symbol_time_frame_updater_threads(self):
        return self.symbol_time_frame_updater_threads

    def get_start_time(self):
        return self.start_time

    def is_ready(self):
        return self.ready
