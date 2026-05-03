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

    """
    Deprecated constants kept as comments for reference.
    # text content of errors due to orders not found errors
    # EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # Binance ex: DDoSProtection('binance {"code":-2015,"msg":"Invalid API-key, IP, or permissions for action."}')
        ("key", "permissions for action"),
    ]
    # text content of errors due to traded assets for account
    # EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = [
        # Binance ex: InvalidOrder binance {"code":-2010,"msg":"This symbol is not permitted for this account."}
        ("symbol", "not permitted", "for this account"),
        # ccxt.base.errors.InvalidOrder: binance {"code":-2010,"msg":"Symbol not whitelisted for API key."}
        ("symbol", "not whitelisted"),
    ]
    # text content of errors due to a closed position on the exchange. Relevant for reduce-only orders
    # EXCHANGE_CLOSED_POSITION_ERRORS: typing.List[typing.Iterable[str]] = [
        # doesn't seem to happen on binance
    ]
    # text content of errors due to an order that would immediately trigger if created. Relevant for stop losses
    # EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS: typing.List[typing.Iterable[str]] = [
        # binance {"code":-2021,"msg":"Order would immediately trigger."}
        ("order would immediately trigger", )
    ]
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    # EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = [
        ('Unknown order sent', )
    ]
    """
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
            ccxt_constants.CCXT_OPTIONS: {}
        }
        if self.FETCH_MIN_EXCHANGE_MARKETS:
            config[ccxt_constants.CCXT_OPTIONS][ccxt_constants.CCXT_FETCH_MARKETS] = (
                [
                    BinanceMarkets.LINEAR.value, BinanceMarkets.INVERSE.value
                ] if self.exchange_manager.is_future else [BinanceMarkets.SPOT.value]
            )
        return config

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


def _filter_positions(positions):
    return [
        position
        for position in positions
        if position is not None
    ]
