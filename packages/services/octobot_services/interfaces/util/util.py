#  Drakkar-Software OctoBot-Services
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
import threading

import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants

import octobot_trading.api as trading_api

import octobot_services.interfaces as interfaces


def get_exchange_managers(bot_api=None, independent_backtesting=None, trading_exchanges_only=True):
    if bot_api is not None:
        return _filter_exchange_manager(trading_api.get_exchange_managers_from_exchange_ids(
            bot_api.get_exchange_manager_ids()), trading_exchanges_only)
    elif independent_backtesting is not None:
        try:
            import octobot.api as api
            return _filter_exchange_manager(
                trading_api.get_exchange_managers_from_exchange_ids(
                    api.get_independent_backtesting_exchange_manager_ids(independent_backtesting)),
                trading_exchanges_only)
        except ImportError:
            logging.get_logger("octobot_services/interfaces/util/util.py").error(
                "get_exchange_managers requires OctoBot package installed")
    else:
        return _filter_exchange_manager(interfaces.AbstractInterface.get_exchange_managers(), trading_exchanges_only)


def _filter_exchange_manager(exchange_managers, trading_exchanges_only):
    if trading_exchanges_only:
        return trading_api.get_trading_exchanges(exchange_managers)
    return exchange_managers


def run_in_bot_main_loop(coroutine, blocking=True, log_exceptions=True,
                         timeout=commons_constants.DEFAULT_FUTURE_TIMEOUT):
    if blocking:
        return interfaces.get_bot_api().run_in_main_asyncio_loop(coroutine, log_exceptions=log_exceptions,
                                                                 timeout=timeout)
    else:
        threading.Thread(
            target=interfaces.get_bot_api().run_in_main_asyncio_loop,
            name=f"run_in_bot_main_loop {coroutine.__name__}",
            args=(coroutine,),
            kwargs={"timeout": timeout}
         ).start()


def run_in_bot_async_executor(coroutine):
    return interfaces.get_bot_api().run_in_async_executor(coroutine)
