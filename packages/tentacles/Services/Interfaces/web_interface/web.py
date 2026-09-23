#  Drakkar-Software OctoBot-Interfaces
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
import os
import threading
import time
import flask
import flask_cors
import uvicorn
import werkzeug.middleware.proxy_fix

import octobot_commons.logging as bot_logging
import octobot_commons.network as network_module
import octobot_commons.os_util as os_util
import octobot_services.constants as services_constants
import octobot_services.interfaces as services_interfaces
import octobot_services.interfaces.util as interfaces_util
import octobot_trading.api as trading_api
import octobot.configuration_manager as configuration_manager
import octobot.enums
import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.security as security
import tentacles.Services.Interfaces.web_interface.websockets as websockets
import tentacles.Services.Interfaces.web_interface.plugins as web_interface_plugins
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import octobot_services.interfaces.util.web as web_util
import tentacles.Services.Interfaces.web_interface as web_interface_root
import tentacles.Services.Interfaces.web_interface.util.uvicorn_log_util as uvicorn_log_util
import tentacles.Services.Interfaces.web_interface.websockets.server.asgi_composite as asgi_composite
import tentacles.Services.Interfaces.web_interface.controllers
import tentacles.Services.Interfaces.web_interface.advanced_controllers
import tentacles.Services.Interfaces.web_interface.api
import tentacles.Services.Services_bases as Service_bases
import octobot_tentacles_manager.api


class WebInterface(services_interfaces.AbstractWebInterface):

    _general_error_notifier_registered = False

    REQUIRED_SERVICES = [Service_bases.WebService]
    COLOR_MODE = "color_mode"
    ANNOUNCEMENTS = "announcements"
    DISPLAY_TIME_FRAME = "display_time_frame"
    DISPLAY_ORDERS = "display_orders"
    WATCHED_SYMBOLS = constants.CONFIG_WATCHED_SYMBOLS

    tools = {
        constants.BOT_TOOLS_BACKTESTING: None,
        constants.BOT_TOOLS_BACKTESTING_SOURCE: None,
        constants.BOT_TOOLS_STRATEGY_OPTIMIZER: None,
        constants.BOT_TOOLS_DATA_COLLECTOR: None,
        constants.BOT_TOOLS_SOCIAL_DATA_COLLECTOR: None,
        constants.BOT_PREPARING_BACKTESTING: False,
    }

    def __init__(self, config):
        super().__init__(config)
        self.logger = self.get_logger()
        self.server_instance = None
        self.host = None
        self.port = None
        self.uvicorn_server = None
        self._serve_finished = None
        self.web_login_manger = None
        self.requires_password = False
        self.password_hash = ""
        self.dev_mode = False
        self.started = False
        self.registered_plugins = []
        self._init_web_settings()
        self.local_config = None
        if interfaces_util.get_bot_api() is None:
            # should not happen in non-test environment
            self.logger.error(
                f"interfaces_util.get_bot_api() is not available at {self.get_name()} constructor"
            )
        else:
            self.reload_config()

    async def register_new_exchange_impl(self, exchange_id):
        if exchange_id not in self.registered_exchanges_ids:
            await self._register_on_channels(exchange_id)

    def reload_config(self, tentacles_setup_config=None):
        self.local_config = octobot_tentacles_manager.api.get_tentacle_config(
            tentacles_setup_config or interfaces_util.get_edited_tentacles_config(), self.__class__
        )

    def _init_web_settings(self):
        try:
            self.host = os.getenv(services_constants.ENV_WEB_ADDRESS,
                                  self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                                  [services_constants.CONFIG_WEB][services_constants.CONFIG_WEB_IP])
        except KeyError:
            self.host = os.getenv(services_constants.ENV_WEB_ADDRESS, services_constants.DEFAULT_SERVER_IP)
        try:
            self.port = int(os.getenv(services_constants.ENV_WEB_PORT,
                                      self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                                      [services_constants.CONFIG_WEB][services_constants.CONFIG_WEB_PORT]))
        except KeyError:
            self.port = int(os.getenv(services_constants.ENV_WEB_PORT, services_constants.DEFAULT_SERVER_PORT))
        try:
            self.requires_password = \
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB] \
                    [services_constants.CONFIG_WEB_REQUIRES_PASSWORD]
        except KeyError:
            pass
        try:
            self.password_hash = self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
                [services_constants.CONFIG_WEB][services_constants.CONFIG_WEB_PASSWORD]
        except KeyError:
            pass
        try:
            env_value = os.getenv(services_constants.ENV_AUTO_OPEN_IN_WEB_BROWSER, None)
            if env_value is None:
                self.should_open_web_interface = self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
                    [services_constants.CONFIG_WEB][services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER]
            else:
                self.should_open_web_interface = env_value.lower() == "true"
        except KeyError:
            self.should_open_web_interface = True
        self.dev_mode = False if interfaces_util.get_bot_api() is None else\
            interfaces_util.get_edited_config(dict_only=False).dev_mode_enabled()

    @staticmethod
    async def _web_trades_callback(exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, trade, old_trade):
        web_interface_root.send_new_trade(
            trade,
            exchange_id,
            symbol
        )

    @staticmethod
    async def _web_orders_callback(exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, order,
                                   update_type, is_from_bot):
        web_interface_root.send_order_update(order, exchange_id, symbol)

    @staticmethod
    async def _web_ohlcv_empty_callback(
            exchange: str,
            exchange_id: str,
            cryptocurrency: str,
            symbol: str,
            time_frame,
            candle
    ):
        pass

    async def _register_on_channels(self, exchange_id):
        try:
            if trading_api.is_exchange_trading(trading_api.get_exchange_manager_from_exchange_id(exchange_id)):
                await trading_api.subscribe_to_trades_channel(self._web_trades_callback, exchange_id)
                await trading_api.subscribe_to_order_channel(self._web_orders_callback, exchange_id)
                await trading_api.subscribe_to_ohlcv_channel(self._web_ohlcv_empty_callback, exchange_id)
        except ImportError:
            self.logger.error("Watching trade channels requires OctoBot-Trading package installed")

    def init_flask_plugins_and_config(self, server_instance):
        # Only setup flask plugins once per flask app (can't call flask setup methods after the 1st request
        # has been received).
        # Override system configuration content types
        flask_util.init_content_types()
        self.server_instance.json = flask_util.FloatDecimalJSONProvider(self.server_instance)

        # Set CORS policy
        if flask_util.get_user_defined_cors_allowed_origins() != "*":
            # never allow "*" as allowed origin, prefer not setting it if user did not specifically set origins
            flask_cors.CORS(self.server_instance, origins=flask_util.get_user_defined_cors_allowed_origins())

        self.server_instance.config['SEND_FILE_MAX_AGE_DEFAULT'] = 604800
        proxy_fix_kwargs = {}
        proxy_fix_log_parts = []
        if os_util.parse_boolean_environment_var("OCTOBOT_PROXY_FIX_SCRIPT_NAME", "False"):
            proxy_fix_kwargs["x_script_name"] = 1
            proxy_fix_log_parts.append(
                "OCTOBOT_PROXY_FIX_SCRIPT_NAME: trusting X-Script-Name for subpath deployments"
            )
        if os_util.parse_boolean_environment_var("OCTOBOT_PROXY_FIX_HTTPS", "False"):
            proxy_fix_kwargs["x_proto"] = 1
            proxy_fix_kwargs["x_host"] = 1
            proxy_fix_log_parts.append(
                "OCTOBOT_PROXY_FIX_HTTPS: trusting X-Forwarded-Proto and X-Forwarded-Host "
                "for reverse-proxy TLS (url_for, redirects, secure cookies)"
            )
        if proxy_fix_kwargs:
            self.logger.info("Werkzeug ProxyFix enabled (%s)", "; ".join(proxy_fix_log_parts))
            self.server_instance.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(
                self.server_instance.wsgi_app,
                **proxy_fix_kwargs,
            )

        if self.dev_mode:
            server_instance.config['TEMPLATES_AUTO_RELOAD'] = True

        flask_util.register_context_processor(self)
        flask_util.register_template_filters(server_instance)
        # register session secret key
        server_instance.secret_key = flask_util.BrowsingDataProvider.instance().get_or_create_session_secret_key()
        self._handle_login(server_instance)

        security.register_responses_extra_header(server_instance, True)

    def _handle_login(self, server_instance):
        self.web_login_manger = login.WebLoginManager(server_instance, self.password_hash)
        login.set_is_login_required(self.requires_password)

    def set_requires_password(self, requires_password):
        self.requires_password = requires_password
        login.set_is_login_required(requires_password)

    def _register_routes(self, server_instance, distribution: octobot.enums.OctoBotDistribution):
        tentacles.Services.Interfaces.web_interface.controllers.register(server_instance, distribution)
        server_instance.register_blueprint(
            tentacles.Services.Interfaces.web_interface.api.register(distribution)
        )
        server_instance.register_blueprint(
            tentacles.Services.Interfaces.web_interface.advanced_controllers.register(distribution)
        )

    def _prepare_websocket(self, server_instance):
        if not WebInterface._general_error_notifier_registered:
            bot_logging.register_error_notifier(web_interface_root.send_general_notifications)
            WebInterface._general_error_notifier_registered = True

    def _release_server_state(self) -> None:
        self.started = False
        self.server_instance = None
        self.uvicorn_server = None
        self._serve_finished = None

    async def _async_run(self) -> bool:
        # wait bot is ready
        while not self.is_bot_ready():
            time.sleep(0.05)

        try:
            self.server_instance = flask.Flask(__name__)
            distribution = configuration_manager.get_distribution(interfaces_util.get_edited_config())

            self._register_routes(self.server_instance, distribution)
            if distribution is octobot.enums.OctoBotDistribution.DEFAULT:
                # for now, plugins are only available on default distribution
                self.registered_plugins = web_interface_plugins.register_all_plugins(
                    self.server_instance, self.registered_plugins
                )
            web_interface_root.update_registered_plugins(self.registered_plugins)
            self.init_flask_plugins_and_config(self.server_instance)
            self._prepare_websocket(self.server_instance)

            asgi_app = websockets.build_composite_asgi_app(self.server_instance)
            config = uvicorn.Config(
                asgi_app,
                host=self.host,
                port=self.port,
                **uvicorn_log_util.minimal_uvicorn_config_kwargs(),
            )
            self.uvicorn_server = uvicorn.Server(config)
            uvicorn_log_util.apply_minimal_uvicorn_logging()
            self._serve_finished = threading.Event()

            if self.should_open_web_interface:
                self._open_web_interface_on_browser()

            self.started = True
            try:
                await self.uvicorn_server.serve()
            finally:
                if self._serve_finished is not None:
                    self._serve_finished.set()
                self._release_server_state()
            return True
        except Exception as e:
            self.logger.exception(e, False, f"Fail to start web interface : {e}")
            self._release_server_state()
        finally:
            self.logger.debug("Web interface thread stopped")
        return False

    def _open_web_interface_on_browser(self):
        try:
            web_util.open_in_background_browser(
                f"http://{network_module.LOCAL_HOST_IP}:{self.port}"
            )
        except Exception as err:
            self.logger.warning(f"Impossible to open automatically web interface: {err} ({err.__class__.__name__})")

    async def _inner_start(self):
        return self.threaded_start()

    async def _wait_for_serve_finished(self, serve_finished: threading.Event, timeout_seconds: float) -> None:
        await asyncio.wait_for(
            asyncio.to_thread(serve_finished.wait),
            timeout=timeout_seconds,
        )

    async def stop(self):
        """
        Best-effort uvicorn shutdown. Lingering HTTP/WebSocket connections may prevent a fully
        graceful drain; uvicorn may log "timeout graceful shutdown exceeded" — that is expected.
        The bot does not require a pristine server shutdown. teardown_web_interface_runtime()
        runs when force_exit skips uvicorn lifespan shutdown.
        """
        if self.uvicorn_server is None:
            return
        try:
            self.logger.debug("Stopping web interface")
            uvicorn_server = self.uvicorn_server
            uvicorn_server.should_exit = True
            serve_finished = self._serve_finished
            if serve_finished is not None:
                try:
                    await self._wait_for_serve_finished(
                        serve_finished,
                        constants.WEB_INTERFACE_STOP_WAIT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Timed out waiting for web interface to stop after %ss; forcing uvicorn exit",
                        constants.WEB_INTERFACE_STOP_WAIT_SECONDS,
                    )
                    uvicorn_server.force_exit = True
                    try:
                        await self._wait_for_serve_finished(
                            serve_finished,
                            constants.WEB_INTERFACE_STOP_FORCE_EXIT_WAIT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            "Web interface did not stop after forced exit (%ss)",
                            constants.WEB_INTERFACE_STOP_FORCE_EXIT_WAIT_SECONDS,
                        )
            self.logger.debug("Stopped web interface")
        except Exception as e:
            self.logger.exception(e, False, f"Error when stopping web interface : {e}")
        finally:
            asgi_composite.teardown_web_interface_runtime()
            self._release_server_state()
