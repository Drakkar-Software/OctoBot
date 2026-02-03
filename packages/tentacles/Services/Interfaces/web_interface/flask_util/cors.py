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
import os

import octobot_services.constants as services_constants


def get_user_defined_cors_allowed_origins():
    # Set services_constants.ENV_CORS_ALLOWED_ORIGINS env variable add stricter cors rules allowed origins
    # example: http://localhost:5000
    # Note: you can specify multiple origins using comma as a separator, ex: http://localhost:5000,https://a.com
    cors_allowed_origins = os.getenv(services_constants.ENV_CORS_ALLOWED_ORIGINS, "*")
    if "," in cors_allowed_origins:
        return [origin.strip() for origin in cors_allowed_origins.split(",")]
    return cors_allowed_origins
