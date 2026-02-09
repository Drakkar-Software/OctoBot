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
import mock
import contextlib
import random

import octobot_commons.configuration as configuration
import octobot_commons.singleton as singleton
import octobot_commons.authentication as authentication
import octobot_commons.constants as commons_constants

import octobot_services.interfaces as interfaces
import octobot.community as community
try:
    import octobot.community.supabase_backend.configuration_storage as configuration_storage
except ImportError:
    # todo remove once supabase migration is complete
    configuration_storage = mock.Mock(
        ASyncConfigurationStorage=mock.Mock(
            _save_value_in_config=mock.Mock()
        )
    )
import octobot.automation as automation
import octobot.enums
import octobot_commons.constants

import tentacles.Services.Interfaces.web_interface.controllers.octobot_authentication as octobot_authentication
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface as web_interface


PASSWORD = "123"
MAX_START_TIME = 5
NON_AUTH_ROUTES = ["/api/", "robots.txt"]


def get_new_port() -> int:
    return random.randint(5555, 65535)


async def _init_bot(distribution: octobot.enums.OctoBotDistribution):
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
    test_config = test_config.load_test_config(dict_only=False)
    test_config.config[octobot_commons.constants.CONFIG_DISTRIBUTION] = distribution.value
    octobot = octobot.OctoBot(test_config)
    octobot.initialized = True
    tentacles_config = config.load_test_tentacles_config()
    loaders.reload_tentacle_by_tentacle_class()
    octobot.task_manager.async_loop = asyncio.get_event_loop()
    octobot.task_manager.create_pool_executor()
    octobot.tentacles_setup_config = tentacles_config
    octobot.configuration_manager.add_element(octobot_constants.TENTACLES_SETUP_CONFIG_KEY, tentacles_config)
    octobot.exchange_producer = producers.ExchangeProducer(None, octobot, None, False)
    octobot.evaluator_producer = producers.EvaluatorProducer(None, octobot)
    await evaluators_api.initialize_evaluators(octobot.config, tentacles_config)
    octobot.evaluator_producer.matrix_id = evaluators_api.create_matrix()
    # Do not edit config file
    octobot.community_auth.edited_config = None
    octobot.automation = automation.Automation(octobot.bot_id, tentacles_config)
    return octobot


def _start_web_interface(interface):
    asyncio.run(interface.start())


# use context manager instead of fixture to prevent pytest threads issues
@contextlib.asynccontextmanager
async def get_web_interface(
    require_password: bool, distribution: octobot.enums.OctoBotDistribution
):
    web_interface_instance = None
    try:
        with mock.patch.object(configuration_storage.SyncConfigurationStorage, "_save_value_in_config", mock.Mock()):
            bot = await _init_bot(distribution)
            interfaces.AbstractInterface.bot_id = bot.bot_id
            web_interface_instance = web_interface.WebInterface({})
            web_interface_instance.port = get_new_port()
            web_interface_instance.should_open_web_interface = False
            web_interface_instance.set_requires_password(require_password)
            web_interface_instance.password_hash = configuration.get_password_hash(PASSWORD)
            first_exchange = next(iter(bot.config[commons_constants.CONFIG_EXCHANGES]))
            with mock.patch.object(web_interface_instance, "_register_on_channels", new=mock.AsyncMock()), \
                 mock.patch.object(models, "get_current_exchange", mock.Mock(return_value=first_exchange)):
                threading.Thread(target=_start_web_interface, args=(web_interface_instance,)).start()
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


async def check_page_no_login_redirect(url, session):
    COMMUNITY_LOGIN_CONTAINED_PAGE_SUFFIXES = [
        "login", "logout", "/profiles_selector",
        "/community"  # redirects
    ]
    async with session.get(url) as resp:
        text = await resp.text()
        assert "We are sorry, but an unexpected error occurred" not in text, f"{url=}"
        assert "We are sorry, but this doesn't exist" not in text, f"{url=}"
        if not (any(url.endswith(suffix)) for suffix in COMMUNITY_LOGIN_CONTAINED_PAGE_SUFFIXES):
            assert "input type=submit value=Login" not in text, f"{url=}"
            assert not resp.real_url.name == "login", f"{resp.real_url.name=} != 200 ({url=})"
        assert resp.status == 200, f"{resp.status=} != 200 ({url=})"


async def check_page_login_redirect(url, session):
    async with session.get(url) as resp:
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
