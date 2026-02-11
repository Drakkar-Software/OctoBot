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
import decimal
import datetime
import typing

import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading_mode
import tentacles.Trading.Mode.profile_copy_trading_mode.profile_distribution as profile_distribution
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.modes.script_keywords as script_keywords
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_services.api as services_api
import octobot_services.constants as services_constants
import async_channel.channels as channels

try:
    import tentacles.Services.Services_feeds.exchange_service_feed as exchange_service_feed
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock exchange_service_feed imports
        class ExchangeServiceFeedImportMock:
            class ExchangeServiceFeed:
                def get_name(self, *args, **kwargs):
                    raise ImportError("exchange_service_feed not installed")
        exchange_service_feed = ExchangeServiceFeedImportMock()

class ProfileCopyTradingMode(index_trading_mode.IndexTradingMode):
    SERVICE_FEED_CLASS = exchange_service_feed.ExchangeServiceFeed if hasattr(exchange_service_feed, 'ExchangeServiceFeed') else None

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.exchange_profile_ids: list[str] = []
        self.per_exchange_profile_portfolio_ratio: decimal.Decimal = trading_constants.ONE
        self.allocation_padding_ratio: decimal.Decimal = trading_constants.ZERO
        self.new_position_only: bool = False
        self.min_unrealized_pnl_percent: typing.Optional[decimal.Decimal] = None
        self.max_unrealized_pnl_percent: typing.Optional[decimal.Decimal] = None
        self.min_mark_price: typing.Optional[decimal.Decimal] = None
        self.max_mark_price: typing.Optional[decimal.Decimal] = None
        self.started_at: datetime.datetime = datetime.datetime.now()
        self.distribution_per_exchange_profile: dict[str, list] = {}

    def init_user_inputs(self, inputs: dict) -> None:
        super().init_user_inputs(inputs)
        self.exchange_profile_ids = self.UI.user_input(
            ProfileCopyTradingModeProducer.EXCHANGE_PROFILE_IDS,
            commons_enums.UserInputTypes.STRING_ARRAY,
            self.exchange_profile_ids, 
            inputs, 
            other_schema_values={"uniqueItems": True},
            array_indexes=[0],
            item_title="Exchange profile id",
            title="Exchange profile ids to copy"
        )
        self.per_exchange_profile_portfolio_ratio = decimal.Decimal(str(self.UI.user_input(
            ProfileCopyTradingModeProducer.PER_PROFILE_PORTFOLIO_RATIO, commons_enums.UserInputTypes.FLOAT,
            float(self.per_exchange_profile_portfolio_ratio * trading_constants.ONE_HUNDRED), inputs,
            min_val=0, max_val=100,
            title="Percentage of the portfolio to allocate to each exchange profile.",
        ))) / trading_constants.ONE_HUNDRED
        self.allocation_padding_ratio = decimal.Decimal(str(self.UI.user_input(
            ProfileCopyTradingModeProducer.ALLOCATION_PADDING_RATIO, commons_enums.UserInputTypes.FLOAT,
            float(self.allocation_padding_ratio * trading_constants.ONE_HUNDRED), inputs,
            min_val=0, max_val=100,
            title="Allocation padding: Allow trading up to X% more than the configured portfolio ratio. "
                  "Useful when the copied profile increases its position count. "
                  "E.g., 20% padding on 50% allocation allows up to 60% usage.",
        ))) / trading_constants.ONE_HUNDRED
        self.new_position_only = self.UI.user_input(
            ProfileCopyTradingModeProducer.NEW_POSITION_ONLY, commons_enums.UserInputTypes.BOOLEAN,
            self.new_position_only, inputs,
            title="New position only: When enabled, only new positions will be taken into account for the portfolio allocation.",
        )
        min_unrealized_pnl_percent = self.UI.user_input(
            ProfileCopyTradingModeProducer.MIN_UNREALIZED_PNL_PERCENT, commons_enums.UserInputTypes.FLOAT,
            float(self.min_unrealized_pnl_percent) if self.min_unrealized_pnl_percent is not None else None, inputs,
            min_val=-999, max_val=999,
            title="Minimum unrealized PnL ratio: Only copy positions with at least this ratio of unrealized PnL on collateral (0.1 = 10%). Set to None to disable.",
        )
        self.min_unrealized_pnl_percent = None if min_unrealized_pnl_percent is None else decimal.Decimal(str(min_unrealized_pnl_percent))
        max_unrealized_pnl_percent = self.UI.user_input(
            ProfileCopyTradingModeProducer.MAX_UNREALIZED_PNL_PERCENT, commons_enums.UserInputTypes.FLOAT,
            float(self.max_unrealized_pnl_percent) if self.max_unrealized_pnl_percent is not None else None, inputs,
            min_val=-999, max_val=999,
            title="Maximum unrealized PnL ratio: Only copy positions with at most this ratio of unrealized PnL on collateral (0.1 = 10%). Set to None to disable.",
        )
        self.max_unrealized_pnl_percent = None if max_unrealized_pnl_percent is None else decimal.Decimal(str(max_unrealized_pnl_percent))
        min_mark_price = self.UI.user_input(
            ProfileCopyTradingModeProducer.MIN_MARK_PRICE, commons_enums.UserInputTypes.FLOAT,
            float(self.min_mark_price) if self.min_mark_price is not None else None, inputs,
            min_val=0, max_val=10000000,
            title="Minimum mark price: Only copy positions with mark price >= this value.",
        )
        self.min_mark_price = None if min_mark_price is None else decimal.Decimal(str(min_mark_price))
        max_mark_price = self.UI.user_input(
            ProfileCopyTradingModeProducer.MAX_MARK_PRICE, commons_enums.UserInputTypes.FLOAT,
            float(self.max_mark_price) if self.max_mark_price is not None else None, inputs,
            min_val=0, max_val=10000000,
            title="Maximum mark price: Only copy positions with mark price <= this value.",
        )
        self.max_mark_price = None if max_mark_price is None else decimal.Decimal(str(max_mark_price))
        self._validate_portfolio_allocation_feasibility()

    def _validate_portfolio_allocation_feasibility(self):
        # Validate that the percentage of the portfolio * exchange profile count is equal or inferior to 100%
        total_allocation = self.per_exchange_profile_portfolio_ratio * decimal.Decimal(len(self.exchange_profile_ids))
        if total_allocation > decimal.Decimal(1):
            raise ValueError(
                f"Total portfolio allocation exceeds 100%: "
                f"{float(self.per_exchange_profile_portfolio_ratio * trading_constants.ONE_HUNDRED):.2f}% "
                f"per profile x {len(self.exchange_profile_ids)} profiles = "
                f"{float(total_allocation * trading_constants.ONE_HUNDRED):.2f}%"
            )

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
            trading_enums.ExchangeTypes.OPTION,
        ]

    def get_current_state(self) -> typing.Tuple[str, float]:
        return super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name, self.producers[0].final_eval

    def get_mode_producer_classes(self) -> list:
        return [ProfileCopyTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [ProfileCopyTradingModeConsumer]

    async def _get_feed_consumers(self):
        feed_consumer = []
        if self.SERVICE_FEED_CLASS is None:
            if commons_constants.USE_MINIMAL_LIBS:
                self.logger.debug(
                    "Exchange service feed not installed, this trading mode won't be listening to exchange service feed."
                )
            else:
                raise ImportError("ExchangeServiceFeed not installed")
        else:
            service_feed = services_api.get_service_feed(self.SERVICE_FEED_CLASS, self.bot_id)
            if service_feed is not None:
                feed_config: dict = {
                    services_constants.CONFIG_EXCHANGE_PROFILES: [
                        {
                            services_constants.CONFIG_EXCHANGE_PROFILE_ID: profile_id
                        } for profile_id in self.exchange_profile_ids
                    ]
                }
                service_feed.update_feed_config(feed_config, self.exchange_manager.id, self.exchange_manager.exchange_name)
                feed_consumer = [await channels.get_chan(service_feed.FEED_CHANNEL.get_name()).new_consumer(
                    self._exchange_service_feed_callback
                )]
            else:
                self.logger.error("Impossible to find the Exchange service feed, this trading mode can't work.")
        return feed_consumer

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        return consumers + await self._get_feed_consumers()

    async def _exchange_service_feed_callback(self, data):
        profile_data: exchange_service_feed.ExchangeProfile = data.get(services_constants.FEED_METADATA, "")
        errors = []
        for error in errors:
            self.logger.error(error)
        try:
            await self.producers[0].profile_callback(profile_data, script_keywords.get_base_context(self))
        except (trading_errors.InvalidArgumentError, trading_errors.InvalidCancelPolicyError) as e:
            self.logger.error(f"Error when processing exchange profile: {e} (profile: {profile_data})")
        except trading_errors.MissingFunds as e:
            self.logger.error(f"Error when processing exchange profile: not enough funds: {e} (profile: {profile_data})")
        except KeyError as e:
            self.logger.error(f"Error when processing exchange profile: missing {e} required value (profile: {profile_data})")
        except Exception as e:
            self.logger.error(
                f"Unexpected error when processing exchange profile: {e} {e.__class__.__name__} (profile: {profile_data})"
            )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return True

    @staticmethod
    def is_backtestable():
        return True

    def update_global_distribution(self):
        global_distribution = profile_distribution.update_global_distribution(
            self.distribution_per_exchange_profile,
            self.per_exchange_profile_portfolio_ratio,
            self.exchange_profile_ids,
            self.allocation_padding_ratio
        )
        self.ratio_per_asset = global_distribution[profile_distribution.RATIO_PER_ASSET]
        self.total_ratio_per_asset = global_distribution[profile_distribution.TOTAL_RATIO_PER_ASSET]
        self.indexed_coins = global_distribution[profile_distribution.INDEXED_COINS]
        self.indexed_coins_prices = global_distribution[profile_distribution.INDEXED_COINS_PRICES]
        # IndexTradingMode consumes reference_market_ratio as the tradable portfolio ratio.
        # Profile distribution returns the reserved reference-market ratio, so convert it.
        reference_market_reserved_ratio = global_distribution[profile_distribution.REFERENCE_MARKET_RATIO]
        self.reference_market_ratio = max(
            trading_constants.ZERO,
            min(trading_constants.ONE, trading_constants.ONE - reference_market_reserved_ratio)
        )


class ProfileCopyTradingModeConsumer(index_trading_mode.IndexTradingModeConsumer):
    pass

class ProfileCopyTradingModeProducer(index_trading_mode.IndexTradingModeProducer):
    EXCHANGE_PROFILE_IDS = "exchange_profile_ids"
    PER_PROFILE_PORTFOLIO_RATIO = "per_exchange_profile_portfolio_ratio"
    ALLOCATION_PADDING_RATIO = "allocation_padding_ratio"
    NEW_POSITION_ONLY = "new_position_only"
    MIN_UNREALIZED_PNL_PERCENT = "min_unrealized_pnl_percent"
    MAX_UNREALIZED_PNL_PERCENT = "max_unrealized_pnl_percent"
    MIN_MARK_PRICE = "min_mark_price"
    MAX_MARK_PRICE = "max_mark_price"

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.requires_initializing_appropriate_coins_distribution = False

    async def profile_callback(self, profile_data: exchange_service_feed.ExchangeProfile, ctx):
        self.trading_mode.distribution_per_exchange_profile = profile_distribution.update_distribution_based_on_profile_data(
            profile_data, self.trading_mode.distribution_per_exchange_profile, self.trading_mode.new_position_only,
            self.trading_mode.started_at, self.trading_mode.min_unrealized_pnl_percent,
            self.trading_mode.max_unrealized_pnl_percent, self.trading_mode.min_mark_price,
            self.trading_mode.max_mark_price
        )
        if profile_distribution.has_distribution_for_all_exchange_profiles(
            self.trading_mode.distribution_per_exchange_profile, self.trading_mode.exchange_profile_ids
        ):
            self.trading_mode.update_global_distribution()
            await self._check_index_if_necessary()
        else:
            self.logger.warning(f"Distribution for all exchange profiles are not yet available, skipping copy...")

    async def ohlcv_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame: str, candle: dict, init_call: bool = False):
        # Nothing to do
        pass

    async def kline_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame, kline: dict):
        # Nothing to do
        pass
