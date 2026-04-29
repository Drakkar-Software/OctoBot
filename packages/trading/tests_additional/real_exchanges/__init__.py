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
import contextlib
import dotenv
import os
import mock

import octobot_commons.constants as commons_constants
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.tests.test_config as test_config
import octobot_trading.api as api
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.exchanges.util.exchange_util


LOADED_EXCHANGE_CREDS_ENV_VARIABLES = False


@contextlib.asynccontextmanager
async def get_exchange_manager(exchange_name, config=None, authenticated=False, market_filter=None, uses_tentacle=False):
    config = {**test_config.load_test_config(), **config} if config else test_config.load_test_config()
    if exchange_name not in config[commons_constants.CONFIG_EXCHANGES]:
        config[commons_constants.CONFIG_EXCHANGES][exchange_name] = {}
    if authenticated:
        config[commons_constants.CONFIG_EXCHANGES][exchange_name].update(_get_exchange_auth_details(
            exchange_name
        ))
    exchange_manager_instance = exchanges.ExchangeManager(config, exchange_name)
    exchange_manager_instance.market_filter = market_filter
    if config[commons_constants.CONFIG_EXCHANGES][exchange_name]. \
       get(commons_constants.CONFIG_EXCHANGE_TYPE, enums.ExchangeTypes.SPOT.value) == enums.ExchangeTypes.FUTURE.value:
        exchange_manager_instance.is_future = True
    if not uses_tentacle:
        # don't use exchange specific tentacles, even if they are available
        with mock.patch.object(
            octobot_trading.exchanges.util.exchange_util, 
            "search_exchange_class_from_exchange_name", 
            mock.Mock(return_value=exchanges.DefaultRestExchange)
        ) as search_exchange_class_from_exchange_name_mock:
            await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
            assert search_exchange_class_from_exchange_name_mock.call_count > 0
    else:
        # allow the use of exchange specific tentacles
        await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    except errors.UnreachableExchange as err:
        raise errors.UnreachableExchange(f"{exchange_name} can't be reached, it is either offline or you are not connected "
                                         "to the internet (or a proxy is preventing connecting to this exchange).") \
            from err
    finally:
        await exchange_manager_instance.stop()
        api.cancel_ccxt_throttle_task()
        # let updaters gracefully shutdown
        await asyncio_tools.wait_asyncio_next_cycle()


def _load_exchange_creds_env_variables_if_necessary():
    global LOADED_EXCHANGE_CREDS_ENV_VARIABLES
    if not LOADED_EXCHANGE_CREDS_ENV_VARIABLES:
        # load environment variables from .env file if exists
        dotenv_path = os.getenv("EXCHANGE_TESTS_DOTENV_PATH", os.path.dirname(os.path.abspath(__file__)))
        dotenv.load_dotenv(os.path.join(dotenv_path, ".env"), verbose=False)
        LOADED_EXCHANGE_CREDS_ENV_VARIABLES = True


def _get_exchange_auth_details(exchange_name):
    _load_exchange_creds_env_variables_if_necessary()
    return {
        commons_constants.CONFIG_EXCHANGE_KEY:
            _get_exchange_credential_from_env(exchange_name, commons_constants.CONFIG_EXCHANGE_KEY),
        commons_constants.CONFIG_EXCHANGE_SECRET:
            _get_exchange_credential_from_env(exchange_name, commons_constants.CONFIG_EXCHANGE_SECRET),
        commons_constants.CONFIG_EXCHANGE_PASSWORD:
            _get_exchange_credential_from_env(exchange_name, commons_constants.CONFIG_EXCHANGE_PASSWORD),
    }


def _get_exchange_credential_from_env(exchange_name, cred_suffix):
    # for bybit api key: get BYBIT_KEY (as encrypted value)
    # for bybit api password: get BYBIT_PASSWORD (as encrypted value)
    # for bybit api secret: get BYBIT_SECRET (as encrypted value)
    return os.getenv(f"{exchange_name}_{cred_suffix.split('-')[-1]}".upper(), None)
