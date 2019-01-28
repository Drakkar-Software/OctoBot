#  Drakkar-Software OctoBot
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

import json

from . import api
from config import PROJECT_NAME, LONG_VERSION, EXTERNAL_RESOURCE_CURRENT_USER_FORM, \
    EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS
from tools import external_resources_manager


@api.route("/version")
def version():
    return json.dumps(f"{PROJECT_NAME} {LONG_VERSION}")


@api.route("/user_feedback")
def user_feedback():
    return json.dumps(external_resources_manager.get_external_resource(EXTERNAL_RESOURCE_CURRENT_USER_FORM,
                                                                       catch_exception=True))


@api.route("/announcements")
def announcements():
    return json.dumps(external_resources_manager.get_external_resource(EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS,
                                                                       catch_exception=True))
