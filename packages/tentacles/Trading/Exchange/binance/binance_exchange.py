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
import enum

import ccxt

import octobot_commons.constants as commons_constants
import octobot_commons.symbols as symbols

import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.errors as errors
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.util as trading_util
import octobot_trading.personal_data as personal_data


class BinanceMarkets(enum.Enum):
    SPOT = "spot"
    LINEAR = "linear"
    INVERSE = "inverse"


class Binance(exchanges.RestExchange):
    DESCRIPTION = ""
    FIX_MARKET_STATUS = True

    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    # should be fetched using recent trades.
    SUPPORTS_SET_MARGIN_TYPE_ON_OPEN_POSITIONS = False  # set False when the exchange refuses to change margin type
    # when an associated position is open
    # binance {"code":-4048,"msg":"Margin type cannot be changed if there exists position."}
    # Set True when the "limit" param when fetching order books is taken into account
    SUPPORTS_CUSTOM_LIMIT_ORDER_BOOK_FETCH = True
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True
    ADJUST_FOR_TIME_DIFFERENCE = True  # set True when the client needs to adjust its requests for time difference with the server

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

    # text content of errors due to orders not found errors
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # Binance ex: DDoSProtection('binance {"code":-2015,"msg":"Invalid API-key, IP, or permissions for action."}')
        ("key", "permissions for action"),
    ]
    # text content of errors due to traded assets for account
    EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # Binance ex: InvalidOrder binance {"code":-2010,"msg":"This symbol is not permitted for this account."}
        ("symbol", "not permitted", "for this account"),
        # ccxt.base.errors.InvalidOrder: binance {"code":-2010,"msg":"Symbol not whitelisted for API key."}
        ("symbol", "not whitelisted"),
    ]
    # text content of errors due to a closed position on the exchange. Relevant for reduce-only orders
    EXCHANGE_CLOSED_POSITION_ERRORS: typing.List[typing.Iterable[str]] = [
        # doesn't seem to happen on binance
    ]
    # text content of errors due to an order that would immediately trigger if created. Relevant for stop losses
    EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS: typing.List[typing.Iterable[str]] = [
        # binance {"code":-2021,"msg":"Order would immediately trigger."}
        ("order would immediately trigger", )
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('Unknown order sent', )
    ]
    # set when the exchange can allow users to pay fees in a custom currency (ex: BNB on binance)
    LOCAL_FEES_CURRENCIES: typing.List[str] = ["BNB"]

    # Name of the price param to give ccxt to edit a stop loss
    STOP_LOSS_EDIT_PRICE_PARAM = ccxt_enums.ExchangeOrderCCXTUnifiedParams.STOP_PRICE.value

    BUY_STR = "BUY"
    SELL_STR = "SELL"
    INVERSE_TYPE = "inverse"
    LINEAR_TYPE = "linear"

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        self._futures_account_types = self._infer_account_types(exchange_manager)
        super().__init__(config, exchange_manager, exchange_config_by_exchange, connector_class=connector_class)

    @classmethod
    def get_name(cls):
        return 'binance'

    def get_adapter_class(self):
        return BinanceCCXTAdapter

    @staticmethod
    def get_default_reference_market(exchange_name: str) -> str:
        return "USDC"

    def supports_native_edit_order(self, order_type: trading_enums.TraderOrderType) -> bool:
        # return False when default edit_order can't be used and order should always be canceled and recreated instead
        is_stop = order_type in (
            trading_enums.TraderOrderType.STOP_LOSS, trading_enums.TraderOrderType.STOP_LOSS_LIMIT
        )
        if self.exchange_manager.is_future:
            # replace not supported in futures stop orders
            return not is_stop

    async def get_account_id(self, **kwargs: dict) -> str:
        try:
            with self.connector.error_describer(True):
                if self.exchange_manager.is_future:
                    raw_binance_balance = await self.connector.client.fapiPrivateV3GetBalance()
                    # accountAlias = unique account code
                    # from https://binance-docs.github.io/apidocs/futures/en/#futures-account-balance-v3-user_data
                    return raw_binance_balance[0]["accountAlias"]
                else:
                    raw_balance = await self.connector.client.fetch_balance()
                    return raw_balance[ccxt_constants.CCXT_INFO]["uid"]
        except (KeyError, IndexError):
            # should not happen
            raise

    def get_max_orders_count(self, symbol: str, order_type: trading_enums.TraderOrderType) -> int:
        """
        from:
            https://developers.binance.com/docs/derivatives/usds-margined-futures/common-definition#max_num_orders
            https://developers.binance.com/docs/binance-spot-api-docs/filters#max_num_orders
        [
            {"filterType": "PRICE_FILTER", "maxPrice": "1000000.00000000", "minPrice": "0.01000000", "tickSize": "0.01000000"}, 
            {"filterType": "LOT_SIZE", "maxQty": "9000.00000000", "minQty": "0.00001000", "stepSize": "0.00001000"}, 
            {"filterType": "ICEBERG_PARTS", "limit": "10"}, 
            {"filterType": "MARKET_LOT_SIZE", "maxQty": "115.46151096", "minQty": "0.00000000", "stepSize": "0.00000000"}, 
            {"filterType": "TRAILING_DELTA", "maxTrailingAboveDelta": "2000", "maxTrailingBelowDelta": "2000", "minTrailingAboveDelta": "10", "minTrailingBelowDelta": "10"}, 
            {"askMultiplierDown": "0.2", "askMultiplierUp": "5", "avgPriceMins": "5", "bidMultiplierDown": "0.2", "bidMultiplierUp": "5", "filterType": "PERCENT_PRICE_BY_SIDE"}, 
            {"applyMaxToMarket": False, "applyMinToMarket": True, "avgPriceMins": "5", "filterType": "NOTIONAL", "maxNotional": "9000000.00000000", "minNotional": "5.00000000"}, 
            {"filterType": "MAX_NUM_ORDERS", "maxNumOrders": "200"}, 
            {"filterType": "MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": "5"}
        ]
        => usually:
            - SPOT: MAX_NUM_ORDERS 200 MAX_NUM_ALGO_ORDERS 5
            - FUTURES: MAX_NUM_ORDERS 200 MAX_NUM_ALGO_ORDERS 10
        """
        try:
            market_status = self.get_market_status(symbol, with_fixer=False)
            filters = market_status[ccxt_constants.CCXT_INFO]["filters"]
            key = "MAX_NUM_ALGO_ORDERS" if personal_data.is_stop_order(order_type) else "MAX_NUM_ORDERS"
            value_key = "maxNumAlgoOrders" if personal_data.is_stop_order(order_type) else "maxNumOrders"
            fallback_value_key = "limit"    # sometimes, "limit" is the key
            for filter_element in filters:
                if filter_element.get("filterType") == key:
                    key = value_key if value_key in filter_element else fallback_value_key
                    return int(filter_element[key])
            raise ValueError(f"{key} not found in filters: {filters}")
        except Exception as err:
            default_count = super().get_max_orders_count(symbol, order_type)
            self.logger.exception(
                err, True, f"Error when computing max orders count: {err}. Using default value: {default_count}"
            )
            return default_count

    def uses_demo_trading_instead_of_sandbox(self) -> bool:
        if self.exchange_manager.is_future:
            return True
        return False

    def _infer_account_types(self, exchange_manager):
        account_types = []
        symbol_counts = trading_util.get_symbol_types_counts(exchange_manager.config, True)
        # only enable the trading type with the majority of asked symbols
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        linear_count = symbol_counts.get(trading_enums.FutureContractType.LINEAR_PERPETUAL.value, 0)
        inverse_count = symbol_counts.get(trading_enums.FutureContractType.INVERSE_PERPETUAL.value, 0)
        if linear_count >= inverse_count:
            account_types.append(self.LINEAR_TYPE)   # allows to fetch linear markets
            if inverse_count:
                exchange_manager.logger.error(
                    f"For now, due to the inverse and linear portfolio split on Binance Futures, OctoBot only "
                    f"supports either linear or inverse trading at a time. Ignoring {inverse_count} inverse "
                    f"futures trading pair as {linear_count} linear futures trading pairs are enabled."
                )
        else:
            account_types.append(self.INVERSE_TYPE)  # allows to fetch inverse markets
            if linear_count:
                exchange_manager.logger.error(
                    f"For now, due to the inverse and linear portfolio split on Binance Futures, OctoBot only "
                    f"supports either linear or inverse trading at a time. Ignoring {linear_count} linear "
                    f"futures trading pair as {inverse_count} inverse futures trading pairs are enabled."
                )
        return account_types

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    def get_additional_connector_config(self):
        config = {
            ccxt_constants.CCXT_OPTIONS: {
                "quoteOrderQty": True,  # enable quote conversion for market orders
                "recvWindow": 60000,    # default is 10000, avoid time related issues
                "fetchPositions": "account",    # required to fetch empty positions as well
                "filterClosed": False,  # return empty positions as well
            }
        }
        if self.FETCH_MIN_EXCHANGE_MARKETS:
            config[ccxt_constants.CCXT_OPTIONS][ccxt_constants.CCXT_FETCH_MARKETS] = (
                [
                    BinanceMarkets.LINEAR.value, BinanceMarkets.INVERSE.value
                ] if self.exchange_manager.is_future else [BinanceMarkets.SPOT.value]
            )
        return config

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        signature_identifier = "signature="
        return bool(
            (
                url
                and signature_identifier in url # for GET & DELETE requests
            ) or (
                body
                and signature_identifier in body # for other requests
            )
        )

    async def get_balance(self, **kwargs: dict):
        if self.exchange_manager.is_future:
            balance = []
            for account_type in self._futures_account_types:
                balance.append(await super().get_balance(**kwargs, subType=account_type))
            # todo remove this and use both types when exchange-side multi portfolio is enabled
            # there will only be 1 balance as both linear and inverse are not supported simultaneously
            # (only 1 _futures_account_types is allowed for now)
            return balance[0]
        return await super().get_balance(**kwargs)

    def get_order_additional_params(self, order) -> dict:
        params = {}
        if self.exchange_manager.is_future:
            params["reduceOnly"] = order.reduce_only
        return params

    def order_request_kwargs_factory(
        self, 
        exchange_order_id: str, 
        order_type: typing.Optional[trading_enums.TraderOrderType] = None, 
        **kwargs
    ) -> dict:
        params = kwargs or {}
        try:
            if "stop" not in params:
                order_type = (
                    order_type or 
                    self.exchange_manager.exchange_personal_data.orders_manager.get_order(
                        None, exchange_order_id=exchange_order_id
                    ).order_type
                )
                params["stop"] = (
                    personal_data.is_stop_order(order_type)
                    or personal_data.is_take_profit_order(order_type)
                )
        except KeyError as err:
            self.logger.warning(
                f"Order {exchange_order_id} not found in order manager: considering it a regular (no stop/take profit) order {err}"
            )
        return params

    def fetch_stop_order_in_different_request(self, symbol: str) -> bool:
        # Override in tentacles when stop orders need to be fetched in a separate request from CCXT
        # Binance futures uses the algo orders endpoint for stop orders (but not for inverse orders)
        return self.exchange_manager.is_future and not symbols.parse_symbol(symbol).is_inverse()

    async def _create_market_sell_order(
        self, symbol, quantity, price=None, reduce_only: bool = False, params=None
        ) -> dict:
        # force price to None to avoid selling using quote amount (force market sell quantity in base amount)
        return await super()._create_market_sell_order(
            symbol, quantity, price=None, reduce_only=reduce_only, params=params
        )

    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: trading_enums.TakeProfitStopLossMode):
        """
        take profit / stop loss mode does not exist on binance futures
        """

    async def get_positions(self, symbols=None, **kwargs: dict) -> list:
        positions = []
        if "useV2" not in kwargs:
            kwargs["useV2"] = True  #V2 api is required to fetch empty positions (not retured in V3)
        if "subType" in kwargs:
            return _filter_positions(await super().get_positions(symbols=symbols, **kwargs))
        for account_type in self._futures_account_types:
            kwargs["subType"] = account_type
            positions += await super().get_positions(symbols=symbols, **kwargs)
        return _filter_positions(positions)

    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        # fetchPosition() supports option markets only
        # => use get_positions
        return (await self.get_positions(symbols=[symbol], **kwargs))[0]

    async def get_symbol_leverage(self, symbol: str, **kwargs: dict):
        """
        :param symbol: the symbol
        :return: the current symbol leverage multiplier
        """
        # leverage is in position
        return self.connector.adapter.adapt_leverage(await self.get_position(symbol))

    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[dict[str, dict]]:
        if "subType" in kwargs or not self.exchange_manager.is_future:
            return await super().get_all_currencies_price_ticker(**kwargs)
        # futures with unspecified subType: fetch both linear and inverse tickers
        linear_tickers = await super().get_all_currencies_price_ticker(subType=self.LINEAR_TYPE, **kwargs)
        inverse_tickers = await super().get_all_currencies_price_ticker(subType=self.INVERSE_TYPE, **kwargs)
        return {**linear_tickers, **inverse_tickers}

    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict):
        """
        Set the symbol margin type
        :param symbol: the symbol
        :param isolated: when False, margin type is cross, else it's isolated
        :return: the update result
        """
        try:
            return await super().set_symbol_margin_type(symbol, isolated, **kwargs)
        except ccxt.ExchangeError as err:
            raise errors.NotSupported(err) from err


class BinanceCCXTAdapter(exchanges.CCXTAdapter):
    STOP_ORDERS = [
        "stop_market", "stop", # futures
        "stop_loss", "stop_loss_limit"  # spot
    ]
    TAKE_PROFITS_ORDERS = [
        "take_profit_market", "take_profit_limit",    # futures
        "take_profit"  # spot
    ]
    BINANCE_DEFAULT_FUNDING_TIME = 8 * commons_constants.HOURS_TO_SECONDS

    def fix_order(self, raw, symbol=None, **kwargs):
        fixed = super().fix_order(raw, symbol=symbol, **kwargs)
        self._adapt_order_type(fixed)
        if fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value, None) == "PENDING_NEW":
            # PENDING_NEW order are old orders on binance and should be considered as open
            fixed[ccxt_enums.ExchangeOrderCCXTColumns.STATUS.value] = trading_enums.OrderStatus.OPEN.value
        return fixed

    def _adapt_order_type(self, fixed):
        order_info = fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.INFO.value, {})
        info_order_type = (order_info.get("type", {}) or order_info.get("orderType", None) or "").lower()
        is_stop = info_order_type in self.STOP_ORDERS
        is_tp = info_order_type in self.TAKE_PROFITS_ORDERS
        if is_stop or is_tp:
            if trigger_price := fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.TRIGGER_PRICE.value, None):
                selling = (
                    fixed.get(ccxt_enums.ExchangeOrderCCXTColumns.SIDE.value, None)
                    == trading_enums.TradeOrderSide.SELL.value
                )
                updated_type = trading_enums.TradeOrderType.UNKNOWN.value
                trigger_above = False
                if is_stop:
                    updated_type = trading_enums.TradeOrderType.STOP_LOSS.value
                    # force price to trigger price
                    fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = trigger_price
                    trigger_above = not selling # sell stop loss triggers when price is lower than target
                elif is_tp:
                    # updated_type = trading_enums.TradeOrderType.TAKE_PROFIT.value
                    # take profits are not yet handled as such: consider them as limit orders
                    updated_type = trading_enums.TradeOrderType.LIMIT.value # waiting for TP handling
                    if not fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]:
                        fixed[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = trigger_price # waiting for TP handling
                    trigger_above = selling # sell take profit triggers when price is higher than target
                else:
                    self.logger.error(
                        f"Unknown [{self.connector.exchange_manager.exchange_name}] order type, order: {fixed}"
                    )
                # stop loss and take profits are not tagged as such by ccxt, force it
                fixed[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] = updated_type
                fixed[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value] = trigger_above
            else:
                self.logger.error(
                    f"Unknown [{self.connector.exchange_manager.exchange_name}] order: stop order "
                    f"with no trigger price, order: {fixed}"
                )
        return fixed

    def fix_trades(self, raw, **kwargs):
        raw = super().fix_trades(raw, **kwargs)
        for trade in raw:
            trade[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = trading_enums.OrderStatus.CLOSED.value
        return raw

    def parse_position(self, fixed, force_empty=False, **kwargs):
        try:
            return super().parse_position(fixed, force_empty=force_empty, **kwargs)
        except decimal.InvalidOperation:
            # on binance, positions might be invalid (ex: LUNAUSD_PERP as None contact size)
            return None

    def parse_leverage(self, fixed, **kwargs):
        parsed = super().parse_leverage(fixed, **kwargs)
        # on binance fixed is a parsed position
        parsed[trading_enums.ExchangeConstantsLeveragePropertyColumns.LEVERAGE.value] = \
            fixed[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value]
        return parsed

    def parse_funding_rate(self, fixed, from_ticker=False, **kwargs):
        """
        Binance last funding time is not provided
        To obtain the last_funding_time :
        => timestamp(next_funding_time) - timestamp(BINANCE_DEFAULT_FUNDING_TIME)
        """
        if from_ticker:
            # no funding info in ticker
            return {}
        else:
            funding_dict = super().parse_funding_rate(fixed, from_ticker=from_ticker, **kwargs)
            funding_next_timestamp = float(
                funding_dict.get(trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value, 0)
            )
            # patch LAST_FUNDING_TIME in tentacle
            funding_dict.update({
                trading_enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                    max(funding_next_timestamp - self.BINANCE_DEFAULT_FUNDING_TIME, 0)
            })
        return funding_dict


def _filter_positions(positions):
    return [
        position
        for position in positions
        if position is not None
    ]
