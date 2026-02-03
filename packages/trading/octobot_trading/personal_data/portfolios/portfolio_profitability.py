#  Drakkar-Software OctoBot-Trading
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
import decimal

import octobot_commons.logging as logging
import octobot_commons.symbols as symbol_util
import octobot_commons.tree as commons_tree
import octobot_commons.enums as commons_enums

import octobot_trading.util as util
import octobot_trading.constants as constants


class PortfolioProfitability:
    """
    PortfolioProfitability calculates the portfolio profitability
    by subtracting portfolio_current_value and portfolio_origin_value
    """

    def __init__(self, portfolio_manager):
        self.portfolio_manager = portfolio_manager
        self.value_manager = portfolio_manager.portfolio_value_holder
        self.logger: logging.BotLogger = logging.get_logger(f"{self.__class__.__name__}["
                                         f"{self.portfolio_manager.exchange_manager.exchange_name}]")

        # profitability attributes
        self.profitability: decimal.Decimal = constants.ZERO
        self.profitability_percent: decimal.Decimal = constants.ZERO
        self.profitability_diff: decimal.Decimal = constants.ZERO
        self.market_profitability_percent: decimal.Decimal = constants.ZERO
        self.initial_portfolio_current_profitability: decimal.Decimal = constants.ZERO

        # buffer of currencies excluding market only used currencies ex: conf = btc/usd, eth/btc, ltc/btc, here usd
        # is market only => not used to compute market average profitability
        self.traded_currencies_without_market_specific: set[str] = set()

        # set of currencies that should be valuated because either present in config or as a reference market
        self.valuated_currencies: set[str] = util.get_all_currencies(self.portfolio_manager.config, enabled_only=False)
        self.valuated_currencies.add(self.portfolio_manager.reference_market)

    def reset_profitability(self):
        self._reset_before_profitability_calculation()

    def get_average_market_profitability(self):
        """
        Returns the % move average of all the watched cryptocurrencies between bot's start time and now
        :return: the average market profitability
        """
        self.portfolio_manager.portfolio_value_holder.get_current_crypto_currencies_values()
        return self._calculate_average_market_profitability()

    def update_profitability(self, force_recompute_origin_portfolio=False):
        """
        Get profitability calls get_currencies_prices to update required data
        Then calls get_portfolio_current_value to set the current value of portfolio_current_value attribute
        :return: True if changed else False
        """
        self._reset_before_profitability_calculation()
        try:
            set_init_event = self.portfolio_manager.portfolio_value_holder.portfolio_current_value == constants.ZERO
            self.portfolio_manager.handle_profitability_recalculation(force_recompute_origin_portfolio)
            self._update_profitability_calculation()
            if set_init_event:
                self._set_initialized_event()
            return self.profitability_diff != constants.ZERO
        except KeyError as missing_data_exception:
            self.logger.warning(f"Missing {missing_data_exception} ticker data to calculate profitability")
        except Exception as missing_data_exception:
            self.logger.exception(missing_data_exception, True, str(missing_data_exception))

    def _set_initialized_event(self):
        commons_tree.EventProvider.instance().trigger_event(
            self.portfolio_manager.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.portfolio_manager.exchange_manager.exchange_name,
                commons_enums.InitializationEventExchangeTopics.PROFITABILITY.value
            )
        )

    def _reset_before_profitability_calculation(self):
        """
        Prepare profitability calculation
        """
        self.profitability_diff = self.profitability_percent
        self.profitability = constants.ZERO
        self.profitability_percent = constants.ZERO
        self.market_profitability_percent = constants.ZERO
        self.initial_portfolio_current_profitability = constants.ZERO

    def _update_profitability_calculation(self):
        """
        Calculates the new portfolio profitability
        """
        initial_portfolio_current_value = self.value_manager.get_origin_portfolio_current_value()
        self.profitability = self.value_manager.portfolio_current_value - self.value_manager.portfolio_origin_value

        if self.value_manager.portfolio_origin_value > constants.ZERO:
            self.profitability_percent = (constants.ONE_HUNDRED * self.value_manager.portfolio_current_value /
                                          self.value_manager.portfolio_origin_value) - constants.ONE_HUNDRED
            self.initial_portfolio_current_profitability = (constants.ONE_HUNDRED * initial_portfolio_current_value /
                                                            self.value_manager.portfolio_origin_value) - \
                                                           constants.ONE_HUNDRED
        else:
            self.profitability_percent = constants.ZERO
        self._update_portfolio_delta()

    def _update_portfolio_delta(self):
        """
        Calculates difference between the current and the last portfolio
        """
        self.profitability_diff = self.profitability_percent - self.profitability_diff
        self.market_profitability_percent = self.get_average_market_profitability()

    def _calculate_average_market_profitability(self):
        """
        Calculate the average of all the watched cryptocurrencies between bot's start time and now
        :return: the calculation result
        """
        origin_values = [
            value / self.value_manager.origin_crypto_currencies_values[currency]
            for currency, value in self._get_trading_currencies_values(
                self.value_manager.current_crypto_currencies_values
            ).items()
            if self.value_manager.origin_crypto_currencies_values[currency] > constants.ZERO
        ]
        return sum(origin_values) / len(origin_values) * constants.ONE_HUNDRED - constants.ONE_HUNDRED \
            if origin_values else constants.ZERO

    def _get_trading_currencies_values(self, currency_dict):
        """
        Return the dict of traded currencies with their portfolio value.
        :param currency_dict: the value by currency dictionary
        :return: the currency portfolio value filtered
        """
        if not self.traded_currencies_without_market_specific:
            self._init_traded_currencies_without_market_specific()
        return {
            currency: v
            for currency, v in currency_dict.items()
            if currency in self.traded_currencies_without_market_specific
        }

    def _init_traded_currencies_without_market_specific(self):
        """
        Initialize traded currencies without market specific set
        Use exchange_config.traded_symbols to take every config pair into account except disabled ones
        """
        self.traded_currencies_without_market_specific = set(
            symbol_util.parse_symbol(pair).base
            for pair in self.portfolio_manager.exchange_manager.exchange_config.traded_symbol_pairs
        )
