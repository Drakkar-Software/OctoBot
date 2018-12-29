#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
import time
import copy

import ccxt

from backtesting.backtesting import Backtesting
from config import CONFIG_DEBUG_OPTION_PERF, CONFIG_NOTIFICATION_INSTANCE, CONFIG_EXCHANGES, \
    CONFIG_NOTIFICATION_GLOBAL_INFO, NOTIFICATION_STARTING_MESSAGE, CONFIG_CRYPTO_PAIRS, CONFIG_CRYPTO_CURRENCIES, \
    NOTIFICATION_STOPPING_MESSAGE, BOT_TOOLS_RECORDER, BOT_TOOLS_STRATEGY_OPTIMIZER, BOT_TOOLS_BACKTESTING, \
    CONFIG_EVALUATORS_WILDCARD
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
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator
from trading.util.trading_config_util import get_activated_trading_mode
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from evaluator import TA
from evaluator.TA import TAEvaluator

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
        self.startup_config = copy.deepcopy(config)
        self.edited_config = copy.deepcopy(config)
        self.ready = False
        self.watcher = None

        # tools: used for alternative operations on a bot on the fly (ex: backtesting started from web interface)
        self.tools = {
            BOT_TOOLS_BACKTESTING: None,
            BOT_TOOLS_STRATEGY_OPTIMIZER: None,
            BOT_TOOLS_RECORDER: None,
        }

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        # Advanced
        AdvancedManager.init_advanced_classes_if_necessary(self.config)

        # Debug tools
        self.performance_analyser = None
        if CONFIG_DEBUG_OPTION_PERF in self.config and self.config[CONFIG_DEBUG_OPTION_PERF]:
            self.performance_analyser = PerformanceAnalyser()

        # Init time frames using enabled strategies
        EvaluatorCreator.init_time_frames_from_strategies(self.config)
        self.time_frames = TimeFrameManager.get_config_time_frame(self.config)

        # Init relevant evaluator names list using enabled strategies
        self.relevant_evaluators = EvaluatorCreator.get_relevant_evaluators_from_strategies(self.config)

        # Backtesting
        self.backtesting_enabled = Backtesting.enabled(self.config)

        # Add services to self.config[CONFIG_CATEGORY_SERVICES]
        ServiceCreator.create_services(self.config, self.backtesting_enabled)

        # Notifier
        self.config[CONFIG_NOTIFICATION_INSTANCE] = Notification(self.config)

        # Notify starting
        if self.config[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
            self.config[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STARTING_MESSAGE, False)

        self.symbol_threads_manager = {}
        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.trading_mode = None
        self.exchange_trading_modes = {}
        self.exchanges_list = {}
        self.symbol_evaluator_list = {}
        self.crypto_currency_evaluator_list = {}
        self.dispatchers_list = []
        self.symbol_time_frame_updater_threads = []

    def create_exchange_traders(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                # Backtesting Exchange
                if self.backtesting_enabled:
                    exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=True)
                else:
                    # Real Exchange
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
                try:
                    self.trading_mode = get_activated_trading_mode(self.config)(self.config, exchange_inst)
                    self.exchange_trading_modes[exchange_inst.get_name()] = self.trading_mode
                    self.logger.debug(f"Using {self.trading_mode.get_name()} trading mode")
                except RuntimeError as e:
                    self.logger.error(e.args[0])
                    raise e
            else:
                self.logger.error(f"{exchange_class_string} exchange not found")

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
                                self.logger.warning(f"{exchange.get_name()} doesn't support {symbol}")

        self._check_required_evaluators()

    def _create_symbol_threads_managers(self, exchange, symbol_evaluator):

        if Backtesting.enabled(self.config):
            real_time_ta_eval_list = []
        else:
            # Create real time TA evaluators
            real_time_ta_eval_list = EvaluatorCreator.create_real_time_ta_evals(self.config,
                                                                                exchange,
                                                                                symbol_evaluator.get_symbol(),
                                                                                self.relevant_evaluators)
        symbol_time_frame_updater_thread = SymbolTimeFramesDataUpdaterThread()
        for time_frame in self.time_frames:
            if exchange.get_exchange_manager().time_frame_exists(time_frame.value, symbol_evaluator.get_symbol()):
                self.symbol_threads_manager[time_frame] = EvaluatorThreadsManager(self.config,
                                                                                  time_frame,
                                                                                  symbol_time_frame_updater_thread,
                                                                                  symbol_evaluator,
                                                                                  exchange,
                                                                                  self.exchange_trading_modes
                                                                                  [exchange.get_name()],
                                                                                  real_time_ta_eval_list,
                                                                                  self.relevant_evaluators)
            else:
                self.logger.warning(f"{exchange.get_name()} exchange is not supporting the required time frame: "
                                    f"'{time_frame.value}' for {symbol_evaluator.get_symbol()}.")
        self.symbol_time_frame_updater_threads.append(symbol_time_frame_updater_thread)

    def _check_required_evaluators(self):
        if self.symbol_threads_manager:
            etm = next(iter(self.symbol_threads_manager.values()))
            ta_list = etm.get_evaluator().get_ta_eval_list()
            if self.relevant_evaluators != CONFIG_EVALUATORS_WILDCARD:
                for required_eval in self.relevant_evaluators:
                    required_class = get_class_from_string(required_eval, TAEvaluator, TA, evaluator_parent_inspection)
                    if required_class and not self._class_is_in_list(ta_list, required_class):
                        self.logger.error(f"Missing technical analysis evaluator {required_class.get_name()} for "
                                          f"current strategy. Activate it in OctoBot advanced configuration interface "
                                          f"to allow activated strategy(ies) to work properly.")

    def start_threads(self):
        if self.performance_analyser:
            self.performance_analyser.start()

        for crypto_currency_evaluator in self.crypto_currency_evaluator_list.values():
            crypto_currency_evaluator.start_threads()

        for manager in self.symbol_threads_manager.values():
            manager.start_threads()

        for thread in self.symbol_time_frame_updater_threads:
            if self.watcher is not None:
                thread.set_watcher(self.watcher)
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

    @staticmethod
    def _class_is_in_list(class_list, required_klass):
        return any(required_klass in klass.get_parent_evaluator_classes() for klass in class_list)

    def set_watcher(self, watcher):
        self.watcher = watcher

    def get_symbols_threads_manager(self):
        return self.symbol_threads_manager

    def get_exchange_traders(self):
        return self.exchange_traders

    def get_exchange_trader_simulators(self):
        return self.exchange_trader_simulators

    def get_exchange_trading_modes(self):
        return self.exchange_trading_modes

    def get_exchanges_list(self):
        return self.exchanges_list

    def get_symbol_evaluator_list(self):
        return self.symbol_evaluator_list

    def get_symbols_list(self):
        return self.symbol_evaluator_list.keys()

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

    def get_config(self):
        return self.config

    def get_startup_config(self):
        return self.startup_config

    def get_edited_config(self):
        return self.edited_config

    def get_tools(self):
        return self.tools

    def get_trading_mode(self):
        return self.trading_mode
