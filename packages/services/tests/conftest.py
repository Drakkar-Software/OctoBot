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

import os
import sys

import pytest

_OCTOBOT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_TESTS_ROOT = os.path.join(_OCTOBOT_ROOT, "tests")
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

from test_utils.journal_test_support import disabled_node_journal_environment


@pytest.fixture(autouse=True)
def disable_node_journal():
    with disabled_node_journal_environment():
        yield
