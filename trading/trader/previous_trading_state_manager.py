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

from os import path, remove, makedirs
import json
import regex

from config import SIMULATOR_STATE_SAVE_FILE, SIMULATOR_INITIAL_STARTUP_PORTFOLIO, SIMULATOR_CURRENT_PORTFOLIO, \
    SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, WATCHED_MARKETS_INITIAL_STARTUP_VALUES, REFERENCE_MARKET, \
    REAL_INITIAL_STARTUP_PORTFOLIO, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE, STATES_FOLDER, LOG_FILE, \
    CURRENT_PORTFOLIO_STRING, CONFIG_TRADING, CONFIG_ENABLED_PERSISTENCE, CONFIG_TRADER_REFERENCE_MARKET
from config.config import load_config
from tools.config_manager import ConfigManager
from tools.logging.logging_util import get_logger
from trading.trader.portfolio import Portfolio


class PreviousTradingStateManager:

    ERROR_MESSAGE = "Impossible to start from the previous trading state: "

    def __init__(self, target_exchanges, reset_simulator, config,
                 save_file=SIMULATOR_STATE_SAVE_FILE, log_file=LOG_FILE):
        self.logger = get_logger(self.__class__.__name__)
        self.save_file = save_file
        self.log_file = log_file
        if reset_simulator:
            self.reset_trading_history()
        self.reset_state_history = False
        self._previous_state = {}
        try:
            if not self._load_previous_state(target_exchanges, config):
                self._previous_state = self._initialize_new_previous_state(target_exchanges)
                self.first_data = True
            else:
                self.first_data = False
        except Exception as e:
            self.logger.error(f"{self.ERROR_MESSAGE}{e}")
            self.logger.exception(e)
            self._previous_state = self._initialize_new_previous_state(target_exchanges)
            self.first_data = True

    @staticmethod
    def enabled(config):
        return CONFIG_TRADING in config and CONFIG_ENABLED_PERSISTENCE in config[CONFIG_TRADING] \
               and config[CONFIG_TRADING][CONFIG_ENABLED_PERSISTENCE]

    def should_initialize_data(self):
        return self.first_data

    def reset_trading_history(self):
        if path.isfile(self.save_file):
            self.logger.info("Resetting trading history")
            remove(self.save_file)
        self.reset_state_history = True

    def update_previous_states(self, exchange, simulated_initial_portfolio=None, real_initial_portfolio=None,
                               simulated_initial_portfolio_value=None, real_initial_portfolio_value=None,
                               watched_markets_initial_values=None, reference_market=None):
        if not self.reset_state_history:
            try:
                exchange_name = exchange.get_name()
                if simulated_initial_portfolio is not None:
                    self._previous_state[exchange_name][SIMULATOR_INITIAL_STARTUP_PORTFOLIO] =  \
                        {currency: value[Portfolio.TOTAL] for currency, value in simulated_initial_portfolio.items()}
                if real_initial_portfolio is not None:
                    self._previous_state[exchange_name][REAL_INITIAL_STARTUP_PORTFOLIO] =  \
                        {currency: value[Portfolio.TOTAL] for currency, value in real_initial_portfolio.items()}
                if simulated_initial_portfolio_value is not None:
                    self._previous_state[exchange_name][SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE] = \
                        simulated_initial_portfolio_value
                if real_initial_portfolio_value is not None:
                    self._previous_state[exchange_name][REAL_INITIAL_STARTUP_PORTFOLIO_VALUE] = \
                        real_initial_portfolio_value
                if watched_markets_initial_values is not None:
                    self._previous_state[exchange_name][WATCHED_MARKETS_INITIAL_STARTUP_VALUES] = \
                        watched_markets_initial_values
                if reference_market is not None:
                    self._previous_state[exchange_name][REFERENCE_MARKET] = reference_market
                self._save_state_file()
            except Exception as e:
                self.logger.error(f"Error when saving simulator state: {e}")
                self.logger.exception(e)

    def has_previous_state(self, exchange):
        return exchange.get_name() in self._previous_state

    def get_previous_state(self, exchange, element):
        return self._previous_state[exchange.get_name()][element]

    def _save_state_file(self):
        if not path.isdir(STATES_FOLDER):
            makedirs(STATES_FOLDER)
        with open(self.save_file, 'w') as state_file:
            json.dump(self._previous_state, state_file, indent=True)

    @staticmethod
    def _initialize_new_previous_state(target_exchanges):
        return {exchange: PreviousTradingStateManager._get_previous_state_model() for exchange in target_exchanges}

    @staticmethod
    def _get_previous_state_model():
        return {
            SIMULATOR_INITIAL_STARTUP_PORTFOLIO: None,
            REAL_INITIAL_STARTUP_PORTFOLIO: None,
            SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE: None,
            REAL_INITIAL_STARTUP_PORTFOLIO_VALUE: None,
            WATCHED_MARKETS_INITIAL_STARTUP_VALUES: None,
            REFERENCE_MARKET: None
        }

    def _load_previous_state(self, target_exchanges, config):
        if self._load_previous_state_metadata(target_exchanges, config):
            if ConfigManager.get_trader_simulator_enabled(config):
                return self._load_previous_state_portfolios(target_exchanges)
            else:
                return True
        else:
            return False

    def _load_previous_state_metadata(self, target_exchanges, config):
        if path.isfile(self.save_file):
            try:
                potential_previous_state = load_config(self.save_file)
                if isinstance(potential_previous_state, dict):
                    if not self._check_required_values(potential_previous_state):
                        return False
                    # check data
                    found_currencies_prices = {currency: False for currency in ConfigManager.get_all_currencies(config)}
                    if not self._check_exchange_data(config, found_currencies_prices):
                        return False
                    if not self._check_missing_symbols(found_currencies_prices):
                        return False
                if not self._check_no_missing_exchanges(target_exchanges):
                    return False
            except Exception as e:
                self.logger.warning(f"{self.ERROR_MESSAGE}{e}")
                return False
            return True
        else:
            return False

    def _check_required_values(self, potential_previous_state):
        required_values = [SIMULATOR_INITIAL_STARTUP_PORTFOLIO, REAL_INITIAL_STARTUP_PORTFOLIO,
                           SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE,
                           WATCHED_MARKETS_INITIAL_STARTUP_VALUES, REFERENCE_MARKET]
        # check trading data
        for exchange, state_data in potential_previous_state.items():
            if all(v in state_data for v in required_values):
                self._previous_state[exchange] = potential_previous_state[exchange]
            else:
                self.logger.warning(f"{self.ERROR_MESSAGE}Missing data in saving file.")
                return False
        return True

    def _check_exchange_data(self, config, found_currencies_prices):
        for exchange_data in self._previous_state.values():
            # check currencies
            missing_traded_currencies = set()
            for currency in exchange_data[WATCHED_MARKETS_INITIAL_STARTUP_VALUES].keys():
                if currency in found_currencies_prices:
                    found_currencies_prices[currency] = True
                else:
                    missing_traded_currencies.add(currency)
            if missing_traded_currencies:
                self.logger.warning(f"{self.ERROR_MESSAGE}Missing trading pair(s) for "
                                    f"{', '.join(missing_traded_currencies)}.")
                return False
            # check reference market
            if exchange_data[REFERENCE_MARKET] != config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET]:
                self.logger.warning(f"{self.ERROR_MESSAGE}Reference market changed, "
                                    f"reinitializing traders.")
                return False

            # check initial portfolios and portfolios values
            if ConfigManager.get_trader_simulator_enabled(config):
                if exchange_data[SIMULATOR_INITIAL_STARTUP_PORTFOLIO] is None \
                        or exchange_data[SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE] is None:
                    return False
            if ConfigManager.get_trader_enabled(config):
                if exchange_data[REAL_INITIAL_STARTUP_PORTFOLIO] is None\
                        or exchange_data[REAL_INITIAL_STARTUP_PORTFOLIO_VALUE] is None:
                    return False
        return True

    def _check_missing_symbols(self, found_currencies_prices):
        if not all(found_currencies_prices.values()):
            missing_symbol = [c for c, v in found_currencies_prices.items() if not v]
            self.logger.warning(f"{self.ERROR_MESSAGE}Missing symbol historical "
                                f"data for {', '.join(missing_symbol)}.")
            return False
        return True

    def _check_no_missing_exchanges(self, target_exchanges):
        if not all(e in self._previous_state for e in target_exchanges):
            missing_exchanges = [e for e in target_exchanges if e not in self._previous_state]
            self.logger.warning(f"{self.ERROR_MESSAGE}Missing historical data from exchange(s): "
                                f"{', '.join(missing_exchanges)}.")
            return False
        return True

    def _load_previous_state_portfolios(self, target_exchanges):
        # read previous executions log files to reconstruct previous portfolios
        to_load_exchanges = set(target_exchanges.keys())
        for i in range(1, 21):
            file_name = f"{self.log_file}.{i}"
            if path.isfile(file_name):
                with open(file_name) as f:
                    for line in reversed(list(f)):
                        if CURRENT_PORTFOLIO_STRING in line:
                            exchange_name, is_simulator = self._extract_exchange_name(line)
                            if exchange_name is not None and is_simulator and exchange_name in self._previous_state \
                                    and SIMULATOR_CURRENT_PORTFOLIO not in self._previous_state[exchange_name]:
                                extracted_portfolio = self._extract_portfolio(line)
                                if extracted_portfolio is not None:
                                    self._previous_state[exchange_name][SIMULATOR_CURRENT_PORTFOLIO] = \
                                        extracted_portfolio
                                if exchange_name in to_load_exchanges:
                                    to_load_exchanges.remove(exchange_name)
                                if not to_load_exchanges:
                                    return True
        return not to_load_exchanges

    @staticmethod
    def _extract_exchange_name(line):
        if "PortfolioSimulator[ExchangeSimulator" in line:
            # for tests
            left_split_line = line.split("PortfolioSimulator[")
            right_split_line = left_split_line[1].split("]]")
            return f"{right_split_line[0]}]", True
        else:
            split_pattern = regex.compile(r"\[|]")
            split_line = split_pattern.split(line)
            if len(split_line) == 3:
                is_simulator = "Simulator" in split_line[0]
                return split_line[1], is_simulator
            return None, None

    def _extract_portfolio(self, line):
        split_line = line.split(CURRENT_PORTFOLIO_STRING)
        if len(split_line) == 2:
            try:
                read_portfolio = json.loads(split_line[1].strip().replace("\'", "\""))
                return self._transform_portfolio(read_portfolio)
            except json.JSONDecodeError as e:
                self.logger.debug(f"Error when extracting log portfolio: {e}")
                return None
        return None

    @staticmethod
    def _transform_portfolio(read_portfolio):
        portfolio = {}
        for key, val in read_portfolio.items():
            if not (Portfolio.AVAILABLE in val and Portfolio.TOTAL in val):
                return None
            else:
                portfolio[key] = val[Portfolio.TOTAL]
        return portfolio
