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

from octobot_services.interfaces.util.web import open_in_background_browser


class TestOpenInBackgroundBrowser:
    def test_open_in_background_browser_is_importable_from_octobot_services(self):
        assert callable(open_in_background_browser)

    def test_open_in_background_browser_calls_webbrowser_open(self):
        with mock.patch("octobot_services.interfaces.util.web.webbrowser.open") as webbrowser_open_mock:
            open_in_background_browser("http://localhost:8000/app")
        webbrowser_open_mock.assert_called_once_with("http://localhost:8000/app")
