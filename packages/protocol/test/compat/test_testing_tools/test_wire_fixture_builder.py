#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Unit tests for build_wire_fixtures.py helpers and promote workflows (tmp_path only).

import json
import pathlib

import mock
import pytest

import scripts.build_wire_fixtures as build_wire_fixtures
import scripts.lib.openapi_compat_lib as openapi_compat_lib
import octobot_protocol.models as protocol_models


class TestSchemaNameFixtureFilenameMapping:
    def test_schema_name_to_fixture_filename(self):
        assert (
            build_wire_fixtures._schema_name_to_fixture_filename("StrategiesState")
            == "strategies_state.json"
        )

    def test_fixture_filename_to_schema_name(self):
        assert build_wire_fixtures._fixture_filename_to_schema_name("strategies_state.json") == "StrategiesState"

    def test_roundtrip_for_state_envelope_names(self):
        for schema_name in openapi_compat_lib.STATE_ENVELOPE_SCHEMA_NAMES:
            filename = build_wire_fixtures._schema_name_to_fixture_filename(schema_name)
            assert build_wire_fixtures._fixture_filename_to_schema_name(filename) == schema_name


class TestNormalizeJsonText:
    def test_sort_keys_indent_and_trailing_newline(self):
        payload = {"b": 2, "a": 1}
        normalized = build_wire_fixtures._normalize_json_text(payload)
        assert normalized == '{\n  "a": 1,\n  "b": 2\n}\n'

    def test_stable_bytes_for_check_comparison(self):
        first = build_wire_fixtures._normalize_json_text({"z": 1, "m": 2})
        second = build_wire_fixtures._normalize_json_text({"m": 2, "z": 1})
        assert first == second


class TestCheckGeneratedFixtures:
    def test_all_match_returns_empty_list(self, tmp_path: pathlib.Path):
        version_dir = tmp_path / "v1.0.0"
        version_dir.mkdir()
        generated = {"foo.json": {"a": 1}}
        build_wire_fixtures._write_fixture_file(version_dir / "foo.json", generated["foo.json"])
        mismatches = build_wire_fixtures._check_generated_fixtures(version_dir, generated)
        assert not mismatches

    def test_missing_fixture_reported(self, tmp_path: pathlib.Path):
        version_dir = tmp_path / "v1.0.0"
        version_dir.mkdir()
        generated = {"missing.json": {"a": 1}}
        mismatches = build_wire_fixtures._check_generated_fixtures(version_dir, generated)
        assert mismatches == ["Missing fixture: missing.json"]

    def test_stale_fixture_reported(self, tmp_path: pathlib.Path):
        version_dir = tmp_path / "v1.0.0"
        version_dir.mkdir()
        build_wire_fixtures._write_fixture_file(version_dir / "foo.json", {"a": 1})
        generated = {"foo.json": {"a": 2}}
        mismatches = build_wire_fixtures._check_generated_fixtures(version_dir, generated)
        assert mismatches == ["Stale fixture: foo.json"]


class TestPromoteVersion:
    def _wire_root(self, tmp_path: pathlib.Path) -> pathlib.Path:
        wire_dir = tmp_path / "wire"
        wire_dir.mkdir()
        return wire_dir

    def test_promote_archives_active_version_and_regenerates(self, tmp_path: pathlib.Path):
        wire_dir = self._wire_root(tmp_path)
        version_dir = wire_dir / "v1.0.0"
        version_dir.mkdir()
        stale_fixture = version_dir / "marker.json"
        stale_fixture.write_text('{"marker": true}\n', encoding="utf-8")
        openapi_compat_lib.write_json(wire_dir / "active_version.json", {"version": "1.0.0"})

        with mock.patch.object(openapi_compat_lib, "wire_root_dir", return_value=wire_dir):
            build_wire_fixtures._promote_version("2.0.0", openapi_compat_lib, protocol_models)

        archive_dir = wire_dir / "legacy" / "v1.0.0"
        assert archive_dir.is_dir()
        assert (archive_dir / "marker.json").is_file()
        active_payload = openapi_compat_lib.read_json(wire_dir / "active_version.json")
        assert active_payload["version"] == "2.0.0"
        new_version_dir = wire_dir / "v2.0.0"
        assert new_version_dir.is_dir()
        regenerated_files = list(new_version_dir.rglob("*.json"))
        assert regenerated_files
        assert not (new_version_dir / "marker.json").exists()

    def test_promote_fails_when_legacy_archive_already_exists(self, tmp_path: pathlib.Path):
        wire_dir = self._wire_root(tmp_path)
        version_dir = wire_dir / "v1.0.0"
        version_dir.mkdir()
        archive_dir = wire_dir / "legacy" / "v1.0.0"
        archive_dir.mkdir(parents=True)
        (archive_dir / "existing.json").write_text("{}", encoding="utf-8")
        openapi_compat_lib.write_json(wire_dir / "active_version.json", {"version": "1.0.0"})

        with mock.patch.object(openapi_compat_lib, "wire_root_dir", return_value=wire_dir):
            with pytest.raises(RuntimeError, match="Legacy archive already exists"):
                build_wire_fixtures._promote_version("2.0.0", openapi_compat_lib, protocol_models)


class TestPromoteFiles:
    def test_copies_fixture_to_ad_hoc_with_flattened_name(self, tmp_path: pathlib.Path):
        wire_dir = tmp_path / "wire"
        version_dir = wire_dir / "v1.0.0" / "user_actions"
        version_dir.mkdir(parents=True)
        source_fixture = version_dir / "foo.json"
        source_payload = {"id": "user-action-foo"}
        source_fixture.write_text(json.dumps(source_payload), encoding="utf-8")
        openapi_compat_lib.write_json(wire_dir / "active_version.json", {"version": "1.0.0"})

        with mock.patch.object(openapi_compat_lib, "wire_root_dir", return_value=wire_dir):
            build_wire_fixtures._promote_files(["user_actions/foo.json"], openapi_compat_lib)

        destination = wire_dir / "legacy" / "ad_hoc" / "user_actions__foo.json"
        assert destination.is_file()
        assert openapi_compat_lib.read_json(destination) == source_payload

    def test_missing_source_raises(self, tmp_path: pathlib.Path):
        wire_dir = tmp_path / "wire"
        (wire_dir / "v1.0.0").mkdir(parents=True)
        openapi_compat_lib.write_json(wire_dir / "active_version.json", {"version": "1.0.0"})

        with mock.patch.object(openapi_compat_lib, "wire_root_dir", return_value=wire_dir):
            with pytest.raises(RuntimeError, match="Fixture not found for promote-files"):
                build_wire_fixtures._promote_files(["missing.json"], openapi_compat_lib)
