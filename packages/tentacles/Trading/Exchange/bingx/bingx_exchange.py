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

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.enums as trading_enums


class BingxConnector(ccxt_connector.CCXTConnector):
    def _create_client(self, force_unauth=False):
        super()._create_client(force_unauth=force_unauth)
        # bingx v1 spotV1PublicGetMarketKline randomly errors when fetching candles: force V2
        self.client.spotV1PublicGetMarketKline = self.client.spotV2PublicGetMarketKline

class Bingx(exchanges.RestExchange):
    FIX_MARKET_STATUS = True
    DEFAULT_CONNECTOR_CLASS = BingxConnector    # TODO remove this when ccxt updates to spotV2PublicGetMarketKline


    # text content of errors due to orders not found errors
    EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'bingx {"code":100404,"msg":" order not exist","debugMsg":""}'
        ("order not exist",),
        # bingx {"code":100404,"msg":"the order you want to cancel is FILLED or CANCELLED already, or is not a valid
        # order id ,please verify","debugMsg":""}
        ("the order you want to cancel is filled or cancelled already", ),
        #  bingx {"code":100404,"msg":"the order is FILLED or CANCELLED already before, or is not a valid
        #  order id ,please verify","debugMsg":""}
        ("the order is filled or cancelled already before", ),
    ]
    # text content of errors due to unhandled authentication issues
    EXCHANGE_AUTHENTICATION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'bingx {'code': '100413', 'msg': 'Incorrect apiKey', 'timestamp': '1725195218082'}'
        ("incorrect apikey",),
    ]
    # text content of errors due to api key permissions issues
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # 'bingx {"code":100004,"msg":"Permission denied as the API key was created without the permission，
        # this api need Spot Trading permission， please config it in https://bingx.com/en/account/api"'
        ("permission denied", "trading permission"),
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('the order is filled or cancelled', ''),
        ('order not exist', '')
    ]
    # text content of errors due to unhandled IP white list issues
    EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = [
        # "PermissionDenied("bingx {"code":100419,"msg":"your current request IP is xx.xx.xx.xxx does not match IP
        # whitelist , please go to https://bingx.com/en/account/api/ to verify the ip you have set",
        # "timestamp":1739291708037}")"
        ("not match ip whitelist",),
    ]
    
    # Set True when get_open_order() can return outdated orders (cancelled or not yet created)
    CAN_HAVE_DELAYED_CANCELLED_ORDERS = True

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

    def get_adapter_class(self):
        return BingxCCXTAdapter

    @classmethod
    def get_name(cls) -> str:
        return 'bingx'

    async def get_account_id(self, **kwargs: dict) -> str:
        with self.connector.error_describer(True):
            resp = await self.connector.client.accountV1PrivateGetUid()
            return resp["data"]["uid"]

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        # unknown (05/06/2025)
        return super().get_max_orders_count(symbol, order_type)

    async def get_my_recent_trades(self, symbol=None, since=None, limit=None, **kwargs):
        # On SPOT Bingx, account recent trades is available under fetch_closed_orders
        if self.exchange_manager.is_future:
            return await super().get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs)
        return await super().get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        signature_identifier = "signature="
        return bool(
            url
            and signature_identifier in url
        )

class BingxCCXTAdapter(exchanges.CCXTAdapter):

    def _update_stop_order_or_trade_type_and_price(self, order_or_trade: dict):
        info = order_or_trade.get(ccxt_constants.CCXT_INFO, {})
        if stop_price := order_or_trade.get(trading_enums.ExchangeConstantsOrderColumns.STOP_LOSS_PRICE.value):
            # from https://bingx-api.github.io/docs/#/en-us/spot/trade-api.html#Current%20Open%20Orders
            order_creation_price = float(
                info.get("price") or order_or_trade.get(
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value
                )
            )
            is_selling = (
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
                == trading_enums.TradeOrderSide.SELL.value
            )
            stop_price = float(stop_price)
            # use stop price as order price to parse it properly
            order_or_trade[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = stop_price
            # type is TAKE_STOP_LIMIT (not unified)
            if order_or_trade.get(trading_enums.ExchangeConstantsOrderColumns.TYPE.value) == "take_stop_limit":
                # unsupported: no way to figure out if this order is a stop loss or a take profit
                # (trigger above or bellow)
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = (
                    trading_enums.TradeOrderType.UNSUPPORTED.value)
                self.logger.info(f"Unsupported order fetched: {order_or_trade}")
            else:
                if stop_price <= order_creation_price:
                    trigger_above = False
                    if is_selling:
                        order_type = trading_enums.TradeOrderType.STOP_LOSS.value
                        order_or_trade[trading_enums.ExchangeConstantsOrderColumns.STOP_PRICE.value] = stop_price
                    else:
                        order_type = trading_enums.TradeOrderType.LIMIT.value
                else:
                    trigger_above = True
                    if is_selling:
                        order_type = trading_enums.TradeOrderType.LIMIT.value
                    else:
                        order_type = trading_enums.TradeOrderType.STOP_LOSS.value
                        order_or_trade[trading_enums.ExchangeConstantsOrderColumns.STOP_PRICE.value] = stop_price
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value] = trigger_above
                order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = order_type

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        self._update_stop_order_or_trade_type_and_price(fixed)
        try:
            info = fixed[ccxt_constants.CCXT_INFO]
            fixed[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] = info["orderId"]
        except KeyError:
            pass
        return fixed

    def fix_trades(self, raw, **kwargs):
        fixed = super().fix_trades(raw, **kwargs)
        for trade in fixed:
            self._update_stop_order_or_trade_type_and_price(trade)
        return fixed

    def fix_market_status(self, raw, remove_price_limits=False, **kwargs):
        fixed = super().fix_market_status(raw, remove_price_limits=remove_price_limits, **kwargs)
        if not fixed:
            return fixed
        # bingx min and max quantity should be ignored
        # https://bingx-api.github.io/docs/#/en-us/spot/market-api.html#Spot%20trading%20symbols
        limits = fixed[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]
        limits[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value][
            trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value
        ] = 0
        limits[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value][
            trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value
        ] = None

        return fixed
