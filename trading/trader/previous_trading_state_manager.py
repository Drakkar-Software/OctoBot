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

from os import path, remove
import json

from config import SIMULATOR_STATE_SAVE_FILE, SIMULATOR_INITIAL_STARTUP_PORTFOLIO, SIMULATOR_CURRENT_PORTFOLIO, \
    SIMULATOR_TRADE_HISTORY, SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, WATCHED_MARKETS_INITIAL_STARTUP_VALUES, \
    SIMULATOR_REFERENCE_MARKET, REAL_INITIAL_STARTUP_PORTFOLIO, REAL_TRADE_HISTORY, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE
from config.config import load_config
from tools.config_manager import ConfigManager
from tools.logging.logging_util import get_logger
from trading.trader.portfolio import Portfolio


class PreviousTradingStateManager:

    ERROR_MESSAGE = "Impossible to start from the previous trading state: "

    def __init__(self, target_exchanges, reset_simulator, config, save_file=SIMULATOR_STATE_SAVE_FILE):
        self.logger = get_logger(self.__class__.__name__)
        self.save_file = save_file
        if reset_simulator:
            self.reset_trading_history()
        self.reset_state_history = False
        self._previous_state = {}
        if not self._load_previous_state(target_exchanges, config):
            self._previous_state = self._initialize_new_previous_state(target_exchanges)
            self.first_data = True
        else:
            self.first_data = False

    def should_initialize_data(self):
        return self.first_data

    def reset_trading_history(self):
        if path.isfile(self.save_file):
            remove(self.save_file)
        self.reset_state_history = True

    def update_previous_states(self, exchange, simulated_portfolio=None, trade=None, simulated_initial_portfolio=None,
                               real_initial_portfolio=None, simulated_initial_portfolio_value=None,
                               real_initial_portfolio_value=None, watched_markets_initial_values=None,
                               reference_market=None):
        if not self.reset_state_history:
            try:
                exchange_name = exchange.get_name()
                if simulated_portfolio is not None:
                    self._previous_state[exchange_name][SIMULATOR_CURRENT_PORTFOLIO] = \
                        {currency: value[Portfolio.TOTAL] for currency, value in simulated_portfolio.items()}
                if trade is not None:
                    trade_dict = trade.as_dict()
                    trade_key = REAL_TRADE_HISTORY
                    if trade.simulated:
                        trade_key = SIMULATOR_TRADE_HISTORY
                    self._previous_state[exchange_name][trade_key].append(trade_dict)
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
                    self._previous_state[exchange_name][SIMULATOR_REFERENCE_MARKET] = reference_market
                self._save_state_file()
            except Exception as e:
                self.logger.error(f"Error when saving simulator state: {e}")
                self.logger.exception(e)

    def has_previous_state(self, exchange):
        return exchange.get_name() in self._previous_state

    def get_previous_state(self, exchange, element):
        return self._previous_state[exchange.get_name()][element]

    def _save_state_file(self):
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
            SIMULATOR_CURRENT_PORTFOLIO: None,
            SIMULATOR_TRADE_HISTORY: [],
            REAL_TRADE_HISTORY: [],
            SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE: None,
            REAL_INITIAL_STARTUP_PORTFOLIO_VALUE: None,
            WATCHED_MARKETS_INITIAL_STARTUP_VALUES: None,
            SIMULATOR_REFERENCE_MARKET: None
        }

    def _load_previous_state(self, target_exchanges, config):
        if path.isfile(self.save_file):
            try:
                potential_previous_state = load_config(self.save_file)
                if isinstance(potential_previous_state, dict):
                    required_values = [SIMULATOR_INITIAL_STARTUP_PORTFOLIO, REAL_INITIAL_STARTUP_PORTFOLIO,
                                       SIMULATOR_CURRENT_PORTFOLIO, SIMULATOR_TRADE_HISTORY, REAL_TRADE_HISTORY,
                                       SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE, REAL_INITIAL_STARTUP_PORTFOLIO_VALUE,
                                       WATCHED_MARKETS_INITIAL_STARTUP_VALUES, SIMULATOR_REFERENCE_MARKET]
                    # check trading data
                    for exchange, state_data in potential_previous_state.items():
                        if all(v in state_data for v in required_values):
                            self._previous_state[exchange] = potential_previous_state[exchange]
                        else:
                            self.logger.warning(f"{self.ERROR_MESSAGE}Missing data in saving file.")
                            return False
                    # check symbol data
                    found_currencies_prices = {currency: False for currency in ConfigManager.get_all_currencies(config)}
                    for exchange_data in self._previous_state.values():
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
                    if not all(found_currencies_prices.values()):
                        missing_symbol = [c for c, v in found_currencies_prices.items() if not v]
                        self.logger.warning(f"{self.ERROR_MESSAGE}Missing symbol historical "
                                            f"data for {', '.join(missing_symbol)}.")
                        return False
                if not all(e in self._previous_state for e in target_exchanges):
                    missing_exchanges = [e for e in target_exchanges if e not in self._previous_state]
                    self.logger.warning(f"{self.ERROR_MESSAGE}Missing historical data from exchange(s): "
                                        f"{', '.join(missing_exchanges)}.")
                    return False
            except Exception as e:
                self.logger.warning(f"{self.ERROR_MESSAGE}{e}")
                return False
            return True
        else:
            return False
