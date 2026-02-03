#  Drakkar-Software OctoBot-Private-Tentacles
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
import time
import decimal
import typing
import ccxt

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_trading.errors
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.constants as constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot.community


_CACHED_CONFIRMED_FEES_BY_SYMBOL = {}


def _kucoin_retrier(f):
    async def kucoin_retrier_wrapper(*args, **kwargs):
        last_error = None
        for i in range(0, Kucoin.FAKE_DDOS_ERROR_INSTANT_RETRY_COUNT):
            try:
                return await f(*args, **kwargs)
            except (octobot_trading.errors.FailedRequest, ccxt.ExchangeError) as err:
                last_error = err
                rest_exchange = args[0]  # self
                if (rest_exchange.connector is not None) and \
                    rest_exchange.connector.client.last_http_response and \
                    Kucoin.INSTANT_RETRY_ERROR_CODE in rest_exchange.connector.client.last_http_response:
                    # should retry instantly, error on kucoin side
                    # see https://github.com/Drakkar-Software/OctoBot/issues/2000
                    logging.get_logger(Kucoin.get_name()).debug(
                        f"{Kucoin.INSTANT_RETRY_ERROR_CODE} error on {f.__name__}(args={args[1:]} kwargs={kwargs}) "
                        f"request, retrying now. Attempt {i+1} / {Kucoin.FAKE_DDOS_ERROR_INSTANT_RETRY_COUNT}, "
                        f"error: {err} ({last_error.__class__.__name__})."
                    )
                else:
                    raise
        last_error = last_error or RuntimeError("Unknown Kucoin error")  # to be able to "raise from" in next line
        raise octobot_trading.errors.FailedRequest(
            f"Failed Kucoin request after {Kucoin.FAKE_DDOS_ERROR_INSTANT_RETRY_COUNT} "
            f"retries on {f.__name__}(args={args[1:]} kwargs={kwargs}) due "
            f"to {Kucoin.INSTANT_RETRY_ERROR_CODE} error code. "
            f"Last error: {last_error} ({last_error.__class__.__name__})"
        ) from last_error
    return kucoin_retrier_wrapper


class KucoinConnector(ccxt_connector.CCXTConnector):

    @_kucoin_retrier
    async def _load_markets(
        self, 
        client, 
        reload: bool, 
        market_filter: typing.Optional[typing.Callable[[dict], bool]] = None
    ):
        # override for retrier
        await self._filtered_if_necessary_load_markets(client, reload, market_filter)
        # sometimes market fees are missing because they are fetched from all tickers 
        # and all ticker can miss symbols on kucoin
        if client.markets:
            ccxt_client_util.fix_client_missing_markets_fees(client, reload, _CACHED_CONFIRMED_FEES_BY_SYMBOL)

class Kucoin(exchanges.RestExchange):
    FIX_MARKET_STATUS = True
    REMOVE_MARKET_STATUS_PRICE_LIMITS = True
    ADAPT_MARKET_STATUS_FOR_CONTRACT_SIZE = True
    # Set True when get_open_order() can return outdated orders (cancelled or not yet created)
    CAN_HAVE_DELAYED_OPEN_ORDERS = True
    # Set True when get_cancelled_order() can return outdated open orders
    CAN_HAVE_DELAYED_CANCELLED_ORDERS = True
    DEFAULT_CONNECTOR_CLASS = KucoinConnector
    # set True when even loading markets can make auth calls when creds are set
    CAN_MAKE_AUTHENTICATED_REQUESTS_WHEN_LOADING_MARKETS = True

    FAKE_DDOS_ERROR_INSTANT_RETRY_COUNT = 5
    INSTANT_RETRY_ERROR_CODE = "429000"
    FUTURES_CCXT_CLASS_NAME = "kucoinfutures"
    MAX_INCREASED_POSITION_QUANTITY_MULTIPLIER = decimal.Decimal("0.95")
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True

    # set True when fetch_tickers can sometimes miss symbols. In this case, the connector will try to fix it
    CAN_MISS_TICKERS_IN_ALL_TICKERS = True

    # set True when get_positions() is not returning empty positions and should use get_position() instead
    REQUIRES_SYMBOL_FOR_EMPTY_POSITION = True

    # set False when the exchange refuses to change margin type when an associated position is open
    SUPPORTS_SET_MARGIN_TYPE_ON_OPEN_POSITIONS = False

    # get_my_recent_trades only covers the last 24h on kucoin
    ALLOW_TRADES_FROM_CLOSED_ORDERS = True  # set True when get_my_recent_trades should use get_closed_orders

    # should be overridden locally to match exchange support
    SUPPORTED_ELEMENTS = {
        trading_enums.ExchangeTypes.FUTURE.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                # trading_enums.TraderOrderType.STOP_LOSS,    # supported on futures
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,  # supported
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        },
        trading_enums.ExchangeTypes.SPOT.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                # trading_enums.TraderOrderType.STOP_LOSS,    # supported on spot
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
    # text content of errors due to api key permissions issues
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoinfutures Access denied, require more permission'
        ("require more permission",),
    ]
    # text content of errors due to account compliancy issues
    EXCHANGE_COMPLIANCY_ERRORS: typing.List[typing.Iterable[str]] = [
        # kucoin {"msg":"Unfortunately, trading is currently unavailable in your location due to country, region, or IP restrictions.","code":"600004"}
        ("trading is currently unavailable in your location",),
    ]
    # text content of errors due to orders not found errors
    EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoin The order does not exist.'
        ("order does not exist",),
    ]
    # text content of errors due to a closed position on the exchange. Relevant for reduce-only orders
    EXCHANGE_CLOSED_POSITION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoinfutures No open positions to close.'
        ("no open positions to close", )
    ]
    # text content of errors due to an order that would immediately trigger if created. Relevant for stop losses
    EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS: typing.List[typing.Iterable[str]] = [
        # doesn't seem to happen on kucoin
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('order cannot be canceled', ),
        ('order_not_exist_or_not_allow_to_cancel', )
    ]
    # text content of errors due to unhandled IP white list issues
    EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # "kucoinfutures Invalid request ip, the current clientIp is:e3b:e3b:e3b:e3b:e3b:e3b:e3b:e3b"
        ("invalid request ip",),
    ]
    # set when the exchange can allow users to pay fees in a custom currency (ex: BNB on binance)
    LOCAL_FEES_CURRENCIES: typing.List[str] = ["KCS"]

    DEFAULT_BALANCE_CURRENCIES_TO_FETCH = ["USDT"]
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server


    @classmethod
    def get_name(cls):
        return 'kucoin'

    @classmethod
    def get_rest_name(cls, exchange_manager):
        if exchange_manager.is_future:
            return cls.FUTURES_CCXT_CLASS_NAME
        return cls.get_name()

    def get_adapter_class(self):
        return KucoinCCXTAdapter

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    def supports_api_leverage_update(self, symbol: str) -> bool:
        """
        Override if necessary
        :param symbol:
        :return:
        """
        if super().supports_api_leverage_update(symbol):
            # set leverage is only supported on cross positions
            # https://www.kucoin.com/docs/rest/futures-trading/positions/modify-cross-margin-leverage
            try:
                return self.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position_margin_type(
                    symbol
                ) is trading_enums.MarginType.CROSS
            except ValueError as err:
                self.logger.exception(f"Failed to get {symbol} position margin type: {err}")
        return False

    async def set_symbol_leverage(self, symbol: str, leverage: float, **kwargs):
        params = kwargs or {}
        if self.exchange_manager.is_future:
            # add marginMode param as required by ccxt
            self._set_margin_mode_param_if_necessary(symbol, params, lower=True)
        return await super().set_symbol_leverage(symbol, leverage, **params)

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        # from
        #   https://www.kucoin.com/docs-new/rest/futures-trading/orders/add-order
        #   https://www.kucoin.com/docs-new/rest/spot-trading/orders/add-order
        # should be 100 to 200 but use 100 to be sure
        return 100

    def supports_native_edit_order(self, order_type: trading_enums.TraderOrderType) -> bool:
        # return False when default edit_order can't be used and order should always be canceled and recreated instead
        # only working on HF orders
        return False

    async def get_account_id(self, **kwargs: dict) -> str:
        # It is currently impossible to fetch subaccounts account id, use a constant value to identify it.
        # updated: 21/05/2024
        try:
            with self.connector.error_describer(True):
                account_id = None
                subaccount_id = None
                sub_accounts = await self.connector.client.private_get_sub_accounts()
                accounts = sub_accounts.get("data", {}).get("items", {})
                has_subaccounts = bool(accounts)
                if has_subaccounts:
                    if len(accounts) == 1:
                        # only 1 account: use its id or name
                        account = accounts[0]
                        # try using subUserId if available
                        # 'ex subUserId: 65d41ea409407d000160cc17 subName: octobot1'
                        account_id = account.get("subUserId") or account["subName"]
                    else:
                        # more than 1 account: consider other accounts
                        for account in accounts:
                            if account["subUserId"]:
                                subaccount_id = account["subName"]
                            else:
                                # only subaccounts have a subUserId: if this condition is True, we are on the main account
                                account_id = account["subName"]
                    if account_id and self.exchange_manager.is_future:
                        account_id = octobot.community.to_community_exchange_internal_name(
                            account_id, commons_constants.CONFIG_EXCHANGE_FUTURE
                        )
                if subaccount_id:
                    # there is at least a subaccount: ensure the current account is the main account as there is no way
                    # to know the id of the current account (only a list of existing accounts)
                    subaccount_api_key_details = await self.connector.client.private_get_sub_api_key(
                        {"subName": subaccount_id}
                    )
                    if "data" not in subaccount_api_key_details or "msg" in subaccount_api_key_details:
                        # subaccounts can't fetch other accounts data, if this is False, we are on a subaccount
                        self.logger.error(
                            f"kucoin api changed: it is now possible to call private_get_sub_accounts on subaccounts. "
                            f"kucoin get_account_id has to be updated. "
                            f"sub_accounts={sub_accounts} subaccount_api_key_details={subaccount_api_key_details}"
                        )
                        return constants.DEFAULT_ACCOUNT_ID
                if has_subaccounts and account_id is None:
                    self.logger.error(
                        f"kucoin api changed: can't fetch master account account_id. "
                        f"kucoin get_account_id has to be updated."
                        f"sub_accounts={sub_accounts}"
                    )
                    account_id = constants.DEFAULT_ACCOUNT_ID
                # we are on the master account
                return account_id or constants.DEFAULT_ACCOUNT_ID
        except ccxt.ExchangeError as err:
            # ExchangeError('kucoin This user is not a master user')
            if "not a master user" not in str(err):
                self.logger.error(f"kucoin api changed: subaccount error on account id is now: '{err}' "
                                  f"instead of 'kucoin This user is not a master user'")
            # raised when calling this endpoint with a subaccount
            return constants.DEFAULT_SUBACCOUNT_ID

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        """
        local override to take "minFunds" into account
        "minFunds	the minimum spot and margin trading amounts" https://docs.kucoin.com/#get-symbols-list
        """
        market_status = super().get_market_status(symbol, price_example=price_example, with_fixer=with_fixer)
        min_funds = market_status.get(ccxt_constants.CCXT_INFO, {}).get("minFunds")
        if min_funds is not None:
            # should only be for spot and margin, use it if available anyway
            limit_costs = market_status[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value][
                trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value
            ]
            # use max (most restrictive) value
            limit_costs[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value] = max(
                limit_costs[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value],
                float(min_funds)
            )
        return market_status

    @_kucoin_retrier
    async def get_symbol_prices(self, symbol, time_frame, limit: int = 200, **kwargs: dict):
        if "since" in kwargs:
            # prevent ccxt from fillings the end param (not working when trying to get the 1st candle times)
            kwargs["to"] = int(time.time() * commons_constants.MSECONDS_TO_SECONDS)
        return await super().get_symbol_prices(symbol, time_frame, limit=limit, **kwargs)

    @_kucoin_retrier
    async def get_recent_trades(self, symbol, limit=50, **kwargs):
        # on ccxt kucoin recent trades are received in reverse order from exchange and therefore should never be
        # filtered by limit before reversing (or most recent trades are lost)
        recent_trades = await super().get_recent_trades(symbol, limit=None, **kwargs)
        return recent_trades[::-1][:limit] if recent_trades else []

    @_kucoin_retrier
    async def get_order_book(self, symbol, limit=20, **kwargs):
        # override default limit to be kucoin complient
        return await super().get_order_book(symbol, limit=limit, **kwargs)

    @_kucoin_retrier
    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        return await super().get_price_ticker(symbol, **kwargs)

    @_kucoin_retrier
    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[dict[str, dict]]:
        return await super().get_all_currencies_price_ticker(**kwargs)

    def should_log_on_ddos_exception(self, exception) -> bool:
        """
        Override when necessary
        """
        return Kucoin.INSTANT_RETRY_ERROR_CODE not in str(exception)

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        signature_identifier = "KC-API-SIGN"
        return bool(
            headers
            and signature_identifier in headers
        )

    def get_order_additional_params(self, order) -> dict:
        params = {}
        if self.exchange_manager.is_future:
            contract = self.exchange_manager.exchange.get_pair_contract(order.symbol)
            params["leverage"] = float(contract.current_leverage)
            params["reduceOnly"] = order.reduce_only
            params["closeOrder"] = order.close_position
        return params

    async def _update_balance(self, balance, currency, **kwargs):
        balance.update(await super().get_balance(code=currency, **kwargs))

    @_kucoin_retrier
    async def get_balance(self, **kwargs: dict):
        balance = {}
        if self.exchange_manager.is_future:
            # on futures, balance has to be fetched per currency
            # use gather to fetch everything at once (and not allow other requests to get in between)
            currencies = self.exchange_manager.exchange_config.get_all_traded_currencies()
            if not currencies:
                currencies = self.DEFAULT_BALANCE_CURRENCIES_TO_FETCH
                self.logger.warning(
                    f"Can't fetch balance on {self.exchange_manager.exchange_name} futures when no traded currencies "
                    f"are set, fetching {currencies[0]} balance instead"
                )
            await asyncio.gather(*(
                self._update_balance(balance, currency, **kwargs)
                for currency in currencies
            ))
            return balance
        return await super().get_balance(**kwargs)

    def fetch_stop_order_in_different_request(self, symbol: str) -> bool:
        # Override in tentacles when stop orders need to be fetched in a separate request from CCXT
        # Kucoin uses the algo orders endpoint for all stop orders
        return True

    @_kucoin_retrier
    async def get_open_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        if limit is None:
            # default is 50, The maximum cannot exceed 1000
            # https://www.kucoin.com/docs/rest/futures-trading/orders/get-order-list
            limit = 200
        return await super().get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    @_kucoin_retrier
    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        return await super().get_order(exchange_order_id, symbol=symbol, order_type=order_type, **kwargs)

    async def create_order(self, order_type: trading_enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if self.exchange_manager.is_future:
            params = params or {}
            self._set_margin_mode_param_if_necessary(symbol, params)
        return await super().create_order(order_type, symbol, quantity,
                                          price=price, stop_price=stop_price,
                                          side=side, current_price=current_price,
                                          reduce_only=reduce_only, params=params)

    async def edit_order(self, exchange_order_id: str, order_type: trading_enums.TraderOrderType, symbol: str,
                         quantity: decimal.Decimal, price: decimal.Decimal,
                         stop_price: decimal.Decimal = None, side: trading_enums.TradeOrderSide = None,
                         current_price: decimal.Decimal = None,
                         params: dict = None):
        if self.exchange_manager.is_future:
            params = params or {}
            self._set_margin_mode_param_if_necessary(symbol, params)
        return await super().edit_order(
            exchange_order_id, order_type, symbol, quantity, price, stop_price=stop_price,
            side=side, current_price=current_price, params=params
        )

    def _set_margin_mode_param_if_necessary(self, symbol, params, lower=False):
        try:
            # "marginMode": "ISOLATED" // Added field for margin mode: ISOLATED, CROSS, default: ISOLATED
            # from https://www.kucoin.com/docs/rest/futures-trading/orders/place-order
            if (
                KucoinCCXTAdapter.KUCOIN_MARGIN_MODE not in params and
                self.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position_margin_type(
                    symbol
                ) is trading_enums.MarginType.CROSS
            ):
                params[KucoinCCXTAdapter.KUCOIN_MARGIN_MODE] = "cross" if lower else "CROSS"
        except ValueError as err:
            self.logger.error(f"Impossible to add {KucoinCCXTAdapter.KUCOIN_MARGIN_MODE} to order: {err}")

    @_kucoin_retrier
    async def cancel_order(
        self, exchange_order_id: str, symbol: str, order_type: trading_enums.TraderOrderType, **kwargs: dict
    ) -> trading_enums.OrderStatus:
        return await super().cancel_order(exchange_order_id, symbol, order_type, **kwargs)

    # add retried to _create_order_with_retry to avoid catching error in self._order_operation context manager
    @_kucoin_retrier
    async def _create_order_with_retry(self, order_type, symbol, quantity: decimal.Decimal,
                                       price: decimal.Decimal, stop_price: decimal.Decimal,
                                       side: trading_enums.TradeOrderSide,
                                       current_price: decimal.Decimal,
                                       reduce_only: bool, params) -> dict:
        return await super()._create_order_with_retry(
            order_type=order_type, symbol=symbol, quantity=quantity, price=price,
            stop_price=stop_price, side=side, current_price=current_price,
            reduce_only=reduce_only, params=params
        )

    @_kucoin_retrier
    async def get_my_recent_trades(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await super().get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs)

    @_kucoin_retrier
    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict):
        """
        Set the symbol margin type
        :param symbol: the symbol
        :param isolated: when False, margin type is cross, else it's isolated
        :return: the update result
        """
        try:
            return await super().set_symbol_margin_type(symbol, isolated, **kwargs)
        except ccxt.errors.ExchangeError as err:
            if "Please close or cancel them" in str(err):
                if self.SUPPORTS_SET_MARGIN_TYPE_ON_OPEN_POSITIONS:
                    raise
                else:
                    raise trading_errors.NotSupported(f"set_symbol_margin_type is not supported on open positions")
            raise

    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        """
        Get the current user symbol position list
        :param symbol: the position symbol
        :return: the user symbol position list
        """

        # todo remove when supported by ccxt
        async def fetch_position(client, symbol, params={}):
            market = client.market(symbol)
            market_id = market['id']
            request = {
                'symbol': market_id,
            }
            response = await client.futuresPrivateGetPosition(request)
            #
            #    {
            #        "code": "200000",
            #        "data": [
            #            {
            #                "id": "615ba79f83a3410001cde321",
            #                "symbol": "ETHUSDTM",
            #                "autoDeposit": False,
            #                "maintMarginReq": 0.005,
            #                "riskLimit": 1000000,
            #                "realLeverage": 18.61,
            #                "crossMode": False,
            #                "delevPercentage": 0.86,
            #                "openingTimestamp": 1638563515618,
            #                "currentTimestamp": 1638576872774,
            #                "currentQty": 2,
            #                "currentCost": 83.64200000,
            #                "currentComm": 0.05018520,
            #                "unrealisedCost": 83.64200000,
            #                "realisedGrossCost": 0.00000000,
            #                "realisedCost": 0.05018520,
            #                "isOpen": True,
            #                "markPrice": 4225.01,
            #                "markValue": 84.50020000,
            #                "posCost": 83.64200000,
            #                "posCross": 0.0000000000,
            #                "posInit": 3.63660870,
            #                "posComm": 0.05236717,
            #                "posLoss": 0.00000000,
            #                "posMargin": 3.68897586,
            #                "posMaint": 0.50637594,
            #                "maintMargin": 4.54717586,
            #                "realisedGrossPnl": 0.00000000,
            #                "realisedPnl": -0.05018520,
            #                "unrealisedPnl": 0.85820000,
            #                "unrealisedPnlPcnt": 0.0103,
            #                "unrealisedRoePcnt": 0.2360,
            #                "avgEntryPrice": 4182.10,
            #                "liquidationPrice": 4023.00,
            #                "bankruptPrice": 4000.25,
            #                "settleCurrency": "USDT",
            #                "isInverse": False
            #            }
            #        ]
            #    }
            #
            data = client.safe_value(response, 'data')
            return client.extend(client.parse_position(data, None), params)

        return self.connector.adapter.adapt_position(
            await fetch_position(self.connector.client, symbol, **kwargs)
        )

    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: trading_enums.TakeProfitStopLossMode):
        """
        take profit / stop loss mode does not exist on kucoin
        """


class KucoinCCXTAdapter(exchanges.CCXTAdapter):
    # Funding
    KUCOIN_DEFAULT_FUNDING_TIME = 8 * commons_constants.HOURS_TO_SECONDS

    # POSITION
    KUCOIN_AUTO_DEPOSIT = "autoDeposit"

    # ORDER
    KUCOIN_LEVERAGE = "leverage"
    KUCOIN_MARGIN_MODE = "marginMode"

    def fix_order(self, raw, symbol=None, **kwargs):
        fixed = super().fix_order(raw, symbol=symbol, **kwargs)
        self._ensure_fees(fixed)
        self._adapt_order_type(fixed)
        return fixed

    def fix_trades(self, raw, **kwargs):
        fixed = super().fix_trades(raw, **kwargs)
        for trade in fixed:
            self._adapt_order_type(trade)
            self._ensure_fees(trade)
        return fixed

    def _adapt_order_type(self, fixed):
        order_info = fixed[trading_enums.ExchangeConstantsOrderColumns.INFO.value]
        if fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == "liquid":
            # liquidation trades: considered as market orders
            fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = trading_enums.TradeOrderType.MARKET.value
        if trigger_direction := order_info.get("stop", None):
            updated_type = trading_enums.TradeOrderType.UNKNOWN.value
            """
            Stop Order Types (https://docs.kucoin.com/futures/#stop-orders)
            down: Triggers when the price reaches or goes below the stopPrice.
            up: Triggers when the price reaches or goes above the stopPrice.
            """
            side = fixed.get(trading_enums.ExchangeConstantsOrderColumns.SIDE.value)
            # SPOT: trigger_direction can be "loss" or  "entry"
            # spot
            is_stop_loss = False
            is_stop_entry = False
            trigger_above = False
            # spot
            if trigger_direction == "loss":
                is_stop_loss = True
            elif trigger_direction == "entry":
                is_stop_entry = True
            # futures
            elif trigger_direction == "up":
                trigger_above = True
            elif trigger_direction == "down":
                trigger_above = False
            else:
                # unhandled, rely on ccxt default parsing
                self.logger.error(
                    f"Unhandled [{self.connector.exchange_manager.exchange_name}] {trigger_direction} order: skipped custom order type parsing ({fixed})"
                )
                return fixed
            if is_stop_loss:
                trigger_above = side == trading_enums.TradeOrderSide.BUY.value
            if is_stop_entry:
                self.logger.error(
                    f"Unhandled [{self.connector.exchange_manager.exchange_name}] stop order type "
                    f"{trigger_direction} ({fixed})"
                )
            stop_price = fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.STOP_PRICE.value, None)
            if side == trading_enums.TradeOrderSide.BUY.value:
                if trigger_above:
                    updated_type = trading_enums.TradeOrderType.STOP_LOSS.value
                else:
                    # take profits are not yet handled as such: consider them as limit orders
                    updated_type = trading_enums.TradeOrderType.LIMIT.value # waiting for TP handling
                    if not fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]:
                        fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = stop_price # waiting for TP handling
            else:
                # selling
                if trigger_above:
                    # take profits are not yet handled as such: consider them as limit orders
                    updated_type = trading_enums.TradeOrderType.LIMIT.value # waiting for TP handling
                    if not fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]:
                        fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = stop_price # waiting for TP handling
                else:
                    updated_type = trading_enums.TradeOrderType.STOP_LOSS.value
            # stop loss are not tagged as such by ccxt, force it
            fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = updated_type
            fixed[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value] = trigger_above
        return fixed

    def parse_funding_rate(self, fixed, from_ticker=False, **kwargs):
        """
        Kucoin next funding time is not provided
        To obtain the last_funding_time :
        => timestamp(previous_funding_timestamp) + timestamp(KUCOIN_DEFAULT_FUNDING_TIME)
        """
        if from_ticker:
            # no funding info in ticker
            return {}
        funding_dict = super().parse_funding_rate(fixed, from_ticker=from_ticker, **kwargs)
        previous_funding_timestamp = fixed[trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value]
        fixed.update({
            # patch LAST_FUNDING_TIME in tentacle
            trading_enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                previous_funding_timestamp,
            # patch NEXT_FUNDING_TIME in tentacle
            trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value:
                previous_funding_timestamp + self.KUCOIN_DEFAULT_FUNDING_TIME,
        })
        return funding_dict

    def parse_position(self, fixed, **kwargs):
        raw_position_info = fixed[ccxt_enums.ExchangePositionCCXTColumns.INFO.value]
        parsed = super().parse_position(fixed, **kwargs)
        parsed[trading_enums.ExchangeConstantsPositionColumns.AUTO_DEPOSIT_MARGIN.value] = (
            raw_position_info.get(self.KUCOIN_AUTO_DEPOSIT, False)  # unset for cross positions
        )
        parsed_leverage = self.safe_decimal(
            parsed, trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value, constants.ZERO
        )
        if parsed_leverage == constants.ZERO:
            # on kucoin, fetched empty position don't have a leverage value. Since it's required within OctoBot,
            # add it manually
            symbol = parsed[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value]
            if self.connector.exchange_manager.exchange.has_pair_contract(symbol):
                parsed[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value] = \
                    self.connector.exchange_manager.exchange.get_pair_contract(symbol).current_leverage
            else:
                parsed[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value] = \
                    constants.DEFAULT_SYMBOL_LEVERAGE
        return parsed
