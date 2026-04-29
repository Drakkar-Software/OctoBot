#  Drakkar-Software OctoBot-Tentacles-Manager
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

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.tentacle_explorer as tentacle_explorer


class _DummyTentacleClass:
    pass


def _write_tentacle_metadata_file(directory: str) -> None:
    metadata_path = os.path.join(directory, constants.TENTACLE_METADATA)
    with open(metadata_path, "w", encoding="utf-8") as metadata_file:
        metadata_file.write("{}")


def _ensure_tentacle_type_with_metadata_nested_under(root: str, type_folder_name: str) -> str:
    """
    Make ``type_folder_name`` a discovered tentacle type: one direct child folder
    must contain ``metadata.json`` (see _has_tentacle_in_direct_sub_directories).
    """
    type_dir = os.path.join(root, type_folder_name)
    marker = os.path.join(type_dir, "_type_marker_tentacle")
    os.makedirs(marker, exist_ok=True)
    _write_tentacle_metadata_file(marker)
    return type_dir


def _add_tentacle_folders(tentacle_type_dir: str, *tentacle_folder_names: str) -> None:
    for entry_name in tentacle_folder_names:
        os.makedirs(os.path.join(tentacle_type_dir, entry_name), exist_ok=True)


class TestParseAllTentacles:
    def test_tentacle_names_are_sorted_regardless_of_filesystem_entry_order(
        self, tmp_path, monkeypatch
    ):
        # Avoid interference from any tentacles registered elsewhere in the test session.
        monkeypatch.setattr(
            tentacle_explorer, "_extra_tentacle_data_by_name", {}
        )
        services_dir = _ensure_tentacle_type_with_metadata_nested_under(
            str(tmp_path), "Services"
        )
        # Intentional non-alphabetic creation order; result must be sorted by name.
        _add_tentacle_folders(services_dir, "zebra", "mike", "charlie")
        names = [tentacle.name for tentacle in tentacle_explorer._parse_all_tentacles(str(tmp_path))]
        expected_names = sorted(names)
        assert names == expected_names
        assert names == [
            "_type_marker_tentacle",
            "charlie",
            "mike",
            "zebra",
        ]

    def test_merges_extra_registered_tentacles_and_sorts_by_name(
        self, tmp_path, monkeypatch
    ):
        extra = {}
        monkeypatch.setattr(
            tentacle_explorer, "_extra_tentacle_data_by_name", extra
        )
        services_dir = _ensure_tentacle_type_with_metadata_nested_under(
            str(tmp_path), "Services"
        )
        _add_tentacle_folders(services_dir, "mountain", "ant")
        # Register names that interleave with filesystem names when unsorted.
        tentacle_explorer.register_extra_tentacle_data("zebra", "Other", _DummyTentacleClass)
        tentacle_explorer.register_extra_tentacle_data("alpha", "Other", _DummyTentacleClass)
        try:
            names = [
                t.name
                for t in tentacle_explorer._parse_all_tentacles(str(tmp_path))
            ]
            assert names == sorted(names)
            assert names == [
                "_type_marker_tentacle",
                "alpha",
                "ant",
                "mountain",
                "zebra",
            ]
        finally:
            extra.clear()
