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
import octobot_services.constants as services_constants
import octobot_services.services as services


class AlternativeMeService(services.AbstractService):
    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def has_required_configuration(self):
        return True

    def get_endpoint(self) -> None:
        return None

    def get_type(self) -> None:
        return services_constants.CONFIG_ALTERNATIVE_ME

    async def prepare(self) -> None:
        pass

    def get_successful_startup_message(self):
        return "", True
