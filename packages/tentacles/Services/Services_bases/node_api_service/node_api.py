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

import os
import socket

import octobot_commons.constants as commons_constants
import octobot_commons.network as network_module
import octobot.configuration_manager as configuration_manager
import octobot.enums as octobot_enums
import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot_node.scheduler
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals


class NodeApiService(services.AbstractService):
    BACKTESTING_ENABLED = True

    def __init__(self):
        super().__init__()
        self.api_app = None
        self.node_api_url = None
        self.node_sqlite_file = None
        self.node_redis_url = None
        self.backend_cors_origins = None
        self.node_external_host = None
        self.cloud_sync_enabled = False
        self.cloud_sync_collections = None

    def get_fields_description(self):
        return {
            services_constants.CONFIG_NODE_API_PORT: "Port to access the OctoBot Node API interface from.",
            services_constants.NODE_API_URL: "Base URL used by the Node Web UI to reach the Node API.",
            services_constants.NODE_SQLITE_FILE: "SQLite database file path for the Node scheduler.",
            services_constants.NODE_REDIS_URL: "Redis URI for the Node scheduler (optional).",
            services_constants.BACKEND_CORS_ALLOWED_ORIGINS: "Allowed CORS origins for the Node API backend.",
            services_constants.NODE_EXTERNAL_HOST: "External host (and port, if non-default) the sync/mobile "
                                                    "client dials to reach this node. Required when this node "
                                                    "sits behind a reverse proxy that presents a different Host "
                                                    "header to the server than the one the client signed "
                                                    "(e.g. tailscale serve), otherwise sync requests fail "
                                                    "signature verification.",
            services_constants.CLOUD_SYNC_ENABLED: "Enable E2E-encrypted mirroring of this node's data to the "
                                                    "shared cloud sync server. Off by default; required for any "
                                                    "third-party (website-pairing) integration to read anything.",
            services_constants.CLOUD_SYNC_COLLECTIONS: "Which node collections are mirrored to the cloud sync "
                                                        "server when cloud sync is enabled. Never includes "
                                                        "user-accounts-auth (exchange credentials) — that "
                                                        "collection is not a configurable option.",
            services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: "When enabled, OctoBot will open the Node web UI "
                                                                "in your browser upon startup.",
            commons_constants.CONFIG_ENABLED_OPTION: "Enable the Node API interface.",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_NODE_API_PORT: services_constants.DEFAULT_NODE_API_PORT,
            services_constants.NODE_API_URL: self._get_default_node_api_url(),
            services_constants.NODE_SQLITE_FILE: "tasks.db",
            services_constants.NODE_REDIS_URL: None,
            services_constants.BACKEND_CORS_ALLOWED_ORIGINS: services_constants.DEFAULT_BACKEND_CORS_ALLOWED_ORIGINS,
            services_constants.NODE_EXTERNAL_HOST: None,
            services_constants.CLOUD_SYNC_ENABLED: False,
            services_constants.CLOUD_SYNC_COLLECTIONS: list(services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS),
            services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: True,
            commons_constants.CONFIG_ENABLED_OPTION: False,
        }

    def get_required_config(self):
        return [services_constants.CONFIG_NODE_API_PORT]

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_NODE_API in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_NODE_API
               ]

    @staticmethod
    def get_is_enabled(config):
        if configuration_manager.get_distribution(config) is octobot_enums.OctoBotDistribution.NODE:
            return True
        if os.getenv(services_constants.ENV_ENABLE_NODE_API):
            return commons_constants.parse_boolean_environment_var(
                services_constants.ENV_ENABLE_NODE_API, "false"
            )
        return config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(services_constants.CONFIG_NODE_API, {}).get(
            commons_constants.CONFIG_ENABLED_OPTION, False
        )

    def has_required_configuration(self):
        return self.get_is_enabled(self.config)

    def get_endpoint(self) -> None:
        return self.api_app

    def get_type(self) -> None:
        return services_constants.CONFIG_NODE_API

    @staticmethod
    def get_should_warn():
        return False

    async def stop(self):
        if self.api_app:
            self.api_app.stop()

    async def prepare(self) -> None:
        try:
            node_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_NODE_API]
            self.node_api_url = node_config.get(services_constants.NODE_API_URL)
            self.node_sqlite_file = node_config.get(services_constants.NODE_SQLITE_FILE)
            self.node_redis_url = node_config.get(services_constants.NODE_REDIS_URL)
            self.backend_cors_origins = node_config.get(services_constants.BACKEND_CORS_ALLOWED_ORIGINS)
            self.node_external_host = node_config.get(services_constants.NODE_EXTERNAL_HOST)
            self.cloud_sync_enabled = node_config.get(services_constants.CLOUD_SYNC_ENABLED, False)
            self.cloud_sync_collections = node_config.get(services_constants.CLOUD_SYNC_COLLECTIONS)
        except KeyError:
            self.node_api_url = None
            self.node_sqlite_file = None
            self.node_redis_url = None
            self.backend_cors_origins = None
            self.node_external_host = None
            self.cloud_sync_enabled = False
            self.cloud_sync_collections = None
        self._sync_config()
        self._register_mirror_context_provider()
        if self.get_is_enabled(self.config) and not octobot_node.scheduler.is_initialized():
            await octobot_node.scheduler.initialize_scheduler()
            await internal_trading_signals.subscribe_internal_trading_signal_consumer()

    def _sync_config(self):
        defaults = self.get_default_value()
        updated_config = {}
        if not self.node_api_url:
            self.node_api_url = defaults[services_constants.NODE_API_URL]
            updated_config[services_constants.NODE_API_URL] = self.node_api_url
        if not self.node_sqlite_file:
            self.node_sqlite_file = defaults[services_constants.NODE_SQLITE_FILE]
            updated_config[services_constants.NODE_SQLITE_FILE] = self.node_sqlite_file
        if self.node_redis_url is None:
            self.node_redis_url = defaults[services_constants.NODE_REDIS_URL]
            updated_config[services_constants.NODE_REDIS_URL] = self.node_redis_url
        if not self.backend_cors_origins:
            self.backend_cors_origins = defaults[services_constants.BACKEND_CORS_ALLOWED_ORIGINS]
            updated_config[services_constants.BACKEND_CORS_ALLOWED_ORIGINS] = self.backend_cors_origins

        if updated_config:
            self.save_service_config(services_constants.CONFIG_NODE_API, updated_config, update=True)

    def _get_default_node_api_url(self):
        port = self._get_node_api_server_port()
        return f"http://{network_module.LOCAL_HOST_IP}:{port}"

    def _get_node_api_server_port(self) -> str:
        try:
            return os.getenv(
                services_constants.ENV_NODE_API_PORT,
                self.config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(services_constants.CONFIG_NODE_API, {}).get(
                    services_constants.CONFIG_NODE_API_PORT, services_constants.DEFAULT_NODE_API_PORT
                ),
            )
        except (KeyError, ValueError, AttributeError) as err:
            return services_constants.DEFAULT_NODE_API_PORT

    def _get_node_api_server_url(self):
        port = self._get_node_api_server_port()
        try:
            return f"{os.getenv(services_constants.ENV_NODE_API_ADDRESS, socket.gethostbyname(socket.gethostname()))}:{port}"
        except OSError as err:
            self.logger.warning(
                f"Impossible to find local node web interface url, using default instead: {err} ({err.__class__.__name__})"
            )
        return f"{network_module.LOCAL_HOST_IP}:{port}"

    def get_successful_startup_message(self):
        return f"Node API interface successfully initialized and accessible at: http://{self._get_node_api_server_url()}.", True

    def get_bind_host(self):
        return os.getenv(services_constants.ENV_NODE_API_ADDRESS, services_constants.DEFAULT_NODE_API_IP)

    def get_bind_port(self):
        return int(self._get_node_api_server_port())

    def get_node_api_url(self):
        return self.node_api_url or self._get_default_node_api_url()

    def get_node_sqlite_file(self):
        return os.getenv(services_constants.ENV_NODE_SQLITE_FILE, self.node_sqlite_file)

    def get_node_postgres_url(self):
        return os.getenv(services_constants.ENV_NODE_POSTGRES_URL, self.node_redis_url)

    def get_backend_cors_origins(self):
        return os.getenv(services_constants.ENV_BACKEND_CORS_ALLOWED_ORIGINS, self.backend_cors_origins)

    def get_backend_cors_origin_regex(self):
        return os.getenv(services_constants.ENV_BACKEND_CORS_ORIGIN_REGEX, "")

    def get_node_external_host(self):
        return os.getenv(services_constants.ENV_NODE_EXTERNAL_HOST, self.node_external_host)

    def set_node_external_host(self, value):
        self.node_external_host = value or None
        self.save_service_config(
            services_constants.CONFIG_NODE_API,
            {services_constants.NODE_EXTERNAL_HOST: self.node_external_host},
            update=True,
        )

    def _register_mirror_context_provider(self):
        """Tell the mirror how to resolve a wallet's key, sync URL and enabled
        collections. Returning None is what keeps a node that cannot (or must
        not) mirror from ever writing."""
        try:
            import octobot.community.authentication as community_authentication
            import octobot.community.identifiers_provider as identifiers_provider
            import octobot_sync.mirror.service as mirror_service

            def resolve(user_id):
                if not self.get_cloud_sync_enabled():
                    return None
                wallet = community_authentication.CommunityAuthentication.instance(
                ).get_wallet_by_user_id(user_id)
                if wallet is None or not wallet.private_key:
                    return None
                sync_url = identifiers_provider.IdentifiersProvider.SYNC_SERVER_URL
                if not sync_url:
                    return None
                return mirror_service.MirrorContext(
                    private_key=wallet.private_key,
                    sync_url=sync_url,
                    enabled_collection_ids=self.get_cloud_sync_collections(),
                )

            mirror_service.MirrorService.instance().set_context_provider(resolve)
        except ImportError:
            # starfish-replica is a full-install dependency; a slim install
            # simply does not mirror.
            pass

    def get_cloud_sync_enabled(self):
        return bool(self.cloud_sync_enabled)

    def set_cloud_sync_enabled(self, value):
        enabled = bool(value)
        self.cloud_sync_enabled = enabled
        update = {services_constants.CLOUD_SYNC_ENABLED: enabled}
        # Mirrors the mobile app's setCloudSyncEnabled(true) behavior: turning cloud
        # sync ON always re-seeds the collection selection to the default set, rather
        # than restoring whatever was last selected, so re-enabling after a disable
        # gives a predictable, reviewable starting point instead of silently
        # resurrecting an old configuration. Turning it OFF leaves the collection
        # selection untouched.
        if enabled:
            self.cloud_sync_collections = list(services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS)
            update[services_constants.CLOUD_SYNC_COLLECTIONS] = self.cloud_sync_collections
        self.save_service_config(services_constants.CONFIG_NODE_API, update, update=True)
        self._reconcile_mirror()

    def get_cloud_sync_collections(self):
        # `is None` on purpose, not a truthy `or`: an explicitly-set empty list (the
        # user disabled every collection) must stay empty, not silently revive the
        # default set just because `[]` is falsy.
        if self.cloud_sync_collections is None:
            return list(services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS)
        return list(self.cloud_sync_collections)

    def set_cloud_sync_collections(self, collections):
        # Defense in depth: user-accounts-auth (exchange credentials) is never a
        # configurable mirror collection, at any layer — the web UI's "Configure"
        # modal never offers it as an option, and this is the second, independent
        # check that rejects it even if a client were modified to send it anyway.
        if services_constants.CLOUD_SYNC_FORBIDDEN_COLLECTION in collections:
            raise ValueError(
                f"{services_constants.CLOUD_SYNC_FORBIDDEN_COLLECTION} can never be a "
                f"cloud-sync collection"
            )
        self.cloud_sync_collections = list(dict.fromkeys(collections))  # de-duplicate, preserve order
        self.save_service_config(
            services_constants.CONFIG_NODE_API,
            {services_constants.CLOUD_SYNC_COLLECTIONS: self.cloud_sync_collections},
            update=True,
        )
        self._reconcile_mirror()

    def _reconcile_mirror(self):
        """Re-mirror after a cloud-sync settings change, for every wallet with
        a live scheduler. Fire-and-forget: a settings write must not fail
        because the mirror did."""
        try:
            import asyncio

            import octobot_sync.mirror.service as mirror_service

            service = mirror_service.MirrorService.instance()
            loop = asyncio.get_running_loop()
            for user_id in service.mirroring_user_ids():
                loop.create_task(service.reconcile(user_id))
        except Exception:  # pylint: disable=broad-except
            pass
