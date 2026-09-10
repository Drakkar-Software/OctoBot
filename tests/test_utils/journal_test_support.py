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

import contextlib
import os

import mock

import octobot.community.node_journal.constants as journal_constants


@contextlib.contextmanager
def disabled_node_journal_environment():
    with mock.patch.dict(os.environ, {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"}):
        yield


@contextlib.contextmanager
def enabled_node_journal_environment():
    enabled_environ = {
        environment_key: environment_value
        for environment_key, environment_value in os.environ.items()
        if environment_key != journal_constants.JOURNAL_ENABLED_ENV_VAR
    }
    with mock.patch.dict(os.environ, enabled_environ, clear=True):
        yield
