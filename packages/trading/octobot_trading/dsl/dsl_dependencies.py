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
import dataclasses
import typing

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges


@dataclasses.dataclass
class SymbolDependency(dsl_interpreter.InterpreterDependency):
    symbol: str
    alias: typing.Optional[str] = None
    time_frame: typing.Optional[str] = None

    def resolve_symbol(
        self, exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager]
    ):
        if exchange_manager is not None:
            unified_symbol = exchange_manager.get_exchange_symbol(self.symbol, error_on_missing=False)
            if unified_symbol != self.symbol:
                self.alias = self.symbol
                self.symbol = unified_symbol

    def unresolve_symbol(self):
        if self.alias is not None:
            self.symbol = self.alias
            self.alias = None


@dataclasses.dataclass(unsafe_hash=True)
class CopyTradingDependency(dsl_interpreter.InterpreterDependency):
    strategy_id: str = dataclasses.field(hash=True)
    refresh_required: bool = dataclasses.field(hash=True)


async def resolve_missing_dependencies(
    dependencies: typing.Iterable[SymbolDependency],
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
) -> None:
    unresolved_dependencies = set(
        dependency
        for dependency in dependencies
        if dependency.alias and not dependency.symbol
    )
    missing_symbols = set(
        dependency.alias
        for dependency in unresolved_dependencies
    )
    if not missing_symbols:
        return
    if exchange_manager.exchange.lazy_load_markets():
        await exchange_manager.exchange.load_markets_for_symbols(list(missing_symbols))
        for dependency in unresolved_dependencies:
            dependency.unresolve_symbol()
            dependency.resolve_symbol(exchange_manager)
    else:
        raise ValueError(f"Exchange {exchange_manager.exchange.name} does not support lazy load markets")


async def resolve_missing_dependencies_if_required(
    dependencies: typing.Iterable[SymbolDependency],
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
) -> None:
    if not exchange_manager.exchange.supports_all_symbols_listing():
        await resolve_missing_dependencies(dependencies, exchange_manager)
