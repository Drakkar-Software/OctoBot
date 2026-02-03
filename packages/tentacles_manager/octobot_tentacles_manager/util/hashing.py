#  Drakkar-Software OctoBot-Commons
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
import inspect
import hashlib

import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration


def get_tentacles_code_hash(tentacles: list) -> str:
    full_code = ""
    for linked_tentacle in tentacles:
        code_location = (
            linked_tentacle.get_script()
            if (
                hasattr(linked_tentacle, "get_script")
                and linked_tentacle.TRADING_SCRIPT_MODULE
            )
            else linked_tentacle.__class__
        )
        full_code = f"{full_code}{inspect.getsource(code_location)}"
    return hashlib.sha256(full_code.encode()).hexdigest()


def get_tentacles_config_hash(identifying_tentacles: list, tentacles_setup_config) -> str:
    full_config = ""
    for linked_tentacle in identifying_tentacles:
        config = linked_tentacle.specific_config if hasattr(linked_tentacle, "specific_config") \
            and linked_tentacle.specific_config else \
            tentacle_configuration.get_config(tentacles_setup_config, linked_tentacle.__class__)
        full_config = f"{full_config}{json.dumps(config)}"
    return hashlib.sha256(full_config.encode()).hexdigest()
