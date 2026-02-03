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
import asyncio
import contextlib
try:
    from aiohttp_socks import ProxyConnectionError
except ImportError:
    # local mock in case aiohttp_socks is not available
    class ProxyConnectionError(Exception):
        pass
import os
import ssl
import aiohttp
import copy
import logging
import typing
import ccxt
import ccxt.pro as ccxt_pro
import ccxt.async_support as async_ccxt

import octobot_commons
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.logging as commons_logging
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache
import octobot_trading.exchanges.config.proxy_config as proxy_config_import
import octobot_trading.exchanges.config.exchange_credentials_data as exchange_credentials_data
import octobot_trading.exchanges.util.exchange_util as exchange_util


def create_client(
    exchange_class, exchange_manager, logger, options, headers,
    additional_config, should_authenticate, unauthenticated_exchange_fallback=None,
    keys_adapter=None, allow_request_counter: bool = True
) -> tuple[async_ccxt.Exchange, bool]:
    """
    Exchange instance creation
    :return: the created ccxt (pro, async or sync) client
    """
    is_authenticated = False
    should_be_authenticated_exchange = should_authenticate and not exchange_manager.is_backtesting
    if not exchange_manager.exchange_only:
        # avoid logging version on temporary exchange_only exchanges
        exchange_type = exchange_util.get_exchange_type(exchange_manager)
        logger.info(
            f"Creating {'' if should_be_authenticated_exchange else 'un'}authenticated {exchange_class.__name__} "
            f"{exchange_type.name} exchange with ccxt in version {ccxt.__version__}"
        )
    if exchange_manager.ignore_config or exchange_manager.check_config(exchange_manager.exchange_name):
        try:
            creds: exchange_credentials_data.ExchangeCredentialsData = (
                exchange_manager.get_exchange_credentials(exchange_manager.exchange_name)
            )
            if keys_adapter:
                creds = keys_adapter(creds)
            if not (creds.has_credentials()) and not exchange_manager.is_simulated and not exchange_manager.ignore_config:
                logger.warning(f"No exchange API key set for {exchange_manager.exchange_name}. "
                               f"Enter your account details to enable real trading on this exchange.")
            if should_be_authenticated_exchange:
                client = instantiate_exchange(
                    exchange_class,
                    _get_client_config(
                        exchange_class, options, headers, additional_config, creds,
                    ),
                    exchange_manager.exchange_name,
                    exchange_manager.proxy_config,
                    allow_request_counter=allow_request_counter
                )
                is_authenticated = True
                if exchange_manager.check_credentials:
                    client.check_required_credentials()
            else:
                client = instantiate_exchange(
                    exchange_class,
                    _get_client_config(exchange_class, options, headers, additional_config),
                    exchange_manager.exchange_name,
                    exchange_manager.proxy_config,
                    allow_request_counter=allow_request_counter
                )
        except (ccxt.AuthenticationError, Exception) as e:
            if unauthenticated_exchange_fallback is None:
                return get_unauthenticated_exchange(
                    exchange_class, options, headers, additional_config,
                    exchange_manager.exchange_name, exchange_manager.proxy_config
                ), False
            return unauthenticated_exchange_fallback(e), False
    else:
        client = get_unauthenticated_exchange(
            exchange_class, options, headers, additional_config,
            exchange_manager.exchange_name, exchange_manager.proxy_config
        )
        logger.error("configuration issue: missing login information !")
    client.logger.setLevel(logging.INFO)
    return client, is_authenticated


async def close_client(client):
    await client.close()
    client.markets = {}
    client.markets_by_id = {}
    client.ids = []
    client.last_json_response = {}
    client.last_http_response = ""
    client.last_response_headers = {}
    client.markets_loading = None
    client.currencies = {}
    client.baseCurrencies = {}
    client.quoteCurrencies = {}
    client.currencies_by_id = {}
    client.codes = []
    client.symbols = {}
    client.accounts = []
    client.accounts_by_id = {}
    client.ohlcvs = {}
    client.trades = {}
    client.orderbooks = {}


def get_unauthenticated_exchange(
    exchange_class, options, headers, additional_config, identifier: str, proxy_config: proxy_config_import.ProxyConfig
) -> async_ccxt.Exchange:
    return instantiate_exchange(
        exchange_class,
        _get_client_config(exchange_class, options, headers, additional_config),
        identifier,
        proxy_config
    )


def instantiate_exchange(
    exchange_class, config: dict, identifier: str, proxy_config: proxy_config_import.ProxyConfig,
    allow_request_counter: bool = True
) -> async_ccxt.Exchange:
    client = exchange_class(config)
    _use_proxy_if_necessary(client, proxy_config)
    if constants.ENABLE_CCXT_REQUESTS_COUNTER and allow_request_counter:
        if proxy_config.socks_proxy or proxy_config.socks_proxy_callback:
            commons_logging.get_logger(__name__).error("socks proxy and request counter can't yet be used together.")
        else:
            _use_request_counter(identifier, client, proxy_config)
    return client


def set_sandbox_mode(exchange_connector, is_sandboxed):
    try:
        if exchange_connector.exchange_manager.exchange.uses_demo_trading_instead_of_sandbox():
            exchange_connector.client.enable_demo_trading(is_sandboxed)
        else:
            exchange_connector.client.set_sandbox_mode(is_sandboxed)
    except ccxt.NotSupported as e:
        default_type = exchange_connector.client.options.get('defaultType', None)
        additional_info = f" in type {default_type}" if default_type else ""
        exchange_connector.logger.warning(f"{exchange_connector.name} does not support sandboxing {additional_info}: {e}")
        # raise exception to stop this exchange and prevent dealing with a real funds exchange
        raise e
    return None


@contextlib.contextmanager
def filtered_fetched_markets(client, market_filter: typing.Callable[[dict], bool]):
    origin_fetch_markets = client.fetch_markets

    async def _filted_fetched_markets(*args, **kwargs):
        all_markets = await origin_fetch_markets(*args, **kwargs)
        filtered_markets = [
            market 
            for market in all_markets
            if market_filter(market)
        ]
        commons_logging.get_logger(__name__).info(
            f"Keeping {len(filtered_markets)} out of {len(all_markets)} fetched markets"
        )
        return filtered_markets
    try:
        client.fetch_markets = _filted_fetched_markets
        yield
    finally:
        client.fetch_markets = origin_fetch_markets


def load_markets_from_cache(client, authenticated_cache: bool, market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None):
    client_key = ccxt_clients_cache.get_client_key(client, authenticated_cache)
    client.set_markets(
        market
        for market in ccxt_clients_cache.get_exchange_parsed_markets(client_key)
        if market_filter is None or market_filter(market)
    )
    if time_difference := ccxt_clients_cache.get_exchange_time_difference(client_key):
        client.options[ccxt_constants.CCXT_TIME_DIFFERENCE] = time_difference


def set_markets_cache(client, authenticated_cache: bool):
    if client.markets:
        client_key = ccxt_clients_cache.get_client_key(client, authenticated_cache)
        ccxt_clients_cache.set_exchange_parsed_markets(
            client_key, copy.deepcopy(list(client.markets.values()))
        )
        if time_difference := client.options.get(ccxt_constants.CCXT_TIME_DIFFERENCE):
            ccxt_clients_cache.set_exchange_time_difference(client_key, time_difference)


def get_ccxt_client_login_options(exchange_manager):
    """
    :return: ccxt client login option dict, can be overwritten to custom exchange login
    """
    if exchange_manager.is_future:
        return {'defaultType': 'future'}
    if exchange_manager.is_margin:
        return {'defaultType': 'margin'}
    return {'defaultType': 'spot'}


def get_symbols(client, active_only) -> set[str]:
    try:
        if active_only:
            return set(
                symbol
                for symbol in client.symbols
                if client.markets.get(symbol, {}).get(
                    enums.ExchangeConstantsMarketStatusColumns.ACTIVE.value, True
                ) in (True, None)
            )
        return set(client.symbols)
    except (AttributeError, TypeError):
        # ccxt exchange load_markets failed
        return set()


def get_time_frames(client):
    try:
        if isinstance(client, ccxt_pro.Exchange):
            # ccxt pro exchanges might have different timeframes in options
            options_time_frames = client.safe_value(client.options, 'timeframes')
            if options_time_frames:
                values = set([
                    time_frame
                    for time_frame in options_time_frames
                    if time_frame_manager.is_time_frame(time_frame)
                ])
                if values:
                    return values
        # use normal client timeframes (values of rest exchange)
        return set(client.timeframes)
    except (AttributeError, TypeError):
        # ccxt exchange describe() is invalid
        return set()


def get_exchange_pair(client, pair) -> str:
    if pair in client.symbols:
        try:
            return client.market(pair)["id"]
        except KeyError:
            pass
    raise ValueError(f'{pair} is not supported')


def get_pair_cryptocurrency(client, pair) -> str:
    if pair in client.symbols:
        try:
            return client.market(pair)["base"]
        except KeyError:
            pass
    raise ValueError(f'{pair} is not supported')


def get_contract_size(client, pair) -> float:
    return get_market_status_contract_size(client.markets[pair])


def get_market_status_contract_size(market_status: dict) :
    return market_status[ccxt_enums.ExchangeConstantsMarketStatusCCXTColumns.CONTRACT_SIZE.value]


def get_fees(market_status) -> dict[str, float]:
    return {
        enums.ExchangeConstantsMarketPropertyColumns.TAKER.value:
            market_status.get(enums.ExchangeConstantsMarketPropertyColumns.TAKER.value,
                              constants.CONFIG_DEFAULT_FEES),
        enums.ExchangeConstantsMarketPropertyColumns.MAKER.value:
            market_status.get(enums.ExchangeConstantsMarketPropertyColumns.MAKER.value,
                              constants.CONFIG_DEFAULT_FEES),
        enums.ExchangeConstantsMarketPropertyColumns.FEE.value:
            market_status.get(enums.ExchangeConstantsMarketPropertyColumns.FEE.value,
                              constants.CONFIG_DEFAULT_FEES)
    }


def add_headers(client, headers_dict):
    """
    Add new headers to ccxt client
    :param headers_dict: the additional header keys and values as dict
    """
    for header_key, header_value in headers_dict.items():
        client.headers[header_key] = header_value


def add_options(client, options_dict):
    """
    Add new options to ccxt client
    :param options_dict: the additional option keys and values as dict
    """
    for option_key, option_value in options_dict.items():
        client.options[option_key] = option_value


def converted_ccxt_common_errors(f):
    async def converted_ccxt_common_errors_wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except ccxt.RateLimitExceeded as err:
            raise errors.RateLimitExceeded(err) from err
        except ccxt.NotSupported as err:
            raise errors.NotSupported(err) from err
    return converted_ccxt_common_errors_wrapper


def _use_proxy_if_necessary(client, proxy_config: proxy_config_import.ProxyConfig):
    client.aiohttp_trust_env = proxy_config.aiohttp_trust_env
    if proxy_config.http_proxy:
        client.http_proxy = proxy_config.http_proxy
    if proxy_config.http_proxy_callback:
        client.http_proxy_callback = proxy_config.http_proxy_callback
    if proxy_config.https_proxy:
        client.https_proxy = proxy_config.https_proxy
    if proxy_config.https_proxy_callback:
        client.https_proxy_callback = proxy_config.https_proxy_callback
    if proxy_config.socks_proxy:
        client.socks_proxy = proxy_config.socks_proxy
    if proxy_config.socks_proxy_callback:
        client.socks_proxy_callback = proxy_config.socks_proxy_callback
    if proxy_config.socks_proxy or proxy_config.socks_proxy_callback:
        # rewrite of async_ccxt.exchange.client.fetch() ProxyConnector creation
        _init_ccxt_client_session_requirements(client)
        proxy_url = proxy_config.get_proxy_url()
        if (client.socks_proxy_sessions is None):
            client.socks_proxy_sessions = {}
        if (proxy_url not in client.socks_proxy_sessions):
            try:
                import aiohttp_socks
                previous_aiohttp_socks_connector = client.aiohttp_socks_connector
                client.aiohttp_socks_connector = aiohttp_socks.ProxyConnector.from_url(
                    proxy_url,
                    # extra args copied from self.open()
                    ssl=client.ssl_context,
                    loop=client.asyncio_loop,
                    enable_cleanup_closed=True
                )
                client.socks_proxy_sessions[proxy_url] = aiohttp.ClientSession(
                    loop=client.asyncio_loop, connector=client.aiohttp_socks_connector,
                    trust_env=client.aiohttp_trust_env
                )
                asyncio.create_task(_close_previous_session_and_connector(
                    None, previous_aiohttp_socks_connector
                ))
            except ImportError as err:
                raise ImportError(
                    "The aiohttp_socks python library is not installed and is required to use a socks proxy"
                ) from err


def _init_ccxt_client_session_requirements(client):
    # from async_ccxt.exchange.client.open()
    if client.asyncio_loop is None:
        client.asyncio_loop = asyncio.get_running_loop()
        client.throttler.loop = client.asyncio_loop

    if client.ssl_context is None:
        # Create our SSL context object with our CA cert file
        client.ssl_context = ssl.create_default_context(cafile=client.cafile) if client.verify else client.verify



def _get_client_config(
    exchange_class, options, headers, additional_config, creds: exchange_credentials_data.ExchangeCredentialsData=None
):
    if creds and creds.auth_token:
        headers["Authorization"] = f"{creds.auth_token_header_prefix or ''}{creds.auth_token}"
    config = {
        'verbose': constants.ENABLE_CCXT_VERBOSE,
        'enableRateLimit': constants.ENABLE_CCXT_RATE_LIMIT,
        'timeout': constants.DEFAULT_REQUEST_TIMEOUT,
        'options': options,
        'headers': headers,
        'timeout_on_exit': constants.CCXT_TIMEOUT_ON_EXIT_MS,
    }
    if creds:
        if creds.api_key is not None:
            config['apiKey'] = creds.api_key
        if creds.secret is not None:
            config['secret'] = creds.secret
        if creds.password is not None:
            config['password'] = creds.password
        if creds.uid is not None:
            config['uid'] = creds.uid
        if creds.wallet_address is not None:
            config['walletAddress'] = creds.wallet_address
        if creds.private_key is not None:
            config['privateKey'] = creds.private_key
    config.update({**get_custom_domain_config(exchange_class), **(additional_config or {})})
    return config


def get_custom_domain_config(exchange_class):
    old, new = _get_replaced_custom_domains(exchange_class)
    if not (old and new):
        return {}
    if url_config := exchange_class().describe()[ccxt_enums.ExchangeColumns.URLS.value]:
        commons_logging.get_logger(__name__).info(
            f"Using custom domain for {exchange_class.__name__}: {old} is replaced by {new}, hostname has been updated"
        )
        return {
            ccxt_enums.ExchangeColumns.URLS.value: _get_patched_url_config(url_config, old, new),
            ccxt_enums.ExchangeColumns.HOSTNAME.value: new
        }
    return {}


def _get_replaced_custom_domains(exchange_class):
    identifier = exchange_class.__name__.upper()
    if custom_domain := os.getenv(f"{identifier}_CUSTOM_DOMAIN"):
        split = custom_domain.split(":")
        if len(split) == 2:
            return split[0], split[1]
        else:
            commons_logging.get_logger(__name__).error(
                f"Invalid {identifier} custom domain config. Expected syntax is to_replace_domain:updated_domain "
                f"Example: MEXC_CUSTOM_DOMAIN=mexc.com:mexc.co"
            )
    return None, None


def _get_patched_url_config(url_config: dict, old: str, new: str):
    updated_config = {}
    for key, val in url_config.items():
        if isinstance(val, dict):
            updated_config[key] = _get_patched_url_config(val, old, new)
        elif isinstance(val, str):
            updated_config[key] = val.replace(old, new)
        else:
            updated_config[key] = val
    return updated_config


async def _close_previous_session_and_connector(session, connector):
    if connector is not None:
        await connector.close()
    if session is not None:
        await session.close()


def _use_request_counter(
    identifier: str, ccxt_client: async_ccxt.Exchange, proxy_config: proxy_config_import.ProxyConfig
):
    """
    Replaces the given exchange async session by an aiohttp_util.CounterClientSession
    WARNING: should only be called right after creating the exchange and on the same async loop as
    the one the exchange will be using (to avoid interrupting open requests from current session and loop errors)
    """
    # use session with request counter
    try:
        # 1. create ssl context and other required elements if necessary
        ccxt_client.open()
        previous_session = ccxt_client.session
        previous_connector = ccxt_client.tcp_connector
        # 2. create patched session using the same params as a normal one
        # same as in ccxt.async_support.exchange.py#open()
        # connector = aiohttp.TCPConnector(ssl=self.ssl_context, loop=self.asyncio_loop, enable_cleanup_closed=True)
        ccxt_client.tcp_connector = aiohttp.TCPConnector(
            ssl=ccxt_client.ssl_context, loop=ccxt_client.asyncio_loop,
            enable_cleanup_closed=True
        )
        counter_session = aiohttp_util.CounterClientSession(
            identifier,
            loop=ccxt_client.asyncio_loop,
            connector=ccxt_client.tcp_connector,
            trust_env=previous_session.trust_env,
        )
        # 3. replace session
        ccxt_client.session = counter_session
        # 4. close replaced session in task to avoid making this function a coroutine
        asyncio.create_task(_close_previous_session_and_connector(previous_session, previous_connector))
        commons_logging.get_logger(__name__).info(f"Request counter enabled for {identifier}")
    except Exception as err:
        commons_logging.get_logger(__name__).exception(
            err, True, f"Error when initializing {identifier} request counter: {err}"
        )


def ccxt_exchange_class_factory(exchange_name):
    return getattr(async_ccxt, exchange_name)


def reraise_with_proxy_prefix_if_relevant(
    ccxt_connector, cause_error: Exception, raised_error: typing.Optional[Exception]
):
    was_proxied, last_proxied_request_url = was_latest_request_proxied(ccxt_connector)
    if was_proxied:
        raised = raised_error or cause_error
        raise raised.__class__(f"[Proxied] {raised} [URL: {last_proxied_request_url}]") from cause_error


def was_latest_request_proxied(ccxt_connector) -> (bool, str):
    if not (
        ccxt_connector.exchange_manager.proxy_config
        and ccxt_connector.exchange_manager.proxy_config.get_last_proxied_request_url
    ):
        return False, ""
    last_proxied_request_url = ccxt_connector.exchange_manager.proxy_config.get_last_proxied_request_url()
    last_client_request_url = ccxt_connector.client.last_request_url
    # if last requests are matching: it was proxied
    if last_proxied_request_url:
        url_without_param = last_proxied_request_url.split("?")[0]
        return last_proxied_request_url == last_client_request_url, url_without_param
    return False, ""


def get_proxy_error_class(proxy_error: Exception):
    if _is_retriable_proxy_error(proxy_error):
        return errors.RetriableExchangeProxyError
    return errors.ExchangeProxyError


def _is_retriable_proxy_error(proxy_error: Exception) -> bool:
    str_err = str(proxy_error)
    for desc in constants.RETRIABLE_EXCHANGE_PROXY_ERRORS_DESC:
        if desc in str_err:
            return True
    return False


def get_proxy_error_if_any(ccxt_connector, error: Exception) -> typing.Optional[Exception]:
    if not ccxt_connector.exchange_manager.proxy_config:
        return None
    max_depth = 10
    depth = 1
    cause_error = error
    while cause_error and depth < max_depth:
        if isinstance(cause_error, (
            # Proxy errors
            aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError, ProxyConnectionError
        )) or (
            # Connector error with the configured proxy host in description
            isinstance(cause_error, aiohttp.ClientConnectorError)
            and ccxt_connector.exchange_manager.proxy_config.proxy_host in str(cause_error)
        ):
            return cause_error
        depth += 1
        cause_error = getattr(cause_error, "__cause__", None)
    return None


def fix_client_missing_markets_fees(
    client: async_ccxt.Exchange, reloaded_markets: bool, confirmed_fees: dict
):
    fees_by_pair_suffix = {}
    update_confirmed_fees = reloaded_markets or not confirmed_fees
    for symbol, market in client.markets.items():
        pair_suffix = _get_market_symbol_suffix(symbol)
        maker_fees = market.get(enums.ExchangeConstantsMarketPropertyColumns.MAKER.value)
        taker_fees = market.get(enums.ExchangeConstantsMarketPropertyColumns.TAKER.value)
        if taker_fees is not None and maker_fees is not None:
            if update_confirmed_fees:
                # only update cached fees if reload is True or if it's the first call 
                # (avoid storing inferred fees)
                confirmed_fees[symbol] = (maker_fees, taker_fees)
            if (
                # be pessimistic and use the highest fees of each market
                pair_suffix not in fees_by_pair_suffix or fees_by_pair_suffix[pair_suffix][0] < maker_fees or fees_by_pair_suffix[pair_suffix][1] < taker_fees
            ):
                fees_by_pair_suffix[pair_suffix] = (maker_fees, taker_fees)
    for symbol, market in client.markets.items():
        # use other similar market fees if missing
        try:
            pair_suffix = _get_market_symbol_suffix(symbol)
            if market[enums.ExchangeConstantsMarketPropertyColumns.MAKER.value] is None or market[enums.ExchangeConstantsMarketPropertyColumns.TAKER.value] is None:
                has_cached_fees = symbol in confirmed_fees
                market[enums.ExchangeConstantsMarketPropertyColumns.MAKER.value] = (
                    market[enums.ExchangeConstantsMarketPropertyColumns.MAKER.value] or (
                        (confirmed_fees[symbol] if has_cached_fees else fees_by_pair_suffix[pair_suffix])[0]
                    )
                )
                market[enums.ExchangeConstantsMarketPropertyColumns.TAKER.value] = (
                    market[enums.ExchangeConstantsMarketPropertyColumns.TAKER.value] or (
                        (confirmed_fees[symbol] if has_cached_fees else fees_by_pair_suffix[pair_suffix])[1]
                    )
                )
                commons_logging.get_logger("fix_missing_markets_fees").info(
                    f"Fixed missing {symbol} fees using {'cached fees' if has_cached_fees else str(pair_suffix)} fees: {fees_by_pair_suffix[pair_suffix]}" 
                )
        except KeyError as err:
            commons_logging.get_logger("fix_missing_markets_fees").error(
                f"Failed to fix missing market fees for {symbol}: {err}"
            )
        except Exception as err:
            commons_logging.get_logger("fix_missing_markets_fees").exception(
                err, True, f"Unexpected error when fixing missing market fees for {symbol}: {err}"
            )


def _get_market_symbol_suffix(symbol):
    return symbol[symbol.index(octobot_commons.MARKET_SEPARATOR):]
