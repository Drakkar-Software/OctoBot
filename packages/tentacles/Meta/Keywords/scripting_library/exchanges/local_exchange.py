import contextlib
import typing

import octobot_trading.exchanges as exchanges
import octobot_trading.util.test_tools.exchange_data as exchange_data_import

import tentacles.Meta.Keywords.scripting_library.configuration.profile_data_configuration as profile_data_configuration


@contextlib.asynccontextmanager
async def local_ccxt_exchange_manager(
    exchange_data: exchange_data_import.ExchangeData,
    tentacles_setup_config,
    exchange_config_by_exchange: typing.Optional[dict[str, dict]] = None,
):
    exchange_config = profile_data_configuration.get_exchange_config(
        exchange_data, tentacles_setup_config, exchange_config_by_exchange, False
    )
    ignore_config = not profile_data_configuration.is_auth_required_exchanges(
        exchange_data, tentacles_setup_config, exchange_config_by_exchange
    )
    async with exchanges.get_local_exchange_manager(
        exchange_data.exchange_details.name, exchange_config, tentacles_setup_config,
        exchange_data.auth_details.sandboxed, ignore_config=ignore_config,
        use_cached_markets=True,
        is_broker_enabled=exchange_data.auth_details.broker_enabled,
        exchange_config_by_exchange=exchange_config_by_exchange,
        disable_unauth_retry=True,  # unauth fallback is never required here, if auth fails, this should fail
    ) as exchange_manager:
        yield exchange_manager
