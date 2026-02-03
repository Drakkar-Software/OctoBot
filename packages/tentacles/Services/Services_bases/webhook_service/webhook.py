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
import asyncio
import logging
import os
import time
import flask
import threading
import gevent.pywsgi
import pyngrok.ngrok as ngrok
import pyngrok.exception

import octobot_commons.logging as bot_logging
import octobot_commons.configuration as configuration
import octobot_commons.authentication as authentication
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot.constants as constants
import octobot.community.errors as community_errors


class WebHookService(services.AbstractService):
    CONNECTION_TIMEOUT = 8  # can take up to 5s on slow setups
    LOGGERS = ["pyngrok.ngrok", "werkzeug"]

    def get_fields_description(self):
        if self.use_web_interface_for_webhook:
            return {}
        return {
            services_constants.CONFIG_ENABLE_OCTOBOT_WEBHOOK:
                f"Use OctoBot cloud webhook. Requires the {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME}.",
            services_constants.CONFIG_ENABLE_NGROK: "Use Ngrok",
            services_constants.CONFIG_NGROK_TOKEN: "The ngrok token used to expose the webhook to the internet.",
            services_constants.CONFIG_NGROK_DOMAIN: "[Optional] The ngrok subdomain.",
            services_constants.CONFIG_WEBHOOK_SERVER_IP: "WebHook bind IP: used for webhook when ngrok is not enabled.",
            services_constants.CONFIG_WEBHOOK_SERVER_PORT: "WebHook port: used for webhook when ngrok is not enabled."
        }

    def get_default_value(self):
        if self.use_web_interface_for_webhook:
            return {}
        return {
            services_constants.CONFIG_ENABLE_OCTOBOT_WEBHOOK: False,
            services_constants.CONFIG_ENABLE_NGROK: True,
            services_constants.CONFIG_NGROK_TOKEN: "",
            services_constants.CONFIG_NGROK_DOMAIN: "",
            services_constants.CONFIG_WEBHOOK_SERVER_IP: services_constants.DEFAULT_WEBHOOK_SERVER_IP,
            services_constants.CONFIG_WEBHOOK_SERVER_PORT: services_constants.DEFAULT_WEBHOOK_SERVER_PORT
        }

    def is_improved_by_extensions(self) -> bool:
        return True

    def __init__(self):
        super().__init__()
        self.use_web_interface_for_webhook = constants.IS_CLOUD_ENV
        self.use_octobot_cloud_webhook = False
        self.use_octobot_cloud_email_webhook = False
        self.ngrok_tunnel = None
        self.webhook_public_url = ""
        self.ngrok_enabled = True
        self.ngrok_domain = None

        self.service_feed_webhooks = {}
        self.service_feed_auth_callbacks = {}

        self.webhook_app = None
        self.webhook_host = None
        self.webhook_port = None
        self.webhook_server = None
        self.webhook_server_context = None
        self.webhook_server_thread = None
        self.connected = None

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_WEBHOOK in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_WEBHOOK]

    @staticmethod
    def get_is_enabled(config):
        return True

    def check_required_config(self, config):
        if self.use_web_interface_for_webhook:
            return True
        if self.is_using_octobot_cloud_webhook() or self.is_using_octobot_cloud_email_webhook():
            return True
        try:
            token = config.get(services_constants.CONFIG_NGROK_TOKEN)
            enabled_ngrok = config.get(services_constants.CONFIG_ENABLE_NGROK, True)
            if enabled_ngrok:
                return token and not configuration.has_invalid_default_config_value(token)
            return not (
                configuration.has_invalid_default_config_value(
                    config.get(services_constants.CONFIG_WEBHOOK_SERVER_PORT)
                ) or configuration.has_invalid_default_config_value(
                    config.get(services_constants.CONFIG_WEBHOOK_SERVER_IP)
                )
            )
        except KeyError:
            return False

    def has_required_configuration(self):
        try:
            return self.check_required_config(self.get_webhook_config())
        except KeyError:
            return False

    def is_using_octobot_cloud_webhook(self):
        return self.get_webhook_config().get(services_constants.CONFIG_ENABLE_OCTOBOT_WEBHOOK)

    def is_using_octobot_cloud_email_webhook(self):
        return self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(
            services_constants.CONFIG_TRADING_VIEW, {}
        ).get(
            services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS, False
        )

    def get_webhook_config(self):
        return self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(services_constants.CONFIG_WEBHOOK, {})

    def get_required_config(self):
        return [] if self.use_web_interface_for_webhook else \
            [services_constants.CONFIG_ENABLE_NGROK, services_constants.CONFIG_NGROK_TOKEN]

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/tradingview/using-a-webhook"

    def get_type(self) -> None:
        return services_constants.CONFIG_WEBHOOK

    def get_logo(self):
        return None

    def is_subscribed(self, feed_name):
        return feed_name in self.service_feed_webhooks

    @staticmethod
    def connect(port, protocol="http", domain=None) -> ngrok.NgrokTunnel:
        """
        Create a new ngrok tunnel
        :param port: the tunnel local port
        :param protocol: the protocol to use
        :return: the ngrok url
        """
        return ngrok.connect(port, protocol, domain=domain)

    def subscribe_feed(self, service_feed_name, service_feed_callback, auth_callback) -> None:
        """
        Subscribe a service feed to the webhook
        :param service_feed_name: the service feed name
        :param service_feed_callback: the service feed callback reference
        :return: the service feed webhook url
        """
        if service_feed_name not in self.service_feed_webhooks:
            self.service_feed_webhooks[service_feed_name] = service_feed_callback
            self.service_feed_auth_callbacks[service_feed_name] = auth_callback
            return
        raise KeyError(f"Service feed has already subscribed to a webhook : {service_feed_name}")

    def get_subscribe_url(self, service_feed_name):
        if self.use_octobot_cloud_email_webhook:
            return services_constants.TRADING_VIEW_USING_EMAIL_INSTEAD_OF_WEBHOOK
        if self.use_octobot_cloud_webhook:
            return self._get_community_feed_webhook_url()
        return f"{self.webhook_public_url}/{service_feed_name}"

    def _prepare_webhook_server(self):
        try:
            self.logger.debug(f"Starting local webhook server at {self.webhook_host}:{self.webhook_port}")
            self.webhook_server = gevent.pywsgi.WSGIServer(
                (self.webhook_host, self.webhook_port),
                self.webhook_app,
                log=None
            )
            self.webhook_server_context = self.webhook_app.app_context()
            self.webhook_server_context.push()
        except OSError as e:
            self.webhook_server = None
            self.logger.exception(e, False, f"Fail to start webhook : {e}")

    def _register_webhook_routes(self, blueprint) -> None:
        @blueprint.route('/')
        def index():
            """
            Route to check if webhook server is online
            """
            return ''

        @blueprint.route('/webhook/<webhook_name>', methods=['POST'])
        def webhook(webhook_name):
            return self._flask_webhook_call(webhook_name)

    def _flask_webhook_call(self, webhook_name):
        if flask.request.method == 'POST':
            data = flask.request.get_data(as_text=True)
            if self._default_webhook_call(webhook_name, data):
                return '', 200
            return 'invalid or missing input parameters', 400
        flask.abort(405)

    def _community_webhook_call_factory(self, service_name: str):

        async def _community_webhook_callback(data: dict) -> bool:
            return await self._async_default_webhook_call(
                service_name, data[commons_enums.CommunityFeedAttrs.VALUE.value]
            )

        return _community_webhook_callback

    def _default_webhook_call(self, webhook_name: str, data: str) -> bool:
        if self.is_valid_webhook_call(webhook_name, data):
            self.service_feed_webhooks[webhook_name](data)
            return True
        return False

    async def _async_default_webhook_call(self, webhook_name: str, data: str) -> bool:
        if self.is_valid_webhook_call(webhook_name, data):
            await self.service_feed_webhooks[webhook_name](data)
            return True
        return False

    def is_valid_webhook_call(self, webhook_name:str , data: str):
        if webhook_name in self.service_feed_webhooks:
            if self.service_feed_auth_callbacks[webhook_name](data):
                return True
            else:
                self.logger.warning(f"Ignored message (wrong token): {data}")
                return False
        self.logger.warning(f"Received unknown request from {webhook_name}")
        return False

    def is_using_cloud_webhooks(self):
        return self.use_octobot_cloud_webhook or self.use_octobot_cloud_email_webhook

    async def prepare(self) -> None:
        if self.use_web_interface_for_webhook:
            return
        if self.is_using_octobot_cloud_email_webhook():
            self.use_octobot_cloud_email_webhook = True
            return
        if self.is_using_octobot_cloud_webhook():
            self.use_octobot_cloud_webhook = True
            return
        bot_logging.set_logging_level(self.LOGGERS, logging.WARNING)
        self.ngrok_enabled = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
            services_constants.CONFIG_WEBHOOK].get(services_constants.CONFIG_ENABLE_NGROK, True)
        if self.ngrok_enabled:
            ngrok.set_auth_token(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEBHOOK][
                    services_constants.CONFIG_NGROK_TOKEN])
        self.ngrok_domain = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEBHOOK]\
            .get(services_constants.CONFIG_NGROK_DOMAIN, None)
        if self.ngrok_domain in commons_constants.DEFAULT_CONFIG_VALUES:
            # ignore default values
            self.ngrok_domain = None
        try:
            self.webhook_host = os.getenv(services_constants.ENV_WEBHOOK_ADDRESS,
                                          self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                                          [services_constants.CONFIG_WEBHOOK][services_constants.CONFIG_WEBHOOK_SERVER_IP])
        except KeyError:
            self.webhook_host = os.getenv(services_constants.ENV_WEBHOOK_ADDRESS,
                                          services_constants.DEFAULT_WEBHOOK_SERVER_IP)
        try:
            self.webhook_port = int(
                os.getenv(services_constants.ENV_WEBHOOK_PORT, self.config[services_constants.CONFIG_CATEGORY_SERVICES]
                [services_constants.CONFIG_WEBHOOK][services_constants.CONFIG_WEBHOOK_SERVER_PORT]))
        except KeyError:
            self.webhook_port = int(
                os.getenv(services_constants.ENV_WEBHOOK_PORT, services_constants.DEFAULT_WEBHOOK_SERVER_PORT))

    def _start_server(self):
        try:
            self._prepare_webhook_server()
            self._register_webhook_routes(self.webhook_app)
            self.webhook_public_url = f"http://{self.webhook_host}:{self.webhook_port}/webhook"
            if self.ngrok_enabled:
                self.ngrok_tunnel = self.connect(self.webhook_port, protocol="http", domain=self.ngrok_domain)
                self.webhook_public_url = f"{self.ngrok_tunnel.public_url}/webhook"
            if self.webhook_server:
                self.connected = True
                self.webhook_server.serve_forever()
        except pyngrok.exception.PyngrokNgrokError as e:
            self.logger.error(f"Error when starting webhook service: Your ngrok.com token might be invalid. ({e})")
        except Exception as e:
            self.logger.exception(e, True, f"Error when running webhook service: ({e})")
        self.connected = False

    async def _start_isolated_server(self):
        if self.webhook_app is None:
            self.webhook_app = flask.Flask(__name__)
            # gevent WSGI server has to be created in the thread it is started: create everything in this thread
            self.webhook_server_thread = threading.Thread(target=self._start_server, name=self.get_name())
            self.webhook_server_thread.start()
            start_time = time.time()
            timeout = False
            while self.connected is None and not timeout:
                time.sleep(0.1)
                timeout = time.time() - start_time > self.CONNECTION_TIMEOUT
            if timeout:
                self.logger.error("Webhook took too long to start, now stopping it.")
                await self.stop()
                self.connected = False
            return self.connected is True
        return True

    async def _register_on_web_interface(self):
        import tentacles.Services.Interfaces.web_interface.api as api
        if not api.has_webhook(self._flask_webhook_call):
            api.register_webhook(self._flask_webhook_call)
        authenticator = authentication.Authenticator.instance()
        if not authenticator.initialized_event.is_set():
            await asyncio.wait_for(authenticator.initialized_event.wait(), authenticator.LOGIN_TIMEOUT)
        try:
            # deployed bot url
            self.webhook_public_url = f"{await authenticator.get_deployment_url()}/api/webhook"
            self.connected = True
            return True
        except community_errors.BotError as err:
            self.logger.exception(err, True, f"Impossible to start web interface based webhook {err}")
            return False

    def _get_community_feed_webhook_url(self) -> str:
        try:
            authenticator = authentication.Authenticator.instance()
            bot_identifier = authenticator.get_saved_mqtt_device_uuid()
            return f"{constants.COMMUNITY_TRADINGVIEW_WEBHOOK_BASE_URL}/{bot_identifier}"
        except community_errors.NoBotDeviceError:
            return ""

    async def _register_on_community_feed(self):
        authenticator = authentication.Authenticator.instance()
        bot_identifier = authenticator.get_saved_mqtt_device_uuid()
        if not authenticator.initialized_event.is_set():
            await asyncio.wait_for(authenticator.initialized_event.wait(), authenticator.LOGIN_TIMEOUT)
        try:
            for feed_name, channel_type in [
                (services_constants.TRADINGVIEW_WEBHOOK_SERVICE_NAME, commons_enums.CommunityChannelTypes.TRADINGVIEW)
            ]:
                await authenticator.register_feed_callback(
                    channel_type,
                    self._community_webhook_call_factory(feed_name),
                    identifier=bot_identifier
                )
            self.webhook_public_url = self._get_community_feed_webhook_url()
            self.connected = True
            return True
        except community_errors.BotError as err:
            self.logger.exception(err, True, f"Impossible to start OctoBot cloud based webhook {err}")
            return False

    async def start_webhooks(self) -> bool:
        if self.use_web_interface_for_webhook:
            return await self._register_on_web_interface()
        if self.is_using_cloud_webhooks():
            try:
                return await self._register_on_community_feed()
            except community_errors.NoBotDeviceError:
                raise community_errors.ExtensionRequiredError(
                    f"A connected OctoBot account using the {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME} "
                    f"is required to use OctoBot {'email' if self.use_octobot_cloud_email_webhook else 'webhook' } "
                    f"alerts for TradingView."
                )
        return await self._start_isolated_server()

    def _is_healthy(self):
        return (
            self.use_web_interface_for_webhook or
            self.is_using_octobot_cloud_webhook() or
            self.is_using_octobot_cloud_email_webhook() or
            (self.webhook_host is not None and self.webhook_port is not None)
        )

    def get_successful_startup_message(self):
        webhook_endpoint = f"ngrok address"
        if self.use_web_interface_for_webhook:
            webhook_endpoint = "web interface webhook api"
        if self.is_using_octobot_cloud_webhook() or self.is_using_octobot_cloud_email_webhook():
            webhook_endpoint = "OctoBot cloud network"
        return f"Webhook configured on {webhook_endpoint}", self._is_healthy()

    async def stop(self):
        if not self.use_web_interface_for_webhook and self.connected:
            ngrok.kill()
            if self.webhook_server:
                try:
                    self.webhook_server.stop()
                except Exception as err:
                    self.logger.warning(f"Error when stopping webhook server: {err}")
