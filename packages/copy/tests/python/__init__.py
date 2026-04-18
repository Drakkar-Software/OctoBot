#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or
#  (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing

import octobot_commons.symbols as commons_symbols


def ensure_traded_symbol_pairs(exchange_manager, symbols: typing.Iterable[str]) -> None:
    """
    Config may list pairs, but exchange init can drop them when symbol_exists is false.
    The copy rebalance planner only keeps assets whose base appears in traded_symbols.
    """
    symbols_set = set(symbols)
    if not symbols_set:
        return
    exchange_config = exchange_manager.exchange_config
    if symbols_set.issubset(set(exchange_config.traded_symbol_pairs)):
        return
    exchange_config.traded_symbol_pairs = sorted(
        set(exchange_config.traded_symbol_pairs) | symbols_set
    )
    exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol) for symbol in exchange_config.traded_symbol_pairs
    ]
    exchange_config.watched_pairs = sorted(
        set(exchange_config.watched_pairs) | symbols_set
    )

    for symbol in symbols_set:
        if symbol not in exchange_manager.client_symbols:
            exchange_manager.client_symbols.append(symbol)
