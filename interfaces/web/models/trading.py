#  Drakkar-Software OctoBot
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

from interfaces import get_bot


def get_exchange_time_frames(exchange_name):
    for exchange in get_bot().get_exchanges_list().values():
        if not exchange_name or exchange.get_name() == exchange_name:
            return exchange.get_exchange_manager().get_config_time_frame(), exchange.get_name()
    return [], ""


def get_evaluation(symbol, exchange_name):
    try:
        if exchange_name:
            for exchange in get_bot().get_exchanges_list().values():
                if exchange.get_name() == exchange_name:
                    symbol_evaluator = get_bot().get_symbol_evaluator_list()[symbol]
                    return (
                        ",".join([
                            f"{dec.get_state().name}: {round(dec.get_final_eval(), 4)}"
                            if dec.get_state() is not None else "N/A"
                            for dec in symbol_evaluator.get_deciders(exchange)
                        ])
                    )
    except KeyError:
        return "N/A"
