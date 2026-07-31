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

import mock
import pytest

import octobot_services.constants as services_constants
import octobot_services.errors as services_errors
import octobot_services.services.abstract_service as abstract_service


class _TestService(abstract_service.AbstractService):
    @staticmethod
    def is_setup_correctly(config):
        return True

    def has_required_configuration(self):
        return True

    def get_endpoint(self) -> None:
        return None

    def get_type(self) -> None:
        return "test-service"

    async def prepare(self) -> None:
        pass

    def get_successful_startup_message(self):
        return "", True


class TestSaveServiceConfig:
    def test_replaces_with_injected_edited_config(self):
        service = _TestService()
        service.edited_config = mock.Mock(config={services_constants.CONFIG_CATEGORY_SERVICES: {}})
        service.save_service_config("key", {"a": 1})
        assert service.edited_config.config[services_constants.CONFIG_CATEGORY_SERVICES]["key"] == {"a": 1}
        service.edited_config.save.assert_called_once()

    def test_updates_existing_key_with_injected_edited_config(self):
        service = _TestService()
        service.edited_config = mock.Mock(
            config={services_constants.CONFIG_CATEGORY_SERVICES: {"key": {"a": 1}}}
        )
        service.save_service_config("key", {"b": 2}, update=True)
        assert service.edited_config.config[services_constants.CONFIG_CATEGORY_SERVICES]["key"] == {
            "a": 1, "b": 2
        }

    def test_creates_missing_services_category(self):
        # a config that never went through ServiceFactory._perform_checkup() can lack the whole
        # "services" category
        service = _TestService()
        service.edited_config = mock.Mock(config={})
        service.save_service_config("key", {"a": 1})
        assert service.edited_config.config[services_constants.CONFIG_CATEGORY_SERVICES]["key"] == {"a": 1}

    def test_raises_typed_error_when_edited_config_is_unset(self):
        # reproduces the reported crash: edited_config was never injected by ServiceFactory (eg because
        # the owning interface's initialize() failed)
        service = _TestService()
        assert service.edited_config is None
        with pytest.raises(services_errors.ServiceConfigurationError):
            service.save_service_config("key", {"a": 1})
