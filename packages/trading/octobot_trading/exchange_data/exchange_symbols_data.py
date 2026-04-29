#  Drakkar-Software OctoBot-Trading
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
import decimal

import octobot_commons.logging as logging

import octobot_trading.exchange_data.exchange_symbol_data as exchange_symbol_data_import
import octobot_trading.exchanges
import octobot_trading.enums as enums
import octobot_trading.exchange_data.markets.markets_manager as markets_manager

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges.util.exchange_data as exchange_data_import


class ExchangeSymbolsData:
    def __init__(self, exchange_manager):
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = exchange_manager
        self.exchange: octobot_trading.exchanges.RestExchange = exchange_manager.exchange
        self.config: dict[str, typing.Any] = exchange_manager.config
        self.exchange_symbol_data: dict[str, exchange_symbol_data_import.ExchangeSymbolData] = {}

        self.markets_manager: markets_manager.MarketsManager = markets_manager.MarketsManager()

    def initialize_from_exchange_data(
        self, exchange_data: "exchange_data_import.ExchangeData", price_by_symbol: dict[str, float]
    ) -> None:
        """
        Initialize prices from exchange data.
        """
        for market in exchange_data.markets:
            price = price_by_symbol.get(market.symbol)
            if price is not None:
                self.get_exchange_symbol_data(market.symbol).prices_manager.set_mark_price(
                    decimal.Decimal(str(price)), enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value
                )

    async def stop(self):
        self.exchange_manager = None # type: ignore
        self.exchange = None # type: ignore
        for exchange_symbol_data in self.exchange_symbol_data.values():
            exchange_symbol_data.stop()
        self.exchange_symbol_data = {}

    def get_exchange_symbol_data(self, symbol, allow_creation=True) -> exchange_symbol_data_import.ExchangeSymbolData:
        try:
            return self.exchange_symbol_data[symbol]
        except KeyError as e:
            if allow_creation:
                # warning: should only be called in the async loop thread
                self.exchange_symbol_data[symbol] = exchange_symbol_data_import.ExchangeSymbolData(self.exchange_manager, symbol)
                return self.exchange_symbol_data[symbol]
            raise e
