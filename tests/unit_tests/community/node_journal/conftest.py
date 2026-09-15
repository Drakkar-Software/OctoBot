#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import pytest

pytest_plugins = ("test_utils.journal_integration_fixtures",)


@pytest.fixture(autouse=True)
def re_enable_node_journal(node_journal_enabled):
    yield


@pytest.fixture(autouse=True)
def autouse_isolated_journal_environment(isolated_journal_environment):
    yield


@pytest.fixture(autouse=True)
def autouse_surface_journal_errors(surface_journal_errors):
    yield
