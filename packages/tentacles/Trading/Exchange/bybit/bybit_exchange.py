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

import ccxt

import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.constants as constants
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.errors


class Bybit(exchanges.RestExchange):
    DESCRIPTION = ""

    FIX_MARKET_STATUS = True

    # Bybit default take profits are market orders
    # note: use BUY_MARKET and SELL_MARKET since in reality those are conditional market orders, which behave the same
    # way as limit order but with higher fees
    _BYBIT_BUNDLED_ORDERS = [trading_enums.TraderOrderType.STOP_LOSS, trading_enums.TraderOrderType.TAKE_PROFIT,
                             trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.SELL_MARKET]

    # should be overridden locally to match exchange support
    SUPPORTED_ELEMENTS = {
        trading_enums.ExchangeTypes.FUTURE.value: {
            # order that should be self-managed by OctoBot
            trading_enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                # trading_enums.TraderOrderType.STOP_LOSS,    # supported on futures
                trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
                trading_enums.TraderOrderType.TAKE_PROFIT,
                trading_enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                trading_enums.TraderOrderType.TRAILING_STOP,
                trading_enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {
                trading_enums.TraderOrderType.BUY_MARKET: _BYBIT_BUNDLED_ORDERS,
                trading_enums.TraderOrderType.SELL_MARKET: _BYBIT_BUNDLED_ORDERS,
                trading_enums.TraderOrderType.BUY_LIMIT: _BYBIT_BUNDLED_ORDERS,
                trading_enums.TraderOrderType.SELL_LIMIT: _BYBIT_BUNDLED_ORDERS,
            },
        },
        trading_enums.ExchangeTypes.SPOT.value: {
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
            trading_enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        }
    }

    MARK_PRICE_IN_TICKER = True
    FUNDING_IN_TICKER = True

    # set True when get_positions() is not returning empty positions and should use get_position() instead
    REQUIRES_SYMBOL_FOR_EMPTY_POSITION = True
    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = True  # set True when get_order() can return None
    # (order not found) when orders are instantly filled on exchange and are not fully processed on the exchange side.

    # Set True when get_open_order() can return outdated orders (cancelled or not yet created)
    CAN_HAVE_DELAYED_CANCELLED_ORDERS = True
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server

    BUY_STR = "Buy"
    SELL_STR = "Sell"

    LONG_STR = BUY_STR
    SHORT_STR = SELL_STR

    # Order category. 0：normal order by default; 1：TP/SL order, Required for TP/SL order.
    ORDER_CATEGORY = "orderCategory"
    STOP_ORDERS_FILTER = "stop"
    SPOT_STOP_ORDERS_FILTER = "StopOrder"
    ORDER_FILTER = "orderFilter"

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        super().__init__(config, exchange_manager, exchange_config_by_exchange, connector_class=connector_class)
        self.order_quantity_by_amount = {}
        self.order_quantity_by_id = {}

    def get_additional_connector_config(self):
        connector_config = {
            ccxt_constants.CCXT_OPTIONS: {
                "recvWindow": 60000,    # default is 5000, avoid time related issues
            }
        }
        if not self.exchange_manager.is_future:
            # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
            # (price should not be sent to market orders). Only used for buy market orders
            connector_config[ccxt_constants.CCXT_OPTIONS][
                "createMarketBuyOrderRequiresPrice"
            ] = False  # disable quote conversion
        return connector_config

    def get_adapter_class(self):
        return BybitCCXTAdapter

    @classmethod
    def get_name(cls) -> str:
        return 'bybit'

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    async def initialize_impl(self):
        await super().initialize_impl()
        # ensure the authenticated account is not a unified trading account as it is not fully supported
        await self._check_unified_account()

    async def _check_unified_account(self):
        if self.connector.client and not self.exchange_manager.exchange_only:
            try:
                self.connector.client.check_required_credentials()
                enable_unified_margin, enable_unified_account = await self.connector.client.is_unified_enabled()
                if enable_unified_margin or enable_unified_account:
                    raise octobot_trading.errors.NotSupported(
                        "Ignoring Bybit exchange: "
                        "Bybit unified trading accounts are not yet fully supported. To trade on Bybit, please use a "
                        "standard account. You can easily switch between unified and standard using subaccounts. "
                        "Transferring funds between subaccounts is free and instant."
                    )
            except ccxt.AuthenticationError:
                # unauthenticated
                pass

    async def get_open_orders(self, symbol: str = None, since: int = None,
                              limit: int = None, **kwargs: dict) -> list:
        orders = await super().get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)
        if not self.exchange_manager.is_future:
            kwargs = kwargs or {}
            # include stop orders
            kwargs[self.ORDER_FILTER] = self.SPOT_STOP_ORDERS_FILTER
            orders += await super().get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)
        return orders

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[trading_enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        # regular get order is not supported
        return await self.get_order_from_open_and_closed_orders(exchange_order_id, symbol=symbol, **kwargs)

    async def cancel_order(
            self, exchange_order_id: str, symbol: str, order_type: trading_enums.TraderOrderType, **kwargs: dict
    ) -> trading_enums.OrderStatus:
        kwargs = kwargs or {}
        if trading_personal_data.is_stop_order(order_type):
            kwargs[self.ORDER_FILTER] = self.SPOT_STOP_ORDERS_FILTER
        return await super().cancel_order(
            exchange_order_id, symbol, order_type, **kwargs
        )

    async def create_order(self, order_type: trading_enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: trading_enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if not self.exchange_manager.is_future:
            # should be replacable by ENABLE_SPOT_BUY_MARKET_WITH_COST = True => check when upgrading to unified
            if order_type is trading_enums.TraderOrderType.BUY_MARKET:
                # on Bybit, market orders are in quote currency (YYY in XYZ/YYY)
                used_price = price or current_price
                if not used_price:
                    raise octobot_trading.errors.NotSupported(f"{self.get_name()} requires a price parameter to create "
                                                              f"market orders as quantity is in quote currency")
                origin_quantity = quantity
                quantity = quantity * used_price
                self.order_quantity_by_amount[float(quantity)] = float(origin_quantity)
        return await super().create_order(order_type, symbol, quantity,
                                          price=price, stop_price=stop_price,
                                          side=side, current_price=current_price,
                                          reduce_only=reduce_only, params=params)

    def _get_stop_trigger_direction(self, side):
        if side == trading_enums.TradeOrderSide.SELL.value:
            return "bellow"
        return "above"

    async def _create_market_stop_loss_order(self, symbol, quantity, price, side, current_price, params=None) -> dict:
        # todo make sure this still works
        params = params or {}
        params["triggerPrice"] = price
        if self.exchange_manager.is_future:
            # BybitCCXTAdapter.BYBIT_TRIGGER_ABOVE_KEY required on future stop orders
            params[BybitCCXTAdapter.BYBIT_TRIGGER_ABOVE_KEY] = self._get_stop_trigger_direction(side)
        # else:
        #     params[self.ORDER_CATEGORY] = 1
        order = self.connector.adapter.adapt_order(
            await self.connector.client.create_order(
                symbol, trading_enums.TradeOrderType.MARKET.value, side, quantity, params=params
            ),
            symbol=symbol, quantity=quantity
        )
        return order

    async def _edit_order(self, exchange_order_id: str, order_type: trading_enums.TraderOrderType, symbol: str,
                          quantity: float, price: float, stop_price: float = None, side: str = None,
                          current_price: float = None, params: dict = None):
        params = params or {}
        if trading_personal_data.is_stop_order(order_type):
            params["stop_order_id"] = exchange_order_id
        if stop_price is not None:
            # params["stop_px"] = stop_price
            # params["stop_loss"] = stop_price
            params["triggerPrice"] = str(stop_price)
        return await super()._edit_order(exchange_order_id, order_type, symbol, quantity=quantity,
                                         price=price, stop_price=stop_price, side=side,
                                         current_price=current_price, params=params)

    async def _verify_order(self, created_order, order_type, symbol, price, quantity, side, get_order_params=None):
        return await super()._verify_order(created_order, order_type, symbol, price, quantity, side,
                                           get_order_params=get_order_params)

    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: trading_enums.TakeProfitStopLossMode):
        # /contract/v3/private/position/switch-tpsl-mode
        # from https://bybit-exchange.github.io/docs/derivativesV3/contract/#t-dv_switchpositionmode
        params = {
            "symbol": self.connector.client.market(symbol)['id'],
            "tpSlMode": tp_sl_mode.value
        }
        try:
            await self.connector.client.privatePostContractV3PrivatePositionSwitchTpslMode(params)
        except ccxt.ExchangeError as e:
            if "same tp sl mode1" in str(e):
                # can't fetch the tp sl mode1 value
                return
            raise

    def get_order_additional_params(self, order) -> dict:
        params = {}
        if self.exchange_manager.is_future:
            contract = self.exchange_manager.exchange.get_pair_contract(order.symbol)
            params["positionIdx"] = self._get_position_idx(contract)
            params["reduceOnly"] = order.reduce_only
        return params

    def _get_margin_type_query_params(self, symbol, **kwargs):
        if not self.exchange_manager.exchange.has_pair_contract(symbol):
            raise KeyError(f"{symbol} contract unavailable")
        else:
            contract = self.exchange_manager.exchange.get_pair_contract(symbol)
            kwargs = kwargs or {}
            kwargs[ccxt_enums.ExchangePositionCCXTColumns.LEVERAGE.value] = float(contract.current_leverage)
        return kwargs

    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict):
        kwargs = self._get_margin_type_query_params(symbol, **kwargs)
        await super().set_symbol_margin_type(symbol, isolated, **kwargs)

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
        if stop_loss_price is not None:
            params["stopLoss"] = str(stop_loss_price)
        if take_profit_price is not None:
            params["takeProfit"] = str(take_profit_price)
        return params

    def _get_position_idx(self, contract):
        # "position_idx" has to be set when trading futures
        # from https://bybit-exchange.github.io/docs/inverse/#t-myposition
        # Position idx, used to identify positions in different position modes:
        # 0-One-Way Mode
        # 1-Buy side of both side mode
        # 2-Sell side of both side mode
        if contract.is_one_way_position_mode():
            return 0
        else:
            raise NotImplementedError(
                f"Hedge mode is not implemented yet. Please switch to One-Way position mode from the Bybit "
                f"trading interface preferences of {contract.pair}"
            )
            # TODO
            # if Buy side of both side mode:
            #     return 1
            # else Buy side of both side mode:
            #     return 2


class BybitCCXTAdapter(exchanges.CCXTAdapter):
    # Position
    BYBIT_BANKRUPTCY_PRICE = "bustPrice"
    BYBIT_CLOSING_FEE = "occClosingFee"
    BYBIT_MODE = "positionIdx"
    BYBIT_TRADE_MODE = "tradeMode"
    BYBIT_REALIZED_PNL = "RealisedPnl"
    BYBIT_ONE_WAY = "MergedSingle"
    BYBIT_ONE_WAY_DIGIT = "0"
    BYBIT_HEDGE = "BothSide"
    BYBIT_HEDGE_DIGITS = ["1", "2"]

    # Funding
    BYBIT_DEFAULT_FUNDING_TIME = 8 * commons_constants.HOURS_TO_SECONDS

    # Orders
    BYBIT_REDUCE_ONLY = "reduceOnly"
    BYBIT_TRIGGER_ABOVE_KEY = "triggerDirection"
    BYBIT_TRIGGER_ABOVE_VALUE = "1"

    # Trades
    EXEC_TYPE = "execType"
    TRADE_TYPE = "Trade"

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        order_info = raw[trading_enums.ExchangeConstantsOrderColumns.INFO.value]
        # parse reduce_only if present
        fixed[trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value] = \
            order_info.get(self.BYBIT_REDUCE_ONLY, False)
        if tigger_above := order_info.get(trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value):
            fixed[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value] = \
                tigger_above == self.BYBIT_TRIGGER_ABOVE_VALUE
        status = fixed.get(trading_enums.ExchangeConstantsOrderColumns.STATUS.value)
        if status == 'ORDER_NEW':
            fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.OPEN.value
        if status == 'ORDER_CANCELED':
            fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CANCELED.value
        if status == 'PARTIALLY_FILLED_CANCELED':
            fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.FILLED.value
        self._adapt_order_type(fixed)
        if not self.connector.exchange_manager.is_future:
            try:
                if fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] \
                        == trading_enums.TradeOrderType.MARKET.value and \
                        fixed[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] \
                        == trading_enums.TradeOrderSide.BUY.value:
                    try:
                        quantity = self.connector.exchange_manager.exchange.order_quantity_by_amount[
                            kwargs.get("quantity", fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.AMOUNT.value))
                        ]
                        self.connector.exchange_manager.exchange.order_quantity_by_id[
                            fixed[ccxt_enums.ExchangeOrderCCXTColumns.ID.value]
                        ] = quantity
                    except KeyError:
                        try:
                            quantity = self.connector.exchange_manager.exchange.order_quantity_by_id[
                                fixed[ccxt_enums.ExchangeOrderCCXTColumns.ID.value]]
                        except KeyError:
                            amount = fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.AMOUNT.value)
                            price = fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.AVERAGE.value,
                                              fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.PRICE.value)
                                              )
                            quantity = amount / (price if price else 1)
                    if fixed[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] is None or \
                            fixed[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] < quantity * 0.999:
                        # when order status is PARTIALLY_FILLED_CANCELED but is actually filled
                        fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = \
                            trading_enums.OrderStatus.OPEN.value
                    # convert amount to have the same units as every other exchange
                    fixed[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] = quantity
            except KeyError:
                pass
        return fixed

    def _adapt_order_type(self, fixed):
        if fixed.get("triggerPrice", None):
            if fixed.get("takeProfitPrice", None):
                # take profit are not tagged as such by ccxt, force it
                # check take profit first as takeProfitPrice is also set for stop losses
                fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = \
                    trading_enums.TradeOrderType.TAKE_PROFIT.value
            elif fixed.get("stopPrice", None):
                # stop loss are not tagged as such by ccxt, force it
                fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = \
                    trading_enums.TradeOrderType.STOP_LOSS.value
            else:
                self.logger.error(f"Unknown [{self.connector.exchange_manager.exchange_name}] trigger order: {fixed}")
        return fixed

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed
    
    def parse_position(self, fixed, **kwargs):
        try:
            # todo handle contract value
            raw_position_info = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.INFO.value)
            size = decimal.Decimal(
                str(fixed.get(ccxt_enums.ExchangePositionCCXTColumns.CONTRACTS.value, 0)))
            # if size == constants.ZERO:
            #     return {}  # Don't parse empty position

            symbol = self.connector.get_pair_from_exchange(
                fixed[ccxt_enums.ExchangePositionCCXTColumns.SYMBOL.value])
            raw_mode = raw_position_info.get(self.BYBIT_MODE)
            mode = trading_enums.PositionMode.ONE_WAY
            if raw_mode == self.BYBIT_HEDGE or raw_mode in self.BYBIT_HEDGE_DIGITS:
                mode = trading_enums.PositionMode.HEDGE
            trade_mode = raw_position_info.get(self.BYBIT_TRADE_MODE)
            margin_type = trading_enums.MarginType.ISOLATED if trade_mode == "1" else trading_enums.MarginType.CROSS
            original_side = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.SIDE.value)

            side = trading_enums.PositionSide.BOTH
            # todo when handling cross positions
            # side = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.SIDE.value, enums.PositionSide.UNKNOWN.value)
            # position_side = enums.PositionSide.LONG \
            #     if side == enums.PositionSide.LONG.value else enums.PositionSide.SHORT

            unrealized_pnl = self.safe_decimal(fixed,
                                               ccxt_enums.ExchangePositionCCXTColumns.UNREALISED_PNL.value,
                                               constants.ZERO)
            liquidation_price = self.safe_decimal(fixed,
                                                  ccxt_enums.ExchangePositionCCXTColumns.LIQUIDATION_PRICE.value,
                                                  constants.ZERO)
            entry_price = self.safe_decimal(fixed,
                                            ccxt_enums.ExchangePositionCCXTColumns.ENTRY_PRICE.value,
                                            constants.ZERO)
            return {
                trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value: symbol,
                trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value:
                    self.connector.client.safe_value(fixed,
                                                     ccxt_enums.ExchangePositionCCXTColumns.TIMESTAMP.value, 0),
                trading_enums.ExchangeConstantsPositionColumns.SIDE.value: side,
                trading_enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value: margin_type,
                trading_enums.ExchangeConstantsPositionColumns.SIZE.value:
                    size if original_side == trading_enums.PositionSide.LONG.value else -size,
                trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value:
                    self.safe_decimal(
                        fixed, ccxt_enums.ExchangePositionCCXTColumns.INITIAL_MARGIN.value,
                        constants.ZERO
                    ),
                trading_enums.ExchangeConstantsPositionColumns.NOTIONAL.value:
                    self.safe_decimal(
                        fixed, ccxt_enums.ExchangePositionCCXTColumns.NOTIONAL.value, constants.ZERO
                    ),
                trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value:
                    self.safe_decimal(
                        fixed, ccxt_enums.ExchangePositionCCXTColumns.LEVERAGE.value, constants.ONE
                    ),
                trading_enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value: unrealized_pnl,
                trading_enums.ExchangeConstantsPositionColumns.REALISED_PNL.value:
                    self.safe_decimal(
                        fixed, self.BYBIT_REALIZED_PNL, constants.ZERO
                    ),
                trading_enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value: liquidation_price,
                trading_enums.ExchangeConstantsPositionColumns.CLOSING_FEE.value:
                    self.safe_decimal(
                        fixed, self.BYBIT_CLOSING_FEE, constants.ZERO
                    ),
                trading_enums.ExchangeConstantsPositionColumns.BANKRUPTCY_PRICE.value:
                    self.safe_decimal(
                        fixed, self.BYBIT_BANKRUPTCY_PRICE, constants.ZERO
                    ),
                trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: entry_price,
                trading_enums.ExchangeConstantsPositionColumns.CONTRACT_TYPE.value:
                    self.connector.exchange_manager.exchange.get_contract_type(symbol),
                trading_enums.ExchangeConstantsPositionColumns.POSITION_MODE.value: mode,
            }
        except KeyError as e:
            self.logger.error(f"Fail to parse position dict ({e})")
        return fixed

    def parse_funding_rate(self, fixed, from_ticker=False, **kwargs):
        """
        Bybit last funding time is not provided
        To obtain the last_funding_time :
        => timestamp(next_funding_time) - timestamp(BYBIT_DEFAULT_FUNDING_TIME)
        """
        funding_dict = super().parse_funding_rate(fixed, from_ticker=from_ticker, **kwargs)
        if from_ticker:
            if ccxt_constants.CCXT_INFO not in funding_dict:
                return {}
            # no data in fixed when coming from ticker
            funding_dict = fixed[ccxt_constants.CCXT_INFO]
            funding_next_timestamp = self.get_uniformized_timestamp(
                float(funding_dict.get(ccxt_enums.ExchangeFundingCCXTColumns.NEXT_FUNDING_TIME.value, 0))
            )
            funding_rate = decimal.Decimal(
                str(funding_dict.get(ccxt_enums.ExchangeFundingCCXTColumns.FUNDING_RATE.value, constants.NaN))
            )
            funding_dict.update({
                trading_enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                    max(funding_next_timestamp - self.BYBIT_DEFAULT_FUNDING_TIME, 0),
                trading_enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value: funding_rate,
                trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value: funding_next_timestamp,
                trading_enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value: funding_rate
            })
        else:
            funding_next_timestamp = float(
                funding_dict.get(trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value, 0)
            )
            # patch LAST_FUNDING_TIME in tentacle
            funding_dict.update({
                trading_enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                    max(funding_next_timestamp - self.BYBIT_DEFAULT_FUNDING_TIME, 0)
            })
        return funding_dict

    def parse_mark_price(self, fixed, from_ticker=False, **kwargs) -> dict:
        if from_ticker and ccxt_constants.CCXT_INFO in fixed:
            try:
                return {
                    trading_enums.ExchangeConstantsMarkPriceColumns.MARK_PRICE.value:
                        fixed[ccxt_constants.CCXT_INFO][trading_enums.ExchangeConstantsMarkPriceColumns.MARK_PRICE.value]
                }
            except KeyError:
                pass
        return {
            trading_enums.ExchangeConstantsMarkPriceColumns.MARK_PRICE.value:
                decimal.Decimal(fixed[
                    trading_enums.ExchangeConstantsTickersColumns.CLOSE.value])
        }

    def fix_trades(self, raw, **kwargs):
        if self.connector.exchange_manager.is_future:
            raw = [
                trade
                for trade in raw
                if trade[trading_enums.ExchangeConstantsOrderColumns.INFO.value].get(
                    self.EXEC_TYPE, None) == self.TRADE_TYPE    # ignore non-trade elements (such as funding)
            ]
        return super().fix_trades(raw, **kwargs)
