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

import octobot_backtesting.api as backtesting_api
import octobot_backtesting.importers as importers

import octobot_commons.symbols as symbol_util
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.constants as commons_constants

import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchanges.connectors.simulator.exchange_simulator_adapter as exchange_simulator_adapter
import octobot_trading.exchanges.connectors.simulator.ccxt_client_simulation as ccxt_client_simulation
import octobot_trading.exchange_data as exchange_data
import octobot_trading.exchanges.util as util


class ExchangeSimulatorConnector(abstract_exchange.AbstractExchange):
    def __init__(self, config, exchange_manager, backtesting, adapter_class=None):
        super().__init__(config, exchange_manager, None)
        self.backtesting = backtesting
        self.allowed_time_lag = constants.DEFAULT_BACKTESTING_TIME_LAG
        self.adapter = self.get_adapter_class(adapter_class)(self)

        self.exchange_importers = []

        self.current_future_candles = {}

        self.is_authenticated = False
        self._forced_market_statuses: dict = None
        self._missing_market_statuses: set = set()

    async def initialize_impl(self):
        self.exchange_importers = self.backtesting.get_importers(importers.ExchangeDataImporter)
        # load symbols and time frames
        for importer in self.exchange_importers:
            self.symbols.update(backtesting_api.get_available_symbols(importer))
            self.time_frames.update(importer.time_frames)

        # remove duplicates
        self.current_future_candles = {
            symbol: {}
            for symbol in self.symbols
        }

        # set exchange manager attributes
        self.exchange_manager.client_symbols = list(self.symbols)

        # init _forced_market_statuses when allowed
        if self.exchange_manager.use_cached_markets:
            additional_client_config = await self._get_additional_client_config()
            self._init_forced_market_statuses(additional_client_config)

    def get_adapter_class(self, adapter_class):
        return adapter_class or exchange_simulator_adapter.ExchangeSimulatorAdapter

    def _init_forced_market_statuses(self, additional_client_config):
        def market_filter(market):
            return market[enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value] in self.symbols

        self._forced_market_statuses = ccxt_client_simulation.parse_markets(
            self._get_exchange_class_rest_name(), additional_client_config, market_filter
        )

    def _get_exchange_class_rest_name(self):
        if self.exchange_manager.exchange.exchange_tentacle_class:
            return self.exchange_manager.exchange.exchange_tentacle_class.get_rest_name(self.exchange_manager)
        return self.exchange_manager.exchange_class_string

    async def _get_additional_client_config(self) -> dict:
        if (
            self.exchange_manager.exchange.exchange_tentacle_class
            and self.exchange_manager.exchange.exchange_tentacle_class.HAS_FETCHED_DETAILS
        ):
            await self.exchange_manager.exchange.exchange_tentacle_class.fetch_exchange_config(
                self.exchange_manager.exchange.exchange_config_by_exchange, self.exchange_manager
            )
            return self.exchange_manager.exchange.exchange_tentacle_class.get_custom_url_config(
                self.exchange_manager.exchange.exchange_config_by_exchange.get(
                    self.exchange_manager.exchange.exchange_tentacle_class.__name__, {}
                ), self.exchange_manager.exchange_name
            )
        return {}

    def should_adapt_market_statuses(self) -> bool:
        return self.exchange_manager.use_cached_markets

    def get_contract_size(self, symbol: str):
        market_status, _ = self.get_market_status(symbol, with_fixer=False)
        return ccxt_client_simulation.get_contract_size(market_status)

    @classmethod
    def load_user_inputs_from_class(cls, tentacles_setup_config, tentacle_config):
        # no user input in connector
        pass

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        return True

    @classmethod
    def is_simulated_exchange(cls) -> bool:
        return True

    @staticmethod
    def handles_real_data_for_updater(channel_type, available_data):
        if channel_type in exchange_data.SIMULATOR_PRODUCERS_TO_REAL_DATA_TYPE:
            return all(data_type in available_data
                       for data_type in exchange_data.SIMULATOR_PRODUCERS_TO_REAL_DATA_TYPE[channel_type])
        return True

    async def create_backtesting_exchange_producers(self):
        for importer in self.exchange_importers:
            available_data_types = backtesting_api.get_available_data_types(importer)
            at_least_one_updater = False
            for channel_type, updater in exchange_data.UNAUTHENTICATED_UPDATER_SIMULATOR_PRODUCERS.items():
                if self._are_required_data_available(channel_type, available_data_types):
                    await updater(exchange_channel.get_chan(updater.CHANNEL_NAME,
                                                            self.exchange_manager.id), importer).run()
                    at_least_one_updater = True
            if not at_least_one_updater:
                self.logger.error(f"No updater created for {importer.symbols} backtesting")

    @staticmethod
    def _are_required_data_available(channel_type, available_data_types):
        if channel_type not in exchange_data.SIMULATOR_PRODUCERS_TO_POSSIBLE_DATA_TYPE:
            # no required data if updater is not in SIMULATOR_PRODUCERS_TO_DATA_TYPE keys
            return True
        else:
            # if updater is in SIMULATOR_PRODUCERS_TO_DATA_TYPE keys: check that at least one of the required data is
            # available
            return any(required_data_type in available_data_types
                       for required_data_type in exchange_data.SIMULATOR_PRODUCERS_TO_POSSIBLE_DATA_TYPE[channel_type])

    async def stop(self):
        self.backtesting = None
        self.exchange_importers = []
        self.exchange_manager = None

    def get_exchange_current_time(self):
        return backtesting_api.get_backtesting_current_time(self.backtesting)

    def get_available_time_frames(self):
        if self.exchange_importers:
            return [time_frame.value
                    for time_frame in backtesting_api.get_available_time_frames(next(iter(self.exchange_importers)))]
        return []

    def get_backtesting_data_files(self):
        return [backtesting_api.get_data_file_path(importer) for importer in self.exchange_importers]

    def get_market_status(self, symbol, price_example=0, with_fixer=True):
        if self._forced_market_statuses:
            try:
                if with_fixer:
                    return util.ExchangeMarketStatusFixer(
                        self._forced_market_statuses[symbol], price_example
                    ).market_status
                return self._forced_market_statuses[symbol], True
            except KeyError:
                self._missing_market_statuses.add(symbol)
                if len(self._missing_market_statuses) >= len(self.symbols) - 1:
                    # issue: almost all market statuses are missing
                    raise errors.NotSupported(
                        f"Missing too many market statuses: {self._missing_market_statuses}, "
                        f"traded symbols: {self.symbols}"
                    )
                else:
                    self.logger.warning(f"Missing cached market status for {symbol}: using default market status")
        return self._get_default_market_status(), False

    def _get_default_market_status(self):
        return {
            # number of decimal digits "after the dot"
            enums.ExchangeConstantsMarketStatusColumns.PRECISION.value: {
                enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 8,
                enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 8,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.00001,
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 1000000000000,
                },
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 0.000001,
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000000000000,
                },
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.001,
                    enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 1000000000000,
                },
            },
        }

    def get_uniform_timestamp(self, timestamp):
        return timestamp / 1000

    def get_fees(self, symbol: str):
        if self._forced_market_statuses and symbol in self._forced_market_statuses:
            # use self._forced_market_statuses when possible
            return ccxt_client_simulation.get_fees(self._forced_market_statuses[symbol])

        result_fees = {
            enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: constants.CONFIG_DEFAULT_SIMULATOR_FEES,
            enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: constants.CONFIG_DEFAULT_SIMULATOR_FEES,
            enums.ExchangeConstantsMarketPropertyColumns.FEE.value: constants.CONFIG_DEFAULT_SIMULATOR_FEES
        }

        if commons_constants.CONFIG_SIMULATOR in self.config and \
                commons_constants.CONFIG_SIMULATOR_FEES in self.config[commons_constants.CONFIG_SIMULATOR]:
            self._read_fees_from_config(result_fees)

        return result_fees

    def _read_fees_from_config(self, result_fees):
        # in configuration, fees are in %, convert them to decimal
        if commons_constants.CONFIG_SIMULATOR_FEES_MAKER in \
                self.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES]:
            result_fees[enums.ExchangeConstantsMarketPropertyColumns.MAKER.value] = \
                self.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES][
                    commons_constants.CONFIG_SIMULATOR_FEES_MAKER] / 100

        if commons_constants.CONFIG_SIMULATOR_FEES_MAKER in self.config[commons_constants.CONFIG_SIMULATOR][
           commons_constants.CONFIG_SIMULATOR_FEES]:
            result_fees[enums.ExchangeConstantsMarketPropertyColumns.TAKER.value] = \
                self.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES][
                    commons_constants.CONFIG_SIMULATOR_FEES_TAKER] / 100

        if commons_constants.CONFIG_SIMULATOR_FEES_WITHDRAW in self.config[commons_constants.CONFIG_SIMULATOR][
           commons_constants.CONFIG_SIMULATOR_FEES]:
            result_fees[enums.ExchangeConstantsMarketPropertyColumns.FEE.value] = \
                self.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_SIMULATOR_FEES][
                    commons_constants.CONFIG_SIMULATOR_FEES_WITHDRAW] / 100

    # returns {
    #     'type': takerOrMaker,
    #     'currency': 'BTC', // the unified fee currency code
    #     'rate': percentage, // the fee rate, 0.05% = 0.0005, 1% = 0.01, ...
    #     'cost': feePaid, // the fee cost (amount * fee rate)
    #     'is_from_exchange': False, // simulated fees
    # }
    def get_trade_fee(self, symbol: str, order_type: enums.TraderOrderType, quantity, price, taker_or_maker):
        fees = self.calculate_fees(symbol, order_type, quantity, price, taker_or_maker)
        fees[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] = False
        fees[enums.FeePropertyColumns.COST.value] = decimal.Decimal(
            str(fees.get(enums.FeePropertyColumns.COST.value) or 0)
        )
        return fees

    def calculate_fees(
        self, symbol: str, order_type: enums.TraderOrderType,
        quantity: decimal.Decimal, price: decimal.Decimal, taker_or_maker: str
    ):
        if not taker_or_maker:
            taker_or_maker = enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
        base, quote = symbol_util.parse_symbol(symbol).base_and_quote()
        fee_currency = self._get_fees_currency(base, quote, order_type)

        symbol_fees = self.get_fees(symbol)
        rate = symbol_fees[taker_or_maker]
        cost = quantity * decimal.Decimal(str(rate))
        if fee_currency == quote:
            cost = cost * price

        return {
            enums.FeePropertyColumns.TYPE.value: taker_or_maker,
            enums.FeePropertyColumns.CURRENCY.value: fee_currency,
            enums.FeePropertyColumns.RATE.value: rate,
            enums.FeePropertyColumns.COST.value: cost,
        }

    def _get_fees_currency(self, base, quote, order_type: enums.TraderOrderType):
        if util.get_order_side(order_type) is enums.TradeOrderSide.SELL.value:
            return quote
        return base

    @classmethod
    def register_simulator_connector_fee_methods(cls, exchange_name: str, simulator_connector):
        # override when using custom fees in backtesting is necessary
        pass

    def get_time_frames(self, importer):
        return time_frame_manager.sort_time_frames(list(set(backtesting_api.get_available_time_frames(importer)) &
                                                        set(self.exchange_manager.exchange_config.available_time_frames)),
                                                   reverse=True)

    def use_accurate_price_time_frame(self) -> bool:
        return self.backtesting.use_accurate_price_time_frame()

    def get_split_pair_from_exchange(self, pair) -> (str, str):
        return symbol_util.parse_symbol(pair).base_and_quote()

    def get_pair_cryptocurrency(self, pair) -> str:
        return self.get_split_pair_from_exchange(pair)[0]

    @staticmethod
    def get_real_available_data(exchange_importers):
        available_data = set()
        for importer in exchange_importers:
            available_data = available_data.union(backtesting_api.get_available_data_types(importer))
        return available_data

    def get_max_handled_pair_with_time_frame(self) -> int:
        """
        :return: the maximum number of simultaneous pairs * time_frame that this exchange can handle.
        """
        return constants.INFINITE_MAX_HANDLED_PAIRS_WITH_TIMEFRAME
