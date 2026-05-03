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
import octobot_commons.enums as commons_enums
import octobot_trading.errors
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.constants as constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors


_CACHED_CONFIRMED_FEES_BY_SYMBOL = {}


class KucoinConnector(ccxt_connector.CCXTConnector):

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
    DEFAULT_CONNECTOR_CLASS = KucoinConnector

    FAKE_DDOS_ERROR_INSTANT_RETRY_COUNT = 5
    # implemented in ccxt
    INSTANT_RETRY_ERROR_CODE = "429000"
    FUTURES_CCXT_CLASS_NAME = "kucoinfutures"
    """
    Deprecated constants kept as comments for reference.
    # text content of errors due to api key permissions issues
    # EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoinfutures Access denied, require more permission'
        ("require more permission",),
    ]
    # text content of errors due to account compliancy issues
    # EXCHANGE_COMPLIANCY_ERRORS: typing.List[typing.Iterable[str]] = [
        # kucoin {"msg":"Unfortunately, trading is currently unavailable in your location due to country, region, or IP restrictions.","code":"600004"}
        ("trading is currently unavailable in your location",),
    ]
    # text content of errors due to orders not found errors
    # EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoin The order does not exist.'
        ("order does not exist",),
    ]
    # text content of errors due to a closed position on the exchange. Relevant for reduce-only orders
    # EXCHANGE_CLOSED_POSITION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'kucoinfutures No open positions to close.'
        ("no open positions to close", )
    ]
    # text content of errors due to an order that would immediately trigger if created. Relevant for stop losses
    # EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS: typing.List[typing.Iterable[str]] = [
        # doesn't seem to happen on kucoin
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    # EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('order cannot be canceled', ),
        ('order_not_exist_or_not_allow_to_cancel', )
    ]
    # text content of errors due to unhandled IP white list issues
    # EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # "kucoinfutures Invalid request ip, the current clientIp is:e3b:e3b:e3b:e3b:e3b:e3b:e3b:e3b"
        ("invalid request ip",),
    ]
    """

    DEFAULT_BALANCE_CURRENCIES_TO_FETCH = ["USDT"]
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

    def should_log_on_ddos_exception(self, exception) -> bool:
        """
        Override when necessary
        """
        return Kucoin.INSTANT_RETRY_ERROR_CODE not in str(exception)

    def get_order_additional_params(self, order) -> dict:
        params = super().get_order_additional_params(order)
        if self.exchange_manager.is_future:
            contract = self.exchange_manager.exchange.get_pair_contract(order.symbol)
            params["leverage"] = float(contract.current_leverage)
            params["closeOrder"] = order.close_position
        return params

    async def _update_balance(self, balance, currency, **kwargs):
        balance.update(await super().get_balance(code=currency, **kwargs))

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
                if self.get_option_value(
                    trading_enums.ExchangeClientOptions.SUPPORTS_SET_MARGIN_TYPE_ON_OPEN_POSITIONS
                ):
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
    # POSITION
    KUCOIN_AUTO_DEPOSIT = "autoDeposit"

    # ORDER
    KUCOIN_MARGIN_MODE = "marginMode"


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
