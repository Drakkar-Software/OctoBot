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
import decimal
import typing

import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.personal_data as trading_personal_data


# def _disabled_okx_algo_order_creation(f):
#     async def disabled_okx_algo_order_creation_wrapper(*args, **kwargs):
#         # Algo order prevent bundled orders from working as they require to use the regular order api
#         # Since the regular order api works for limit and market orders as well, us it all the time
#         # Algo api is used for stop losses.
#         # This ccxt issue will remain as long as privatePostTradeOrderAlgo will be used for each order with a
#         # stopLossPrice or takeProfitPrice even when both are set (which make it an invalid okx algo order)
#         connector = args[0]
#         client = connector.client
#         client.privatePostTradeOrderAlgo = client.privatePostTradeOrder
#         try:
#             return await f(*args, **kwargs)
#         finally:
#             client.privatePostTradeOrderAlgo = connector.get_saved_data(connector.PRIVATE_POST_TRADE_ORDER_ALGO)
#     return disabled_okx_algo_order_creation_wrapper
#
#
# def _enabled_okx_algo_order_creation(f):
#     async def enabled_okx_algo_order_creation_wrapper(*args, **kwargs):
#         # Used to force algo orders availability and avoid concurrency issues due to _disabled_algo_order_creation
#         connector = args[0]
#         connector.client.privatePostTradeOrderAlgo = connector.get_saved_data(connector.PRIVATE_POST_TRADE_ORDER_ALGO)
#         return await f(*args, **kwargs)
#     return enabled_okx_algo_order_creation_wrapper
#
#
# class OkxConnector(ccxt_connector.CCXTConnector):
#     PRIVATE_POST_TRADE_ORDER_ALGO = "privatePostTradeOrderAlgo"
#
#     def _create_client(self, force_unauth=False):
#         super()._create_client(force_unauth=force_unauth)
#         # save client.privatePostTradeOrderAlgo ref to prevent concurrent _disabled_algo_order_creation issues
#         self.set_saved_data(self.PRIVATE_POST_TRADE_ORDER_ALGO, self.client.privatePostTradeOrderAlgo)
#
#     @_disabled_okx_algo_order_creation
#     async def create_market_buy_order(self, symbol, quantity, price=None, params=None) -> dict:
#         return await super().create_market_buy_order(symbol, quantity, price=price, params=params)
#
#     @_disabled_okx_algo_order_creation
#     async def create_limit_buy_order(self, symbol, quantity, price=None, params=None) -> dict:
#         return await super().create_limit_buy_order(symbol, quantity, price=price, params=params)
#
#     @_disabled_okx_algo_order_creation
#     async def create_market_sell_order(self, symbol, quantity, price=None, params=None) -> dict:
#         return await super().create_market_sell_order(symbol, quantity, price=price, params=params)
#
#     @_disabled_okx_algo_order_creation
#     async def create_limit_sell_order(self, symbol, quantity, price=None, params=None) -> dict:
#         return await super().create_limit_sell_order(symbol, quantity, price=price, params=params)
#
#     @_enabled_okx_algo_order_creation
#     async def create_market_stop_loss_order(self, symbol, quantity, price, side, current_price, params=None) -> dict:
#         return self.adapter.adapt_order(
#             await self.client.create_order(
#                 symbol, trading_enums.TradeOrderType.MARKET.value, side, quantity, params=params
#             ),
#             symbol=symbol, quantity=quantity
#         )


class Okx(exchanges.RestExchange):

    """
    Deprecated constants kept as comments for reference.
    # text content of errors due to orders not found errors
    # EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # OKX ex: okx {"msg":"API key doesn't exist","code":"50119"}
        ("api", "key", "doesn't exist"),
    ]
    # text content of errors due to account compliancy issues
    # EXCHANGE_COMPLIANCY_ERRORS: typing.List[typing.Iterable[str]] = [
        # OKX ex: Trading of this pair or contract is restricted due to local compliance requirements
        ("restricted", "compliance"),
        # OKX ex: You can't trade this pair or borrow this crypto due to local compliance restrictions.
        ("restrictions", "compliance"),
    ]
    # text content of errors due to unhandled authentication issues
    # EXCHANGE_AUTHENTICATION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'okx {"msg":"API key doesn't exist","code":"50119"}'
        ("api key doesn't exist",),
    ]
    # text content of errors due to unhandled IP white list issues
    # EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # okx {"msg":"Your IP 1.1.1.1 is not included in your API key's xxxx IP whitelist.","code":"50110"}
        ("is not included in your", "ip whitelist"),
    ]
    """
    _OKX_BUNDLED_ORDERS = [trading_enums.TraderOrderType.STOP_LOSS, trading_enums.TraderOrderType.TAKE_PROFIT,
                           trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.SELL_MARKET]

    @classmethod
    def get_name(cls):
        return 'okx'

    def get_adapter_class(self):
        return OKXCCXTAdapter

    @classmethod
    def is_supporting_sandbox(cls) -> bool:
        return False

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    async def get_sub_account_list(self):
        sub_account_list = (await self.connector.client.privateGetUsersSubaccountList()).get("data", [])
        if not sub_account_list:
            return []
        return [
            {
                trading_enums.SubAccountColumns.ID.value: sub_account.get("subAcct", ""),
                trading_enums.SubAccountColumns.NAME.value: sub_account.get("label", "")
            }
            for sub_account in sub_account_list
            if sub_account.get("enable", False)
        ]

    def get_order_additional_params(self, order) -> dict:
        params = super().get_order_additional_params(order)
        if self.exchange_manager.is_future:
            params[ccxt_enums.ExchangeOrderCCXTColumns.MARGIN_MODE.value] = self._get_ccxt_margin_type(order.symbol)
        return params

    def get_bundled_order_parameters(self, order, stop_loss_price=None, take_profit_price=None) -> dict:
        """
        Returns the updated params when this exchange supports orders created upon other orders fill
        (ex: a stop loss created at the same time as a buy order)
        :param order: the initial order
        :param stop_loss_price: the bundled order stopLoss price
        :param take_profit_price: the bundled order takeProfit price
        :return: A dict with the necessary parameters to create the bundled order on exchange alongside the
        base order in one request
        """
        params = {}
        if not (
            trading_personal_data.is_stop_order(order.order_type) or
            trading_personal_data.is_take_profit_order(order.order_type)
        ):
            # force non algo order "order type"
            if isinstance(order, trading_personal_data.MarketOrder):
                params["ordType"] = "market"
            elif isinstance(order, trading_personal_data.LimitOrder):
                params["px"] = str(order.origin_price)
                params["ordType"] = "limit"
        if stop_loss_price is not None:
            params[self.connector.adapter.OKX_STOP_LOSS_PRICE] = float(stop_loss_price)
            params["slOrdPx"] = -1  # execute as market order
        if take_profit_price is not None:
            params[self.connector.adapter.OKX_TAKE_PROFIT_PRICE] = float(take_profit_price)
            params["tpOrdPx"] = -1  # execute as market order
        return params

    async def _get_all_typed_orders(self, method, symbol=None, since=None, limit=None, **kwargs) -> list:
        # todo replace by settings fetch_stop_order_in_different_request method when OKX will be stable again
        # limit = self._fix_limit(limit)
        is_stop_order = kwargs.get("stop", False)
        if is_stop_order and self.connector.adapter.OKX_ORDER_TYPE not in kwargs:
            kwargs[self.connector.adapter.OKX_ORDER_TYPE] = self.connector.adapter.OKX_CONDITIONAL_ORDER_TYPE
        regular_orders = await method(symbol=symbol, since=since, limit=limit, **kwargs)
        if is_stop_order:
            # only require stop orders
            return regular_orders
        # add order types of order (different param in api endpoint)
        other_orders = []
        if self.exchange_manager.is_future:
            # stop orders are futures only for now
            for order_type in self._get_used_order_types():
                kwargs["ordType"] = order_type
                other_orders += await method(symbol=symbol, since=since, limit=limit, **kwargs)
        return regular_orders + other_orders

    async def get_open_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await self._get_all_typed_orders(
            super().get_open_orders, symbol=symbol, since=since, limit=limit, **kwargs
        )

    async def get_closed_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await self._get_all_typed_orders(
            super().get_closed_orders, symbol=symbol, since=since, limit=limit, **kwargs
        )

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        try:
            order = await super().get_order(
                exchange_order_id, symbol=symbol, order_type=order_type, **kwargs
            )
            return order
        except trading_errors.NotSupported:
            if kwargs.get("stop", False):
                # from ccxt 2.8.4
                # fetchOrder() does not support stop orders, use fetchOpenOrders() fetchCanceledOrders() or fetchClosedOrders
                return await self.get_order_from_open_and_closed_orders(exchange_order_id, symbol=symbol, **kwargs)
            raise

    def _is_oco_order(self, params):
        return all(
            oco_order_param in (params or {})
            for oco_order_param in (
                self.connector.adapter.OKX_STOP_LOSS_PRICE,
                self.connector.adapter.OKX_TAKE_PROFIT_PRICE
            )
        )

    async def create_order(self, order_type: trading_enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if self._is_oco_order(params):
            raise trading_errors.NotSupported(
                f"OCO bundled orders (orders including both a stop loss and take profit price) "
                f"are not yet supported on {self.get_name()}"
            )
        return await super().create_order(order_type, symbol, quantity,
                                          price=price, stop_price=stop_price,
                                          side=side, current_price=current_price,
                                          reduce_only=reduce_only, params=params)

    def _get_ccxt_margin_type(self, symbol, contract=None):
        if not self.exchange_manager.exchange.has_pair_contract(symbol):
            raise KeyError(f"{symbol} contract unavailable")
        contract = contract or self.exchange_manager.exchange.get_pair_contract(symbol)
        return ccxt_enums.ExchangeMarginTypes.ISOLATED.value if contract.is_isolated() \
            else ccxt_enums.ExchangeMarginTypes.CROSS.value

    def _get_margin_query_params(self, symbol, **kwargs):
        pos_side = self.connector.adapter.OKX_ONE_WAY_MODE
        if not self.exchange_manager.exchange.has_pair_contract(symbol):
            raise KeyError(f"{symbol} contract unavailable")
        else:
            contract = self.exchange_manager.exchange.get_pair_contract(symbol)
            if not contract.is_one_way_position_mode():
                self.logger.debug(f"Switching {symbol} position mode to one way")
                contract.set_position_mode(is_one_way=True, is_hedge=False)
                # todo: handle other position sides when cross is supported
            kwargs = kwargs or {}
            kwargs.update({
                self.connector.adapter.OKX_LEVER: float(contract.current_leverage),
                self.connector.adapter.OKX_MARGIN_MODE: self._get_ccxt_margin_type(symbol, contract=contract),
                self.connector.adapter.OKX_POS_SIDE: pos_side,
            })
        return kwargs

    async def get_symbol_leverage(self, symbol: str, **kwargs: dict):
        """
        :param symbol: the symbol
        :return: the current symbol leverage multiplier
        """
        kwargs = kwargs or {}
        if ccxt_enums.ExchangePositionCCXTColumns.MARGIN_MODE.value not in kwargs:
            margin_type = ccxt_enums.ExchangeMarginTypes.ISOLATED.value
            try:
                margin_type = self._get_ccxt_margin_type(symbol)
            except KeyError:
                pass
            kwargs[ccxt_enums.ExchangePositionCCXTColumns.MARGIN_MODE.value] = margin_type
        return await self.connector.get_symbol_leverage(symbol=symbol, **kwargs)

    async def set_symbol_leverage(self, symbol: str, leverage: float, **kwargs):
        """
        Set the symbol leverage
        :param symbol: the symbol
        :param leverage: the leverage
        :return: the update result
        """
        kwargs = self._get_margin_query_params(symbol, **kwargs)
        kwargs.pop(self.connector.adapter.OKX_LEVER, None)
        return await self.connector.set_symbol_leverage(leverage=leverage, symbol=symbol, **kwargs)

    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict):
        kwargs = self._get_margin_query_params(symbol, **kwargs)
        kwargs.pop(self.connector.adapter.OKX_MARGIN_MODE)
        await super().set_symbol_margin_type(symbol, isolated, **kwargs)

    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        """
        Get the current user symbol position
        :param symbol: the position symbol
        :return: the user symbol position
        """
        position = await super().get_position(symbol=symbol, **kwargs)
        if position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value] == constants.ZERO:
            await self._update_position_with_leverage_data(symbol, position)

        if position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value] != symbol:
            # happened in previous ccxt version, todo remove if no seen again
            raise ValueError(
                f"Invalid position symbol: "
                f"{position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value]}, "
                f"expected {symbol}"
            )
        return position

    async def _update_position_with_leverage_data(self, symbol, position):
        leverage_data = await self.get_symbol_leverage(symbol)
        adapter = self.connector.adapter
        OKX_info = leverage_data[ccxt_constants.CCXT_INFO]
        position[trading_enums.ExchangeConstantsPositionColumns.POSITION_MODE.value] = \
            adapter.parse_position_mode(OKX_info[0][adapter.OKX_POS_SIDE])
        position[trading_enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value] = \
            adapter.parse_margin_type(leverage_data[ccxt_enums.ExchangeLeverageCCXTColumns.MARGIN_MODE.value])
        position[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value] = \
            leverage_data[trading_enums.ExchangeConstantsLeveragePropertyColumns.LEVERAGE.value]

    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: trading_enums.TakeProfitStopLossMode):
        """
        take profit / stop loss mode does not exist on okx futures
        """

    def _get_used_order_types(self):
        return [
            # stop orders
            self.connector.adapter.OKX_CONDITIONAL_ORDER_TYPE,
            # created with bundled orders including stop loss & take profit: unsupported for now
            # self.connector.adapter.OKX_OCO_ORDER_TYPE,
        ]


class OKXCCXTAdapter(exchanges.CCXTAdapter):
    # ORDERS
    OKX_ORDER_TYPE = "ordType"
    OKX_TRIGGER_ORDER_TYPE = "trigger"
    OKX_OCO_ORDER_TYPE = "oco"
    OKX_CONDITIONAL_ORDER_TYPE = "conditional"
    OKX_BASIC_ORDER_TYPES = ["market", "limit"]
    OKX_LAST_PRICE = "last"
    OKX_STOP_LOSS_PRICE = "stopLossPrice"
    OKX_TAKE_PROFIT_PRICE = "takeProfitPrice"
    OKX_STOP_LOSS_TRIGGER_PRICE = "slTriggerPx"
    OKX_TAKE_PROFIT_TRIGGER_PRICE = "tpTriggerPx"

    # POSITIONS
    OKX_MARGIN_MODE = "mgnMode"
    OKX_POS_SIDE = "posSide"
    OKX_ONE_WAY_MODE = "net"

    # LEVERAGE
    OKX_LEVER = "lever"
    DATA = "data"

    # Funding
    OKX_DEFAULT_FUNDING_TIME = 8 * commons_constants.HOURS_TO_SECONDS


    def parse_position(self, fixed, force_empty=False, **kwargs):
        parsed = super().parse_position(fixed, force_empty=force_empty, **kwargs)
        # use isolated by default. Set in set_leverage
        parsed[trading_enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value] = \
            trading_enums.MarginType(
                fixed.get(ccxt_enums.ExchangePositionCCXTColumns.MARGIN_MODE.value)
                or trading_enums.MarginType.ISOLATED.value
            )
        # use one way by default. Set in set_leverage
        if parsed[trading_enums.ExchangeConstantsPositionColumns.SIZE.value] == constants.ZERO:
            parsed[trading_enums.ExchangeConstantsPositionColumns.POSITION_MODE.value] = \
                trading_enums.PositionMode.ONE_WAY
        return parsed

    def parse_margin_type(self, margin_mode):
        if margin_mode == ccxt_enums.ExchangeMarginTypes.ISOLATED.value:
            return trading_enums.MarginType.ISOLATED
        elif margin_mode == ccxt_enums.ExchangeMarginTypes.CROSS.value:
            return trading_enums.MarginType.CROSS
        raise ValueError(margin_mode)

    def parse_position_mode(self, position_mode):
        if position_mode == self.OKX_ONE_WAY_MODE:
            return trading_enums.PositionMode.ONE_WAY
        return trading_enums.PositionMode.HEDGE

    def parse_leverage(self, fixed, **kwargs):
        fixed = super().parse_leverage(fixed, **kwargs)
        leverages = [
            fixed[ccxt_enums.ExchangeLeverageCCXTColumns.LONG_LEVERAGE.value],
            fixed[ccxt_enums.ExchangeLeverageCCXTColumns.SHORT_LEVERAGE.value],
        ]
        fixed[trading_enums.ExchangeConstantsLeveragePropertyColumns.LEVERAGE.value] = \
            decimal.Decimal(str(leverages[0] or leverages[1]))
        return fixed
