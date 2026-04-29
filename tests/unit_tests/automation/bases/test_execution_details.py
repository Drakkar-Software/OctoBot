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

from octobot.automation.bases.execution_details import ExecutionDetails


class TestExecutionDetails:
    def test_init_with_all_params(self):
        details = ExecutionDetails(
            timestamp=123.45,
            description="Test execution",
            source=None
        )
        assert details.timestamp == 123.45
        assert details.description == "Test execution"
        assert details.source is None

    def test_init_with_none_description(self):
        details = ExecutionDetails(timestamp=0.0, description=None, source=None)
        assert details.timestamp == 0.0
        assert details.description is None
        assert details.source is None

    def test_str_with_description(self):
        details = ExecutionDetails(100.0, "Custom description", None)
        assert str(details) == "Custom description"

    def test_str_without_description(self):
        details = ExecutionDetails(100.0, None, None)
        assert str(details) == "Execution at 100.0"

    def test_repr_equals_str(self):
        details = ExecutionDetails(50.0, "Test", None)
        assert repr(details) == str(details)

    def test_get_initial_execution_details_no_source(self):
        details = ExecutionDetails(1.0, "Root", None)
        result = details.get_initial_execution_details()
        assert result is details

    def test_get_initial_execution_details_with_source_chain(self):
        root = ExecutionDetails(1.0, "Root", None)
        child = ExecutionDetails(2.0, "Child", None)
        grandchild = ExecutionDetails(3.0, "Grandchild", None)
        child.source = root
        grandchild.source = child
        result = grandchild.get_initial_execution_details()
        assert result is root