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
import ccxt.async_support

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants


class BitMartConnector(exchanges.CCXTConnector):

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchanges.ExchangeCredentialsData], exchanges.ExchangeCredentialsData]=None
    ) -> tuple:
        client, is_authenticated = super()._client_factory(force_unauth, keys_adapter=self._keys_adapter)
        if client:
            client.handle_errors = self._patched_handle_errors_factory(client)
        return client, is_authenticated

    def _patched_handle_errors_factory(self, client: ccxt.async_support.Exchange):
        self = client # set self to the client to use the client methods
        def _patched_handle_errors(code: int, reason: str, url: str, method: str, headers: dict, body: str, response, requestHeaders, requestBody):
            # temporary patch waiting for CCXT fix (issue in ccxt 4.5.28)
            if response is None:
                return None
            #
            # spot
            #
            #     {"message":"Bad Request [to is empty]","code":50000,"trace":"f9d46e1b-4edb-4d07-a06e-4895fb2fc8fc","data":{}}
            #     {"message":"Bad Request [from is empty]","code":50000,"trace":"579986f7-c93a-4559-926b-06ba9fa79d76","data":{}}
            #     {"message":"Kline size over 500","code":50004,"trace":"d625caa8-e8ca-4bd2-b77c-958776965819","data":{}}
            #     {"message":"Balance not enough","code":50020,"trace":"7c709d6a-3292-462c-98c5-32362540aeef","data":{}}
            #     {"code":40012,"message":"You contract account available balance not enough.","trace":"..."}
            #
            # contract
            #
            #     {"errno":"OK","message":"INVALID_PARAMETER","code":49998,"trace":"eb5ebb54-23cd-4de2-9064-e090b6c3b2e3","data":null}
            #
            message = self.safe_string_lower(response, 'message') # PATCH
            isErrorMessage = (message is not None) and (message != 'ok') and (message != 'success')
            errorCode = self.safe_string(response, 'code')
            isErrorCode = (errorCode is not None) and (errorCode != '1000')
            if isErrorCode or isErrorMessage:
                feedback = self.id + ' ' + body
                self.throw_exactly_matched_exception(self.exceptions['exact'], message, feedback)
                self.throw_broadly_matched_exception(self.exceptions['broad'], message, feedback)
                self.throw_exactly_matched_exception(self.exceptions['exact'], errorCode, feedback)
                self.throw_broadly_matched_exception(self.exceptions['broad'], errorCode, feedback)
                raise ccxt.ExchangeError(feedback)  # unknown message
            return None
        return _patched_handle_errors

    def _keys_adapter(self, creds: exchanges.ExchangeCredentialsData) -> exchanges.ExchangeCredentialsData:
        # use password as uid
        creds.uid = creds.password
        creds.password = None
        return creds


class BitMart(exchanges.RestExchange):
    FIX_MARKET_STATUS = True
    DEFAULT_CONNECTOR_CLASS = BitMartConnector
    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True
    # broken: need v4 endpoint required, 10/10/25 ccxt still doesn't have it
    # bitmart {"msg":"This endpoint has been deprecated. Please refer to the document:
    # https://developer-pro.bitmart.com/en/spot/#update-plan","code":30031}
    SUPPORT_FETCHING_CANCELLED_ORDERS = False
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server

    @classmethod
    def get_name(cls):
        return 'bitmart'

    def get_adapter_class(self):
        return BitMartCCXTAdapter

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False  # disable quote conversion
            }
        }

    async def get_account_id(self, **kwargs: dict) -> str:
        # not available on bitmart
        return trading_constants.DEFAULT_ACCOUNT_ID


class BitMartCCXTAdapter(exchanges.CCXTAdapter):
    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        self.adapt_amount_from_filled_or_cost(fixed)
        if (
            fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == trading_enums.TradeOrderType.MARKET.value
            and fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value]
                == trading_enums.OrderStatus.CANCELED.value
            and fixed[trading_enums.ExchangeConstantsOrderColumns.FILLED.value]
        ):
            # consider as filled & closed (Bitmart is sometimes tagging filled market orders as "canceled": ignore it)
            fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CLOSED.value
        return fixed
