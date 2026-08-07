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

import mock
import pytest

import octobot_services.constants as services_constants
import octobot_services.errors as services_errors
import tentacles.Services.Services_bases.node_api_service.node_api as node_api_service_module


class TestNodeApiServiceCloudSyncEnabled:
    def test_defaults_to_disabled(self):
        service = node_api_service_module.NodeApiService()
        assert service.get_cloud_sync_enabled() is False

    def test_set_cloud_sync_enabled_true_persists_and_reseeds_default_collections(self):
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            service.set_cloud_sync_enabled(True)
        save_mock.assert_called_once_with(
            services_constants.CONFIG_NODE_API,
            {
                services_constants.CLOUD_SYNC_ENABLED: True,
                services_constants.CLOUD_SYNC_COLLECTIONS: list(
                    services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS
                ),
            },
            update=True,
        )
        assert service.get_cloud_sync_enabled() is True
        assert service.get_cloud_sync_collections() == list(
            services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS
        )

    def test_set_cloud_sync_enabled_true_reseeds_defaults_even_if_previously_narrowed(self):
        # Mirrors mobile2's setCloudSyncEnabled(true) contract: re-enabling always
        # resets to the reviewable default set rather than restoring whatever was
        # left selected from a prior session.
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config"):
            service.set_cloud_sync_collections(["user-accounts"])
            service.set_cloud_sync_enabled(True)
        assert service.get_cloud_sync_collections() == list(
            services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS
        )

    def test_set_cloud_sync_enabled_false_persists_without_touching_collections(self):
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            service.set_cloud_sync_collections(["user-accounts", "user-settings"])
            save_mock.reset_mock()
            service.set_cloud_sync_enabled(False)
        save_mock.assert_called_once_with(
            services_constants.CONFIG_NODE_API,
            {services_constants.CLOUD_SYNC_ENABLED: False},
            update=True,
        )
        assert service.get_cloud_sync_enabled() is False
        assert service.get_cloud_sync_collections() == ["user-accounts", "user-settings"]

    def test_set_cloud_sync_enabled_without_edited_config_raises(self):
        service = node_api_service_module.NodeApiService()
        assert service.edited_config is None
        with pytest.raises(services_errors.ServiceConfigurationError):
            service.set_cloud_sync_enabled(True)


class TestNodeApiServiceCloudSyncCollections:
    def test_defaults_to_the_default_collection_set(self):
        service = node_api_service_module.NodeApiService()
        assert service.get_cloud_sync_collections() == list(
            services_constants.DEFAULT_CLOUD_SYNC_COLLECTIONS
        )

    def test_set_cloud_sync_collections_persists_and_updates_getter(self):
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            service.set_cloud_sync_collections(["user-accounts", "user-accounts-trading"])
        save_mock.assert_called_once_with(
            services_constants.CONFIG_NODE_API,
            {
                services_constants.CLOUD_SYNC_COLLECTIONS: [
                    "user-accounts",
                    "user-accounts-trading",
                ]
            },
            update=True,
        )
        assert service.get_cloud_sync_collections() == ["user-accounts", "user-accounts-trading"]

    def test_set_cloud_sync_collections_de_duplicates_preserving_order(self):
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config"):
            service.set_cloud_sync_collections(["user-accounts", "user-data", "user-accounts"])
        assert service.get_cloud_sync_collections() == ["user-accounts", "user-data"]

    def test_set_cloud_sync_collections_empty_list_clears_selection(self):
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config"):
            service.set_cloud_sync_collections([])
        assert service.get_cloud_sync_collections() == []

    def test_set_cloud_sync_collections_rejects_accounts_auth(self):
        # The defense-in-depth check: user-accounts-auth (exchange credentials) must
        # never be settable as a cloud-sync collection, independent of whether the
        # web UI ever offers it as an option.
        service = node_api_service_module.NodeApiService()
        with mock.patch.object(service, "save_service_config") as save_mock:
            with pytest.raises(ValueError):
                service.set_cloud_sync_collections(
                    ["user-accounts", services_constants.CLOUD_SYNC_FORBIDDEN_COLLECTION]
                )
        save_mock.assert_not_called()
        # the rejected call must not have partially applied
        assert services_constants.CLOUD_SYNC_FORBIDDEN_COLLECTION not in (
            service.get_cloud_sync_collections()
        )

    def test_set_cloud_sync_collections_without_edited_config_raises(self):
        service = node_api_service_module.NodeApiService()
        assert service.edited_config is None
        with pytest.raises(services_errors.ServiceConfigurationError):
            service.set_cloud_sync_collections(["user-accounts"])
