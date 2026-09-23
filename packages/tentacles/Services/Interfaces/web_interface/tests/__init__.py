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
import threading
import asyncio
import time
import typing
import mock
import contextlib
import socket

import aiohttp
import aiohttp.client_exceptions
import aiohttp.http_exceptions

import octobot_commons.configuration as configuration
import octobot_commons.singleton as singleton
import octobot_commons.authentication as authentication
import octobot_commons.constants as commons_constants

import octobot_services.interfaces as interfaces
import octobot.community as community
import octobot.automation as automation
import octobot.enums
import octobot_commons.constants

import tentacles.Services.Interfaces.web_interface.controllers.octobot_authentication as octobot_authentication
import tentacles.Services.Interfaces.web_interface as web_interface


PASSWORD = "123"
MAX_START_TIME = 5
WEB_INTERFACE_TEST_THREAD_JOIN_TIMEOUT_SECONDS = 15
NON_AUTH_ROUTES = ["/api/", "robots.txt"]

# Parallel browse can reset TCP mid-body (ContentLengthError) under full-suite / Windows load.
# That is an accepted integration flake, not a product bug; _aihttp_request retries once.
BROWSE_HTTP_INCOMPLETE_PAYLOAD_MAX_RETRIES = 1
BROWSE_HTTP_INCOMPLETE_PAYLOAD_RETRY_DELAY_SECONDS = 0.05

# Small static data for distribution browse tests (avoids Coingecko / CCXT under parallel gather).
_TEST_CURRENCY_LIST_STUB = [
    {"n": "Bitcoin", "s": "BTC", "i": "bitcoin"},
    {"n": "Ethereum", "s": "ETH", "i": "ethereum"},
]
_TEST_SYMBOL_LIST_STUB = ["BTC/USDT", "ETH/USDT"]


def _reset_web_interface_model_caches_for_tests() -> None:
    import tentacles.Services.Interfaces.web_interface.models.configuration as configuration_models
    configuration_models.markets_by_exchanges.clear()


def _disable_configuration_save(
    loaded_configuration: configuration.Configuration,
) -> None:
    loaded_configuration.save = lambda *_, **__: None  # type: ignore[method-assign]


def get_new_port() -> int:
    # Bind port 0 so the OS assigns a free port (random picks collide under pytest-xdist).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _init_bot(
    distribution: octobot.enums.OctoBotDistribution,
    configure_profile_storage: typing.Callable | None = None,
    configure_tentacles_setup: typing.Callable | None = None,
):
    # import here to prevent web interface import issues
    import octobot.octobot as octobot
    import octobot.constants as octobot_constants
    import octobot.producers as producers
    import octobot_commons.tests as test_config
    import octobot_tentacles_manager.loaders as loaders
    import octobot_evaluators.api as evaluators_api
    import tests.test_utils.config as config
    # force community CommunityAuthentication reset
    community.IdentifiersProvider.use_production()
    singleton.Singleton._instances.pop(authentication.Authenticator, None)
    singleton.Singleton._instances.pop(community.CommunityAuthentication, None)
    loaded_config = test_config.load_test_config(dict_only=False)
    if configure_profile_storage is not None:
        configure_profile_storage(loaded_config.profile_storage)
    loaded_config.config[octobot_commons.constants.CONFIG_DISTRIBUTION] = distribution.value
    _disable_configuration_save(loaded_config)
    bot = octobot.OctoBot(loaded_config)
    bot.initialized = True
    tentacles_config = config.load_test_tentacles_config()
    if configure_tentacles_setup is not None:
        configure_tentacles_setup(tentacles_config)
    loaders.reload_tentacle_by_tentacle_class()
    bot.task_manager.async_loop = asyncio.get_event_loop()
    bot.task_manager.create_pool_executor()
    bot.tentacles_setup_config = tentacles_config
    bot.configuration_manager.add_element(octobot_constants.TENTACLES_SETUP_CONFIG_KEY, tentacles_config)
    bot.exchange_producer = producers.ExchangeProducer(None, bot, None, False)
    bot.evaluator_producer = producers.EvaluatorProducer(None, bot)
    await evaluators_api.initialize_evaluators(bot.config, tentacles_config)
    bot.evaluator_producer.matrix_id = evaluators_api.create_matrix()
    # Do not edit config file
    bot.community_auth.edited_config = None
    bot.automation = automation.Automation(bot.bot_id, tentacles_config)
    return bot


def _start_web_interface(interface):
    asyncio.run(interface.start())


# use context manager instead of fixture to prevent pytest threads issues
@contextlib.asynccontextmanager
async def get_web_interface(
    require_password: bool,
    distribution: octobot.enums.OctoBotDistribution,
    configure_profile_storage: typing.Callable | None = None,
    configure_tentacles_setup: typing.Callable | None = None,
    cleanup_tentacles_setup: typing.Callable | None = None,
):
    web_interface_instance = None
    start_thread = None
    try:
        _reset_web_interface_model_caches_for_tests()
        bot = await _init_bot(
            distribution,
            configure_profile_storage=configure_profile_storage,
            configure_tentacles_setup=configure_tentacles_setup,
        )
        interfaces.AbstractInterface.bot_id = bot.bot_id
        web_interface_instance = web_interface.WebInterface({})
        web_interface_instance.port = get_new_port()
        web_interface_instance.should_open_web_interface = False
        web_interface_instance.set_requires_password(require_password)
        web_interface_instance.password_hash = configuration.get_password_hash(PASSWORD)
        first_exchange = next(iter(bot.config[commons_constants.CONFIG_EXCHANGES]))
        with mock.patch.object(web_interface_instance, "_register_on_channels", new=mock.AsyncMock()), \
             mock.patch(
                 "tentacles.Services.Interfaces.web_interface.models.get_current_exchange",
                 mock.Mock(return_value=first_exchange),
             ), \
             mock.patch(
                 "tentacles.Services.Interfaces.web_interface.models.get_symbol_list",
                 mock.Mock(return_value=_TEST_SYMBOL_LIST_STUB),
             ), \
             mock.patch(
                 "tentacles.Services.Interfaces.web_interface.models.get_all_symbols_list",
                 mock.Mock(return_value=_TEST_CURRENCY_LIST_STUB),
             ):
            start_thread = threading.Thread(
                target=_start_web_interface,
                args=(web_interface_instance,),
                name="web-interface-test",
            )
            start_thread.start()
            # ensure web interface had time to start or it can't be stopped at the moment
            launch_time = time.time()
            while not web_interface_instance.started and time.time() - launch_time < MAX_START_TIME:
                await asyncio.sleep(0.3)
            if not web_interface_instance.started:
                raise RuntimeError("Web interface did not start in time")
            yield web_interface_instance
    finally:
        if web_interface_instance is not None:
            await web_interface_instance.stop()
        if start_thread is not None:
            start_thread.join(timeout=WEB_INTERFACE_TEST_THREAD_JOIN_TIMEOUT_SECONDS)
            if start_thread.is_alive():
                raise RuntimeError("Web interface thread did not exit after stop")
        if cleanup_tentacles_setup is not None:
            cleanup_tentacles_setup()


def _is_acceptable_browse_transport_flake(error: BaseException) -> bool:
    current_error: BaseException | None = error
    while current_error is not None:
        if isinstance(current_error, aiohttp.client_exceptions.ClientPayloadError):
            error_message = str(current_error).lower()
            if "payload is not completed" in error_message or "contentlengtherror" in error_message:
                return True
        if isinstance(current_error, aiohttp.http_exceptions.ContentLengthError):
            return True
        if isinstance(current_error, ConnectionResetError):
            return True
        current_error = current_error.__cause__
    return False


class _BrowseTestHttpResponse:
    def __init__(self, aiohttp_response, body: bytes):
        self.status = aiohttp_response.status
        self.real_url = aiohttp_response.real_url
        self._body = body

    async def text(self) -> str:
        return self._body.decode()


def _raise_enriched_aihttp_error(url, response, error: Exception) -> None:
    response_status = response.status if response is not None else None
    raise type(error)(f"{url=}: status={response_status}: {error}") from error


@contextlib.asynccontextmanager
async def _aihttp_request(session, url):
    for attempt_index in range(BROWSE_HTTP_INCOMPLETE_PAYLOAD_MAX_RETRIES + 1):
        response = None
        try:
            async with session.get(url) as response:
                body = await response.read()
                yield _BrowseTestHttpResponse(response, body)
                return
        except Exception as error:
            if (
                attempt_index < BROWSE_HTTP_INCOMPLETE_PAYLOAD_MAX_RETRIES
                and _is_acceptable_browse_transport_flake(error)
            ):
                await asyncio.sleep(BROWSE_HTTP_INCOMPLETE_PAYLOAD_RETRY_DELAY_SECONDS)
                continue
            _raise_enriched_aihttp_error(url, response, error)


async def check_page_no_login_redirect(url, session):
    COMMUNITY_LOGIN_CONTAINED_PAGE_SUFFIXES = [
        "login", "logout", "/profiles_selector",
        "/community"  # redirects
    ]
    async with _aihttp_request(session, url) as resp:
        assert resp.status == 200, f"{resp.status=} != 200 ({url=})"
        text = await resp.text()
        assert "We are sorry, but an unexpected error occurred" not in text, f"{url=}"
        assert "We are sorry, but this doesn't exist" not in text, f"{url=}"
        if not (any(url.endswith(suffix)) for suffix in COMMUNITY_LOGIN_CONTAINED_PAGE_SUFFIXES):
            assert "input type=submit value=Login" not in text, f"{url=}"
            assert not resp.real_url.name == "login", f"{resp.real_url.name=} != 200 ({url=})"


async def check_page_login_redirect(url, session):
    async with _aihttp_request(session, url) as resp:
        text = await resp.text()
        assert "We are sorry, but an unexpected error occurred" not in text, f"{url=}"
        assert "We are sorry, but this doesn't exist" not in text, f"{url=}"
        if not any(route in url for route in NON_AUTH_ROUTES):
            assert "input type=submit value=Login" in text, url
            assert resp.real_url.name == "login", f"{resp.real_url.name=} != 200 ({url=})"
        assert resp.status == 200, f"{resp.status=} != 200 ({url=})"

def get_plugins_routes(web_interface_instance):
    all_rules = tuple(rule for rule in web_interface_instance.server_instance.url_map.iter_rules())
    plugin_routes = []
    for plugin in web_interface_instance.registered_plugins:
        plugin_routes += [
            rule.rule
            for rule in get_plugin_routes(web_interface_instance.server_instance, plugin, all_rules)
        ]
    return plugin_routes


def get_plugin_routes(app, plugin, all_rules=None):
    all_rules = all_rules or [rule for rule in app.url_map.iter_rules()]
    return (
        route for route in all_rules
        if route.rule.startswith(f"{plugin.blueprint.url_prefix}/")
    )


def _force_validate_on_submit(*_):
    return True


async def login_user_on_session(session, port: int):
    login_data = {
        "password": PASSWORD,
        "remember_me": False
    }
    with mock.patch.object(octobot_authentication.LoginForm, "validate_on_submit", new=_force_validate_on_submit):
        async with session.post(f"http://localhost:{port}/login",
                                data=login_data) as resp:
            assert resp.status == 200


def get_all_plugin_rules(app, plugin_class, black_list):
    plugin_instance = plugin_class.factory()
    plugin_instance.blueprint_factory()
    return set(rule.rule
               for rule in get_plugin_routes(app, plugin_instance)
               if "GET" in rule.methods
               and _has_no_empty_params(rule)
               and rule.rule not in black_list)


def _has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)
