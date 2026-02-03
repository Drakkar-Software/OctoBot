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
import typing
import octobot_services.constants as services_constants
import octobot_services.services as services


class LunarCrushService(services.AbstractService):
    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def has_required_configuration(self):
        return services_constants.CONFIG_CATEGORY_SERVICES in self.config \
               and services_constants.CONFIG_LUNARCRUSH in self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(
            self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_LUNARCRUSH])

    def get_endpoint(self) -> None:
        return None

    def get_type(self) -> None:
        return services_constants.CONFIG_LUNARCRUSH

    async def prepare(self) -> None:
        pass

    def get_successful_startup_message(self):
        return "", True

    def get_fields_description(self):
        return {
            services_constants.CONFIG_LUNARCRUSH_API_KEY: "Api key.",
         }

    def get_default_value(self):
        return {
            services_constants.CONFIG_LUNARCRUSH_API_KEY: ""
        }

    def get_required_config(self):
        return [services_constants.CONFIG_LUNARCRUSH_API_KEY]

    def get_authentication_headers(self) -> typing.Optional[dict]:
        api_key = self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(services_constants.CONFIG_LUNARCRUSH, {}).get(services_constants.CONFIG_LUNARCRUSH_API_KEY, None)
        return {
            "Authorization": f"Bearer {api_key}"
        } if api_key else None
