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


class WebInterfaceTab:
    def __init__(
        self, identifier, route, display_name, location, requires_open_source_package=False
    ):
        self.identifier = identifier
        self.route = route
        self.display_name = display_name
        self.location = location
        self.requires_open_source_package = requires_open_source_package

    def is_available(self, has_open_source_package):
        if not self.requires_open_source_package:
            # is available in general
            return True
        if self.requires_open_source_package and has_open_source_package:
            # is available if has_open_source_package
            return True
        # is not available
        return False
