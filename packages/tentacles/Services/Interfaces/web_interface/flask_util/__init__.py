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

from tentacles.Services.Interfaces.web_interface.flask_util import content_types_management
from tentacles.Services.Interfaces.web_interface.flask_util.content_types_management import (
    init_content_types,
)

from tentacles.Services.Interfaces.web_interface.flask_util import context_processor
from tentacles.Services.Interfaces.web_interface.flask_util.context_processor import (
    register_context_processor,
)

from tentacles.Services.Interfaces.web_interface.flask_util import file_services
from tentacles.Services.Interfaces.web_interface.flask_util.file_services import (
    send_and_remove_file,
)

from tentacles.Services.Interfaces.web_interface.flask_util import template_filters
from tentacles.Services.Interfaces.web_interface.flask_util.template_filters import (
    register_template_filters,
)

from tentacles.Services.Interfaces.web_interface.flask_util import json_provider
from tentacles.Services.Interfaces.web_interface.flask_util.json_provider import (
    FloatDecimalJSONProvider,
)

from tentacles.Services.Interfaces.web_interface.flask_util import cors
from tentacles.Services.Interfaces.web_interface.flask_util.cors import (
    get_user_defined_cors_allowed_origins,
)


from tentacles.Services.Interfaces.web_interface.flask_util import browsing_data_provider
from tentacles.Services.Interfaces.web_interface.flask_util.browsing_data_provider import (
    BrowsingDataProvider,
)

__all__ = [
    "init_content_types",
    "register_context_processor",
    "send_and_remove_file",
    "register_template_filters",
    "FloatDecimalJSONProvider",
    "get_user_defined_cors_allowed_origins",
    "BrowsingDataProvider",
]
