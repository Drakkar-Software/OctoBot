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
    DEFAULT_CONNECTOR_CLASS = CoinbaseConnector

    FAKE_RATE_LIMIT_ERROR_INSTANT_RETRY_COUNT = 5
    # stop limit price is 2% bellow trigger price to ensure instant fill
    STOP_LIMIT_ORDER_INSTANT_FILL_PRICE_RATIO = decimal.Decimal("0.98")
    # implemented in ccxt
    INSTANT_RETRY_ERROR_CODE = "429"

    """
    Deprecated constants kept as comments for reference.
    # text content of errors due to orders not found errors
    # EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # coinbase {"error":"NOT_FOUND","error_details":"order with this orderID was not found",
        #   "message":"order with this orderID was not found"}
        ("not_found", "order")
    ]

    # text content of errors due to api key permissions issues
    # EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # coinbase ex: coinbase {"error":"PERMISSION_DENIED",
        # "error_details":"Missing required scopes","message":"Missing required scopes"}
        # ExchangeError('coinbase {"error":"unknown","error_details":"Missing required scopes",
        # "message":"Missing required scopes"}')
        ("missing required scopes", ),
        ("permission is required", ),
    ]
    # text content of errors due to traded assets for account
    # EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # ex when trading WBTC/USDC with and account that can't trade it:
        # ccxt.base.errors.BadRequest: target is not enabled for trading
        ("target is not enabled for trading", ),
        # ccxt.base.errors.PermissionDenied: coinbase {"error":"PERMISSION_DENIED","error_details":
        # "User is not allowed to convert crypto","message":"User is not allowed to convert crypto"}
        ("user is not allowed to convert crypto", ),
    ]
    # text content of errors due to exchange internal synch (like when portfolio is not yet up to date after a trade)
    # EXCHANGE_INTERNAL_SYNC_ERRORS: typing.List[typing.Iterable[str]] = [
        # BadRequest coinbase {"error":"INVALID_ARGUMENT","error_details":"account is not available","message":"account is not available"}
        ("account is not available", )
    ]
    # text content of errors due to missing fnuds when creating an order (when not identified as such by ccxt)
    # EXCHANGE_MISSING_FUNDS_ERRORS: typing.List[typing.Iterable[str]] = [
        ("insufficient balance in source account", )
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    # EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('cancelorders() has failed, check your arguments and parameters', )
    ]
    """

    @classmethod
    def get_name(cls):
        return 'coinbase'

    def get_alias_symbols(self) -> set[str]:
        """
        :return: a set of symbol of this exchange that are aliases to other symbols
        """
        return ALIASED_SYMBOLS

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
