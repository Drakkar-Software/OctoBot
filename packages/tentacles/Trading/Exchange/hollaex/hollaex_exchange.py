#  Drakkar-Software OctoBot-Tentacles
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
import ccxt
import typing
import decimal
import enum
import cachetools

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.symbols as symbols_utils
import octobot_commons.logging as logging
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as exchanges
import octobot_trading.errors as errors
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache


_EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME: dict[str, dict] = {}
# refresh exchange fee tiers every day but don't delete outdated info, only replace it with updated ones
_REFRESHED_EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME : cachetools.TTLCache[str, bool] = cachetools.TTLCache(
    maxsize=50, ttl=commons_constants.DAYS_TO_SECONDS
)
DEFAULT_FEE_SIDE = trading_enums.ExchangeFeeSides.GET.value     # the fee is always in the currency you get


class FeeTiers(enum.Enum):
    BASIC = "1"
    VIP = "2"


class hollaexConnector(exchanges.CCXTConnector):

    async def load_symbol_markets(
        self,
        reload=False,
        market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None
    ):
        await super().load_symbol_markets(reload=reload, market_filter=market_filter)
        await self.disable_quick_trade_only_pairs()
        # also refresh fee tiers when necessary
        if self.exchange_manager.exchange_name not in _REFRESHED_EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME:
            authenticated_cache = self.exchange_manager.exchange.requires_authentication_for_this_configuration_only()
            # always update fees cache using all markets to avoid market filter side effects from the current client
            all_markets = ccxt_clients_cache.get_exchange_parsed_markets(
                ccxt_clients_cache.get_client_key(self.client, authenticated_cache)
            )
            await self._refresh_exchange_fee_tiers(all_markets)

    async def disable_quick_trade_only_pairs(self):
        # on hollaex exchanges, a market can be "quick trade only" or "spot order book trade" as well.
        # a quick trade only market can't be traded like a spot market, disable it.
        exchange_constants = await self.client.publicGetConstants()
        quick_trade_only_pairs = self._parse_quick_trades_only_pairs(exchange_constants)
        if disabled_pairs := [
            pair 
            for pair in quick_trade_only_pairs
            if pair in self.client.markets
        ]:
            self.logger.info(
                f"Disabling [{self.exchange_manager.exchange_name}] {len(disabled_pairs)} quick trade only pairs: {disabled_pairs}"
            )
            for disabled_pair in disabled_pairs:
                self._disable_pair(disabled_pair)

    def _disable_pair(self, symbol: str):
        if symbol in self.client.markets:
            self.client.markets[symbol][trading_enums.ExchangeConstantsMarketStatusColumns.ACTIVE.value] = False

    def _parse_quick_trades_only_pairs(self, exchange_constants: dict) -> list[str]:
        if 'quicktrade' not in exchange_constants:
            self.logger.error(
                f"Unexpected [{self.exchange_manager.exchange_name}] no 'quicktrade' key found in exchange constants"
            )
            return []
        quick_trade_details = exchange_constants['quicktrade']
        # format: [{'type': 'network', 'symbol': 'rune-usdt', 'active': True}, ...]
        quick_trade_only_pairs = []
        for pair_details in quick_trade_details:
            if "type" not in pair_details or "symbol" not in pair_details:
                self.logger.error(f"Ignored invalid quick trade only pair details: {pair_details}")
                continue
            # type=pro means this pair is traded in spot order book markets, otherwise it's a quick trade only pair
            if pair_details['type'] != "pro":
                market_id = pair_details["symbol"]
                market = self.client.safe_market(market_id, None, '-')
                quick_trade_only_pairs.append(
                    market[trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value]
                )
        return quick_trade_only_pairs

    async def _refresh_exchange_fee_tiers(self, all_markets: list[dict]):
        self.logger.info(f"Refreshing {self.exchange_manager.exchange_name} fee tiers")
        response = await self.client.publicGetTiers()
        # similar to ccxt's fetch_trading_fees except that we parse all tiers
        if not response:
            self.logger.error("No fee tiers available")
        fees_by_tier = {}
        for tier, values in response.items():
            fees = self.client.safe_value(values, 'fees', {})
            makerFees = self.client.safe_value(fees, 'maker', {})
            takerFees = self.client.safe_value(fees, 'taker', {})
            result: dict = {}
            for market in all_markets:
                # get symbol, taker and maker fee for each traded pair identified by its id
                symbol = market[trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value]
                maker_string = self.client.safe_string(
                    makerFees, market[trading_enums.ExchangeConstantsMarketStatusColumns.ID.value]
                )
                taker_string = self.client.safe_string(
                    takerFees, market[trading_enums.ExchangeConstantsMarketStatusColumns.ID.value]
                )
                if not (maker_string and taker_string):
                    self.logger.error(
                        f"Missing fee details for {symbol} in fetched {self.exchange_manager.exchange_name} fees "
                        f"(using {market[trading_enums.ExchangeConstantsMarketStatusColumns.ID.value]} as market id)"
                    )
                    continue
                result[symbol] = {
                    trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value:
                        self.client.parse_number(ccxt.Precise.string_div(maker_string, '100')),
                    trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value:
                        self.client.parse_number(ccxt.Precise.string_div(taker_string, '100')),
                    trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value: market.get(
                        trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value, DEFAULT_FEE_SIDE
                    )
                    # don't keep unecessary info
                    # 'info': fees,
                    # 'symbol': symbol,
                    # 'percentage': True,
                    # 'tierBased': True,
                }
            fees_by_tier[tier] = result
        exchange_name = self.exchange_manager.exchange_name
        _EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME[exchange_name] = fees_by_tier
        _REFRESHED_EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME[exchange_name] = True
        sample = {
            tier: next(iter(fees.values())) if fees else None
            for tier, fees in fees_by_tier.items()
        }
        fee_pairs = list(fees_by_tier[next(iter(fees_by_tier))]) if fees_by_tier else []
        self.logger.info(
            f"Refreshed {exchange_name} fee tiers. Sample: {sample}. {len(sample)} tiers: {list(sample)} "
            f"over {len(fee_pairs)} pairs: {fee_pairs}. Using fee tiers "
            f"{self._get_fee_tiers(self.exchange_manager.exchange, not self.exchange_manager.is_backtesting).value}."
        )

    @classmethod
    def simulator_connector_calculate_fees_factory(cls, exchange_name: str, tiers: FeeTiers):
        # same signature as ExchangeSimulatorConnector.calculate_fees
        def simulator_connector_calculate_fees(
            symbol: str, order_type: trading_enums.TraderOrderType,
            quantity: decimal.Decimal, price: decimal.Decimal, taker_or_maker: str
        ):
            # no try/catch: should raise in case fees are not available
            return cls._calculate_fetched_fees(
                exchange_name, tiers, symbol, order_type, quantity, price, taker_or_maker
            )
        return simulator_connector_calculate_fees

    @classmethod
    def simulator_connector_get_fees_factory(cls, exchange_name: str, tiers: FeeTiers):
        # same signature as ExchangeSimulatorConnector.get_fees
        def simulator_connector_get_fees(symbol):
            return cls._get_fees(exchange_name, tiers, symbol)
        return simulator_connector_get_fees

    @classmethod
    def register_simulator_connector_fee_methods(
        cls, exchange_name: str, simulator_connector: exchanges.ExchangeSimulatorConnector
    ):
        # only called in backtesting
        # overrides exchange simulator connector calculate_fees and get_fees to use fetched fees instead
        fee_tiers = cls._get_fee_tiers(None, False)
        simulator_connector.calculate_fees = cls.simulator_connector_calculate_fees_factory(exchange_name, fee_tiers)
        simulator_connector.get_fees = cls.simulator_connector_get_fees_factory(exchange_name, fee_tiers)

    def calculate_fees(
        self, symbol: str, order_type: trading_enums.TraderOrderType,
        quantity: decimal.Decimal, price: decimal.Decimal, taker_or_maker: str
    ):
        # only called in live trading
        is_real_trading = not self.exchange_manager.is_backtesting  # consider live trading as real to use basic tier
        try:
            fee_tiers = self._get_fee_tiers(self.exchange_manager.exchange, is_real_trading)
            return self._calculate_fetched_fees(
                self.exchange_manager.exchange_name, fee_tiers,
                symbol, order_type, quantity, price, taker_or_maker
            )
        except errors.MissingFeeDetailsError as err:
            self.logger.error(f"Error calculating fees: {err}. Using default ccxt values")
            # live trading: can fallback to ccxt default values as the ccxt client exists and is initialized
            return super().calculate_fees(symbol, order_type, quantity, price, taker_or_maker)

    def get_fees(self, symbol):
        # only called in live trading
        try:
            is_real_trading = not self.exchange_manager.is_backtesting  # consider live trading as real to use basic tier
            fee_tiers = self._get_fee_tiers(self.exchange_manager.exchange, is_real_trading)
            return self._get_fees(self.exchange_manager.exchange_name, fee_tiers, symbol)
        except errors.MissingFeeDetailsError:
            if _EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME.get(self.exchange_manager.exchange_name):
                self.logger.error(f"Missing {self.exchange_manager.exchange_name} {symbol} fee details, using default value")
            else:
                self.logger.warning(f"Missing all {self.exchange_manager.exchange_name} fee details, using ccxt default values")
            market = self.get_market_status(symbol, with_fixer=False)
            # use default ccxt values
            return {
                trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: market[
                    trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value
                ],
                trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: market[
                    trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
                ],
                trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value: market.get(
                    trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value, DEFAULT_FEE_SIDE
                ),
                trading_enums.ExchangeConstantsMarketPropertyColumns.FEE.value: market.get(
                    trading_enums.ExchangeConstantsMarketPropertyColumns.FEE.value,
                    trading_constants.CONFIG_DEFAULT_FEES
                )
            }

    @classmethod
    def _calculate_fetched_fees(
        cls, exchange_name: str, fee_tiers: FeeTiers, symbol: str, order_type: trading_enums.TraderOrderType,
        quantity: decimal.Decimal, price: decimal.Decimal, taker_or_maker: str
    ):
        # will raise MissingFeeDetailsError if fees details are not available
        fee_details = cls._get_fetched_fees(exchange_name, fee_tiers, symbol)
        fee_side = fee_details[trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value]
        side = exchanges.get_order_side(order_type)
        # similar as ccxt.Exchange.calculate_fee
        if fee_side == trading_enums.ExchangeFeeSides.GET.value:
            # the fee is always in the currency you get
            use_quote = side == trading_enums.TradeOrderSide.SELL.value
        elif fee_side == trading_enums.ExchangeFeeSides.GIVE.value:
            # the fee is always in the currency you give
            use_quote = side == trading_enums.TradeOrderSide.BUY.value
        else:
            # the fee is always in feeSide currency
            use_quote = fee_side == trading_enums.ExchangeFeeSides.QUOTE.value
        parsed_symbol = symbols_utils.parse_symbol(symbol)
        if use_quote:
            cost = quantity * price
            fee_currency = parsed_symbol.quote
        else:
            cost = quantity
            fee_currency = parsed_symbol.base
        fee_rate = decimal.Decimal(str(fee_details[taker_or_maker]))
        fee_cost = cost * fee_rate
        return {
            trading_enums.FeePropertyColumns.TYPE.value: taker_or_maker,
            trading_enums.FeePropertyColumns.CURRENCY.value: fee_currency,
            trading_enums.FeePropertyColumns.RATE.value: float(fee_rate),
            trading_enums.FeePropertyColumns.COST.value: float(fee_cost),
        }

    @classmethod
    def _get_fee_tiers(cls, rest_exchange: typing.Optional[exchanges.RestExchange], is_real_trading: bool):
        if (
            rest_exchange
            and isinstance(rest_exchange, hollaex)
            and (fee_tiers := rest_exchange.get_configured_fee_tiers())
        ):
            return fee_tiers
        # default to basic tier
        return FeeTiers.BASIC if is_real_trading else FeeTiers.VIP

    @classmethod
    def _get_fees(cls, exchange_name: str, tiers: FeeTiers, symbol: str):
        return {
            ** cls._get_fetched_fees(exchange_name, tiers, symbol),
            ** {
                # todo update this if withdrawal fees become relevant
                trading_enums.ExchangeConstantsMarketPropertyColumns.FEE.value: trading_constants.CONFIG_DEFAULT_FEES
            }
        }

    @classmethod
    def _get_default_fee_symbol(cls, exchange: str):
        try:
            exchange_fees = _EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME[exchange]
            first_fee_tier = next(iter(exchange_fees.values()))
            return next(iter(first_fee_tier))
        except (StopIteration, KeyError) as err:
            raise errors.MissingFeeDetailsError(
                f"No available {exchange} fee details {err} ({err.__class__.__name__})"
            ) from err

    @classmethod
    def _get_fetched_fees(cls, exchange: str, tier_to_use: FeeTiers, symbol: str):
        try:
            exchange_fees = _EXCHANGE_FEE_TIERS_BY_EXCHANGE_NAME[exchange]
        except KeyError as err:
            raise errors.MissingFeeDetailsError(f"No available {exchange} fee details") from err
        try:
            return exchange_fees[tier_to_use.value][symbol]
        except KeyError as err:
            if not exchange_fees:
                # mssing exchange fees, should not happen
                raise errors.MissingFeeDetailsError(
                    f"Unexpected: missing {exchange} fee details"
                ) from err
            if symbol not in exchange_fees[FeeTiers.BASIC.value]:
                default_fee_symbol = cls._get_default_fee_symbol(exchange)
                if symbol == default_fee_symbol:
                    raise errors.MissingFeeDetailsError(
                        f"No available {exchange} {tier_to_use.name} {symbol} fee details"
                    ) from err
                logging.get_logger(cls.__name__).error(
                    f"No {symbol} fee tier info on {exchange}: using {default_fee_symbol} fees as default value"
                )
                return cls._get_fetched_fees(exchange, tier_to_use, default_fee_symbol)
            if tier_to_use.value not in exchange_fees and FeeTiers.BASIC.value in tier_to_use.value:
                # symbol is in exchange_fees[FeeTiers.BASIC.value] or previous condition would have triggered
                logging.get_logger(cls.__name__).info(
                    f"Falling back on {FeeTiers.BASIC.name} fee tier for {exchange}: no {tier_to_use.name} value"
                )
                return exchange_fees[FeeTiers.BASIC.value][symbol]
            raise errors.MissingFeeDetailsError(
                f"No available {exchange} {tier_to_use.name} {symbol} fee details"
            ) from err


class hollaex(exchanges.RestExchange):
    DESCRIPTION = ""
    DEFAULT_CONNECTOR_CLASS = hollaexConnector

    FIX_MARKET_STATUS = True

    BASE_REST_API = "api.hollaex.com"
    REST_KEY = "rest"
    FEE_TIERS_KEY = "fee_tiers"
    HAS_WEBSOCKETS_KEY = "has_websockets"
    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    SUPPORT_FETCHING_CANCELLED_ORDERS = False

    IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH = True

    # STOP_PRICE is used in ccxt/hollaex instead of default STOP_LOSS_PRICE
    STOP_LOSS_CREATE_PRICE_PARAM = ccxt_enums.ExchangeOrderCCXTUnifiedParams.STOP_PRICE.value
    STOP_LOSS_EDIT_PRICE_PARAM = STOP_LOSS_CREATE_PRICE_PARAM

    # should be overridden locally to match exchange support
    SUPPORTED_ELEMENTS = {
        trading_enums.ExchangeTypes.FUTURE.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                trading_enums.TraderOrderType.STOP_LOSS,
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            # not supported or need custom mechanics with batch orders
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        },
        trading_enums.ExchangeTypes.SPOT.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                trading_enums.TraderOrderType.STOP_LOSS,    # still broken ccxt 4.5.8: stop param is ignored by exchange because it's sent as a string instead of float. Converting it to flaat fails the signature
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        }
    }

    DEFAULT_MAX_LIMIT = 500
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # '"message":"Access denied: Unauthorized Access. This key does not have the right permissions to access this endpoint"'
        ("permissions to access",),
    ]
    EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # {"message":"Access denied: Unauthorized Access.
        # The IP address you are reaching this endpoint through is not allowed to access this endpoint"}
        ("the ip address", "is not allowed"),
    ]
    EXCHANGE_MAX_ORDERS_FOR_MARKET_REACHED_ERRORS: typing.List[typing.Iterable[str]] = [
        # "hollaex {"message":"You are only allowed to have maximum 50 active orders per market"}"
        ("maximum", "active orders", "per market"),
    ]

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        super().__init__(config, exchange_manager, exchange_config_by_exchange, connector_class=connector_class)
        self.exchange_manager.rest_only = self.exchange_manager.rest_only \
            or not self.tentacle_config.get(
                self.HAS_WEBSOCKETS_KEY, not self.exchange_manager.rest_only
            )

    def get_adapter_class(self):
        return HollaexCCXTAdapter

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        """
        Called at constructor, should define all the exchange's user inputs.
        """
        cls.CLASS_UI.user_input(
            cls.REST_KEY, commons_enums.UserInputTypes.TEXT, f"https://{cls.BASE_REST_API}", inputs,
            title=f"Address of the Hollaex based exchange API (similar to https://{cls.BASE_REST_API})"
        )
        cls.CLASS_UI.user_input(
            cls.FEE_TIERS_KEY, commons_enums.UserInputTypes.OPTIONS, FeeTiers.BASIC.value, inputs,
            title=f"Fee tiers to use for the exchange. Used to predict fees.",
            options=[tier.value for tier in FeeTiers]
        )
        cls.CLASS_UI.user_input(
            cls.HAS_WEBSOCKETS_KEY, commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            title=f"Use websockets feed. To enable only when websockets are supported by the exchange."
        )

    def get_additional_connector_config(self):
        return {
            ccxt_enums.ExchangeColumns.URLS.value: self.get_patched_urls(self.get_api_url()),
            ccxt_constants.CCXT_OPTIONS: {
                "api-expires": int(trading_constants.DEFAULT_REQUEST_TIMEOUT / 1000)
            },
        }

    def get_api_url(self):
        return self.tentacle_config[self.REST_KEY]

    def get_configured_fee_tiers(self) -> typing.Optional[FeeTiers]:
        if tiers := self.tentacle_config.get(self.FEE_TIERS_KEY):
            return FeeTiers(tiers)
        return None

    @classmethod
    def get_custom_url_config(cls, tentacle_config: dict, exchange_name: str) -> dict:
        if details := cls.get_exchange_details(tentacle_config, exchange_name):
            return {
                ccxt_enums.ExchangeColumns.URLS.value: cls.get_patched_urls(details.api)
            }
        return {}

    @classmethod
    def get_exchange_details(cls, tentacle_config, exchange_name) -> typing.Optional[exchanges.ExchangeDetails]:
        return None

    @classmethod
    def get_patched_urls(cls, api_url: str):
        urls = ccxt.hollaex().urls
        custom_urls = {
            ccxt_enums.ExchangeColumns.API.value: {
                cls.REST_KEY: api_url
            }
        }
        urls.update(custom_urls)
        return urls

    @classmethod
    def get_name(cls):
        return 'hollaex'

    @classmethod
    def is_configurable(cls):
        return True

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        signature_identifier = "api-signature"
        return bool(
            headers
            and signature_identifier in headers
        )

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        #  (30/06/2025: Error 1010 - You are only allowed to have maximum 50 active orders per market)
        return 50

    async def get_account_id(self, **kwargs: dict) -> str:
        with self.connector.error_describer(True):
            user_info = await self.connector.client.private_get_user()
            return user_info["id"]

    async def get_closed_orders(self, symbol: str = None, since: int = None,
                                limit: int = None, **kwargs: dict) -> list:
        # get_closed_orders sometimes does not return orders use _get_closed_orders_from_my_recent_trades in this case
        return (
            await super().get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs) or
            await self._get_closed_orders_from_my_recent_trades(
                symbol=symbol, since=since, limit=limit, **kwargs
            )
        )


class HollaexCCXTAdapter(exchanges.CCXTAdapter):

    def fix_order(self, raw, symbol=None, **kwargs):
        raw_order_info = raw[ccxt_enums.ExchangePositionCCXTColumns.INFO.value]
        # average is not supported by ccxt
        fixed = super().fix_order(raw, symbol=symbol, **kwargs)
        if not fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] and "average" in raw_order_info:
            fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = raw_order_info.get("average", 0)

        if fixed[ccxt_enums.ExchangeOrderCCXTColumns.TRIGGER_PRICE.value]:
            order_type = trading_enums.TradeOrderType.STOP_LOSS.value
            # todo uncomment when stop loss limit are supported
            # if fixed[ccxt_enums.ExchangeOrderCCXTColumns.PRICE.value] is None:
            #     order_type = trading_enums.TradeOrderType.STOP_LOSS.value
            fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = order_type

        # fees are usually not in order, but if they are, fix them as ccxt is not parsing them
        self._fix_fees(raw_order_info, fixed)
        return fixed

    def _fix_fees(self, info, fixed):
        if (fee_coin := info.get("fee_coin")) and fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.FEE.value):
            # fee_coin is wrongly overwritten by ccxt as quote currency, used fetched value
            fixed[trading_enums.ExchangeConstantsOrderColumns.FEE.value][
                trading_enums.FeePropertyColumns.CURRENCY.value
            ] = fee_coin.upper()

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed
