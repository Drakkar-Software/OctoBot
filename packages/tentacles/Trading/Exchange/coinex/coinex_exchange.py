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
import octobot_trading.enums as trading_enums
import octobot_trading.constants as constants


class Coinex(exchanges.RestExchange):
    DESCRIPTION = ""

    FIX_MARKET_STATUS = True

    MAX_PAGINATION_LIMIT: int = 100

    # text content of errors due to orders not found errors
    EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = [
        # ExchangeError('coinex Order not found')
        ("order not found", )
    ]
    SUPPORT_FETCHING_CANCELLED_ORDERS = False
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True

    @classmethod
    def get_name(cls):
        return 'coinex'

    def get_adapter_class(self):
        return CoinexCCXTAdapter

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False  # disable quote conversion
            }
        }

    async def get_account_id(self, **kwargs: dict) -> str:
        # current impossible to get account UID (22/02/25)
        return constants.DEFAULT_ACCOUNT_ID

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        v1_signature_identifiers = "Authorization"
        v2_signature_identifiers = "X-COINEX-SIGN"
        return bool(
            headers
            and (
                v1_signature_identifiers in headers
                or v2_signature_identifiers in headers
            )
        )

    async def get_open_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await super().get_open_orders(symbol=symbol,
                                             since=since,
                                             limit=self._fix_limit(limit),
                                             **kwargs)

    async def get_closed_orders(self, symbol=None, since=None, limit=None, **kwargs) -> list:
        return await super().get_closed_orders(symbol=symbol,
                                               since=since,
                                               limit=self._fix_limit(limit),
                                               **kwargs)

    def _fix_limit(self, limit: int) -> int:
        return min(self.MAX_PAGINATION_LIMIT, limit) if limit else limit


class CoinexCCXTAdapter(exchanges.CCXTAdapter):

    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        self.adapt_amount_from_filled_or_cost(fixed)
        try:
            if fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] is None:
                fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = \
                    trading_enums.OrderStatus.CLOSED.value
            # from https://docs.coinex.com/api/v2/enum#order_status
            elif fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == "part_filled":
                # order partially executed (still pending)
                fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = \
                    trading_enums.OrderStatus.OPEN.value
            elif fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == "part_canceled":
                # order partially executed and then canceled
                fixed[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = \
                    trading_enums.OrderStatus.CANCELED.value
        except KeyError:
            pass
        return fixed

    def fix_trades(self, raw, **kwargs):
        raw = super().fix_trades(raw, **kwargs)
        for trade in raw:
            info = trade[ccxt_constants.CCXT_INFO]
            # fees are not parsed by ccxt
            fee = trade[trading_enums.ExchangeConstantsOrderColumns.FEE.value] or {}
            if not fee.get(trading_enums.FeePropertyColumns.CURRENCY.value):
                fee[trading_enums.FeePropertyColumns.CURRENCY.value] = info.get("fee_ccy")
            if not fee.get(trading_enums.FeePropertyColumns.COST.value):
                fee[trading_enums.FeePropertyColumns.COST.value] = info.get("fee")
            trade[trading_enums.ExchangeConstantsOrderColumns.FEE.value] = fee
            self._register_exchange_fees(trade)
        return raw

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed
