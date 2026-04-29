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
import contextlib
import decimal
import time
import typing
import ccxt
import hashlib
from ccxt.base.types import Entry

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors
import octobot_commons.symbols as symbols_util
import octobot_commons.constants as commons_constants
import octobot_commons
import octobot_trading.constants as constants


class MEXCConnector(exchanges.CCXTConnector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_signed_requests: typing.Optional[bool] = None

    def _create_client(self, force_unauth=False):
        super()._create_client(force_unauth=force_unauth)
        self.client.sign = self._lazy_maybe_force_signed_requests(self.client.sign)

    def _lazy_maybe_force_signed_requests(self, origin_ccxt_sign):
        def lazy_sign(path, api, method, params, headers, body):
            if self._force_signed_requests is None:
                self._force_signed_requests = self.exchange_manager.exchange.requires_authentication(
                    self.exchange_manager.exchange.tentacle_config, None, None
                )
                if self._force_signed_requests:
                    self.logger.info(f"Enabled force signing requests for {self.exchange_manager.exchange_name}")
            ccxt_sign_result = origin_ccxt_sign(path, api, method, params, headers, body)
            if self._force_signed_requests:
                url = ccxt_sign_result.get("url") or ""
                ccxt_headers = ccxt_sign_result.get("headers") or {}
                if "signature=" in url or "Signature" in ccxt_headers:
                    # already signed
                    return ccxt_sign_result
                # force signature
                return self._force_sign(path, api, method, params, headers, body)
            return ccxt_sign_result
        return lazy_sign

    def _force_sign(self, path, api, method, params, headers, body):
        self = self.client  # to use the same code as ccxt.async_support.mexc.sign (same self)
        # same code as ccxt.async_support.mexc.sign but forced to sign
        section = self.safe_string(api, 0)
        access = self.safe_string(api, 1)
        path, params = self.resolve_path(path, params)
        url = None
        if section == 'spot' or section == 'broker':
            if section == 'broker':
                url = self.urls['api'][section][access] + '/' + path
            else:
                url = self.urls['api'][section][access] + '/api/' + self.version + '/' + path
            urlParams = params
            if True or access == 'private':  # local override to force signature
                if section == 'broker' and ((method == 'POST') or (method == 'PUT') or (method == 'DELETE')):
                    urlParams = {
                        'timestamp': self.nonce(),
                        'recvWindow': self.safe_integer(self.options, 'recvWindow', 5000),
                    }
                    body = self.json(params)
                else:
                    urlParams['timestamp'] = self.nonce()
                    urlParams['recvWindow'] = self.safe_integer(self.options, 'recvWindow', 5000)
            paramsEncoded = ''
            if urlParams:
                paramsEncoded = self.urlencode(urlParams)
                url += '?' + paramsEncoded
            if True or access == 'private':  # local override to force signature
                self.check_required_credentials()
                signature = self.hmac(self.encode(paramsEncoded), self.encode(self.secret), hashlib.sha256)
                url += '&' + 'signature=' + signature
                headers = {
                    'X-MEXC-APIKEY': self.apiKey,
                    'source': self.safe_string(self.options, 'broker', 'CCXT'),
                }
            if (method == 'POST') or (method == 'PUT') or (method == 'DELETE'):
                headers['Content-Type'] = 'application/json'
        elif section == 'contract' or section == 'spot2':
            url = self.urls['api'][section][access] + '/' + self.implode_params(path, params)
            params = self.omit(params, self.extract_params(path))
            if False and access == 'public':  # local override to force signature
                if params:
                    url += '?' + self.urlencode(params)
            else:
                self.check_required_credentials()
                timestamp = str(self.nonce())
                auth = ''
                headers = {
                    'ApiKey': self.apiKey,
                    'Request-Time': timestamp,
                    'Content-Type': 'application/json',
                    'source': self.safe_string(self.options, 'broker', 'CCXT'),
                }
                if method == 'POST':
                    auth = self.json(params)
                    body = auth
                else:
                    params = self.keysort(params)
                    if params:
                        auth += self.urlencode(params)
                        url += '?' + auth
                auth = self.apiKey + timestamp + auth
                signature = self.hmac(self.encode(auth), self.encode(self.secret), hashlib.sha256)
                headers['Signature'] = signature
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

class MEXC(exchanges.RestExchange):
    DEFAULT_CONNECTOR_CLASS = MEXCConnector
    FIX_MARKET_STATUS = True
    REMOVE_MARKET_STATUS_PRICE_LIMITS = True
    # set True when disabled symbols should still be considered (ex: mexc with its temporary api trading disabled symbols)
    # => avoid skipping untradable symbols
    INCLUDE_DISABLED_SYMBOLS_IN_AVAILABLE_SYMBOLS = True
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = True  # set True when get_order() can return None
    # (order not found) when orders are instantly filled on exchange and are not fully processed on the exchange side.

    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    # text content of errors due to unhandled authentication issues
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True

    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'mexc {"code":700007,"msg":"No permission to access the endpoint."}'
        ("no permission to access",),
    ]
    EXCHANGE_AUTHENTICATION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'mexc {"code":10072,"msg":"Api key info invalid"}'
        ("api key info invalid",),
    ]
    EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # "mexc {"code":700006,"msg":"IP [33.33.33.33] not in the ip white list"}"
        ("not in the ip white list",),
    ]
    # set when the exchange can allow users to pay fees in a custom currency (ex: BNB on binance)
    LOCAL_FEES_CURRENCIES: typing.List[str] = ["MX"]
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server

    @classmethod
    def get_name(cls):
        return 'mexc'

    def get_adapter_class(self):
        return MEXCCCXTAdapter

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False,  # disable quote conversion
                "recvWindow": 60000,  # default is 5000, avoid time related issues
            }
        }

    async def get_account_id(self, **kwargs: dict) -> str:
        # https://www.mexc.com/api-docs/spot-v3/spot-account-trade#query-uid
        private_get_uid = Entry('uid', ['spot', 'private'], 'GET', {'cost': 10})
        try:
            resp = await private_get_uid.unbound_method(self.connector.client)
            return str(resp["uid"])
        except Exception as err:
            self.logger.exception(
                err, 
                True, 
                f"Unexpected error when getting {self.get_name()} account ID: {err}. Using default account ID."
            )
            return constants.DEFAULT_ACCOUNT_ID

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        # unknown (05/06/2025)
        return super().get_max_orders_count(symbol, order_type)

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        url_signature_identifiers = "signature="
        header_signature_identifiers = "Signature"
        return bool(
            headers
            and header_signature_identifiers in headers
        ) or bool(
            url
            and url_signature_identifiers in url
        )

    async def get_all_tradable_symbols(self, active_only=True) -> set[str]:
        """
        Override if the exchange is not allowing trading for all available symbols (ex: MEXC)
        :return: the list of all symbols supported by the exchange that can currently be traded through API
        """
        if CACHED_MEXC_API_HANDLED_SYMBOLS.should_be_updated():
            await CACHED_MEXC_API_HANDLED_SYMBOLS.update(self)
        return CACHED_MEXC_API_HANDLED_SYMBOLS.symbols

    async def _create_specific_order(self, order_type, symbol, quantity: decimal.Decimal, price: decimal.Decimal = None,
                                     side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                                     stop_price: decimal.Decimal = None, reduce_only: bool = False,
                                     params=None) -> dict:
        async with self._mexc_handled_symbols_filter(symbol):
            return await super()._create_specific_order(order_type, symbol, quantity,
                                                        price=price, stop_price=stop_price,
                                                        side=side, current_price=current_price,
                                                        reduce_only=reduce_only, params=params)

    @contextlib.asynccontextmanager
    async def _mexc_handled_symbols_filter(self, symbol):
        try:
            yield
        except (ccxt.BadSymbol, ccxt.BadRequest) as err:
            if "symbol not support api" in str(err):
                raise octobot_trading.errors.UntradableSymbolError(
                    f"{self.get_name()} error: {symbol} trading pair is not available to the API at the moment, "
                    f"{symbol} is under maintenance ({err})."
                )
            raise err

    async def get_open_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return self._filter_orders(
            await super().get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs),
            True
        )

    async def get_closed_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return self._filter_orders(
            await super().get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs),
            False
        )

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        try:
            return await super().get_order(
                exchange_order_id, symbol=symbol, order_type=order_type, **kwargs
            )
        except octobot_trading.errors.FailedRequest as err:
            if "Order does not exist" in str(err):
                return None
            raise

    def _filter_orders(self, orders: list, open_only: bool) -> list:
        return [
            order
            for order in orders
            if (
                open_only and order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value]
                == trading_enums.OrderStatus.OPEN.value
            ) or (
                not open_only and order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value]
                != trading_enums.OrderStatus.OPEN.value
            )
        ]


class APIHandledSymbols:
    """
    MEXC has pairs that are sometimes tradable from the exchange UI but not from the API. Get the list of
    currently api tradable symbols from the defaultSymbols endpoint.
    """

    def __init__(self, update_interval):
        self.symbols = set()
        self.last_update = 0
        self._update_interval = update_interval

    def should_be_updated(self):
        return time.time() - self._update_interval >= self._update_interval

    async def update(self, exchange):
        try:
            result = await exchange.connector.client.spot2_public_get_market_api_default_symbols()
            self.symbols = set(
                # in some cases, "_" is not replaced as symbol is not found in markets
                exchange.connector.client.safe_market(s)["symbol"].replace("_", octobot_commons.MARKET_SEPARATOR)
                for s in result["data"]["symbol"]
            )
            self.last_update = time.time()
            exchange.logger.info(f"Updated handled symbols, list: {self.symbols}")
        except Exception as err:
            exchange.logger.exception(err, True, f"Error when fetching api-tradable symbols: {err}")

# make it available a singleton
CACHED_MEXC_API_HANDLED_SYMBOLS = APIHandledSymbols(commons_constants.DAYS_TO_SECONDS)

class MEXCCCXTAdapter(exchanges.CCXTAdapter):

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        try:
            if fixed[
                trading_enums.ExchangeConstantsOrderColumns.STATUS.value
            ] == trading_enums.OrderStatus.CANCELED.value \
                    and fixed[trading_enums.ExchangeConstantsOrderColumns.FEE.value] is None:
                symbol = fixed.get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value, "")
                fixed[trading_enums.ExchangeConstantsOrderColumns.FEE.value] = {
                    trading_enums.FeePropertyColumns.CURRENCY.value:
                        symbols_util.parse_symbol(symbol).quote if symbol else "",
                    trading_enums.FeePropertyColumns.COST.value: 0.0,
                    trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: False,
                    trading_enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value: 0.0,
                }
        except KeyError as err:
            self.logger.debug(f"Failed to fix order fees: {err}")
        return fixed
