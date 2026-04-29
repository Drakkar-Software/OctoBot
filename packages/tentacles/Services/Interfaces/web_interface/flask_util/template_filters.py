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


def register_template_filters(app):
    # should only be called after app configuration

    @app.template_filter()
    def is_dict(value):
        return isinstance(value, dict)

    @app.template_filter()
    def is_list(value):
        return isinstance(value, list)

    @app.template_filter()
    def is_bool(value):
        return isinstance(value, bool)
