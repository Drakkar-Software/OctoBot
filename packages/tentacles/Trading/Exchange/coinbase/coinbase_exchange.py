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
import typing
import decimal
import ccxt
import copy

import octobot_trading.errors
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.symbols as commons_symbols
import octobot_commons.logging as logging
import octobot_commons.os_util as os_util


ALIASED_SYMBOLS = set()

# hard code Coinbase base tier fees as long as there is no way to fetch it
# https://www.coinbase.com/advanced-fees
INTRO_1_TAKER_MAKER_FEES = (0.012, 0.006) # Intro 1: 1.2%, 0.6%: <1k monthly trading volume Coinbase taker fees tier
INTRO_2_TAKER_MAKER_FEES = (0.0075, 0.0035) # Intro 2: 0.75%, 0.35%: >1k & <10k monthly trading volume Coinbase taker fees tier


# simulate live fees considering the INTRO_1_TAKER_MAKER_FEES as the base tier fees to avoid 
# fees issues for intro 1 tier users
DEFAULT_LIVE_TAKER_FEE_VALUE = INTRO_1_TAKER_MAKER_FEES[0]
DEFAULT_LIVE_MAKER_FEE_VALUE = INTRO_1_TAKER_MAKER_FEES[1]
# compute backtesting fees considering the INTRO_2_TAKER_MAKER_FEES as the base tier fees
DEFAULT_BACKTESTING_TAKER_FEE_VALUE = INTRO_2_TAKER_MAKER_FEES[0]
DEFAULT_BACKTESTING_MAKER_FEE_VALUE = INTRO_2_TAKER_MAKER_FEES[1]
# disabled by default
FORCE_COINBASE_BASE_FEES = os_util.parse_boolean_environment_var("FORCE_COINBASE_BASE_FEES", "false")
_MAX_CURSOR_ITERATIONS = 10


def _refresh_alias_symbols(client):
    if client.markets:
        ALIASED_SYMBOLS.update({
            symbol
            for symbol, market_status in client.markets.items()
            if market_status["info"].get("alias_to")
        })


def _coinbase_retrier(f):
    async def coinbase_retrier_wrapper(*args, **kwargs):
        last_error = None
        for i in range(0, Coinbase.FAKE_RATE_LIMIT_ERROR_INSTANT_RETRY_COUNT):
            try:
                return await f(*args, **kwargs)
            except (
                octobot_trading.errors.FailedRequest, octobot_trading.errors.RateLimitExceeded, ccxt.BaseError
            ) as err:
                last_error = err
                if Coinbase.INSTANT_RETRY_ERROR_CODE in str(err):
                    # should retry instantly, error on coinbase side
                    logging.get_logger(Coinbase.get_name()).debug(
                        f"{Coinbase.INSTANT_RETRY_ERROR_CODE} error on {f.__name__}(args={args[1:]} kwargs={kwargs}) "
                        f"request, retrying now. Attempt {i+1} / {Coinbase.FAKE_RATE_LIMIT_ERROR_INSTANT_RETRY_COUNT}, "
                        f"error: {err} ({last_error.__class__.__name__})."
                    )
                else:
                    raise
        last_error = last_error or RuntimeError("Unknown Coinbase error")  # to be able to "raise from" in next line
        raise octobot_trading.errors.FailedRequest(
            f"Failed Coinbase request after {Coinbase.FAKE_RATE_LIMIT_ERROR_INSTANT_RETRY_COUNT} "
            f"retries on {f.__name__}(args={args[1:]} kwargs={kwargs}) due "
            f"to {Coinbase.INSTANT_RETRY_ERROR_CODE} error code. "
            f"Last error: {last_error} ({last_error.__class__.__name__})"
        ) from last_error
    return coinbase_retrier_wrapper


class CoinbaseConnector(ccxt_connector.CCXTConnector):

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchanges.ExchangeCredentialsData], exchanges.ExchangeCredentialsData]=None
    ) -> tuple:
        return super()._client_factory(force_unauth, keys_adapter=self._keys_adapter)

    def _keys_adapter(self, creds: exchanges.ExchangeCredentialsData) -> exchanges.ExchangeCredentialsData:
        if creds.auth_token:
            # when auth token is provided, force invalid keys
            creds.api_key = "ANY_KEY"
            creds.secret = "ANY_KEY"
            creds.auth_token_header_prefix = "Bearer "
        # CCXT pem key reader is not expecting users to under keys pasted as text from the coinbase UI
        # convert \\n to \n to make this format compatible as well
        if creds.secret and "\\n" in creds.secret:
            creds.secret = creds.secret.replace("\\n", "\n")
        return creds

    @_coinbase_retrier
    async def _load_markets(
        self, 
        client, 
        reload: bool, 
        market_filter: typing.Optional[typing.Callable[[dict], bool]] = None
    ):
        # override for retrier and populate ALIASED_SYMBOLS
        await self._filtered_if_necessary_load_markets(client, reload, market_filter)
        # only call _refresh_alias_symbols from here as markets just got reloaded,
        # no market can be missing unlike when using cached markets
        _refresh_alias_symbols(client)
        if FORCE_COINBASE_BASE_FEES:
            # always use base fee tiers inside OctoBot to avoid issues with coinbase high fees
            self._apply_base_fee_tiers()

    @classmethod
    def register_simulator_connector_fee_methods(
        cls, exchange_name: str, simulator_connector: exchanges.ExchangeSimulatorConnector
    ):
        if FORCE_COINBASE_BASE_FEES:
            # only called in backtesting
            # overrides exchange simulator connector get_fees to use backtesting fees
            simulator_connector.get_fees = cls.simulator_connector_get_fees

    @classmethod
    def simulator_connector_get_fees(cls, symbol: str):
        # same signature as ExchangeSimulatorConnector.get_fees
        # force selecetd fee tier in backtesting
        return {
            trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: DEFAULT_BACKTESTING_TAKER_FEE_VALUE,
            trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: DEFAULT_BACKTESTING_MAKER_FEE_VALUE,
            trading_enums.ExchangeConstantsMarketPropertyColumns.FEE.value: trading_constants.CONFIG_DEFAULT_SIMULATOR_FEES
        }

    def _apply_base_fee_tiers(self):
        taker_fee, maker_fee = self._get_base_tier_fees()
        self.logger.info(
            f"Applying {self.exchange_manager.exchange_name} base fees tiers to markets: {taker_fee=}, {maker_fee=}"
        )
        for market in self.client.markets.values():
            market[trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value] = taker_fee
            market[trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value] = maker_fee


    def _get_base_tier_fees(self) -> (float, float):
        return (
            DEFAULT_LIVE_TAKER_FEE_VALUE, DEFAULT_LIVE_MAKER_FEE_VALUE
        )
        # TODO uncomment this in case there is a way to fetch tier 0 fees in Coinbase
        # try:
        #     # use ccxt default fee tiers
        #     fee_tiers = self.client.describe()["fees"]["trading"]["tiers"]
        #     return (
        #         fee_tiers[trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value][0][1],
        #         fee_tiers[trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value][0][1],
        #     )
        # except KeyError as err:
        #     self.logger.error(
        #         f"Error when getting base fee tier: {err}. Using default {DEFAULT_FEE_VALUE} value"
        #     )
        #     return (
        #         DEFAULT_TAKER_FEE_VALUE, DEFAULT_MAKER_FEE_VALUE
        #     )

    async def _edit_order_by_cancel_and_create(
        self, exchange_order_id: str, symbol: str, order_type: trading_enums.TraderOrderType,
        side: str, quantity: float, price: float, params: dict
    ) -> dict:
        if order_type == trading_enums.TraderOrderType.STOP_LOSS:
            # can't use super()._edit_order_by_cancel_and_create when order is a stop loss as stop market orders
            # are not supported
            await self.client.cancel_order(exchange_order_id, symbol)
            stop_price = price
            price = float(
                decimal.Decimal(str(price)) * self.exchange_manager.exchange.STOP_LIMIT_ORDER_INSTANT_FILL_PRICE_RATIO
            )
            local_param = copy.deepcopy(params)
            return await self.create_limit_stop_loss_order(symbol, quantity, price, stop_price, side, params=local_param)
        # not a stop loss: proceed with the usual edit flow
        return await super()._edit_order_by_cancel_and_create(
            exchange_order_id, symbol, order_type, side, quantity, price, params
        )


    @ccxt_client_util.converted_ccxt_common_errors
    async def get_balance(self, **kwargs: dict):
        """
        Local override to handle pagination of coinbase's max of 250 assets per request
        fetch balance (free + used) by currency
        :return: balance dict
        """
        if not kwargs:
            kwargs = {}
        with self.error_describer(True):
            results = await self._paginated_request(self.client.fetch_balance, params=kwargs)
            merged_balances = {}
            for result in results:
                merged_balances.update(result)
            return self.adapter.adapt_balance(merged_balances)

    @_coinbase_retrier
    async def _paginated_request(self, func, *args, **kwargs):
        results = [await func(*args, **kwargs)]
        if "params" not in kwargs:
            kwargs["params"] = {}
        next_cursor = ""
        i = 0
        for i in range(_MAX_CURSOR_ITERATIONS):
            if next_cursor := self._get_next_cursor(results[-1], func.__name__):
                self.logger.info(f"Large portfolio fetch in progress: request [{i}] processing ...")
                kwargs["params"]["cursor"] = next_cursor
                results.append(await func(*args, **kwargs))
            else:
                break
        if next_cursor:
            self.logger.error(
                f"Not all {self.exchange_manager.exchange_name} {func.__name__} was fetched after [{i + 1}] "
                f"iterations. This is unexpected."
            )
        return results

    def _get_next_cursor(self, response: dict, func_name: str) -> str:
        try:
            return response[ccxt_constants.CCXT_INFO]["cursor"]
        except KeyError:
            self.logger.error(
                f"Unexpected missing cursor key in {self.exchange_manager.exchange_name} {func_name} response info, "
                f"available keys: {list(response[ccxt_constants.CCXT_INFO])}"
            )
        return ""

    @ccxt_client_util.converted_ccxt_common_errors
    async def _ensure_auth(self):
        # Override of ccxt_connector._ensure_auth to use get_open_orders instead and propagate authentication errors
        try:
            # load markets before calling _ensure_auth() to avoid fetching markets status while they are cached
            await self._unauth_ensure_exchange_init()
            # replace self.exchange_manager.exchange.get_balance by get_open_orders
            # to mitigate coinbase balance cache side effect
            if self.client.markets:
                # fetch orders for any available symbol to ensure authentication is working
                first_symbol = next(iter(self.client.markets.keys()))
                await self.exchange_manager.exchange.get_open_orders(symbol=first_symbol)
            else:
                self.logger.error(
                    f"Unexpected: No [{self.exchange_manager.exchange_name}] markets loaded. Impossible to check authentication."
                )
        except (
            octobot_trading.errors.AuthenticationError, 
            octobot_trading.errors.ExchangeProxyError, 
            ccxt.AuthenticationError
        ):
            # this error is critical on coinbase as it prevents loading markets: propagate it
            raise
        except Exception as err:
            if self.force_authentication:
                raise
            # Is probably handled in exchange tentacles, important thing here is that authentication worked
            self.logger.warning(
                f"Error when checking exchange connection: {err} ({err.__class__.__name__}). This should not be an issue."
            )


class Coinbase(exchanges.RestExchange):
    MAX_PAGINATION_LIMIT: int = 300
    ALWAYS_REQUIRES_AUTHENTICATION = True
    IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH = True
    DEFAULT_CONNECTOR_CLASS = CoinbaseConnector

    FAKE_RATE_LIMIT_ERROR_INSTANT_RETRY_COUNT = 5
    INSTANT_RETRY_ERROR_CODE = "429"

    FIX_MARKET_STATUS = True
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True

    # text content of errors due to orders not found errors
    EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # coinbase {"error":"NOT_FOUND","error_details":"order with this orderID was not found",
        #   "message":"order with this orderID was not found"}
        ("not_found", "order")
    ]

    # text content of errors due to api key permissions issues
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # coinbase ex: coinbase {"error":"PERMISSION_DENIED",
        # "error_details":"Missing required scopes","message":"Missing required scopes"}
        # ExchangeError('coinbase {"error":"unknown","error_details":"Missing required scopes",
        # "message":"Missing required scopes"}')
        ("missing required scopes", ),
        ("permission is required", ),
    ]
    # text content of errors due to traded assets for account
    EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # ex when trading WBTC/USDC with and account that can't trade it:
        # ccxt.base.errors.BadRequest: target is not enabled for trading
        ("target is not enabled for trading", ),
        # ccxt.base.errors.PermissionDenied: coinbase {"error":"PERMISSION_DENIED","error_details":
        # "User is not allowed to convert crypto","message":"User is not allowed to convert crypto"}
        ("user is not allowed to convert crypto", ),
    ]
    # text content of errors due to exchange internal synch (like when portfolio is not yet up to date after a trade)
    EXCHANGE_INTERNAL_SYNC_ERRORS: typing.List[typing.Iterable[str]] = [
        # BadRequest coinbase {"error":"INVALID_ARGUMENT","error_details":"account is not available","message":"account is not available"}
        ("account is not available", )
    ]
    # text content of errors due to missing fnuds when creating an order (when not identified as such by ccxt)
    EXCHANGE_MISSING_FUNDS_ERRORS: typing.List[typing.Iterable[str]] = [
        ("insufficient balance in source account", )
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('cancelorders() has failed, check your arguments and parameters', )
    ]

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
                # trading_enums.TraderOrderType.STOP_LOSS,    # supported on spot (as spot limit)
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
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server
    # stop limit price is 2% bellow trigger price to ensure instant fill
    STOP_LIMIT_ORDER_INSTANT_FILL_PRICE_RATIO = decimal.Decimal("0.98")

    @classmethod
    def get_name(cls):
        return 'coinbase'

    def get_adapter_class(self):
        return CoinbaseCCXTAdapter

    @staticmethod
    def get_default_reference_market(exchange_name: str) -> str:
        return "USDC"

    def get_alias_symbols(self) -> set[str]:
        """
        :return: a set of symbol of this exchange that are aliases to other symbols
        """
        return ALIASED_SYMBOLS

    def supports_native_edit_order(self, order_type: trading_enums.TraderOrderType) -> bool:
        # return False when default edit_order can't be used and order should always be canceled and recreated instead
        # only working with regular limit orders
        return order_type not in (
            trading_enums.TraderOrderType.STOP_LOSS, trading_enums.TraderOrderType.STOP_LOSS_LIMIT
        )

    async def get_account_id(self, **kwargs: dict) -> str:
        try:
            with self.connector.error_describer(True):
                accounts = await self.connector.client.fetch_accounts()
                # use portfolio id when possible to enable "coinbase subaccounts" which are called "portfolios"
                # note: oldest portfolio portfolio id == user id (from previous v2PrivateGetUser) when
                # using master account
                portfolio_ids = set(account[ccxt_constants.CCXT_INFO]['retail_portfolio_id'] for account in accounts)
                if len(portfolio_ids) != 1:
                    is_up_to_date_key = self._is_up_to_date_api_key()
                    if is_up_to_date_key:
                        self.logger.error(
                            f"Unexpected: failed to identify Coinbase portfolio id on up to date API keys: "
                            f"{portfolio_ids=}"
                        )
                    sorted_portfolios = sorted(
                        [
                            account[ccxt_constants.CCXT_INFO]
                            for account in accounts
                        ],
                        key=lambda account: account["created_at"],
                    )
                    portfolio_id = sorted_portfolios[0]['retail_portfolio_id']
                    self.logger.info(
                        f"{len(portfolio_ids)} portfolio found on Coinbase account. "
                        f"This can happen with non up-to-date API keys ({is_up_to_date_key=}). "
                        f"Using the oldest portfolio id to bind to main account: {portfolio_id=}."
                    )
                else:
                    portfolio_id = next(iter(portfolio_ids))
                return portfolio_id
        except ccxt.AuthenticationError:
            raise
        except (ccxt.BaseError, octobot_trading.errors.OctoBotExchangeError) as err:
            self.logger.exception(
                err, True,
                f"Error when fetching {self.get_name()} account id: {err} ({err.__class__.__name__}). "
                f"This is not normal, endpoint might be deprecated, see "
                f"https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-users. "
                f"Using generated account id instead"
            )
            return trading_constants.DEFAULT_ACCOUNT_ID

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        # unknown (05/06/2025)
        return super().get_max_orders_count(symbol, order_type)

    def _is_up_to_date_api_key(self) -> bool:
        return (
            self.connector.client.apiKey.find('organizations/') >= 0 or
            self.connector.client.apiKey.startswith('-----BEGIN')
        )


    @_coinbase_retrier
    async def get_symbol_prices(self, symbol: str, time_frame: commons_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        return await super().get_symbol_prices(
            symbol, time_frame, **self._get_ohlcv_params(time_frame, limit, **kwargs)
        )

    @_coinbase_retrier
    async def get_recent_trades(self, symbol, limit=50, **kwargs):
        # override for retrier
        return await super().get_recent_trades(symbol, limit=limit, **kwargs)

    @_coinbase_retrier
    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        # override for retrier
        return await super().get_price_ticker(symbol, **kwargs)

    @_coinbase_retrier
    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[dict[str, dict]]:
        # override for retrier
        return await super().get_all_currencies_price_ticker(**kwargs)

    @_coinbase_retrier
    async def cancel_order(
        self, exchange_order_id: str, symbol: str, order_type: trading_enums.TraderOrderType, **kwargs: dict
    ) -> trading_enums.OrderStatus:
        # override for retrier
        return await super().cancel_order(exchange_order_id, symbol, order_type, **kwargs)

    async def get_balance(self, **kwargs: dict):
        # warning: sometimes has unexpected delays after creating / filling orders
        if "v3" not in kwargs:
            # use v3 to get free and total amounts (default is only returning free amounts)
            kwargs["v3"] = True
        return await super().get_balance(**kwargs)

    @_coinbase_retrier
    async def _create_order_with_retry(self, order_type, symbol, quantity: decimal.Decimal,
                                       price: decimal.Decimal, stop_price: decimal.Decimal,
                                       side: trading_enums.TradeOrderSide,
                                       current_price: decimal.Decimal,
                                       reduce_only: bool, params) -> dict:
        # override for retrier
        return await super()._create_order_with_retry(
            order_type=order_type, symbol=symbol, quantity=quantity, price=price,
            stop_price=stop_price, side=side, current_price=current_price,
            reduce_only=reduce_only, params=params
        )

    @_coinbase_retrier
    async def get_open_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        # override for retrier
        return await super().get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    @_coinbase_retrier
    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        # override for retrier
        return await super().get_order(exchange_order_id, symbol=symbol, order_type=order_type, **kwargs)

    async def _create_market_stop_loss_order(self, symbol, quantity, price, side, current_price, params=None) -> dict:
        # warning coinbase only supports stop limit orders, stop markets are not available
        stop_price = price
        price = float(decimal.Decimal(str(price)) * self.STOP_LIMIT_ORDER_INSTANT_FILL_PRICE_RATIO)
        # use limit stop loss with a "normally instantly" filled price
        return await self._create_limit_stop_loss_order(symbol, quantity, price, stop_price, side, params=params)

    def _get_ohlcv_params(self, time_frame, input_limit, **kwargs):
        limit = input_limit
        if not input_limit or input_limit > self.MAX_PAGINATION_LIMIT:
            limit = min(self.MAX_PAGINATION_LIMIT, input_limit) if input_limit else self.MAX_PAGINATION_LIMIT
        if "since" not in kwargs:
            time_frame_sec = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MSECONDS_TO_MINUTE
            to_time = self.connector.client.milliseconds()
            kwargs["since"] = to_time - (time_frame_sec * limit)
            kwargs["limit"] = limit
        return kwargs

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        signature_identifier = "CB-ACCESS-SIGN"
        oauth_identifier = "Authorization"
        return bool(
            headers
            and (
                signature_identifier in headers
                or oauth_identifier in headers
            )
        )

    def is_market_open_for_order_type(self, symbol: str, order_type: trading_enums.TraderOrderType) -> bool:
        """
        Override if necessary
        """
        market_status_info = self.get_market_status(symbol, with_fixer=False).get(ccxt_constants.CCXT_INFO, {})
        trade_order_type = order_util.get_trade_order_type(order_type)
        try:
            if trade_order_type is trading_enums.TradeOrderType.MARKET:
                return not market_status_info["limit_only"]
            if trade_order_type is trading_enums.TradeOrderType.LIMIT:
                return not market_status_info["cancel_only"]
        except KeyError as err:
            self.logger.exception(
                err,
                True,
                f"Can't check {self.get_name()} market opens status for order type: missing {err} "
                f"in market status info. {self.get_name()} API probably changed. Considering market as open. "
                f"market_status_info: {market_status_info}"
            )
        return True


class CoinbaseCCXTAdapter(exchanges.CCXTAdapter):

    def _register_exchange_fees(self, order_or_trade):
        super()._register_exchange_fees(order_or_trade)
        try:
            fees = order_or_trade[trading_enums.ExchangeConstantsOrderColumns.FEE.value]
            if not fees[trading_enums.FeePropertyColumns.CURRENCY.value]:
                # fees currency are not provided, they are always in quote on Coinbase
                fees[trading_enums.FeePropertyColumns.CURRENCY.value] = commons_symbols.parse_symbol(
                    order_or_trade[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value]
                ).quote
        except (KeyError, TypeError):
            pass

    def _update_stop_order_or_trade_type_and_price(self, order_or_trade: dict):
        if stop_price := order_or_trade.get(trading_enums.ExchangeConstantsOrderColumns.STOP_PRICE.value):
            # from https://bingx-api.github.io/docs/#/en-us/spot/trade-api.html#Current%20Open%20Orders
            limit_price = order_or_trade.get(trading_enums.ExchangeConstantsOrderColumns.PRICE.value)
            # use stop price as order price to parse it properly
            order_or_trade[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = stop_price
            # type is TAKE_STOP_LIMIT (not unified)
            if order_or_trade.get(trading_enums.ExchangeConstantsOrderColumns.TYPE.value) not in (
                trading_enums.TradeOrderType.STOP_LOSS.value, trading_enums.TradeOrderType.TAKE_PROFIT.value
            ):
                # Force stop loss. Add order direction parsing logic to handle take profits if necessary
                order_type = trading_enums.TradeOrderType.STOP_LOSS.value
                trigger_above = False
                try:
                    order_config = order_or_trade.get(ccxt_constants.CCXT_INFO, {}).get("order_configuration", {})
                    stop_config = order_config.get("stop_limit_stop_limit_gtc") or order_config.get("stop_limit_stop_limit_gtd")
                    stop_direction = stop_config.get("stop_direction", "")
                    if "down" in stop_direction.lower():
                        trigger_above = False
                    elif "up" in stop_direction.lower():
                        trigger_above = True
                    else:
                        self.logger.error(f"Unknown order direction: {stop_direction} ({order_or_trade})")
                    side = order_or_trade[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                    if side == trading_enums.TradeOrderSide.SELL.value:
                        if trigger_above:
                            # take profits are not yet handled as such: consider them as limit orders
                            order_type = trading_enums.TradeOrderType.LIMIT.value # waiting for TP handling
                        else:
                            order_type = trading_enums.TradeOrderType.STOP_LOSS.value
                    elif side == trading_enums.TradeOrderSide.BUY.value:
                        if trigger_above:
                            order_type = trading_enums.TradeOrderType.STOP_LOSS.value
                        else:
                            # take profits are not yet handled as such: consider them as limit orders
                            order_type = trading_enums.TradeOrderType.LIMIT.value # waiting for TP handling
                except (KeyError, TypeError) as err:
                    self.logger.error(f"missing expected coinbase order config: {err}, {order_or_trade}")
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = order_type
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value] = trigger_above

    def fix_order(self, raw, **kwargs):
        """
        Handle 'order_type': 'UNKNOWN_ORDER_TYPE in coinbase order response (translated into None in ccxt order type)
        ex:
        {'info': {'order_id': 'd7471b4e-960e-4c92-bdbf-755cb92e176b', 'product_id': 'AAVE-USD',
        'user_id': '9868efd7-90e1-557c-ac0e-f6b943d471ad', 'order_configuration': {'limit_limit_gtc':
        {'base_size': '6.798', 'limit_price': '110.92', 'post_only': False}}, 'side': 'BUY',
        'client_order_id': '465ead64-6272-4e92-97e2-59653de3ca24', 'status': 'OPEN', 'time_in_force':
        'GOOD_UNTIL_CANCELLED', 'created_time': '2024-03-02T03:04:11.070126Z', 'completion_percentage':
        '0', 'filled_size': '0', 'average_filled_price': '0', 'fee': '', 'number_of_fills': '0', 'filled_value': '0',
        'pending_cancel': False, 'size_in_quote': False, 'total_fees': '0', 'size_inclusive_of_fees': False,
        'total_value_after_fees': '757.05029664', 'trigger_status': 'INVALID_ORDER_TYPE', 'order_type':
        'UNKNOWN_ORDER_TYPE', 'reject_reason': 'REJECT_REASON_UNSPECIFIED', 'settled': False, 'product_type':
        'SPOT', 'reject_message': '', 'cancel_message': '', 'order_placement_source': 'RETAIL_ADVANCED',
        'outstanding_hold_amount': '757.05029664', 'is_liquidation': False, 'last_fill_time': None,
        'edit_history': [], 'leverage': '', 'margin_type': 'UNKNOWN_MARGIN_TYPE'}, 'clientOrderId':
        '465ead64-6272-4e92-97e2-59653de3ca24', 'timestamp': 1709348651.07, 'datetime': '2024-03-02T03:04:11.070126Z',
        'lastTradeTimestamp': None, 'symbol': 'AAVE/USD', 'type': None, 'timeInForce': 'GTC', 'postOnly': False,
        'side': 'buy', 'price': 110.92, 'stopPrice': None, 'triggerPrice': None, 'amount': 6.798, 'filled': 0.0,
        'remaining': 6.798, 'cost': 0.0, 'average': None, 'status': 'open', 'fee': {'cost': '0', 'currency': 'USD',
        'exchange_original_cost': '0', 'is_from_exchange': True}, 'trades': [],
        'fees': [{'cost': 0.0, 'currency': 'USD'}], 'lastUpdateTimestamp': None, 'reduceOnly': None,
        'takeProfitPrice': None, 'stopLossPrice': None, 'exchange_id': 'd7471b4e-960e-4c92-bdbf-755cb92e176b'}
        """
        fixed = super().fix_order(raw, **kwargs)
        self._update_stop_order_or_trade_type_and_price(fixed)
        if fixed[ccxt_enums.ExchangeOrderCCXTColumns.TYPE.value] is None:
            if fixed[ccxt_enums.ExchangeOrderCCXTColumns.STOP_PRICE.value] is not None:
                # stop price set: stop order
                order_type = trading_enums.TradeOrderType.STOP_LOSS.value
            elif fixed[ccxt_enums.ExchangeOrderCCXTColumns.PRICE.value] is None:
                # price not set: market order
                order_type = trading_enums.TradeOrderType.MARKET.value
            else:
                # price is set and stop price is not: limit order
                order_type = trading_enums.TradeOrderType.LIMIT.value
            fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = order_type
        if fixed[ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value] == "PENDING":
            fixed[ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value] = trading_enums.OrderStatus.PENDING_CREATION.value
        if fixed[ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value] == "CANCEL_QUEUED":
            fixed[ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value] = trading_enums.OrderStatus.PENDING_CANCEL.value
        # sometimes amount is not set
        if not fixed[ccxt_enums.ExchangeOrderCCXTColumns.AMOUNT.value] \
                and fixed[ccxt_enums.ExchangeOrderCCXTColumns.FILLED.value]:
            fixed[ccxt_enums.ExchangeOrderCCXTColumns.AMOUNT.value] = \
                fixed[ccxt_enums.ExchangeOrderCCXTColumns.FILLED.value]
        return fixed

    def fix_trades(self, raw, **kwargs):
        raw = super().fix_trades(raw, **kwargs)
        for trade in raw:
            self._update_stop_order_or_trade_type_and_price(trade)
            trade[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CLOSED.value
            try:
                if trade[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] is None and \
                        trade[trading_enums.ExchangeConstantsOrderColumns.COST.value] and \
                        trade[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]:
                    # convert amount to have the same units as every other exchange
                    trade[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] = (
                            trade[trading_enums.ExchangeConstantsOrderColumns.COST.value] /
                            trade[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
                    )
            except KeyError:
                pass
        return raw
