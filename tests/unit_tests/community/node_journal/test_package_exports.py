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

import octobot.community.node_journal as node_journal_module
import octobot.community.node_journal.recording as journal_recording_module


class TestPackageExports:
    def test_every_all_name_resolves_on_package(self):
        for export_name in node_journal_module.__all__:
            assert hasattr(node_journal_module, export_name), export_name

    def test_internal_modules_are_not_package_attributes(self):
        assert not hasattr(node_journal_module, "journal_state")
        assert not hasattr(node_journal_module, "journal_store")


class TestRecordAccountDeletedExport:
    def test_package_export_is_recording_function(self):
        assert node_journal_module.record_account_deleted is journal_recording_module.record_account_deleted
