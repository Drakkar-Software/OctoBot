# pylint: disable=E701
# Drakkar-Software OctoBot-Tentacles
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
import asyncio
import collections
import decimal
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.errors as commons_errors

import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.util as trading_util
import octobot_tentacles_manager.api
import octobot_trading.api as trading_api

import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution
import tentacles.Trading.Mode.market_making_trading_mode.market_making_trading as market_making_trading
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_order_book_distribution as advanced_order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as advanced_reference_price_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.scheduled_volume as scheduled_volume_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging as hedging
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators


class PostponedAction(market_making_trading.SkippedAction):
    pass


_MAX_ALLOWED_CONSECUTIVE_CREDS_ERROR_TIME = commons_constants.HOURS_TO_SECONDS
_MAX_ALLOWED_CONSECUTIVE_CREDS_ERROR_TIME = 12

class SimpleMarketMakingTradingMode(market_making_trading.MarketMakingTradingMode):
    CONFIG_PAIR_SETTINGS = "pair_settings"
    CONFIG_PAIR = "trading_pair"
    ORDER_BOOK_DEPTH = "order_book_depth"
    CUMULATED_VOLUME_PERCENT = "cumulated_volume_percent"
    PERCENT_DAILY_TRADING_VOLUME = "percent_daily_trading_volume"
    ORDERS_DISTRIBUTION = "orders_distribution"
    FUNDS_DISTRIBUTION = "funds_distribution"
    AUTO_ADAPT_CONFIG = "auto_adapt_config"
    MAX_BASE_BUDGET = "max_base_budget"
    MAX_QUOTE_BUDGET = "max_quote_budget"
    MIN_BASE_BUDGET = "min_base_budget"
    MIN_QUOTE_BUDGET = "min_quote_budget"
    REFERENCE_PRICE = "reference_price"
    MIN_INTERVAL_SECONDS = "min_interval_seconds"
    MAX_INTERVAL_SECONDS = "max_interval_seconds"
    MIN_AMOUNT = "min_amount"
    MAX_AMOUNT = "max_amount"
    SCHEDULED_VOLUME = "scheduled_volume"
    MAX_POSITIVE_PERCENT_PRICE_CHANGE = "max_positive_percent_price_change"
    MAX_NEGATIVE_PERCENT_PRICE_CHANGE = "max_negative_percent_price_change"
    AVERAGE_PRICE_COUNTED_MINUTES = "average_price_counted_minutes"
    LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY = "average_prive_counted_minutes"
    PAIR = "pair"
    TIME_FRAME = "time_frame"
    WEIGHT = "weight"
    FORMULA = "formula"
    REFRESH_PERIOD = "refresh_period"
    TOLERATED_BELLOW_DEPTH_RATIO = "tolerated_bellow_depth_ratio"
    TOLERATED_ABOVE_DEPTH_RATIO = "tolerated_above_depth_ratio"
    EXCHANGE = "exchange"
    HEDGING_ENGINE = "hedging_engine"
    HEDGING_ENGINE_TYPE = "hedging_engine_type"
    HEDGING_PROFIT_THRESHOLD = "hedging_profit_threshold"
    HEDGING_MAX_LOSS_THRESHOLD = "hedging_max_loss_threshold"
    HEDGING_EXCHANGE = "hedging_exchange"


    # 2% of 50k is 1k, which means 0.5 or 1k in each side of the book (depending on volume (0 or >1k))
    DEFAULT_USD_LIKE_VOL = decimal.Decimal(str(50000))
    DEFAULT_CRYPTO_VOL = decimal.Decimal(str(10))

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(self.CONFIG_PAIR_SETTINGS, commons_enums.UserInputTypes.OBJECT_ARRAY,
                           self.trading_config.get(self.CONFIG_PAIR_SETTINGS, None), inputs,
                           item_title="Pair configuration",
                           other_schema_values={"minItems": 1, "uniqueItems": True},
                           title="Configuration for each traded pairs.")
        self.UI.user_input(
            self.CONFIG_PAIR, commons_enums.UserInputTypes.TEXT, "BTC/USDT", inputs,
            other_schema_values={"minLength": 3, "pattern": commons_constants.TRADING_SYMBOL_REGEX},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Name of the traded pair."
        )
        self.UI.user_input(
            self.MIN_SPREAD, commons_enums.UserInputTypes.FLOAT, 0.5, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS, title=self.MIN_SPREAD_DESC
        )
        self.UI.user_input(
            self.MAX_SPREAD, commons_enums.UserInputTypes.FLOAT, 5, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS, title=self.MAX_SPREAD_DESC,
        )
        self.UI.user_input(
            self.BIDS_COUNT, commons_enums.UserInputTypes.INT, 5, inputs,
            min_val=1, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS, title=self.BIDS_COUNT_DECS,        
        )
        self.UI.user_input(
            self.ASKS_COUNT, commons_enums.UserInputTypes.INT, 5, inputs,
            min_val=1, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS, title=self.ASKS_COUNT_DECS,
        )
        self.UI.user_input(
            self.ORDER_BOOK_DEPTH, commons_enums.UserInputTypes.OBJECT, 5, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Order book depth",
        )
        self.UI.user_input(
            self.CUMULATED_VOLUME_PERCENT, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0, max_val=100,
            parent_input_name=self.ORDER_BOOK_DEPTH,
            title="Order book depth cumulated volume %. Should be larger than 1/2 the Min spread %",
        )
        self.UI.user_input(
            self.PERCENT_DAILY_TRADING_VOLUME, commons_enums.UserInputTypes.FLOAT, 2, inputs,
            min_val=0, max_val=100,
            parent_input_name=self.ORDER_BOOK_DEPTH,
            title="Order book depth daily trading volume %",
        )
        self.UI.user_input(
            self.ORDERS_DISTRIBUTION, commons_enums.UserInputTypes.OPTIONS, advanced_order_book_distribution.OrdersDistribution.LINEAR.value, inputs,
            options=list(d.value for d in advanced_order_book_distribution.OrdersDistribution),
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Orders distribution",
        )
        self.UI.user_input(
            self.FUNDS_DISTRIBUTION, commons_enums.UserInputTypes.OPTIONS, advanced_order_book_distribution.FundsDistribution.VALLEY.value, inputs,
            options=list(d.value for d in advanced_order_book_distribution.FundsDistribution),
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Funds distribution",
        )
        self.UI.user_input(
            self.AUTO_ADAPT_CONFIG, commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Auto adapt config",
        )
        self.UI.user_input(
            self.MAX_BASE_BUDGET, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Max base budget. Leave 0 for infinite",
        )
        self.UI.user_input(
            self.MAX_QUOTE_BUDGET, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Max quote budget. Leave 0 for infinite",
        )
        self.UI.user_input(
            self.MIN_BASE_BUDGET, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Min base budget to include in order book. Leave 0 for default values",
        )
        self.UI.user_input(
            self.MIN_QUOTE_BUDGET, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Min quote budget to include in order book. Leave 0 for default values",
        )
        reference_prices = [{
            self.EXCHANGE: self.UI.user_input(
                self.EXCHANGE, commons_enums.UserInputTypes.TEXT,
                "binance", inputs,
                parent_input_name=self.REFERENCE_PRICE,
                array_indexes=[0],
                title=f"Exchange. Use {self.LOCAL_EXCHANGE_PRICE} to use local exchange price"
            ),
            self.WEIGHT: self.UI.user_input(
                self.WEIGHT, commons_enums.UserInputTypes.FLOAT,
                1, inputs, parent_input_name=self.REFERENCE_PRICE,
                array_indexes=[0],
                title="Weight"
            ),
            self.FORMULA: self.UI.user_input(
                self.FORMULA, commons_enums.UserInputTypes.TEXT,
                "", inputs, parent_input_name=self.REFERENCE_PRICE,
                other_schema_values={"minLength": 0},
                array_indexes=[0],
                title="Formula: How the reference price should be computed, if different from the exchange latest price"
            ),
            self.PAIR: self.UI.user_input(
                self.PAIR, commons_enums.UserInputTypes.TEXT,
                "BTC/USDT", inputs,
                other_schema_values={"minLength": 3, "pattern": commons_constants.TRADING_SYMBOL_REGEX},
                parent_input_name=self.REFERENCE_PRICE,
                array_indexes=[0],
                title="Pair"
            ),
            self.TIME_FRAME: self.UI.user_input(
                self.TIME_FRAME, commons_enums.UserInputTypes.OPTIONS,
                commons_enums.TimeFrames.ONE_HOUR.value, inputs,
                options=list(tf.value for tf in commons_enums.TimeFrames),
                parent_input_name=self.REFERENCE_PRICE,
                array_indexes=[0],
                title="Time frame"
            ),
        }]
        self.UI.user_input(
            self.REFERENCE_PRICE, commons_enums.UserInputTypes.OBJECT_ARRAY, reference_prices, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            other_schema_values={"minItems": 1, "uniqueItems": True},
            item_title="Price reference source",
            title="Price references ",
        )
        self.UI.user_input(
            self.REFRESH_PERIOD, commons_enums.UserInputTypes.FLOAT, 0, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Periodic check period. Set 0 to disable",
        )
        scheduled_volume = {
            self.MIN_INTERVAL_SECONDS: self.UI.user_input(
                self.MIN_INTERVAL_SECONDS, commons_enums.UserInputTypes.FLOAT,
                30, inputs, parent_input_name=self.SCHEDULED_VOLUME,
                min_val=0,
                title="Min interval: minimum seconds between each scheduled volume."
            ),
            self.MAX_INTERVAL_SECONDS: self.UI.user_input(
                self.MAX_INTERVAL_SECONDS, commons_enums.UserInputTypes.FLOAT,
                55, inputs, parent_input_name=self.SCHEDULED_VOLUME,
                min_val=0,
                title="Max interval: maximum seconds between each scheduled volume."
            ),
            self.MIN_AMOUNT: self.UI.user_input(
                self.MIN_AMOUNT, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.SCHEDULED_VOLUME,
                min_val=0,
                title="Min amount: minimum order size to trade in scheduled volume orders, in quote currency."
            ),
            self.MAX_AMOUNT: self.UI.user_input(
                self.MAX_AMOUNT, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.SCHEDULED_VOLUME,
                min_val=0,
                title="Max amount: maximum order size to trade in scheduled volume orders, in quote currency. Leave 0 to disable scheduled volume."
            ),
        }
        self.UI.user_input(
            self.SCHEDULED_VOLUME, commons_enums.UserInputTypes.OBJECT, scheduled_volume, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title=f"Scheduled volume",
        )
        hedging_engine_config = {
            self.HEDGING_ENGINE_TYPE: self.UI.user_input(
                self.HEDGING_ENGINE_TYPE, commons_enums.UserInputTypes.OPTIONS, hedging.HedgingEngineTypes.SPOT.value, inputs,
                options=list(d.value for d in hedging.HedgingEngineTypes),
                parent_input_name=self.HEDGING_ENGINE,
                title="Hedging engine type",
            ),
            self.HEDGING_PROFIT_THRESHOLD: self.UI.user_input(
                self.HEDGING_PROFIT_THRESHOLD, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.HEDGING_ENGINE,
                min_val=0,
                title="Arbitrage minimum profit threshold: min arbitrage profit % before replacing arbitrage orders. Should be accounting for at least both exchanges fees and be larger than 2x Min spread %"
            ),
            self.HEDGING_MAX_LOSS_THRESHOLD: self.UI.user_input(
                self.HEDGING_MAX_LOSS_THRESHOLD, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.HEDGING_ENGINE,
                min_val=0,
                title="Hedging max loss threshold: max loss % threshold. Used to create a stop loss in case the hedging order is not quickly filled. Leave 0 to disable"
            ),
            self.MAX_NEGATIVE_PERCENT_PRICE_CHANGE: self.UI.user_input(
                self.MAX_NEGATIVE_PERCENT_PRICE_CHANGE, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.HEDGING_ENGINE,
                min_val=0,
                title="Max negative price change: max negative price change % before pausing hedging. Leave 0 to disable"
            ),
            self.MAX_POSITIVE_PERCENT_PRICE_CHANGE: self.UI.user_input(
                self.MAX_POSITIVE_PERCENT_PRICE_CHANGE, commons_enums.UserInputTypes.FLOAT,
                0, inputs, parent_input_name=self.HEDGING_ENGINE,
                min_val=0,
                title="Max positive price change: max positive price change % before pausing hedging. Leave 0 to disable"
            ),
            self.AVERAGE_PRICE_COUNTED_MINUTES: self.UI.user_input(
                self.AVERAGE_PRICE_COUNTED_MINUTES, commons_enums.UserInputTypes.INT,
                60*6, # default = 6h
                inputs, parent_input_name=self.HEDGING_ENGINE,
                min_val=1,
                title="Volatility period: how many minutes to consider when computing the average price in max price volatility hedging conditions."
            ),
            self.HEDGING_EXCHANGE: self.UI.user_input(
                self.HEDGING_EXCHANGE, commons_enums.UserInputTypes.TEXT,
                "binance", inputs, parent_input_name=self.HEDGING_ENGINE,
                title="Hedging exchange: exchange to hedge on. This exchange must be enabled in exchange configuration.",
            ),
        }
        self.UI.user_input(
            self.HEDGING_ENGINE, commons_enums.UserInputTypes.OBJECT, hedging_engine_config, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title=f"Hedging",
        )
        self.UI.user_input(
            self.TOLERATED_BELLOW_DEPTH_RATIO, commons_enums.UserInputTypes.FLOAT,
            float(advanced_order_book_distribution.DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO), inputs,
            min_val=0,
            max_val=1,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Ratio bellow with a an order book depth is considered too small",
        )
        self.UI.user_input(
            self.TOLERATED_ABOVE_DEPTH_RATIO, commons_enums.UserInputTypes.FLOAT,
            float(advanced_order_book_distribution.DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO), inputs,
            min_val=1,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Ratio bellow with a an order book depth is considered too large",
        )
        self.UI.user_input(
            self.EXCHANGE, commons_enums.UserInputTypes.TEXT, "binance", inputs,
            other_schema_values={"minLength": 0},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Name of the exchange this configuration is for. Leave empty to use it on the selected exchange.",
        )

    def get_mode_producer_classes(self) -> list:
        return [SimpleMarketMakingTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [SimpleMarketMakingTradingModeConsumer]

    async def _order_notification_callback(
        self, exchange, exchange_id, cryptocurrency, symbol, order, update_type, is_from_bot
    ):
        if (
            order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] in (
                trading_enums.TradeOrderType.LIMIT.value
            ) and (
                order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value
                or order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] > 0
            )
        ):
            await self.producers[0].order_filled_or_partially_filled_callback(order)

    @classmethod
    def get_pair_settings_for_exchange(cls, target_exchange_name, tentacle_config) -> list:
        return [
            pair_setting
            for pair_setting in tentacle_config.get(cls.CONFIG_PAIR_SETTINGS, [])
            if cls.is_exchange_compatible_pair_setting(pair_setting, target_exchange_name)
        ]

    def get_pair_settings(self) -> list:
        return [
            pair_setting
            for pair_setting in self.trading_config.get(self.CONFIG_PAIR_SETTINGS, [])
            if self.is_exchange_compatible_pair_setting(pair_setting, self.exchange_manager.exchange_name)
        ]

    @classmethod
    def get_price_sources_by_exchange(
        cls, symbol_trading_config: dict
    ) -> dict[str, list[advanced_reference_price_import.AdvancedPriceSource]]:
        price_sources_by_exchanges = {}
        for ref in symbol_trading_config[cls.REFERENCE_PRICE]:
            if ref[cls.EXCHANGE] not in price_sources_by_exchanges:
                price_sources_by_exchanges[ref[cls.EXCHANGE]] = []
            price_sources_by_exchanges[ref[cls.EXCHANGE]].append(
                advanced_reference_price_import.AdvancedPriceSource(
                    ref[cls.EXCHANGE],
                    ref[cls.PAIR],
                    ref.get(cls.TIME_FRAME, None),
                    decimal.Decimal(str(1 if ref[cls.WEIGHT] in ("", None) else ref[cls.WEIGHT])),
                    str(ref.get(cls.FORMULA, "")),
                )
            )
        return price_sources_by_exchanges

    @classmethod
    def get_scheduled_volume_config(
        cls, symbol_trading_config: dict
    ):
        try:
            return symbol_trading_config[cls.SCHEDULED_VOLUME]
        except KeyError:
            return {}

    @classmethod
    def get_hedging_engine_config(cls, symbol_trading_config: dict) -> dict[str, typing.Any]:
        try:
            raw_config = symbol_trading_config[cls.HEDGING_ENGINE]
        except KeyError:
            return {}
        hedging_config = dict(raw_config)
        if cls.AVERAGE_PRICE_COUNTED_MINUTES not in hedging_config:
            legacy_value = hedging_config.get(cls.LEGACY_AVERAGE_PRIVE_COUNTED_MINUTES_KEY)
            if legacy_value is not None:
                hedging_config[cls.AVERAGE_PRICE_COUNTED_MINUTES] = legacy_value
        return hedging_config

    @classmethod
    def get_order_book_distribution(cls, pair_config: dict) -> order_book_distribution.OrderBookDistribution:
        try:
            min_spread = decimal.Decimal(str(pair_config[cls.MIN_SPREAD] / 100))
            max_spread = decimal.Decimal(str(pair_config[cls.MAX_SPREAD] / 100))
            bids_count = int(pair_config[cls.BIDS_COUNT])
            asks_count = int(pair_config[cls.ASKS_COUNT])
            cumulated_volume_percent = decimal.Decimal(
                str(pair_config[cls.ORDER_BOOK_DEPTH][cls.CUMULATED_VOLUME_PERCENT])
            )
            percent_daily_trading_volume = decimal.Decimal(
                str(pair_config[cls.ORDER_BOOK_DEPTH][cls.PERCENT_DAILY_TRADING_VOLUME])
            )
            orders_distribution = advanced_order_book_distribution.OrdersDistribution(pair_config[cls.ORDERS_DISTRIBUTION])
            funds_distribution = advanced_order_book_distribution.FundsDistribution(pair_config[cls.FUNDS_DISTRIBUTION])
            max_base_budget = max_quote_budget = None
            if max_b_budget := pair_config.get(cls.MAX_BASE_BUDGET, None):
                max_base_budget = decimal.Decimal(str(max_b_budget))
            if max_q_budget := pair_config.get(cls.MAX_QUOTE_BUDGET, None):
                max_quote_budget = decimal.Decimal(str(max_q_budget))
            min_base_budget = min_quote_budget = None
            if min_b_budget := pair_config.get(cls.MIN_BASE_BUDGET, None):
                min_base_budget = decimal.Decimal(str(min_b_budget))
            if min_q_budget := pair_config.get(cls.MIN_QUOTE_BUDGET, None):
                min_quote_budget = decimal.Decimal(str(min_q_budget))
            tolerated_above_depth_ratio = decimal.Decimal(str(pair_config.get(
                cls.TOLERATED_ABOVE_DEPTH_RATIO, advanced_order_book_distribution.DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO
            )))
            tolerated_bellow_depth_ratio = decimal.Decimal(str(pair_config.get(
                cls.TOLERATED_BELLOW_DEPTH_RATIO, advanced_order_book_distribution.DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO
            )))
            return advanced_order_book_distribution.AdvancedOrderBookDistribution(
                bids_count, asks_count, min_spread, max_spread, 
                cumulated_volume_percent, percent_daily_trading_volume,
                orders_distribution, funds_distribution,
                max_base_budget=max_base_budget, max_quote_budget=max_quote_budget,
                min_base_budget=min_base_budget, min_quote_budget=min_quote_budget,
                tolerated_bellow_depth_ratio=tolerated_bellow_depth_ratio,
                tolerated_above_depth_ratio=tolerated_above_depth_ratio,
            )
        except TypeError as err:
            raise ValueError(f"Invalid config value: {err}") from err

    @classmethod
    def get_quote_default_volume(
        cls, symbol: str, quote_volume: decimal.Decimal
    ) -> decimal.Decimal:
        default_volume = cls.DEFAULT_CRYPTO_VOL
        if symbol_util.is_usd_like_coin(symbol_util.parse_symbol(symbol).quote):
             default_volume = cls.DEFAULT_USD_LIKE_VOL
        minimum_default_volume = default_volume / decimal.Decimal("2")
        # if volume is not 0: compare it to default value and use half default if necessary
        if quote_volume and not quote_volume.is_nan() and quote_volume < minimum_default_volume:
            return minimum_default_volume
        return default_volume

    @classmethod
    def get_default_min_base_and_quote_volume(
        cls, symbol: str, reference_price: decimal.Decimal, quote_volume: decimal.Decimal
    ) -> (decimal.Decimal, decimal.Decimal):
        return trading_api.compute_base_and_quote_volume(
            trading_constants.ZERO, cls.get_quote_default_volume(symbol, quote_volume), reference_price
        )

    @classmethod
    def is_exchange_compatible_pair_setting(cls, pair_setting: dict, target_exchange_name: str) -> bool:
        return (
            (not pair_setting[cls.EXCHANGE])
            or pair_setting[cls.EXCHANGE] == target_exchange_name
        )

    @classmethod
    def get_is_trading_on_exchange(cls, exchange_name, tentacles_setup_config) -> bool:
        """
        returns True if exchange_name is not in price sources
        """
        tentacle_config = octobot_tentacles_manager.api.get_tentacle_config(tentacles_setup_config, cls)
        for pair_setting in tentacle_config.get(cls.CONFIG_PAIR_SETTINGS, []):
            if heding_config := cls.get_hedging_engine_config(pair_setting):
                if heding_config.get(cls.HEDGING_EXCHANGE) == exchange_name:
                    # is hedging on this exchange
                    return True
        return super().get_is_trading_on_exchange(exchange_name, tentacles_setup_config)

    async def stop_strategy_execution(self, reason_description: typing.Optional[str]):
        await self.producers[0].force_stop_strategy(reason_description)


class SimpleMarketMakingTradingModeConsumer(market_making_trading.MarketMakingTradingModeConsumer):

    async def _process_plan(
        self,
        order_actions_plan: market_making_trading.OrdersUpdatePlan,
        current_price: decimal.Decimal,
        symbol_market: dict
    ):
        created_orders = []
        #tmp
        # self.exchange_manager.exchange.connector.client.apiKey = "1234567890" #tmp
        # self.exchange_manager.exchange.connector.client.secret = "1234567890" #tmp
        #tmp
        cancelled_orders = []
        processed_actions = {}
        skipped_actions = {}
        scheduled_actions = collections.deque(order_actions_plan.order_actions)
        postponed_actions = collections.deque()

        force_scheduled_action_next = False
        while scheduled_actions or postponed_actions:
            is_from_postponed_actions = False
            # 1. try to process postponed_actions if possible
            # 2. fallback to scheduled_actions otherwise
            if force_scheduled_action_next and scheduled_actions:
                action = scheduled_actions.popleft()
            elif postponed_actions:
                action = postponed_actions.popleft()
                is_from_postponed_actions = True
            else:
                action = scheduled_actions.popleft()
            force_scheduled_action_next = False
            can_be_postponed = bool(scheduled_actions)
            try:
                if order_actions_plan.cancelled and order_actions_plan.cancellable:
                    actions_class = action.__class__.__name__
                    self.logger.debug(
                        f"{self.trading_mode.symbol} {self.exchange_manager.exchange_name} "
                        f"order actions cancelled, skipping {actions_class} action."
                    )
                    if actions_class not in skipped_actions:
                        skipped_actions[actions_class] = 1
                    else:
                        skipped_actions[actions_class] += 1
                else:
                    # actions can be postponed as long as all initially scheduled_actions are not completed or postponed
                    await self._process_action(
                        action, current_price, symbol_market,
                        processed_actions, created_orders, cancelled_orders, can_be_postponed=can_be_postponed
                    )
            except PostponedAction as err:
                if can_be_postponed:
                    self.logger.debug(f"Postponed {action}: {err}")
                    if is_from_postponed_actions:
                        # replace action to the front of the queue
                        postponed_actions.appendleft(action)
                    else:
                        postponed_actions.append(action)
                    # just postponed an action: proceed with initially scheduled action next and come back to
                    # postponed action afterward
                    force_scheduled_action_next = True
                else:
                    self.logger.exception(err, True, f"Skipped unexpectedly postponed action: {err} {action=}")
            except trading_errors.AuthenticationError as err:
                self.logger.error(f"Failed to execute action plan due to {err.__class__.__name__}:  {err}.")
            except Exception as err:
                self.logger.exception(err, True, f"Error when processing {action}: {err}")

        self._log_actions_report(
            order_actions_plan, processed_actions, skipped_actions, created_orders, cancelled_orders
        )
        return created_orders

    def _should_skip(
        self, selling, base_available, quote_available, order_quantity, order_price, order_desc,
        currency, market, can_be_postponed=False, **kwargs
    ):
        should_skip, skip_message = super()._should_skip(
            selling, base_available, quote_available, order_quantity, order_price,
            order_desc, currency, market, **kwargs
        )
        if should_skip and can_be_postponed:
            raise PostponedAction(skip_message)
        return should_skip, skip_message


class SimpleMarketMakingTradingModeProducer(market_making_trading.MarketMakingTradingModeProducer):
    ORDERS_DESC = "simple market making"


    def __init__(self, channel, config, trading_mode, exchange_manager):
        self.auto_adapt_config: bool = True
        self.reference_prices_by_exchange: dict[str, list[advanced_reference_price_import.AdvancedPriceSource]] = {}
        self.refresh_period: float = 0
        self.reference_price_warning_ratio: decimal.Decimal = None # type: ignore
        self.outdated_reference_price_delta_ratio: decimal.Decimal = trading_constants.ZERO
        self._scheduled_volume: typing.Optional[scheduled_volume_import.ScheduledVolume] = None
        self._hedging_engine: typing.Optional[hedging_engine.HedgingEngine] = None
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.trading_mode: SimpleMarketMakingTradingMode = typing.cast(SimpleMarketMakingTradingMode, trading_mode)

        if self.symbol_trading_config is None:
            exchange_configured_pairs = [
                setting[self.trading_mode.CONFIG_PAIR]
                for setting in self.trading_mode.get_pair_settings()
            ]
            if not exchange_configured_pairs:
                self.logger.error(
                    f"No {self.ORDERS_DESC} {self.exchange_manager.exchange_name} trading pair "
                    f"configuration. This is unexpected."
                )
            else:
                self.logger.info(
                    f"No {self.ORDERS_DESC} {self.exchange_manager.exchange_name} configuration "
                    f"for trading pair: {self.symbol}. Add this pair's details into your {self.ORDERS_DESC} "
                    f"{self.exchange_manager.exchange_name} orders configuration to apply the strategy on it. "
                    f"Configured {self.ORDERS_DESC} orders pairs for {self.exchange_manager.exchange_name} "
                    f"are {', '.join(exchange_configured_pairs)}."
                )

    async def _ensure_market_making_orders(self, trigger_source: str) -> bool:
        # can be called:
        #   - on initialization
        #   - when price moves beyond spread
        #   - when orders are filled
        if self._hedging_engine is not None and not self._hedging_engine.is_healthy(self.symbol):
            # can't hedge in this condition: stop update
            self.logger.info(
                f"Ignored [{self.exchange_manager.exchange_name}] {self.symbol} market making orders creation: "
                f"hedging engine is not healthy. Heding state is {self._hedging_engine.get_symbol_details(self.symbol).state.value}"
            )
            if abnormal_state := self._hedging_engine.get_critical_abnormal_state():
                message = (
                    f"Scheduling bot stop [{self.exchange_manager.exchange_name}]: {self.symbol} "
                    f"hedging engine is in an abnormal state: {abnormal_state.value}"
                )
                await self.exchange_manager.trader.schedule_bot_stop(
                    commons_enums.StopReason.INVALID_CONFIG, message
                )
                return False
            return False
        _, _, _, current_price, symbol_market = await trading_personal_data.get_pre_order_data(
            self.exchange_manager,
            symbol=self.symbol,
            timeout=self.PRICE_FETCHING_TIMEOUT
        )
        force_full_refresh = False
        if self._scheduled_volume is not None:
            await self._scheduled_volume.wait_required_locked_funds_init()
            action = self._scheduled_volume.ensure_locked_funds(current_price)
            force_full_refresh = action is scheduled_volume_import.LockFundsActions.REALLOCATE_SCHEDULED_VOLUME_FUNDS
            if force_full_refresh:
                self.logger.info(
                    f"Force full-refresh from scheduled volume for {self.symbol} [{self.exchange_manager.exchange_name}]"
                )
        return await self.create_state(current_price, symbol_market, trigger_source, force_full_refresh)


    async def stop(self) -> None:
        """
        Stop trading mode channels subscriptions
        """
        await super().stop()
        if self._scheduled_volume is not None:
            self._scheduled_volume.stop()
        if self._hedging_engine is not None:
            await self._hedging_engine.stop()

    async def start(self) -> None:
        # bypass super().start to start volume scheduler first
        await super(market_making_trading.MarketMakingTradingModeProducer, self).start()
        # insert bot started log before any other initialization to avoid logging error logs after the start/restart log
        if not self.healthy:
            message = (
                f"Configuration error ({self.healthy=}) on {self.symbol} [{self.exchange_manager.exchange_name}], scheduling bot stop"
            )
            await self.exchange_manager.trader.schedule_bot_stop(
                commons_enums.StopReason.INVALID_CONFIG, message
            )
            return
        if self.symbol_trading_config and not self.should_stop:
            try:
                await self._validate_reference_prices()
            except (ValueError, NotImplementedError, commons_errors.DSLInterpreterError) as err:
                self.healthy = False
                message = f"Error when initializing reference prices: {err}"
                self.logger.exception(err, True, message)
                await self.exchange_manager.trader.schedule_bot_stop(
                    commons_enums.StopReason.INVALID_CONFIG, message
                )
                return
            try:
                await self._initialize_hedging_engine()
            except hedging_errors.HedgingConfigurationError as err:
                self.healthy = False
                message = f"Error when initializing hedging engine: {err}"
                self.logger.exception(err, True, message)
                await self.exchange_manager.trader.schedule_bot_stop(
                    commons_enums.StopReason.INVALID_CONFIG, message
                )
                return
            await self._initialize_scheduled_volume()
            self.healthy = True
        if self.healthy:
            if self.should_stop:
                self.logger.info(f"[{self.exchange_manager.exchange_name}] {self.symbol} trading mode stopped, skipping orders creation")
            else:
                self.logger.debug(f"Initializing orders creation")
                await self._ensure_market_making_orders_and_reschedule()

    async def _validate_reference_prices(self):
        for reference_prices in self.reference_prices_by_exchange.values():
            for reference_price in reference_prices:
                await reference_price.validate_interpreted_formula(self.exchange_manager)
                # reset formula interpreter not to keep self.exchange_manager 
                # (a different one might be actually required)
                reference_price.reset_formula_interpreter()

    async def _initialize_hedging_engine(self):
        hedging_engine_config = self.trading_mode.get_hedging_engine_config(self.symbol_trading_config)
        if hedging_engine_config:
            hedging_exchange_raw = hedging_engine_config.get(self.trading_mode.HEDGING_EXCHANGE)
            if not hedging_exchange_raw:
                self.logger.info(
                    f"Disabled {self.symbol} hedging engine: "
                    f"{self.trading_mode.HEDGING_EXCHANGE} is not set or empty."
                )
                return
            hedging_exchange = (
                hedging_exchange_raw.strip()
                if isinstance(hedging_exchange_raw, str)
                else hedging_exchange_raw
            )
            for element in [
                self.trading_mode.HEDGING_PROFIT_THRESHOLD,
                self.trading_mode.HEDGING_MAX_LOSS_THRESHOLD,
                self.trading_mode.MAX_POSITIVE_PERCENT_PRICE_CHANGE,
                self.trading_mode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE,
                self.trading_mode.AVERAGE_PRICE_COUNTED_MINUTES,
            ]:
                val = hedging_engine_config.get(element, None)
                if val is None:
                    self.logger.info(f"Disabled {self.symbol} hedging engine: {element} is not set (value: {val}).")
                    return
                if element == self.trading_mode.AVERAGE_PRICE_COUNTED_MINUTES and val == 0:
                    self.logger.info(f"Disabled {self.symbol} hedging engine: {element} is 0 (value: {val}).")
                    return
            self._hedging_engine = hedging.get_or_create_hedging_engine(
                hedging.HedgingEngineTypes(hedging_engine_config[self.trading_mode.HEDGING_ENGINE_TYPE]),
                self.exchange_manager,
                hedging_exchange,
            )
            profit_threshold = decimal.Decimal(str(hedging_engine_config[self.trading_mode.HEDGING_PROFIT_THRESHOLD]))
            max_loss_threshold = decimal.Decimal(str(hedging_engine_config[self.trading_mode.HEDGING_MAX_LOSS_THRESHOLD]))
            self._hedging_engine.register_symbol(
                self.symbol,
                profit_threshold,
                max_loss_threshold,
                self.order_book_distribution,
                hedging_engine_config[self.trading_mode.MAX_POSITIVE_PERCENT_PRICE_CHANGE],
                hedging_engine_config[self.trading_mode.MAX_NEGATIVE_PERCENT_PRICE_CHANGE],
                hedging_engine_config[self.trading_mode.AVERAGE_PRICE_COUNTED_MINUTES],
            )
            if profit_threshold != trading_constants.ZERO:
                self.outdated_reference_price_delta_ratio = (
                    profit_threshold / trading_constants.ONE_HUNDRED
                )
        else:
            self.logger.info("Disabled hedging engine: no hedging engine config")

    async def _initialize_scheduled_volume(self):
        try:
            schedule_config = self.trading_mode.get_scheduled_volume_config(self.symbol_trading_config)
        except KeyError:
            self.logger.error("Skipped scheduled volume: no scheduled volume config")
            return
        if max_amount := schedule_config.get(self.trading_mode.MAX_AMOUNT, 0):
            if self._hedging_engine is not None:
                self.logger.error(
                    f"Skipped scheduled volume: as hedging is enabled for {self.symbol} "
                    f"[{self.exchange_manager.exchange_name}], scheduled volume is not supported"
                )
                return
            self._scheduled_volume = scheduled_volume_import.ScheduledVolume(
                self.exchange_manager, self.symbol, self._ensure_market_making_orders,
                schedule_config.get(self.trading_mode.MIN_INTERVAL_SECONDS, 0),
                schedule_config.get(self.trading_mode.MAX_INTERVAL_SECONDS, 0),
                schedule_config.get(self.trading_mode.MIN_AMOUNT, 0),
                max_amount,
            )
            await self._scheduled_volume.start()
        else:
            self.logger.info(
                f"[Disabled] scheduled volume for {self.symbol} [{self.exchange_manager.exchange_name}]"
            )

    def _load_symbol_trading_config(self) -> bool:
        config = self.get_symbol_trading_config(self.symbol)
        if config is None:
            return False
        self.symbol_trading_config = config
        return True

    def get_symbol_trading_config(self, symbol):
        for config in self.trading_mode.get_pair_settings():
            if config[self.trading_mode.CONFIG_PAIR] == symbol:
                return config
        return None

    def read_config(self):
        self.order_book_distribution = self.trading_mode.get_order_book_distribution(self.symbol_trading_config)
        self.auto_adapt_config = self.symbol_trading_config.get(
            self.trading_mode.AUTO_ADAPT_CONFIG, self.auto_adapt_config
        )
        self.reference_prices_by_exchange = self.trading_mode.get_price_sources_by_exchange(
            self.symbol_trading_config
        )
        self.refresh_period = self.symbol_trading_config.get(self.trading_mode.REFRESH_PERIOD, self.refresh_period)
        self.reference_price_warning_ratio = decimal.Decimal(str(
            self.symbol_trading_config[self.trading_mode.MIN_SPREAD] / 100
        ))
        self.scheduled_volume_config = self.trading_mode.get_scheduled_volume_config(self.symbol_trading_config)

    async def _reschedule_if_necessary(self, can_create_orders: bool):
        if can_create_orders:
            if self.refresh_period:
                self.logger.info(f"Next refresh in: {self.refresh_period} seconds")
                self.scheduled_health_check = asyncio.get_event_loop().call_later(
                    self.refresh_period,
                    self._schedule_order_refresh
                )
            else:
                self.logger.info(
                    f"No refresh period, orders will only be maintained from price and orders updates"
                )
        else:
            is_portfolio_initialized = await trading_util.wait_for_topic_init(
                self.exchange_manager, 0, commons_enums.InitializationEventExchangeTopics.BALANCE.value
            )
            if trading_api.get_portfolio(self.exchange_manager) == {} and is_portfolio_initialized:
                message = (
                    f"Empty [{self.exchange_manager.exchange_name}] portfolio for {self.symbol} market making, scheduling bot stop"
                )
                await self.exchange_manager.trader.schedule_bot_stop(
                    commons_enums.StopReason.MISSING_MINIMAL_FUNDS, message
                )
            else:
                await super()._reschedule_if_necessary(can_create_orders)

    def _get_daily_volume(self, reference_price: decimal.Decimal) -> (decimal.Decimal, decimal.Decimal):
        symbol_data = self.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
            self.symbol, allow_creation=False
        )
        default_base_volume = default_quote_volume = trading_constants.ZERO
        try:
            default_base_volume, default_quote_volume = self.trading_mode.get_default_min_base_and_quote_volume(
                self.symbol, reference_price, trading_constants.ZERO
            )
        except ValueError:
            # attempt to get real daily volume, raise later on if it fails
            pass
        try:
            base_volume, quote_volume = trading_api.get_daily_base_and_quote_volume(symbol_data, reference_price)
            if base_volume < default_base_volume or quote_volume < default_quote_volume:
                self.logger.warning(
                    f"Daily volume for {self.symbol} on {self.exchange_manager.exchange_name} is less than default volume: {base_volume=}, {quote_volume=}. "
                    f"Using default volume: {default_base_volume=}, {default_quote_volume=}"
                )
            return max(base_volume, default_base_volume), max(quote_volume, default_quote_volume)
        except ValueError as err:
            if default_base_volume and default_quote_volume:
                self.logger.debug(
                    f"Fallback to default value using reference_price and default_volume_multiplier for "
                    f"{self.symbol} trading volume on {self.exchange_manager.exchange_name}"
                )
                return default_base_volume, default_quote_volume
            raise ValueError(
                f"Missing volume for {self.symbol} on {self.exchange_manager.exchange_name}: "
                f"{err}. {reference_price=}"
            ) from err

    def _get_available_funds(self) -> (decimal.Decimal, decimal.Decimal):
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        portfolio_available_base = trading_api.get_portfolio_currency(self.exchange_manager, base).available
        portfolio_available_quote = trading_api.get_portfolio_currency(self.exchange_manager, quote).available
        schedule_orders_locked_base = scheduled_volume_import.get_global_locked_funds(
            self.exchange_manager.id, base, ""
        )
        schedule_orders_locked_quote = scheduled_volume_import.get_global_locked_funds(
            self.exchange_manager.id, quote, ""
        )
        if self._hedging_engine is None:
            hedging_engine_locked_base = hedging_engine_locked_quote = trading_constants.ZERO
        else:
            hedging_engine_locked_base, hedging_engine_locked_quote = self._hedging_engine.get_locked_base_and_quote(
                self.symbol
            )
        return (
            # use max as this can be negative when scheduled orders locked open order funds in advance
            max(
                portfolio_available_base - schedule_orders_locked_base - hedging_engine_locked_base,
                trading_constants.ZERO
            ),
            max(
                portfolio_available_quote - schedule_orders_locked_quote - hedging_engine_locked_quote,
                trading_constants.ZERO
            )
        )
        
    async def on_new_reference_price(self, reference_price: decimal.Decimal) -> bool:
        """
        Returns True if market making orders should be updated.
        """
        if self._hedging_engine is not None:
            if self._hedging_engine.reached_max_tolerated_volatility(self.symbol):
                # can't hedge in this condition: stop update
                self.logger.info(
                    f"Ignored new [{self.exchange_manager.exchange_name}] {self.symbol} reference price: {reference_price}: hedging engine reached max tolerated volatility"
                )
                # make sure all orders have been cancelled
                await self._emergency_cancel_all_market_making_orders()
                return False
            try:
                await self._hedging_engine.on_new_price(self.symbol, reference_price)
            except hedging_errors.HedgingEngineReachedMaxToleratedVolatility as e:
                # max volatility reached, cancel all market making orders to avoid further losses
                self.logger.exception(e, True, f"Hedging engine reached max tolerated volatility: {e}")
                await self._emergency_cancel_all_market_making_orders()
                return False
            except Exception as e:
                self.logger.exception(e, True, f"Error when handling new reference price in hedging engine: {e}")
                return False
        return await super().on_new_reference_price(reference_price)

    def _is_outdated(
        self, order_price: decimal.Decimal, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal
    ) -> bool:
        adapted_reference_price = reference_price
        if self.outdated_reference_price_delta_ratio != trading_constants.ZERO:
            adapted_reference_price = reference_price * (
                1 + (
                    self.outdated_reference_price_delta_ratio * -1 if side == trading_enums.TradeOrderSide.BUY else 1
                )
            )
        if side == trading_enums.TradeOrderSide.BUY:
            return order_price > adapted_reference_price
        return order_price < adapted_reference_price

    async def _ensure_dependencies(
        self, exchange_manager, dependencies: typing.List[exchange_operators.ExchangeDataDependency]
    ):
        exchange_id = trading_api.get_exchange_manager_id(exchange_manager)
        for dependency in dependencies:
            if dependency.data_source == trading_constants.OHLCV_CHANNEL:
                await self._subscribe_to_exchange_ohlcv(
                    exchange_id,
                    exchange_manager,
                    dependency.symbol,
                    dependency.time_frame
                )
                # also subscribe to mark price to trigger on price updates
                await self._subscribe_to_exchange_mark_price(exchange_id, exchange_manager)
            elif dependency.data_source == trading_constants.MARK_PRICE_CHANNEL:
                await self._subscribe_to_exchange_mark_price(exchange_id, exchange_manager)
            else:
                self.logger.error(f"Unknown dependency data source: {dependency.data_source}")

    async def _subscribe_to_exchange_ohlcv(
        self, exchange_id: str, exchange_manager, symbol: str, time_frame: str
    ):
        if self.already_subscribed_to_channel(
            exchange_id, trading_constants.OHLCV_CHANNEL, self._ohlcv_callback, symbol=symbol, time_frame=time_frame
        ):
            return
        await exchanges_channel.get_chan(trading_constants.OHLCV_CHANNEL, exchange_id).new_consumer(
            callback=self._ohlcv_callback, symbol=symbol,
            time_frame=time_frame
        )
        self.logger.info(
            f"{self.trading_mode.get_name()} for {symbol} {time_frame} on {self.exchange_name}:  "
            f"{exchange_manager.exchange_name} OHLCV data feed."
        )

    async def _ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle,
    ):
        """
        Called on a new OHLCV update from an exchange
        """
        await self._on_reference_price_update()

    async def _register_pair_requirement_on_reference_exchanges(self):
        local_exchange_name = self.exchange_manager.exchange_name
        for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(
            local_exchange_name, self.exchange_manager.id
        ):
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            other_exchange_key = self.trading_mode.LOCAL_EXCHANGE_PRICE if (
                self.trading_mode.LOCAL_EXCHANGE_PRICE in self.reference_prices_by_exchange
                and local_exchange_name == exchange_manager.exchange_name
            ) else exchange_manager.exchange_name
            if other_exchange_key not in self.reference_prices_by_exchange:
                continue
            exchange_reference_prices = self.reference_prices_by_exchange[other_exchange_key]
            if exchange_id not in self.subscribed_requirements_exchange_ids:
                await self._register_pair_requirement_on_reference_exchange(exchange_manager, exchange_reference_prices)
                self.subscribed_requirements_exchange_ids.add(exchange_id)
                for reference_price_spec in exchange_reference_prices:
                    # exchange just initialized, subscribe to channels and initialize all ref prices for this exchange
                    await reference_price_spec.initialize_if_required(exchange_manager)
                    await self._ensure_dependencies(
                        exchange_manager,
                        reference_price_spec.get_dependencies(exchange_manager)
                    )
    
    def _is_registered_on_all_reference_exchanges(self) -> bool:
        return len(self.subscribed_requirements_exchange_ids) >= len(self.reference_prices_by_exchange)

    async def _get_reference_price(self) -> decimal.Decimal:
        if not await self._register_on_reference_exchanges_if_required():
            return trading_constants.ZERO
        local_exchange_name = self.exchange_manager.exchange_name
        price_by_pair_by_exchange = {}
        for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(
            local_exchange_name, self.exchange_manager.id
        ):
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            other_exchange_key = self.trading_mode.LOCAL_EXCHANGE_PRICE if (
                self.trading_mode.LOCAL_EXCHANGE_PRICE in self.reference_prices_by_exchange
                and local_exchange_name == exchange_manager.exchange_name
            ) else exchange_manager.exchange_name
            if other_exchange_key not in self.reference_prices_by_exchange:
                continue
            exchange_reference_prices = self.reference_prices_by_exchange[other_exchange_key]
            price_by_pair_by_exchange[other_exchange_key] = {}
            for reference_price_spec in exchange_reference_prices:
                try:
                    price, updated = trading_personal_data.get_potentially_outdated_price(
                        exchange_manager, reference_price_spec.pair
                    )
                    if not updated:
                        self.logger.warning(
                            f"{exchange_manager.exchange_name} mark price: {price} is outdated for {reference_price_spec.pair}. "
                            f"Using it anyway"
                        )
                    price_by_pair_by_exchange[other_exchange_key][reference_price_spec.pair] = price
                except KeyError:
                    method = self.logger.info if self.is_first_execution else (
                        self.logger.error if (
                            self.exchange_manager.exchange.get_exchange_current_time() - self._started_at
                            > self.REFERENCE_PRICE_INIT_DELAY
                        )
                        else self.logger.warning
                    )
                    method(
                        f"No {exchange_manager.exchange_name} exchange symbol data for {reference_price_spec.pair}, "
                        f"it's probably initializing"
                    )
        reference_price = await advanced_reference_price_import.compute_reference_price(
            price_by_pair_by_exchange, self.reference_prices_by_exchange
        )
        self._log_on_too_different_price_sources(reference_price, price_by_pair_by_exchange)
        return reference_price

    def _log_on_too_different_price_sources(
        self, reference_price: decimal.Decimal, 
        price_by_pair_by_exchange: dict[str, dict[str, decimal.Decimal]]
    ):
        if not reference_price:
            return
        for source, price_by_pair in price_by_pair_by_exchange.items():
            if self.trading_mode.symbol in price_by_pair:
                price = price_by_pair[self.trading_mode.symbol]
                source_difference_ratio = abs(reference_price - price) / reference_price
                if source_difference_ratio > self.reference_price_warning_ratio:
                    self.logger.warning(
                        f"{source} current {self.symbol} price is "
                        f"{source_difference_ratio * trading_constants.ONE_HUNDRED} % different from final reference "
                        f"price: {reference_price}. This source might affect local orders."
                    )

    async def order_filled_or_partially_filled_callback(self, order: dict):
        if order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value:
            # order is fully filled
            self.logger.info(
                f"{self.symbol} [{self.exchange_manager.exchange_name}] fully filled order update: "
                f"order exchange id: {order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}, "
                f"side: {order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]}, "
                f"amount:{order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]}, "
                f"price: {order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}"
            )
            await self._on_filled_or_partially_filled_order(order)
            await super().order_filled_callback(order)
        elif order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] > 0:
            # order is partially filled
            self.logger.info(
                f"{self.symbol} [{self.exchange_manager.exchange_name}] partially filled order update: "
                f"order exchange id: {order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}, "
                f"side: {order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]}, "
                f"filled {order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value]} "
                f"out of {order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]}, "
                f"price: {order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}"
            )
            await self._on_filled_or_partially_filled_order(order)
        else:
            self.logger.warning(
                f"{self.symbol} [{self.exchange_manager.exchange_name}] order_filled_callback should not have been called for order: {order}"
            )

    async def _on_filled_or_partially_filled_order(self, order: dict):
        if self._hedging_engine is not None:
            try:
                await self._hedging_engine.hedge_filled_or_partially_filled_order(order)
            except hedging_errors.HedgingEngineError as e:
                self.logger.exception(
                    e, True, f"Error when handling filled or partially filled order in hedging engine: {e}"
                )
            except Exception as e:
                self.logger.exception(
                    e, True, f"Unexpected error when handling filled or partially filled order: {e}"
                )

    async def _register_pair_requirement_on_reference_exchange(
        self,
        exchange_manager: trading_exchanges.ExchangeManager,
        exchange_reference_prices: list[advanced_reference_price_import.AdvancedPriceSource]
    ):
        # Warning: should only be called after the exchange is initialized
        watched_symbols = []
        traded_symbols = []
        required_time_frames = []
        # exchange_reference_prices requirements
        for reference_price in exchange_reference_prices:
            await reference_price.initialize_if_required(exchange_manager)
            for dependency in reference_price.get_dependencies(exchange_manager):
                if dependency.data_source == trading_constants.MARK_PRICE_CHANNEL:
                    # mark price = watched symbol
                    watched_symbols.append(dependency.symbol)
                else:
                    # other data source = traded symbol
                    traded_symbols.append(dependency.symbol)
                    if dependency.time_frame:
                        # a specific time framee is required: make sure it's available 
                        tf = commons_enums.TimeFrames(dependency.time_frame)
                        if tf not in required_time_frames:
                            required_time_frames.append(tf)
        # hedging engine requirements
        if self._hedging_engine and self._hedging_engine.hedging_exchange_name == exchange_manager.exchange_name:
            traded_symbols.append(self.symbol)
        if traded_symbols:
            await trading_api.register_new_pairs_on_exchange_manager(
                exchange_manager,
                traded_symbols,
                watch_only=False,
                time_frames=required_time_frames
            )
        if watched_symbols:
            await trading_api.register_new_pairs_on_exchange_manager(
                exchange_manager,
                watched_symbols,
                watch_only=True,
            )

    async def force_stop_strategy(
        self,
        reason_description: typing.Optional[str]
    ):
        self.logger.warning(
            f"Force stopping strategy for {self.symbol} [{self.exchange_manager.exchange_name}] reason description: {reason_description}"
        )
        self.should_stop = True
        finished_previous_execution = True
        if self.latest_actions_plan is not None and not self.latest_actions_plan.processed.is_set():
            self.logger.info(
                f"Force cancelling previous {self.symbol} [{self.exchange_manager.exchange_name}] execution: reason description: {reason_description}"
            )
            self.latest_actions_plan.force_cancelled = True
            finished_previous_execution = self.latest_actions_plan.processed.is_set()
        if self._scheduled_volume is not None:
            self._scheduled_volume.stop()
        await self._emergency_cancel_all_market_making_orders()
        if self.latest_actions_plan is not None and not finished_previous_execution:
            await asyncio.wait_for(self.latest_actions_plan.processed.wait(), self.ORDER_ACTION_TIMEOUT)
            # re-cancel all orders in case the previous execution created new orders before being force cancelled
            await self._emergency_cancel_all_market_making_orders()

    async def _emergency_cancel_all_market_making_orders(self):
        for order in self.get_market_making_orders():
            try:
                await self.trading_mode.cancel_order(order, wait_for_cancelling=False)
            except trading_errors.OrderNotFoundOnCancelError as err:
                self.logger.error(f"Order not found on cancel: {order} ({err})")
            except Exception as err:
                self.logger.exception(err, True, f"Error when cancelling order: {err}, order: {order}")
